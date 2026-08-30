"""FastAPI wrapper around starter.agent.Agent for the hackathon demo UI.

Run from the repository root:

    python3 -m uvicorn demo.server:app --host 127.0.0.1 --port 8000

Handlers are async so the in-memory SQLite FTS index stays on the startup
thread. FastAPI would otherwise run sync routes in a threadpool.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from evaluator.local_evaluator import (
    MAX_TURNS,
    TOP_K,
    customer_reply,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
    normalize_recommendations,
)
from starter.agent import Agent

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.jsonl"
PUBLIC_SET = ROOT / "data" / "public_set.jsonl"

BROWSING_TURNS = [
    "I'm looking for running shoes, but I'm still exploring.",
    "For that, what matters is: lightweight mesh upper; cushioned sole.",
    "For that, what matters is: budget around $60; good for daily training.",
]
BUYING_TURNS = [
    "I'm looking for women's running shoes. A key requirement is: breathable mesh upper.",
    "For that, what matters is: lightweight; suitable for road running.",
]

agent: Agent | None = None
catalog_ids: set[str] = set()
public_samples: dict[str, dict] = {}
# Demo overlay: turn counter and optional replay target (Agent keeps dialog state).
demo_sessions: dict[str, dict[str, Any]] = {}


def default_profile() -> dict:
    return {
        "preference_tags": ["material", "comfort", "fit"],
        "rating_style": "usually positive",
        "summary": "Prior purchases emphasize material, comfort, and fit.",
        "purchase_frequency": "3-4 prior purchases",
        "average_prior_rating": 4.8,
    }


def _require_agent() -> Agent:
    if agent is None:
        raise HTTPException(status_code=503, detail="Catalog index is still loading")
    return agent


def _store():
    return _require_agent().searcher._store


def _hydrate(asins: list[str], target_asin: str | None = None) -> list[dict]:
    store = _store()
    cards: list[dict] = []
    for rank, asin in enumerate(asins, start=1):
        meta = store.get(asin)
        cards.append(
            {
                "parent_asin": asin,
                "rank": rank,
                "title": meta.title if meta else asin,
                "store": meta.store if meta else "",
                "price": meta.price if meta else None,
                "average_rating": meta.average_rating if meta else None,
                "rating_number": meta.rating_number if meta else None,
                "categories": meta.categories if meta else "",
                "is_target": bool(target_asin and asin == target_asin),
            }
        )
    return cards


def _coarse_from_meta(categories: str) -> str:
    text = categories.replace("Clothing, Shoes & Jewelry", " ").strip()
    tokens = [part.strip() for part in text.replace(",", " ").split() if part.strip()]
    excluded = {"clothing", "shoes", "&", "jewelry", "and"}
    cleaned = [token for token in tokens if token.lower() not in excluded]
    if len(cleaned) >= 2:
        return f"{cleaned[-2]} {cleaned[-1]}"
    if cleaned:
        return cleaned[-1]
    return "clothing item"


def _product_dict(asin: str) -> dict:
    meta = _store().get(asin)
    if meta is None:
        return {"parent_asin": asin, "title": asin}
    return {
        "parent_asin": asin,
        "title": meta.title,
        "features": meta.features,
        "details": meta.details,
        "description": meta.description,
        "categories": meta.categories,
        "store": meta.store,
        "price": meta.price,
    }


def _ranked_asins(response: dict) -> list[str]:
    return normalize_recommendations(response.get("recommendations"), catalog_ids)


def _pack_turn(
    session_id: str,
    user_message: str,
    turn: int,
    response: dict,
    target_asin: str | None = None,
) -> dict:
    live = _require_agent()
    ranked = _ranked_asins(response)
    hit_rank = ranked.index(target_asin) + 1 if target_asin and target_asin in ranked else None
    state = live.get_dialog_state(session_id)
    overlay = demo_sessions.get(session_id, {})
    profile = overlay.get("profile") or live._sessions[session_id]["profile"]
    return {
        "session_id": session_id,
        "turn": turn,
        "user_message": user_message,
        "message": response.get("message") or "",
        "ask_attribute": response.get("ask_attribute"),
        "recommendations": _hydrate(ranked, target_asin),
        "dialog_state": state,
        "profile": profile,
        "usage": response.get("usage") or {"prompt_tokens": 0, "completion_tokens": 0},
        "target_asin": target_asin,
        "hit_rank": hit_rank,
    }


def _new_session(profile: dict, target_asin: str | None = None) -> str:
    live = _require_agent()
    session_id = uuid.uuid4().hex[:12]
    live.reset(session_id, profile)
    demo_sessions[session_id] = {"turn": 0, "profile": profile, "target_asin": target_asin}
    return session_id


def _run_messages(
    messages: list[str],
    profile: dict,
    target_asin: str | None = None,
) -> tuple[str, list[dict], int | None, int | None]:
    live = _require_agent()
    session_id = _new_session(profile, target_asin)
    packed: list[dict] = []
    hit_turn: int | None = None
    hit_rank: int | None = None
    for turn, message in enumerate(messages, start=1):
        response = live.respond(session_id, message, turn, TOP_K)
        row = _pack_turn(session_id, message, turn, response, target_asin)
        packed.append(row)
        demo_sessions[session_id]["turn"] = turn
        if row["hit_rank"] is not None and hit_turn is None:
            hit_turn = turn
            hit_rank = row["hit_rank"]
    return session_id, packed, hit_turn, hit_rank


def _run_replay(sample_id: str) -> dict:
    if sample_id not in public_samples:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown sample_id {sample_id}. Try public_0001 or public_0002.",
        )
    sample = public_samples[sample_id]
    target = str(sample["ground_truth"]["parent_asin"])
    products = {target: _product_dict(target)}
    card, behavior = materialize_hidden_fields(sample, products)
    effective = {**sample, "intent_card": card, "behavior": behavior}
    meta = _store().get(target)
    category = _coarse_from_meta(meta.categories if meta else "")

    live = _require_agent()
    session_id = _new_session(sample["user_profile"], target)
    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    user_message = initial_message(effective, category, disclosed)

    packed: list[dict] = []
    hit_turn: int | None = None
    hit_rank: int | None = None

    for turn in range(1, MAX_TURNS + 1):
        response = live.respond(session_id, user_message, turn, TOP_K)
        row = _pack_turn(session_id, user_message, turn, response, target)
        packed.append(row)
        demo_sessions[session_id]["turn"] = turn
        if target in _ranked_asins(response):
            hit_turn = turn
            hit_rank = row["hit_rank"]
            break
        if turn == MAX_TURNS:
            break
        override = effective.get("behavior", {}).get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                disclosed.add(new_value)
            user_message = str(
                override.get("message", "Actually, please ignore my earlier preference.")
            )
        else:
            user_message, boundary_used = customer_reply(
                effective, response.get("ask_attribute"), disclosed, boundary_used
            )

    return {
        "session_id": session_id,
        "script": "replay",
        "sample_id": sample_id,
        "scenario_type": sample["scenario_type"],
        "target_asin": target,
        "target_title": meta.title if meta else target,
        "hit_turn": hit_turn,
        "hit_rank": hit_rank,
        "profile": sample["user_profile"],
        "turns": packed,
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global agent, catalog_ids, public_samples
    if not CATALOG.exists():
        raise FileNotFoundError(
            f"Catalog not found at {CATALOG}. Download catalog.jsonl into data/ first."
        )
    print(f"Indexing catalog {CATALOG} …", flush=True)
    agent = Agent(CATALOG)
    catalog_ids = set(agent.searcher._store.all_asins())
    if PUBLIC_SET.exists():
        public_samples = {row["sample_id"]: row for row in load_jsonl(PUBLIC_SET)}
    print(f"Demo API ready — {len(catalog_ids):,} products, {len(public_samples)} public sessions", flush=True)
    yield


app = FastAPI(title="Doom Scrollers Demo", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SessionRequest(BaseModel):
    user_profile: dict | None = None


class TurnRequest(BaseModel):
    session_id: str = Field(min_length=1)
    user_message: str = Field(min_length=1)


class PlaybackRequest(BaseModel):
    script: Literal["browsing", "buying", "replay"]
    sample_id: str = "public_0001"


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": agent is not None,
        "catalog_size": len(catalog_ids),
        "public_sessions": len(public_samples),
    }


@app.post("/api/session")
async def create_session(body: SessionRequest | None = None) -> dict:
    profile = (body.user_profile if body and body.user_profile else None) or default_profile()
    session_id = _new_session(profile)
    live = _require_agent()
    return {
        "session_id": session_id,
        "turn": 0,
        "profile": profile,
        "dialog_state": live.get_dialog_state(session_id),
        "recommendations": [],
        "message": "What are you looking for today?",
        "ask_attribute": None,
        "target_asin": None,
        "hit_rank": None,
    }


@app.post("/api/turn")
async def take_turn(body: TurnRequest) -> dict:
    live = _require_agent()
    overlay = demo_sessions.get(body.session_id)
    if overlay is None or body.session_id not in live._sessions:
        raise HTTPException(status_code=404, detail="Unknown session. Start a new session first.")
    turn = int(overlay["turn"]) + 1
    if turn > MAX_TURNS:
        raise HTTPException(status_code=400, detail=f"Session already reached {MAX_TURNS} turns.")
    response = live.respond(body.session_id, body.user_message.strip(), turn, TOP_K)
    overlay["turn"] = turn
    return _pack_turn(
        body.session_id,
        body.user_message.strip(),
        turn,
        response,
        overlay.get("target_asin"),
    )


@app.post("/api/playback")
async def playback(body: PlaybackRequest) -> dict:
    if body.script == "browsing":
        session_id, turns, hit_turn, hit_rank = _run_messages(BROWSING_TURNS, default_profile())
        return {
            "session_id": session_id,
            "script": "browsing",
            "sample_id": None,
            "scenario_type": "browsing",
            "target_asin": None,
            "target_title": None,
            "hit_turn": hit_turn,
            "hit_rank": hit_rank,
            "profile": default_profile(),
            "turns": turns,
        }
    if body.script == "buying":
        session_id, turns, hit_turn, hit_rank = _run_messages(BUYING_TURNS, default_profile())
        return {
            "session_id": session_id,
            "script": "buying",
            "sample_id": None,
            "scenario_type": "buying",
            "target_asin": None,
            "target_title": None,
            "hit_turn": hit_turn,
            "hit_rank": hit_rank,
            "profile": default_profile(),
            "turns": turns,
        }
    return _run_replay(body.sample_id)
