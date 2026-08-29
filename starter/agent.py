from __future__ import annotations

import re
from pathlib import Path

from starter.retrieval import HybridSearcher
from starter.retrieval.query_builder import extract_constraint_phrases

TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
}

ATTRIBUTES = ("category", "material", "color", "size", "style", "brand", "budget", "feature", "use_case")
OVERRIDE_MARKERS = ("actually", "instead", "never mind", "nevermind", "forget that", "change of plans", "i meant", "rather")
BUYING_MARKERS = ("key requirement is:", "what matters is:", "what i need is:")
BROWSING_MARKER = "still exploring"
BOUNDARY_RE = re.compile(r"don'?t have (?:a|an) (?:preference|additional preference) for\s+(\w+)", re.I)
BUDGET_RE = re.compile(r"(?:budget around|under|<=|\$)\s*\$?\s*([\d.]+)", re.I)

ATTRIBUTE_TERMS = {
    "category": ("looking for", "need", "want", "shoes", "dress", "shirt", "bag", "jewelry", "boots"),
    "material": ("leather", "cotton", "wool", "linen", "suede", "silk", "denim", "material"),
    "color": ("black", "white", "blue", "red", "green", "brown", "pink", "grey", "gray", "color"),
    "size": ("size", "small", "medium", "large", " xs ", " s ", " m ", " l ", " xl "),
    "style": ("style", "casual", "formal", "vintage", "minimalist", "classic", "sporty"),
    "brand": ("brand",),
    "budget": ("$", "budget", "under", "less than", "cheap", "affordable", "price"),
    "feature": ("feature", "waterproof", "comfortable", "durable", "pockets", "slip resistant"),
    "use_case": ("for work", "for running", "for hiking", "for a wedding", "for travel", "gift", "occasion"),
}


def _terms(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    ]


