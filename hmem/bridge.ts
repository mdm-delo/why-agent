// Why-Agent <-> Meterless H-MEM bridge. JSON in/out on stdout.
//   tsx bridge.ts remember '<json card summary>'   -> {id}
//   tsx bridge.ts recall "<question>"              -> {memories:[{id,relevance,content}], strategy}
//   tsx bridge.ts audit <id>                        -> {history:[...]}
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadHMEM } from "./src/engine.ts";
const here = path.dirname(fileURLToPath(import.meta.url));
const [cmd, ...rest] = process.argv.slice(2); const arg = rest.join(" ");
const { HMEM, source } = await loadHMEM();
const hmem = new HMEM({ persistDir: process.env.HMEM_DIR || path.join(here, ".whyagent") });
let out: any = { engine: "meterless/hmem", source };
if (cmd === "remember") {
  const r = hmem.add({ content: arg, type: "decision", source: "why-agent" });
  out.id = r.id; out.layer = r.layer;
} else if (cmd === "recall") {
  const res = hmem.query(arg, { threshold: 0.1 });
  out.strategy = res.trace.strategy;
  out.memories = res.memories.slice(0, 3).map((m: any) => ({ id: m.memory.id, relevance: Math.round(m.relevance * 100) / 100, content: m.memory.content }));
} else if (cmd === "audit") {
  out.history = hmem.ledger.history(arg).map((e: any) => ({ action: e.action, actor: e.actor, ts: new Date(e.timestamp).toISOString() }));
}
process.stdout.write(JSON.stringify(out));
