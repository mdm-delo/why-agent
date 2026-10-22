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

## Sponsor layers (with honest fallbacks, see `providers.py`)
- **Zetaris** is the evidence layer. With `ZETARIS_REST_URL`, `ZETARIS_API_KEY` and `ZETARIS_ORG_ID` set, the agent pulls evidence from the governed view `why_agent.evidence` (`data/zetaris_seed.sql`). Otherwise it uses `data/evidence.json`. Every card states which layer was used.
- **Meterless Nightshift** is the LLM layer. It uses the local OpenAI-compatible runtime (`meterless/auto`, with the `meterless-app: why-agent` header) and falls back to the Groq free tier.
- **Metering:** every evidence or LLM call writes a receipt (provider, latency, tokens) to `data/receipts.jsonl`.

## Files
- `agent.py` — rule matching, evidence retrieval, option scoring, reviewers and quorum, confidence, memory
- `server.py`, `web/index.html` — web demo
- `data/rules.json` — rules P1–P12 in English (`rules_ru.json` holds the originals)
- `data/evidence.json`, `data/scenarios.json`, `data/memory.jsonl` (created at runtime)

## Pre-existing components (declared)
The rule set P1–P12 and the facts in the evidence file come from the team's earlier notes. All code in this folder was written during the hackathon window, from 22.10.2026 on.

## Roadmap
Zetaris data harness as the evidence layer, Meterless Nightshift model races as extra reviewers, and a Telegram bridge for Yes/No/Later.
