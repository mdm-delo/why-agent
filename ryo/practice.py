"""Explainable practice-trade agent (RYO Track 01). RYO evidence -> Why-Agent card -> paper trade log.
No real funds: trades are only appended to data/ryo_practice.jsonl."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agent
from ryo import adapter
LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'ryo_practice.jsonl')

def run(symbol, transport=None, remember=False):
    ev = adapter.evidence([symbol], transport=transport)
    gaps = [e for e in ev if e.get('unavailable')]
    opts = ['Practice-buy a small share of %s with a stop' % symbol, 'Wait and collect more evidence on %s' % symbol]
    agent.EVID[:0] = [e for e in ev if not e.get('unavailable')]
    try: card = agent.decide('Should we risk a practice trade on %s now?' % symbol, opts, remember=remember)
    finally: del agent.EVID[:len([e for e in ev if not e.get('unavailable')])]
    if gaps and len(gaps) * 2 >= len(ev):  # honesty: too much missing data -> no trade
        card['action'] = opts[1]; card['why'].setdefault('notes', []).append('%d of %d RYO evidence items unavailable' % (len(gaps), len(ev)))
    card['ryo_evidence'] = ev
    rec = dict(ts=time.strftime('%Y-%m-%dT%H:%M:%S'), symbol=symbol, action=card['action'], confidence=card['confidence'],
               evidence=[e['id'] for e in ev], gaps=[e['id'] for e in gaps], paper=True)
    open(LOG, 'a', encoding='utf-8').write(json.dumps(rec) + '\n')
    return card, rec

if __name__ == '__main__':
    c, r = run(sys.argv[1] if len(sys.argv) > 1 else 'SOL'); print(agent.render(c)); print(json.dumps(r))
