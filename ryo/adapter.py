"""RYO-CHAN research-API evidence adapter for Why-Agent.

Calls RYO's read-only research tools over MCP (JSON-RPC 2.0 `tools/call`) at
RYO_MCP_URL (default https://app-ryochan.com/api/mcp) with `Authorization: Bearer $RYO_MCP_KEY`.
Tools: market_overview, scan_market, analyze_token, deep_analysis, compare_tokens,
check_safety, supported_tokens.

Honesty convention: missing data stays missing. If the key is unset or a call fails,
the adapter returns an explicit `unavailable` evidence item with the reason. It never
invents a number. Every call writes a receipt (provider ryo/<tool>).
The adapter is read-only. Practice trades stay on the builder side (see ryo/practice.py)."""
import json, os, time, urllib.request, itertools
from providers import receipt

TOOLS = ('market_overview', 'scan_market', 'analyze_token', 'deep_analysis',
         'compare_tokens', 'check_safety', 'supported_tokens')
_ids = itertools.count(1)

def _url(): return os.environ.get('RYO_MCP_URL', 'https://app-ryochan.com/api/mcp')

def _rpc(method, params, transport=None, timeout=40):
    body = {'jsonrpc': '2.0', 'id': next(_ids), 'method': method, 'params': params}
    if transport: return transport(body)
    key = os.environ.get('RYO_MCP_KEY')
    if not key: raise PermissionError('RYO_MCP_KEY not set')
    rq = urllib.request.Request(_url(), json.dumps(body).encode(), {
        'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
        'Authorization': 'Bearer ' + key, 'User-Agent': 'why-agent-ryo/0.1'})
    raw = urllib.request.urlopen(rq, timeout=timeout).read().decode()
    if raw.lstrip().startswith(('event:', 'data:')):  # streamable-HTTP SSE answer
        raw = [l[5:].strip() for l in raw.splitlines() if l.startswith('data:')][-1]
    return json.loads(raw)

def call(tool, args=None, transport=None):
    """Returns (data, None) or (None, reason). Never fabricates."""
    if tool not in TOOLS: return None, 'unknown tool ' + tool
    t0 = time.time()
    try:
        out = _rpc('tools/call', {'name': tool, 'arguments': args or {}}, transport)
        if 'error' in out: raise RuntimeError(out['error'].get('message', 'rpc error'))
        res = out.get('result', {})
        if res.get('isError'): raise RuntimeError('tool error')
        data = res.get('structuredContent')
        if data is None:
            txt = ''.join(c.get('text', '') for c in res.get('content', []) if c.get('type') == 'text')
            try: data = json.loads(txt)
            except ValueError: data = {'text': txt}
        receipt('evidence', 'ryo/' + tool, t0, ok=True); return data, None
    except Exception as e:
        reason = '%s: %s' % (type(e).__name__, str(e)[:120])
        receipt('evidence', 'ryo/' + tool, t0, error=type(e).__name__); return None, reason

def _fmt(v):
    return json.dumps(v, ensure_ascii=False)[:240] if isinstance(v, (dict, list)) else str(v)

def evidence(symbols, deep=False, transport=None):
    """Turn RYO research into Why-Agent evidence items: {id, fact, source, date, tags}.
    Fields RYO marks missing/unavailable are kept as explicit gaps."""
    day = time.strftime('%Y-%m-%d'); ev = []
    plan = [('market_overview', {})]
    for s in symbols:
        plan += [('deep_analysis' if deep else 'analyze_token', {'symbol': s}), ('check_safety', {'symbol': s})]
    if len(symbols) >= 2: plan.append(('compare_tokens', {'symbols': list(symbols)[:4]}))
    for tool, args in plan:
        data, err = call(tool, args, transport)
        tag = [tool.split('_')[0], 'ryo', 'market'] + [x.lower() for x in args.get('symbols', [args.get('symbol')]) if x]
        if err:
            ev.append(dict(id='ryo-%s-gap' % tool, fact='UNAVAILABLE: %s (%s). Not used as fact.' % (tool, err),
                           source='RYO %s' % tool, date=day, tags=tag + ['gap'], unavailable=True)); continue
        items = data.items() if isinstance(data, dict) else enumerate(data or [])
        for k, v in list(items)[:6]:
            missing = v is None or (isinstance(v, dict) and (v.get('status') in ('unavailable', 'missing') or v.get('missing')))
            ev.append(dict(id='ryo-%s-%s' % (tool, k), source='RYO %s' % tool, date=day, tags=tag + (['gap'] if missing else []),
                           fact=('MISSING: %s' % k) if missing else '%s: %s' % (k, _fmt(v)), unavailable=bool(missing)))
    return ev
