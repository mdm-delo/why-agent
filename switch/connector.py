"""Why-Agent as a Switch room agent (Flip the Switch, WeMakeDevs, Nov 4-7 2026).

Implements the Switch agent protocol (docs.switchagents.ai .../internals/agent-protocol):
SSE down (GET /agents/{id}/events), HTTP up (POST /agents/{id}/ops/{op}), heartbeat every 2 s.
Bridge it to a Telegram group with Switch Console; the room then behaves like this:

  @why-agent decide: Pay for the GPU now? | Pay now | Use free tier, pay when it pays off
  -> a decision card with the why trace, and "reply YES / NO / LATER".
  A person replies YES/NO/LATER -> recorded in data/switch_decisions.jsonl. The agent never acts by itself.

Env: SWITCH_BRIDGE_URL, SWITCH_AGENT_ID, SWITCH_API_KEY (from register-known, returned once), SWITCH_ROOMS (comma ids)."""
import json, os, sys, threading, time, urllib.request, uuid
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
LOG = os.path.join(ROOT, 'data', 'switch_decisions.jsonl')
PENDING = {}  # room_id -> last card awaiting a human verdict

def parse(body):
    """'@why-agent decide: Q | A | B' -> (question, [A, B]) or None."""
    b = body.split('decide:', 1)
    if len(b) < 2: return None
    parts = [p.strip() for p in b[1].split('|') if p.strip()]
    return (parts[0], parts[1:]) if len(parts) >= 3 else None

def card_text(c):
    w = c['why']; lines = ['Decision: ' + c['action'], 'Confidence: %.2f' % c['confidence']]
    lines += ['Rule %s: %s' % (r.get('id', ''), r.get('text', r.get('rule', ''))[:90]) for r in w.get('rules', [])[:3]]
    lines += ['Evidence: %s (%s)' % (e['fact'][:90], e['source']) for e in w.get('evidence', [])[:3]]
    lines += ['Alt: %s  score %s%s' % (a['option'][:60], a.get('score'), ' BLOCKED by ' + a['blocked_by'] if a.get('blocked_by') else '') for a in w.get('alternatives', [])]
    lines.append('Human in the loop: reply YES / NO / LATER. Silence = NO.')
    return '\n'.join(lines)

def handle(ev, decide=None):
    """Pure event handler: returns the reply text to post, or None."""
    if ev.get('type') != 'message': return None
    p = ev.get('payload', {}); body = (p.get('body') or '').strip(); room = ev.get('room_id')
    verdict = body.upper().strip(' .!')
    if room in PENDING and verdict in ('YES', 'NO', 'LATER') and p.get('sender_kind') != 'platform':
        c = PENDING.pop(room)
        rec = dict(ts=time.strftime('%Y-%m-%dT%H:%M:%S'), room=room, by=p.get('sender_name') or p.get('sender'), verdict=verdict,
                   question=c['question'], action=c['action'])
        open(LOG, 'a', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False) + '\n')
        return 'Recorded %s from %s for: %s' % (verdict, rec['by'], c['action'])
    if not p.get('addressed'): return None
    q = parse(body)
    if not q: return 'Usage: decide: question | option A | option B'
    if decide is None:
        import agent; decide = agent.decide
    c = decide(q[0], q[1]); c.setdefault('question', q[0]); PENDING[room] = c
    return card_text(c)

class Client:
    def __init__(self, base=None, agent_id=None, key=None, rooms=None, http=urllib.request.urlopen):
        e = os.environ.get
        self.base = (base or e('SWITCH_BRIDGE_URL', 'http://127.0.0.1:8090')).rstrip('/')
        self.id, self.key = agent_id or e('SWITCH_AGENT_ID'), key or e('SWITCH_API_KEY')
        self.rooms = rooms if rooms is not None else [r for r in e('SWITCH_ROOMS', '').split(',') if r]
        self.conn, self.cursor, self.http, self.alive = str(uuid.uuid4()), None, http, True

    def _req(self, method, path, body=None, headers=None, timeout=30):
        h = {'Authorization': 'Bearer ' + (self.key or ''), 'Content-Type': 'application/json', 'X-Switch-Connection-Id': self.conn}
        h.update(headers or {})
        return self.http(urllib.request.Request(self.base + path, json.dumps(body).encode() if body is not None else None, h, method=method), timeout=timeout)

    def op(self, name, **args):
        return json.load(self._req('POST', '/agents/%s/ops/%s' % (self.id, name), args)).get('result')

    def post(self, room, text):
        return self._req('POST', '/agents/%s/message' % self.id, {'room_id': room, 'content': text}).read()

    def beat(self):
        while self.alive:
            try: self._req('POST', '/agents/%s/connection/beat' % self.id, {'connection_id': self.conn, 'cursor': self.cursor}, timeout=5).read()
            except Exception: pass  # 404/409 -> stream loop reopens
            time.sleep(2)

    def events_path(self):
        q = 'connection_id=%s&scope=all&filter=all&start_from=head&client=why-agent&client_version=0.4' % self.conn
        return '/agents/%s/events?%s%s' % (self.id, q, '&rooms=' + ','.join(self.rooms) if self.rooms else '')

    def frames(self, resp):
        ev_type, data = None, []
        for raw in resp:
            line = raw.decode().rstrip('\n')
            if line.startswith(':'): continue  # keepalive comment
            if line.startswith('event:'): ev_type = line[6:].strip()
            elif line.startswith('data:'): data.append(line[5:].strip())
            elif line == '' and data:
                d = json.loads('\n'.join(data)); d.setdefault('type', ev_type); yield d; ev_type, data = None, []

    def run(self, decide=None):
        threading.Thread(target=self.beat, daemon=True).start()
        while self.alive:
            try:
                h = {'Accept': 'text/event-stream'}
                if self.cursor: h['Last-Event-ID'] = str(self.cursor)
                for f in self.frames(self._req('GET', self.events_path(), headers=h, timeout=60)):
                    if f['type'] == 'connection_state': self.cursor = f.get('cursor')
                    elif f['type'] == 'evicted': break
                    elif 'sequence' in f:
                        self.cursor = f['sequence']; out = handle(f, decide)
                        if out: self.post(f['room_id'], out)
            except Exception as e:
                print('stream:', type(e).__name__, file=sys.stderr); time.sleep(3)

if __name__ == '__main__':
    Client().run()
