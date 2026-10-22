# Cursor cloud agent task: Why-Agent v0.3

Repo: why-agent (Python stdlib, no dependencies). Read README.md, agent.py and providers.py first.

**Goal:** add an "explainability audit" plus a counterfactual "what-if" mode, and keep everything deterministic.
1. In `agent.py`, add `counterfactual(card, evidence_id)`. It re-runs the decision with one evidence item removed or negated and reports whether the action flips. Put the result in `why.would_refute`, replacing today's text-only list with `{evidence, flips_action: bool, new_action}`.
2. Add per-rule contribution percentages to each alternative (share of the final score).
3. Add `GET /api/audit/<id>` to `server.py`. It returns the stored card with its receipts from `data/receipts.jsonl`. In the web UI, add a "What if?" toggle next to each evidence item.
4. Extend `test_agent.py`: removing E8 must not unblock the P7 hard rule, and the counterfactual must flip the paid-credits scenario when E4 is removed.
5. Don't add network calls, secrets or new dependencies. Update the README.

**Done when:** `python3 test_agent.py` passes, `python3 agent.py --demo` prints the counterfactual flips, and the web UI shows them.
