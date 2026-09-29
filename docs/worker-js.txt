/* Loads price files and runs backtests off the main thread. */
importScripts("engine.js");

const store = { daily: new Map(), intraday: new Map() };

async function loadMany(tf, files, id) {
  const need = files.filter((f) => !store[tf].has(f));
  let done = files.length - need.length, bytes = 0, failed = [];
  const total = files.length;
  postMessage({ type: "progress", id, done, total, phase: "load" });
  let idx = 0;
  async function next() {
    while (idx < need.length) {
      const f = need[idx++];
      try {
        const r = await fetch(`data/${tf}/${encodeURIComponent(f)}`);
        if (!r.ok) throw new Error(r.status);
        const txt = await r.text(); bytes += txt.length;
        const j = JSON.parse(txt);
        store[tf].set(f, j);
      } catch (e) { failed.push(f); store[tf].set(f, null); }
      done++;
      if (done % 5 === 0 || done === total) postMessage({ type: "progress", id, done, total, phase: "load" });
    }
  }
  await Promise.all(Array.from({ length: 12 }, next));
  return failed;
}

onmessage = async (ev) => {
  const m = ev.data;
  if (m.type !== "run") return;
  const { id, tf, stocks, strategy } = m;
  try {
    const t0 = performance.now();
    const failed = await loadMany(tf, stocks.map((s) => s.f), id);
    const trades = [], signals = [];
    let errors = new Set(), bars = 0, first = Infinity, last = 0;
    stocks.forEach((s, k) => {
      const b = store[tf].get(s.f);
      if (!b || !b.c || b.c.length < 2) return;
      const keyArr = b.t || b.d;
      bars += b.c.length; first = Math.min(first, keyArr[0]); last = Math.max(last, keyArr[keyArr.length - 1]);
      try {
        for (const t of BT.simulate(s.s, b, strategy)) trades.push(t);
        const sig = BT.lastSignal(s.s, b, strategy);
        if (sig) signals.push(sig);
      } catch (e) { errors.add(e.message); }
      if (k % 20 === 0) postMessage({ type: "progress", id, done: k + 1, total: stocks.length, phase: "test" });
    });
    const st = BT.stats(trades);
    postMessage({ type: "result", id, stats: st, trades: trades.filter((t) => !t.pending), signals, failed,
      errors: [...errors], bars, first, last, ms: Math.round(performance.now() - t0), tested: stocks.length });
  } catch (e) {
    postMessage({ type: "error", id, message: e.message });
  }
};
