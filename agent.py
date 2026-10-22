#!/usr/bin/env python3
"""Why-Agent: a decision avatar that explains why. Stdlib only.
Each decision = action + transparent trace: rules applied, evidence, alternatives, reviewer votes, confidence."""
import json, os, re, sys, time, urllib.request, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda f: os.path.join(HERE, 'data', f)
RULES = json.load(open(D('rules.json'), encoding='utf-8'))
import providers
EVID, EVID_SRC = providers.load_evidence()
MEM = D('memory.jsonl')
WORD = re.compile(r'[a-z0-9\-]+')

def toks(s): return set(WORD.findall(s.lower()))
def has(text, phrase): return phrase.lower() in text.lower()

def relevant_rules(q):
    t = toks(q); out = []
    for r in RULES:
        hit = [g for g in r['tags'] if g in t or has(q, g)]
        if hit: out.append((r, hit))
    return out

def evidence_for(q, rules):
    t = toks(q) | {g for r, _ in rules for g in r['tags']}
    sc = [(len(t & set(e['tags'])), e) for e in EVID]
    return [e for s, e in sorted(sc, key=lambda x: -x[0]) if s >= 2][:4] or [e for s, e in sc if s][:2]

def score_option(opt, rules):
    s, why, blocked = 0.0, [], None
    for r, _ in rules:
        for p in r['prefer']:
            if has(opt, p): s += 1; why.append({'rule': r['id'], 'effect': '+1', 'because': f'matches "{p}"'})
        for a in r['avoid']:
            if has(opt, a):
                s -= 2 if r.get('hard') else 1
                why.append({'rule': r['id'], 'effect': '-2' if r.get('hard') else '-1', 'because': f'conflicts with "{a}"'})
                if r.get('hard'): blocked = r['id']
    return s, why, blocked

def similar_past(q, k=1):
    o = providers.hmem('recall', q)
    if o is not None:
        return [{'id': m['content'].split(' ')[0], 'memory_id': m['id'], 'question': m['content'].split(' Q: ')[-1].split(' -> ')[0],
                 'action': m['content'].split(' -> ')[-1], 'similarity': m['relevance'], 'engine': 'meterless/hmem', 'audit': providers.hmem('audit', m['id']).get('history')}
                for m in o.get('memories', [])[:k] if m['relevance'] >= 0.3]
    if not os.path.exists(MEM): return []
    t = toks(q); best = []
    for line in open(MEM, encoding='utf-8'):
        m = json.loads(line); j = len(t & toks(m['question'])) / max(1, len(t | toks(m['question'])))
        if j > 0.25: best.append((j, m))
    return [dict(m, similarity=round(j, 2)) for j, m in sorted(best, key=lambda x: -x[0])[:k]]

def reviewers(best, ranked, ev, conf):
    v = []
    costly = any('cost' in e['tags'] or 'credits' in e['tags'] for e in ev)
    pay = any(has(best['option'], w) for w in ('pay', 'buy', 'subscribe', 'top up'))
    v.append({'agent': 'Treasurer', 'vote': 'reject' if (pay and costly and not has(best['option'], 'free')) else 'approve',
              'reason': ('spends money while income is $0' if not has(best['option'], 'free') else 'stays free; spends only if it pays off') if (pay and costly) else 'no unplanned spend'})
    v.append({'agent': 'Lawyer', 'vote': 'reject' if best['blocked'] else 'approve',
              'reason': f"violates hard rule {best['blocked']}" if best['blocked'] else 'no hard-rule conflict (P7 boundary respected)'})
    gap = best['score'] - (ranked[1]['score'] if len(ranked) > 1 else 0)
    v.append({'agent': 'Skeptic', 'vote': 'approve' if conf >= 0.6 and gap > 0 else 'reject',
              'reason': f'margin {gap:+.1f}, confidence {conf:.2f}' + ('' if conf >= 0.6 else ' is too low')})
    return v

def llm_note(q, card):
    txt, prov = providers.chat([
        {'role': 'system', 'content': 'Explain in 3 short sentences why this decision follows from the listed rules and evidence. Do not add new facts.'},
        {'role': 'user', 'content': json.dumps({'q': q, 'action': card['action'], 'rules': card['why']['rules_applied'], 'evidence': card['why']['evidence']})}])
    return f'[{prov}] ' + txt if txt else '(LLM narration unavailable; deterministic trace is authoritative)'

