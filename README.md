# Why-Agent: a decision avatar that explains why

Open Agent Hackathon 2026, track 02 "The Agent That Can Explain Why". Team MENfigiTAL.

The founder's decision rules (P1–P12) are learned from his real answers. For every question with options, the agent returns an **action plus a transparent "why" trace**:

- **Rules applied:** which founder rules matched and on which words.
- **Evidence:** facts from read-only project sources, each with its source and date.
- **Alternatives considered:** every option, its score, the per-rule +/- trace, and any option blocked by a hard rule.
- **Reviewers:** Treasurer, Lawyer and Skeptic vote. A 2/3 quorum is required; with no quorum the default is NO (silence = no).
- **Confidence:** based on the margin over the runner-up and the amount of evidence.
- **What would refute it**, plus **past similar decisions** from memory.
- **Human in the loop:** the agent never signs, pays or messages as the founder. It returns a card for Yes / No / Later.

The decision itself is deterministic and auditable. An LLM is optional and only *narrates* the trace. It never changes the decision.

## Run (Python 3.9+, no dependencies)
```bash
python3 agent.py --demo                       # 5 scripted scenarios (the last one recalls memory)
python3 agent.py "Should we pay for X?" "Pay now|Use free tier, pay when it pays off"
python3 agent.py --json "question" "opt A|opt B"   # machine-readable card
python3 server.py 8765                         # web demo at http://localhost:8765
GROQ_API_KEY=... python3 agent.py --demo --llm # optional narration via the Groq free tier
python3 test_agent.py
```

The Meterless H-MEM memory needs Node 20 one time: `cd hmem && npm install && npm run setup`. Without it, memory falls back to `data/memory.jsonl`.

## Sponsor tech
| Sponsor | Where it is used | Status |
|---|---|---|
| **Meterless H-MEM engine** | Decision memory (`hmem/bridge.ts`, called from `providers.hmem()`). Each card is stored with `remember`. New questions `recall` precedents through H-MEM hybrid retrieval. The card's "Decided before" section shows the H-MEM memory id and its **trust-ledger audit** (create → read). | **Working**, zero keys, runs locally. Proof: `agent.py --demo`, scenario 5 recalls `mem-4`; receipts are in `data/receipts.jsonl` (`provider: meterless/hmem`). |
| Meterless Nightshift runtime | Optional LLM narration via `127.0.0.1:8088/v1`, model `meterless/auto` | Adapter ready. Nightshift is a desktop app (Windows/Mac/DGX); when it is not running, narration uses the Groq free tier. |
| Zetaris | Evidence layer: REST query of the governed view `why_agent.evidence` (`data/zetaris_seed.sql`), env `ZETARIS_REST_URL`, `ZETARIS_API_KEY`, `ZETARIS_ORG_ID` | Adapter ready and the account is being registered. Until a token and Org ID are set, evidence comes from `data/evidence.json`. Every card states the layer it used. |

Every evidence, memory or LLM call writes a receipt (provider, op, latency) to `data/receipts.jsonl`.

## AI coding tools used
- Grok Bot agent: code, tests, docs, slides and demo video.
- Cursor: optional, not required to run.

## Media
- Slides: `docs/slides.html`, `docs/slides.pdf`
- Demo video (102 s, captions, no voice): `media/why-agent-demo.mp4`

## Files
- `agent.py` — rule matching, evidence retrieval, option scoring, reviewers and quorum, confidence, memory
- `server.py`, `web/index.html` — web demo
- `data/rules.json` — rules P1–P12 in English (`rules_ru.json` holds the originals)
- `data/evidence.json`, `data/scenarios.json`, `data/memory.jsonl` (created at runtime)

## Pre-existing components (declared)
The rule set P1–P12 and the facts in the evidence file come from the team's earlier notes. All code in this folder was written during the hackathon window, from 22.10.2026 on.

## Roadmap
Live Zetaris evidence, H-MEM sleep-cycle consolidation of old decisions, H-MEM feedback from Yes/No answers, Nightshift model races as extra reviewers, and a Telegram bridge for Yes/No/Later.
