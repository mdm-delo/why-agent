# Why-Agent × RYO-CHAN (Track 01 Autonomous Agents, Track 03 skill contract)

Why-Agent reads RYO's live research layer and returns an explainable **practice-trade** decision with a full "why" trace: rules applied, RYO evidence (with tool and date), alternatives, reviewers' 2/3 quorum, confidence and what would refute it.

- `ryo/adapter.py`: MCP client (`tools/call`) for the 7 read-only tools at `https://app-ryochan.com/api/mcp`, `Authorization: Bearer $RYO_MCP_KEY`.
- **Honesty convention:** a failed or rate-limited tool becomes an explicit `UNAVAILABLE` gap, and a field RYO marks missing stays `MISSING`. Gaps are never used as facts. When half or more of the evidence is missing, the agent chooses "wait".
- `ryo/practice.py`: paper trades only, appended to `data/ryo_practice.jsonl`. No funds, no signing.
- Every call writes a receipt `ryo/<tool>` to `data/receipts.jsonl`.

```bash
export RYO_MCP_KEY=...        # builder key from the RYO Discord
python3 ryo/practice.py SOL
python3 ryo/test_ryo.py       # offline tests with a fake transport
```