def decide(question, options, use_llm=False, remember=True):
    rules = relevant_rules(question + ' ' + ' '.join(options))
    ev = evidence_for(question, rules)
    ranked = []
    for o in options:
        s, why, b = score_option(o, rules)
        ranked.append({'option': o, 'score': s, 'blocked': b, 'trace': why})
    ranked.sort(key=lambda x: (x['blocked'] is not None, -x['score']))
    best = ranked[0]
    tot = sum(abs(r['score']) for r in ranked) or 1
    conf = round(min(0.95, 0.4 + 0.5 * max(0, best['score'] - (ranked[1]['score'] if len(ranked) > 1 else 0)) / tot + 0.05 * len(ev)), 2)
    if not rules: conf = 0.3
    votes = reviewers(best, ranked, ev, conf)
    ok = sum(v['vote'] == 'approve' for v in votes)
    status = 'ready for human yes' if ok >= 2 else 'no quorum -> default NO (silence = no)'
    if best['blocked']: action = f"PREPARE ONLY, ask founder: {best['option']}"
    elif ok >= 2: action = best['option']
    else: action = 'No action yet; escalate with this card'
    card = {'id': 'D-' + datetime.datetime.now().strftime('%m%d%H%M%S%f')[:13], 'question': question, 'action': action, 'status': status,
            'confidence': conf, 'quorum': f'{ok}/3',
            'why': {'rules_applied': [{'id': r['id'], 'name': r['name'], 'text': r['text'], 'matched_on': h} for r, h in rules],
                    'evidence': ev,
                    'alternatives': [{'option': r['option'], 'score': r['score'], 'blocked_by': r['blocked'], 'trace': r['trace']} for r in ranked],
                    'reviewers': votes,
                    'would_refute': [f"if '{e['fact'][:60]}' is no longer true ({e['source']})" for e in ev[:3]],
                    'past_similar': similar_past(question)},
            'layers': dict(providers.status(), evidence_used=EVID_SRC, memory='meterless/hmem' if providers.hmem_ok() else 'local-jsonl'),
            'human_in_loop': 'Agent never executes money moves, signatures or messages as the founder; it returns a card for Yes/No/Later.'}
    if use_llm: card['why']['narration'] = llm_note(question, card)
    if remember:
        hm = providers.hmem('remember', f"{card['id']} Q: {question} -> {action}")
        card['memory'] = {'engine': 'meterless/hmem', 'id': hm['id']} if hm else {'engine': 'local-jsonl'}
        open(MEM, 'a', encoding='utf-8').write(json.dumps({'id': card['id'], 'question': question, 'action': action, 'confidence': conf}, ensure_ascii=False) + '\n')
    return card

def render(c):
    w = c['why']; L = [f"\n== {c['id']} | {c['question']}", f"ACTION: {c['action']}", f"STATUS: {c['status']} | quorum {c['quorum']} | confidence {c['confidence']}", "WHY - rules:"]
    L += [f"  {r['id']} {r['name']}: {r['text']} (matched: {', '.join(r['matched_on'])})" for r in w['rules_applied']] or ['  (no rule matched -> low confidence)']
    L += ['WHY - evidence:'] + [f"  {e['id']} {e['fact']} [{e['source']}, {e['date']}]" for e in w['evidence']]
    L += ['ALTERNATIVES:'] + [f"  {a['score']:+.0f} {a['option']}" + (f"  BLOCKED by {a['blocked_by']}" if a['blocked_by'] else '') + ''.join(f"\n      {t['rule']} {t['effect']} {t['because']}" for t in a['trace']) for a in w['alternatives']]
    L += ['REVIEWERS:'] + [f"  {v['agent']}: {v['vote']} - {v['reason']}" for v in w['reviewers']]
    L += ['WOULD REFUTE:'] + ['  ' + x for x in w['would_refute']]
    if w['past_similar']: L += [f"PAST: {p['id']} '{p['question']}' -> {p['action']} (sim {p['similarity']}, {p.get('engine','jsonl')} {p.get('memory_id','')})" for p in w['past_similar']]
    if w.get('narration'): L += ['NARRATION (LLM): ' + w['narration']]
    return '\n'.join(L)

if __name__ == '__main__':
    a = sys.argv[1:]
    llm = '--llm' in a; a = [x for x in a if x != '--llm']
    if not a or a[0] == '--demo':
        for s in json.load(open(D('scenarios.json'), encoding='utf-8')):
            print(render(decide(s['question'], s['options'], llm)))
    elif a[0] == '--json':
        print(json.dumps(decide(a[1], a[2].split('|'), llm), ensure_ascii=False, indent=1))
    else:
        print(render(decide(a[0], a[1].split('|'), llm)))