class Agent:
    """Pillar II dialog + Pillar I HybridSearcher retrieval."""

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self._searcher = HybridSearcher(self.catalog_path)
        self._sessions: dict[str, dict] = {}

    def reset(self, session_id: str, user_profile: dict) -> None:
        self._sessions[session_id] = {
            "profile": user_profile or {},
            "mode": "browsing",
            "slots": {attribute: None for attribute in ATTRIBUTES},
            "slot_status": {attribute: "unknown" for attribute in ATTRIBUTES},
            "unconstrained": set(),
            "asked": [],
            "history": [],
            "override_pending": False,
            "retrieval_feedback": {},
        }

    def update_retrieval_feedback(self, session_id: str, feedback: dict) -> None:
        if session_id not in self._sessions:
            raise RuntimeError("reset must be called before updating feedback")
        self._sessions[session_id]["retrieval_feedback"] = dict(feedback or {})

    def _extract_updates(self, message: str) -> dict[str, str]:
        text = " " + message.lower() + " "
        updates: dict[str, str] = {}
        for attribute, terms in ATTRIBUTE_TERMS.items():
            found = next((term.strip() for term in terms if term in text), None)
            if found:
                updates[attribute] = message.strip()
        return updates

    def _apply_message(self, state: dict, message: str) -> None:
        lowered = message.lower()
        override = any(marker in lowered for marker in OVERRIDE_MARKERS)
        no_preference = any(phrase in lowered for phrase in (
            "no preference", "anything is fine", "you decide", "doesn't matter",
            "does not matter", "i'm flexible", "im flexible",
        ))
        boundary = BOUNDARY_RE.search(message)
        updates = self._extract_updates(message)

        if override:
            for attribute in state["slots"]:
                state["slots"][attribute] = None
            state["unconstrained"].clear()
            state["asked"].clear()
            state["override_pending"] = True

        for attribute, value in updates.items():
            if attribute in state["slots"]:
                state["slots"][attribute] = value
                state["slot_status"][attribute] = "confirmed"
                state["unconstrained"].discard(attribute)

        if boundary:
            attribute = boundary.group(1).strip().lower().replace(" ", "_")
            if attribute in state["slots"]:
                state["slots"][attribute] = None
                state["slot_status"][attribute] = "unconstrained"
                state["unconstrained"].add(attribute)

        if no_preference and state["asked"]:
            attribute = state["asked"][-1]
            if attribute in state["slots"]:
                state["slots"][attribute] = None
                state["slot_status"][attribute] = "unconstrained"
                state["unconstrained"].add(attribute)

        state["history"].append(message)
        state["mode"] = _detect_mode(state)

    def _choose_question(self, state: dict, turn: int) -> str | None:
        feedback = state.get("retrieval_feedback", {})
        overloaded = bool(feedback.get("overloaded")) or int(feedback.get("candidate_count", 0) or 0) > 100
        if turn >= 8:
            return None
        if state.get("override_pending"):
            state["asked"].append("other")
            state["override_pending"] = False
            return "What is the most important requirement for this new request?"

        slots = state["slots"]
        missing = feedback.get("missing_attributes")
        priority = tuple(attribute for attribute in missing if attribute in ATTRIBUTES) if isinstance(missing, list) else ()
        priority += ("category", "use_case", "budget", "size", "color", "material", "style", "brand", "feature")
        for attribute in priority:
            if slots[attribute] is None and attribute not in state["unconstrained"] and attribute not in state["asked"]:
                if attribute == "category":
                    question = "What type of item are you looking for?"
                elif attribute == "use_case":
                    question = "What will you mainly use it for?"
                else:
                    question = f"Do you have a preference for {attribute}?"
                state["asked"].append(attribute)
                return question
        if overloaded:
            return None
        return None

    def _is_overgeneral(self, state: dict, message: str) -> bool:
        vague = (
            "something", "anything", "some options", "show me options",
            "surprise me", "not sure", "whatever", "just browsing",
        )
        known_slots = sum(value is not None for value in state["slots"].values())
        return known_slots == 0 and (len(_terms(message)) <= 4 or any(phrase in message.lower() for phrase in vague))

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
    ) -> dict:
        if session_id not in self._sessions:
            raise RuntimeError("reset must be called before respond")

        state = self._sessions[session_id]
        self._apply_message(state, user_message)
        state["overgeneral"] = self._is_overgeneral(state, user_message)

        result = self._searcher.search(
            query_text=" ".join(state["history"]),
            mode=state["mode"],
            filters=_to_filters(state),
            top_k=top_k,
        )
        state["retrieval_feedback"] = result.feedback

        question = self._choose_question(state, turn)
        recommendations = [{"parent_asin": asin} for asin in result.asins]
        return {
            "message": question or "Here are the closest matches I found.",
            "ask_attribute": state["asked"][-1] if question else None,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }


def _detect_mode(state: dict) -> str:
    history = " ".join(state["history"]).lower()
    if any(marker in history for marker in BUYING_MARKERS):
        return "buying"
    if BROWSING_MARKER in history:
        return "browsing"
    return state.get("mode", "browsing")


def _to_filters(state: dict) -> dict:
    filters: dict[str, object] = {
        "unconstrained": list(state["unconstrained"]),
        "asked": list(state["asked"]),
        "slot_status": dict(state["slot_status"]),
    }
    for attribute in ATTRIBUTES:
        value = state["slots"].get(attribute)
        if value is None:
            continue
        text = str(value)
        if attribute == "category":
            category = _category_from_message(text)
            if category:
                filters["category_tokens"] = [category]
        elif attribute == "budget":
            match = BUDGET_RE.search(text)
            if match:
                try:
                    filters["max_price"] = float(match.group(1))
                except ValueError:
                    pass
        else:
            phrases = _slot_filter_values(text)
            if phrases:
                filters[attribute] = phrases
    return filters


def _category_from_message(message: str) -> str:
    match = re.search(r"i'?m looking for\s+(.+?)(?:\.|,|$)", message, re.I)
    if match:
        category = match.group(1).strip(" .")
        if "still exploring" not in category.lower():
            return category
    return ""


def _slot_filter_values(raw: str) -> list[str]:
    phrases = extract_constraint_phrases(raw)
    if phrases:
        return phrases
    cleaned = re.sub(r"\s+", " ", raw).strip()
    if len(cleaned) <= 60:
        return [cleaned]
    return []
