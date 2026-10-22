import io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from switch import connector as s
fake = lambda q, o: {'action': o[1], 'confidence': 0.7, 'question': q,
    'why': {'rules': [{'id': 'P3', 'text': 'pay only when it pays off'}], 'evidence': [{'fact': 'free tier exists', 'source': 'docs'}],
            'alternatives': [{'option': o[0], 'score': -1, 'blocked_by': None}, {'option': o[1], 'score': 2}]}}
assert s.parse('@why-agent decide: Pay? | Now | Later') == ('Pay?', ['Now', 'Later'])
assert s.parse('hello') is None
ev = lambda body, addr=True: {'type': 'message', 'room_id': 'r1', 'sequence': 1, 'payload': {'addressed': addr, 'body': body, 'sender_name': 'Priya'}}
assert s.handle(ev('random chat', False), fake) is None
out = s.handle(ev('@why-agent decide: Pay GPU? | Pay now | Use free tier'), fake)
assert 'Decision: Use free tier' in out and 'YES / NO / LATER' in out
out = s.handle(ev('yes', False), fake); assert out.startswith('Recorded YES from Priya')
assert 'r1' not in s.PENDING
# real agent end to end
out = s.handle(ev('@why-agent decide: Agent should sign a wallet transaction? | Agent signs and sends funds itself | Prepare draft and ask the founder'))
assert 'ask the founder' in out.split('\n')[0]
# SSE parsing + protocol paths
c = s.Client('http://x', 'a1', 'k', ['r1'])
fr = list(c.frames([b': keepalive\n', b'event: connection_state\n', b'data: {"cursor": 5}\n', b'\n',
                    b'id: 6\n', b'event: message\n', b'data: {"type":"message","sequence":6,"room_id":"r1","payload":{}}\n', b'\n']))
assert fr[0]['type'] == 'connection_state' and fr[1]['sequence'] == 6
assert c.events_path().startswith('/agents/a1/events?connection_id=') and '&rooms=r1' in c.events_path()
sent = []
c.http = lambda rq, timeout=0: (sent.append((rq.get_method(), rq.full_url, rq.headers, rq.data)), io.BytesIO(b'{"result": 1}'))[1]
assert c.op('list_rooms') == 1 and sent[-1][1] == 'http://x/agents/a1/ops/list_rooms' and sent[-1][2]['Authorization'] == 'Bearer k'
c.post('r1', 'hi'); assert json.loads(sent[-1][3]) == {'room_id': 'r1', 'content': 'hi'}
print('switch tests ok')
