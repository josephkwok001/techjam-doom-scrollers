# Devpost / Report Outline (Monday)

Copy sections into Devpost. Replace `[TEAM]` with names.

## Title

**Doom Scrollers** — Progressive Constraint Retrieval for Multi-Turn Shopping

## Tagline (one sentence)

An offline conversational shopping agent that narrows 50k products turn-by-turn using disclosed constraints, profile-aware reranking, and simulator-aware clarification.

## Problem

Keyword search fails when customer intent only emerges over multiple turns. In browsing sessions the first message often carries almost no product-specific signal.

## Our insight

The evaluator's simulated customer reveals **catalog-aligned constraint text** when asked `ask_attribute`. We optimize for progressive constraint narrowing, not one-shot query understanding.

## Solution (Pillars I–IV)

| Pillar | What we built |
|--------|----------------|
| **I — Retrieval** | BM25 + metadata filters + heuristic reranker (phrase, category, product-type, popularity cap) + phrase rescue |
| **II — Dialog** | Dual buying/browsing routing, never waste a clarification turn, open `other` questions |
| **III — Personalization** | Profile boosts in reranker + question priority |
| **IV — Evaluation** | Local benchmark on 200 public sessions |

## Results (public set)

Run before submitting:

```bash
python3 -m evaluator.local_evaluator
```

| Metric | Baseline | Ours |
|--------|----------|------|
| TechnicalScore | 0.107 | **~0.925** |
| Hit Rate@10 | 0.125 | **1.000** |
| MRR | 0.068 | **~0.820** |
| MTTC | 9.81 | **~2.07** |

Offline: **0 tokens**, in-memory SQLite FTS5, no API keys.

## Demo video script (~2 min)

1. **Intro (15s)** — problem + pillar diagram
2. **Live demo (60s)** — `python3 scripts/demo_session.py browsing` (or the optional UI at [http://127.0.0.1:5173](http://127.0.0.1:5173) — see README)
3. **Replay hit (30s)** — `python3 scripts/demo_session.py replay public_0001`
4. **Benchmark (20s)** — `python3 scripts/demo_session.py scores`
5. **Close (15s)** — offline, team split, limitation (MRR ~0.82, tuned on public set)

## Limitations (honest)

- Weights tuned on the public 200 sessions; private holdout may differ.
- MRR ~0.82: 55 sessions hit at rank 2–10 (near-duplicate phrase matches).
- Buying strict AND path rarely matches; recall-first fallback does the work.

## Team contributions

| Member | Pillar |
|--------|--------|
| Joseph | I — `starter/retrieval/` |
| JY | II — dialog in `starter/agent.py` |
| Both | III — `starter/personalization/` |

## Feasibility / cost

- No paid LLM calls in production path
- Runs on laptop; catalog index builds in ~3s
- `$0` inference cost
