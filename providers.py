"""Pluggable layers with honest fallbacks.
Evidence: Zetaris REST (/api/v1.0, SQL over governed sources) -> local data/evidence.json.
LLM:      Meterless Nightshift runtime (OpenAI-compatible, 127.0.0.1:8088/v1) -> Groq free tier -> none.
Metering: every LLM/evidence call writes a receipt (provider, latency, tokens) to data/receipts.jsonl."""
import json, os, time, uuid, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(HERE, 'data', 'receipts.jsonl')

def receipt(kind, provider, t0, **kw):
    r = dict(ts=time.strftime('%Y-%m-%dT%H:%M:%S'), kind=kind, provider=provider, ms=int((time.time() - t0) * 1000), **kw)
    open(REC, 'a', encoding='utf-8').write(json.dumps(r) + '\n'); return r

def _post(url, body, headers, timeout=30):
    rq = urllib.request.Request(url, json.dumps(body).encode(), dict({'Content-Type': 'application/json', 'User-Agent': 'why-agent/0.2'}, **headers))
    return json.load(urllib.request.urlopen(rq, timeout=timeout))

# ---------- evidence
def zetaris_evidence(sql):
    """Run SQL on Zetaris (env ZETARIS_REST_URL, ZETARIS_API_KEY, ZETARIS_ORG_ID). Rows -> evidence dicts.
    Expected view: why_agent.evidence(id, fact, source, date, tags) with tags as comma string."""
    url, key, org = (os.environ.get(k) for k in ('ZETARIS_REST_URL', 'ZETARIS_API_KEY', 'ZETARIS_ORG_ID'))
    if not (url and key and org): return None
    t0 = time.time()
    try:
        out = _post(url.rstrip('/') + '/query', {'sql': sql}, {'Authorization': 'Bearer ' + key, 'X-Org-ID': org, 'X-Request-ID': str(uuid.uuid4())})
        rows = out.get('rows') or out.get('data') or []
        ev = [dict(r, tags=[x.strip() for x in str(r.get('tags', '')).split(',') if x.strip()]) for r in rows]
        receipt('evidence', 'zetaris', t0, rows=len(ev)); return ev
    except Exception as e:
        receipt('evidence', 'zetaris', t0, error=type(e).__name__); return None

def load_evidence():
    ev = zetaris_evidence('SELECT id, fact, source, date, tags FROM why_agent.evidence')
    if ev: return ev, 'zetaris'
    t0 = time.time(); ev = json.load(open(os.path.join(HERE, 'data', 'evidence.json'), encoding='utf-8'))
    receipt('evidence', 'local-json', t0, rows=len(ev)); return ev, 'local-json'

# ---------- llm
def _meterless_cfg():
    base = os.environ.get('METERLESS_BASE_URL', 'http://127.0.0.1:8088/v1').rstrip('/')
    tok = os.environ.get('METERLESS_TOKEN')
    if not tok:
        p = os.environ.get('METERLESS_TOKEN_FILE')
        if p and os.path.exists(p): tok = open(p).read().strip()
    return base, tok

def chat(messages, max_tokens=220):
    """Returns (text, provider). Tries Meterless, then Groq. Never raises."""
    base, tok = _meterless_cfg()
    if tok:
        t0 = time.time()
        try:
            o = _post(base + '/chat/completions', {'model': 'meterless/auto', 'messages': messages, 'max_tokens': max_tokens},
                      {'Authorization': 'Bearer ' + tok, 'meterless-app': 'why-agent', 'meterless-scope': 'user'}, timeout=180)
            receipt('llm', 'meterless', t0, tokens=o.get('usage', {}).get('total_tokens'))
            return o['choices'][0]['message']['content'].strip(), 'meterless'
        except Exception as e: receipt('llm', 'meterless', t0, error=type(e).__name__)
    key = os.environ.get('GROQ_API_KEY')
    if key:
        t0 = time.time()
        try:
            o = _post('https://api.groq.com/openai/v1/chat/completions', {'model': 'openai/gpt-oss-120b', 'temperature': 0.2, 'max_tokens': max_tokens, 'messages': messages},
                      {'Authorization': 'Bearer ' + key}, timeout=30)
            receipt('llm', 'groq', t0, tokens=o.get('usage', {}).get('total_tokens'))
            return o['choices'][0]['message']['content'].strip(), 'groq'
        except Exception as e: receipt('llm', 'groq', t0, error=type(e).__name__)
    return None, 'none'

def status():
    base, tok = _meterless_cfg()
    z = all(os.environ.get(k) for k in ('ZETARIS_REST_URL', 'ZETARIS_API_KEY', 'ZETARIS_ORG_ID'))
    return {'evidence': 'zetaris' if z else 'local-json (Zetaris not configured)',
            'llm': 'meterless' if tok else ('groq' if os.environ.get('GROQ_API_KEY') else 'none'), 'meterless_base': base}

# ---------- decision memory: Meterless H-MEM engine (hmem/bridge.ts), fallback JSONL
import subprocess
HM = os.path.join(HERE, 'hmem')
def hmem_ok(): return os.path.isdir(os.path.join(HM, 'vendor', 'hmem')) and os.path.isdir(os.path.join(HM, 'node_modules'))
def hmem(cmd, arg):
    if not hmem_ok() or os.environ.get('WHY_NO_HMEM'): return None
    t0 = time.time()
    try:
        p = subprocess.run([os.path.join(HM, 'node_modules', '.bin', 'tsx'), 'bridge.ts', cmd, arg], cwd=HM, capture_output=True, text=True, timeout=60)
        o = json.loads(p.stdout); receipt('memory', 'meterless/hmem', t0, op=cmd); return o
    except Exception as e:
        receipt('memory', 'meterless/hmem', t0, op=cmd, error=type(e).__name__); return None
