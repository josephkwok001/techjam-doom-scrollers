"""Sweep MRR reranker knobs. Reuses one catalog index."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl  # noqa: E402
from starter.agent import Agent  # noqa: E402
from starter.retrieval import reranker  # noqa: E402

GRID = {
    "POPULARITY_CAP_RATIO": (0.45, 0.5, 0.55),
    "FEATURE_PHRASE_BONUS": (2.5, 3.0, 3.5, 4.0),
    "HARD_CONSTRAINT_WEIGHT": (1.8, 2.0, 2.2),
}


def main() -> None:
    samples = load_jsonl("data/public_set.jsonl")
    catalog_ids, categories, products = catalog_index("data/catalog.jsonl")
    agent = Agent("data/catalog.jsonl")
    rows: list[tuple[float, float, str, dict]] = []

    names = list(GRID)
    for combo in itertools.product(*(GRID[name] for name in names)):
        config = dict(zip(names, combo))
        for name, value in config.items():
            setattr(reranker, name, value)
        result = evaluate(agent, samples, catalog_ids, categories, products)
        label = " ".join(f"{k.split('_')[0].lower()}={v}" for k, v in config.items())
        rows.append((result["recommended_technical_score"], result["mrr"], label, result))
        print(
            f"{result['recommended_technical_score']:.4f} hit={result['hit_rate_at_10']:.3f} "
            f"mrr={result['mrr']:.3f} {label}",
            flush=True,
        )

    rows.sort(key=lambda row: (row[0], row[1]), reverse=True)
    print("\n=== TOP 8 ===")
    for score, mrr, label, result in rows[:8]:
        print(
            f"{score:.4f} hit={result['hit_rate_at_10']:.3f} mrr={mrr:.3f} {label}"
        )


if __name__ == "__main__":
    main()
