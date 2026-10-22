import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ryo import adapter, practice
def fake(body):
    n = body['params']['name']
    if n == 'check_safety': return {'jsonrpc': '2.0', 'id': body['id'], 'error': {'message': 'rate limited'}}
    data = {'price': 151.2, 'rsi14': 48, 'derivatives': {'status': 'unavailable'}}
    return {'jsonrpc': '2.0', 'id': body['id'], 'result': {'content': [{'type': 'text', 'text': json.dumps(data)}]}}
ev = adapter.evidence(['SOL'], transport=fake)
assert any(e['id'] == 'ryo-check_safety-gap' and e['unavailable'] for e in ev)
assert any(e['fact'] == 'MISSING: derivatives' for e in ev)
assert any('rsi14: 48' in e['fact'] for e in ev)
os.environ.pop('RYO_MCP_KEY', None)
d, err = adapter.call('market_overview'); assert d is None and 'RYO_MCP_KEY' in err
assert adapter.call('buy_token')[1].startswith('unknown')
c, r = practice.run('SOL', transport=fake); assert r['paper'] and r['symbol'] == 'SOL' and c['action']
c, r = practice.run('SOL', transport=lambda b: {'error': {'message': 'down'}}); assert c['action'].startswith('Wait')
print('ryo tests ok')
