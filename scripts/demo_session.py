"""Recordable terminal demo for the Devpost video.

Usage:
    python3 scripts/demo_session.py scores          # benchmark summary (~10s)
    python3 scripts/demo_session.py browsing      # scripted 3-turn browsing demo
    python3 scripts/demo_session.py buying        # scripted buying demo
    python3 scripts/demo_session.py replay ID     # replay one public_set session
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluator.local_evaluator import (  # noqa: E402
    MAX_TURNS,
    TOP_K,
    catalog_index,
    coarse_category,
    customer_reply,
    evaluate,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
    normalize_recommendations,
)
from starter.agent import Agent  # noqa: E402

CATALOG = "data/catalog.jsonl"
PUBLIC_SET = "data/public_set.jsonl"
WRAP = 88


def _rule(title: str = "") -> None:
    print()
    print("=" * WRAP)
    if title:
        print(title)
        print("-" * WRAP)


def _say(role: str, message: str) -> None:
    prefix = f"{role.upper():>8}: "
    for line in textwrap.wrap(message, width=WRAP - len(prefix), break_long_words=False):
        print(prefix + line)
        prefix = " " * (len(prefix))


def _short_title(products: dict[str, dict], asin: str, limit: int = 72) -> str:
    title = str(products.get(asin, {}).get("title") or asin)
    return title if len(title) <= limit else title[: limit - 3] + "..."


def _print_top(products: dict[str, dict], asins: list[str], target: str | None = None) -> None:
    print("     TOP RECOMMENDATIONS:")
    for index, asin in enumerate(asins[:5], start=1):
        marker = "  <-- target" if asin == target else ""
        print(f"       {index}. {asin}  {_short_title(products, asin)}{marker}")


def _profile() -> dict:
    return {
        "preference_tags": ["material", "comfort", "fit"],
        "rating_style": "usually positive",
        "summary": "Prior purchases emphasize material, comfort, and fit.",
        "purchase_frequency": "3-4 prior purchases",
        "average_prior_rating": 4.8,
    }


def demo_scores() -> None:
    _rule("PILLAR IV — LOCAL BENCHMARK (200 public sessions)")
    print("Running evaluator…")
    samples = load_jsonl(PUBLIC_SET)
    catalog_ids, categories, products = catalog_index(CATALOG)
    result = evaluate(Agent(CATALOG), samples, catalog_ids, categories, products)
    print()
    print(f"  TechnicalScore   {result['recommended_technical_score']:.4f}")
    print(f"  Hit Rate@10      {result['hit_rate_at_10']:.4f}")
    print(f"  MRR              {result['mrr']:.4f}")
    print(f"  MTTC             {result['mttc']:.2f} turns")
    print(f"  Efficiency       {result['efficiency']:.4f}")
    print(f"  Token usage      {result['reported_token_usage']['total_tokens']} (offline BM25)")
    print()
    print("  Per scenario:")
    for name, metrics in sorted(result["scenario_metrics"].items()):
        print(
            f"    {name:<16} hit={metrics['hit_rate_at_10']:.3f}  "
            f"mrr={metrics['mrr']:.3f}  mttc={metrics['mttc']:.2f}"
        )
    _rule()


def _run_scripted(agent: Agent, products: dict[str, dict], catalog_ids: set[str], turns: list[tuple[str, str]]) -> None:
    session_id = "demo"
    agent.reset(session_id, _profile())
    _say("system", "reset(session_id, user_profile) — profile loaded for personalization")
    target: str | None = None

    for turn, (label, message) in enumerate(turns, start=1):
        _rule(f"TURN {turn} — {label}")
        _say("customer", message)
        response = agent.respond(session_id, message, turn, TOP_K)
        ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
        _say("agent", response.get("message") or "")
        if response.get("ask_attribute"):
            print(f"     ask_attribute: {response['ask_attribute']}")
        _print_top(products, ranked, target)
        print(f"     usage: {response.get('usage', {})}")


def demo_browsing() -> None:
    _rule("MULTI-TURN DEMO — BROWSING (Pillar I + II + III)")
    print("Offline agent: BM25 retrieval + dialog + profile-aware reranking")
    agent = Agent(CATALOG)
    _, _, products = catalog_index(CATALOG)
    catalog_ids = set(products)
    _run_scripted(
        agent,
        products,
        catalog_ids,
        [
            ("explore", "I'm looking for running shoes, but I'm still exploring."),
            (
                "constraint",
                "For that, what matters is: lightweight mesh upper; cushioned sole.",
            ),
            (
                "constraint",
                "For that, what matters is: budget around $60; good for daily training.",
            ),
        ],
    )
    _rule("END DEMO")


def demo_buying() -> None:
    _rule("MULTI-TURN DEMO — BUYING")
    agent = Agent(CATALOG)
    _, _, products = catalog_index(CATALOG)
    catalog_ids = set(products)
    _run_scripted(
        agent,
        products,
        catalog_ids,
        [
            (
                "hard requirement",
                "I'm looking for women's running shoes. A key requirement is: breathable mesh upper.",
            ),
            (
                "soft preference",
                "For that, what matters is: lightweight; suitable for road running.",
            ),
        ],
    )
    _rule("END DEMO")


def demo_replay(sample_id: str) -> None:
    samples = {row["sample_id"]: row for row in load_jsonl(PUBLIC_SET)}
    if sample_id not in samples:
        print(f"Unknown sample_id: {sample_id}", file=sys.stderr)
        print("Example IDs: public_0001, public_0168, public_0020", file=sys.stderr)
        raise SystemExit(1)

    sample = samples[sample_id]
    catalog_ids, categories, products = catalog_index(CATALOG)
    target = str(sample["ground_truth"]["parent_asin"])
    card, behavior = materialize_hidden_fields(sample, products)
    effective = {**sample, "intent_card": card, "behavior": behavior}

    _rule(f"REPLAY — {sample_id} ({sample['scenario_type']})")
    print(f"  Target ASIN: {target}")
    print(f"  Target title: {_short_title(products, target, 80)}")
    print(f"  Category: {coarse_category(categories.get(target, []))}")

    agent = Agent(CATALOG)
    session_id = f"replay_{uuid.uuid4().hex[:8]}"
    agent.reset(session_id, sample["user_profile"])

    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    user_message = initial_message(
        effective, coarse_category(categories.get(target, [])), disclosed
    )
    hit_turn: int | None = None
    hit_rank: int | None = None

    for turn in range(1, MAX_TURNS + 1):
        _rule(f"TURN {turn}")
        _say("customer", user_message)
        response = agent.respond(session_id, user_message, turn, TOP_K)
        ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
        _say("agent", response.get("message") or "")
        if response.get("ask_attribute"):
            print(f"     ask_attribute: {response['ask_attribute']}")
        _print_top(products, ranked, target)
        if target in ranked:
            hit_turn = turn
            hit_rank = ranked.index(target) + 1
            print(f"     ✓ TARGET FOUND at rank {hit_rank} on turn {turn}")
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

    print()
    if hit_turn is None:
        print("  Result: MISS (target never entered top 10)")
    else:
        print(f"  Result: HIT on turn {hit_turn}, rank {hit_rank}, MRR contribution 1/{hit_rank}")
    _rule()


def main() -> None:
    parser = argparse.ArgumentParser(description="Recordable demo for Devpost video")
    parser.add_argument(
        "mode",
        choices=("scores", "browsing", "buying", "replay"),
        help="scores=benchmark, browsing/buying=scripted dialog, replay=public session",
    )
    parser.add_argument(
        "sample_id",
        nargs="?",
        default="public_0001",
        help="For replay mode: public_set sample_id (default public_0001)",
    )
    args = parser.parse_args()

    if args.mode == "scores":
        demo_scores()
    elif args.mode == "browsing":
        demo_browsing()
    elif args.mode == "buying":
        demo_buying()
    else:
        demo_replay(args.sample_id)


if __name__ == "__main__":
    main()
