# Doom Scrollers — Conversational E-Commerce Search

**TechJam 2026** · Multi-turn shopping agent for the [Conversational E-Commerce Search Challenge](docs/competition_specification.md)

Team **Doom Scrollers** — an offline agent that progressively narrows 50,000 catalog products through multi-turn dialogue, profile-aware reranking, and simulator-aware clarification.

---

## Project overview

Customers rarely state every requirement upfront. Our agent plays both **shop assistant** and **search engine**:

1. **Dialog (Pillar II)** — tracks session state, routes buying vs browsing, and asks clarification questions every actionable turn.
2. **Retrieval (Pillar I)** — BM25 over an in-memory FTS5 index, metadata filters, phrase rescue for long constraints, and a heuristic reranker.
3. **Personalization (Pillar III)** — uses the anonymized `user_profile` to boost reranking and prioritize questions.
4. **Evaluation (Pillar IV)** — scored locally on 200 public sessions via the official evaluator.

**Design insight:** The evaluator's simulated customer reveals **catalog-aligned constraint text** when asked `ask_attribute`. We optimize for progressive constraint narrowing rather than one-shot query understanding.

**Stack:** Python 3.10+, standard library only for the core path. No LLM API keys required. Zero inference tokens.

We also ship an **optional demo UI** (`demo/`) — a local React front-end for live chat and product cards. It is not scored; see [Try the demo UI](#try-the-demo-ui) below.

### Architecture

```text
evaluator  →  Agent (starter/agent.py)
                 ├── dialog: slots, intent routing, question policy
                 ├── personalization: profile boosts, question priority
                 └── retrieval/HybridSearcher
                       ├── query_builder  (phrase extraction, buying/browsing FTS)
                       ├── catalog_store  (FTS5 BM25 index)
                       ├── filters        (metadata narrowing)
                       ├── reranker       (phrase, category, product-type, popularity cap)
                       └── search         (orchestration + phrase rescue)
```

Deeper design notes: [agent.md](agent.md) · [docs/pillars.md](docs/pillars.md) · [docs/tuning_log.md](docs/tuning_log.md)

### Results (public set, 200 sessions)

Reproduced with `python3 -m evaluator.local_evaluator` on our latest commit:

| Metric | Baseline starter | Our agent |
|--------|------------------|-----------|
| **TechnicalScore** | 0.107 | **0.925** |
| Hit Rate@10 | 0.125 | **1.000** |
| MRR | 0.068 | **0.820** |
| MTTC (turns) | 9.81 | **2.07** |
| Token usage | — | **0** |

Per scenario: browsing 1.000 hit · buying 1.000 hit · intent_override 1.000 hit · boundary 1.000 hit.

---

## Setup and installation

### Requirements

- **Python 3.10+** (3.12 tested)
- **git**
- ~20 MB disk for the compressed catalog; ~50 MB decompressed

No `pip install` is required for the core agent — only the Python standard library.

### 1. Clone the repository

```bash
git clone https://github.com/josephkwok001/techjam-doom-scrollers.git
cd techjam-doom-scrollers
```

### 2. Download the product catalog

The catalog is not stored in git (size). Either:

**Option A — from the release in this repo**

```bash
# If catalog.jsonl.gz is in the repo root:
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
```

**Option B — from GitHub Releases** (see original challenge instructions)

```bash
# Download catalog.jsonl.gz from Releases, then:
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
```

Verify with the published `SHA256SUMS` if provided.

### 3. Verify layout

```text
data/catalog.jsonl          # 50,000 products (you provide)
data/public_set.jsonl       # 200 development sessions (included)
starter/agent.py            # main agent entry point
evaluator/local_evaluator.py
tests/
```

---

## Reproduce our results

### Run the official evaluator

From the repository root:

```bash
python3 -m evaluator.local_evaluator
```

Expected aggregate output (approximate):

```text
TechnicalScore ≈ 0.925
Hit Rate@10    = 1.000
MRR            ≈ 0.820
MTTC           ≈ 2.07
```

The command writes per-session details to `results.json` (gitignored locally).

### Run unit tests

```bash
python3 -m unittest discover -s tests -q
```

Expected: **46 tests, OK**.

### Recordable demo (for video / manual inspection)

```bash
python3 scripts/demo_session.py scores       # benchmark summary
python3 scripts/demo_session.py browsing     # 3-turn browsing session
python3 scripts/demo_session.py buying       # buying-mode session
python3 scripts/demo_session.py replay public_0001
```

### Compact score script

```bash
python3 scripts/score.py mylabel
```

### Try the demo UI

Optional showcase only (not part of the scored agent). After the catalog is in place:

```bash
python3 -m pip install -r demo/requirements.txt
cd demo/web && npm install && cd ../..
python3 -m uvicorn demo.server:app --host 127.0.0.1 --port 8000   # terminal 1
cd demo/web && npm run dev                                         # terminal 2
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

---

## Repository structure

```text
starter/
  agent.py                 # Agent API + dialog + orchestration
  retrieval/               # Pillar I: BM25, filters, reranker, search
  personalization/         # Pillar III: profile signals and boosts
evaluator/
  local_evaluator.py       # Public-set simulator (do not edit for scoring)
tests/                     # Unit tests for retrieval, dialog, personalization
scripts/
  demo_session.py          # Terminal demo for Devpost video
  score.py                 # One-shot evaluator with histograms
demo/
  server.py                # FastAPI wrapper for the showcase UI
  web/                     # Vite + React demo SPA
docs/
  pillars.md               # Pillar framework and metrics
  tuning_log.md            # Experiment log (0.107 → 0.925)
  devpost_outline.md       # Devpost copy + video script
  agent_api_contract.json  # Required API schema
agent.md                   # Team architecture guide
```

---

## Agent API

Our submission implements the required interface:

```python
from starter.agent import Agent

agent = Agent("data/catalog.jsonl")
agent.reset(session_id, user_profile)
response = agent.respond(session_id, user_message, turn=1, top_k=10)
# → {"message", "ask_attribute", "recommendations", "usage"}
```

Full contract: [docs/agent_api_contract.json](docs/agent_api_contract.json)

---

## Limitations and future work

**Public-set tuning.** Weights were tuned on the 200 public development sessions. The private holdout may behave differently; we prioritized broad plateaus over knife-edge optima.

**MRR ceiling (~0.82).** Hit rate is 1.000 on the public set, but ~55 sessions still land at rank 2–10 instead of rank 1. Near-duplicate products often match the same disclosed marketing phrases; substring reranking alone cannot always separate them.

**Buying strict path.** The conjunctive buying FTS expression rarely matches real products; recall-first fallback + reranking does the actual work.

**No semantic model.** We deliberately stayed offline (BM25 + heuristics) for feasibility and zero cost. Given more time we would:

- Add a **local cross-encoder** or lightweight reranker on the top-10 candidates only.
- Implement **field-aware contradiction penalties** (color/material mismatches).
- **Diagnose rank-2 sessions** systematically and add hard-vs-soft constraint weighting refinements.
- Evaluate on a **held-out split** of public sessions to reduce overfitting risk.

**Catalog quirks.** Some products are miscategorized (e.g. bracelets under `Pendants`). We handle this with product-type conflict scoring and phrase rescue, but edge cases remain.

---

## Team contributions

| Member | Role | Contributions |
|--------|------|----------------|
| **Joseph** | Pillar I · retrieval lead | `starter/retrieval/`: BM25 index, query builder, metadata filters, heuristic reranker, phrase rescue, buying/browsing search paths; evaluation harnesses (`scripts/score.py`, tuning sweeps); integration testing |
| **JY** | Pillar II · dialog lead | `starter/agent.py`: session state, slot parsing, buying/browsing intent routing, `ask_attribute` question policy, intent override and boundary handling |
| **Both** | Pillars III & IV | `starter/personalization/`: profile signals, rerank boosts, question priority; evaluator-driven tuning, documentation, demo UI (`demo/`), and Devpost materials |

---

## Data and attribution

Catalog and sessions are derived from [Amazon Reviews 2023](https://amazon-reviews-2023.github.io/) (McAuley Lab, UCSD). See [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md).

Do not commit `data/catalog.jsonl` or API keys. The evaluator and `data/public_set.jsonl` are provided for local development only.

---

## References

- [Competition specification](docs/competition_specification.md)
- [Submission rules](docs/submission_rules.md)
- [Baseline starter scores](docs/baseline_results.json)
