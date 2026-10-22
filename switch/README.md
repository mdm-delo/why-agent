# Why-Agent in team chat via Switch (Flip the Switch, Track 01 Business Workflow)

The team asks in a Telegram, Slack or Discord channel. Why-Agent answers with a decision **and why**, and a human closes it with YES / NO / LATER. Silence = NO. The agent never signs, pays or messages for anyone.

- `switch/connector.py`: a from-scratch Switch agent-protocol client. It opens the SSE `GET /agents/{id}/events` stream with `scope=all`, sends a heartbeat every 2 s, resumes with `Last-Event-ID`, and posts with `POST /agents/{id}/message`.
- `switch/why-agent-room.template.yaml`: a Switch Console template for the room.
- Verdicts are logged to `data/switch_decisions.jsonl`.

```bash
# Switch Console (Docker) -> connect Telegram bridge -> register agent (POST /agents/register-known)
export SWITCH_BRIDGE_URL=... SWITCH_AGENT_ID=... SWITCH_API_KEY=... SWITCH_ROOMS=...
python3 switch/connector.py
python3 switch/test_switch.py   # offline tests
```
