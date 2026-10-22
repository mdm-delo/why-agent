#!/usr/bin/env python3
"""Tiny web demo: python3 server.py [port] -> http://localhost:8765"""
import json, sys, os
from http.server import HTTPServer, SimpleHTTPRequestHandler
import agent
WEB = os.path.join(agent.HERE, 'web')
class H(SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=WEB, **k)
    def do_GET(s):
        if s.path == '/api/scenarios': return s.send_json(json.load(open(agent.D('scenarios.json'), encoding='utf-8')))
        return super().do_GET()
    def do_POST(s):
        b = json.loads(s.rfile.read(int(s.headers.get('Content-Length', 0))) or '{}')
        opts = [o.strip() for o in b.get('options', []) if o.strip()]
        if not b.get('question') or len(opts) < 2: return s.send_json({'error': 'question and 2+ options required'}, 400)
        s.send_json(agent.decide(b['question'], opts, bool(b.get('llm'))))
    def send_json(s, o, code=200):
        d = json.dumps(o, ensure_ascii=False).encode(); s.send_response(code)
        s.send_header('Content-Type', 'application/json; charset=utf-8'); s.send_header('Content-Length', len(d)); s.end_headers(); s.wfile.write(d)
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
print(f'Why-Agent demo on http://localhost:{port}'); HTTPServer(('0.0.0.0', port), H).serve_forever()
