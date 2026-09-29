/* UI for the Strategy Backtester */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  };
  const O = BT.OPERANDS, P = BT.PATTERNS;

  /* ---------- theme ---------- */
  const th = store.get("bt_theme", null); if (th) document.documentElement.dataset.theme = th;
  $("#themeBtn").onclick = () => {
    const dark = matchMedia("(prefers-color-scheme: dark)").matches;
    const cur = document.documentElement.dataset.theme || (dark ? "dark" : "light");
    const nx = cur === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = nx; store.set("bt_theme", nx);
    if (lastResult) drawEquity(lastResult.stats);
  };

  /* ---------- presets ---------- */
  const op = (k, p, extra) => Object.assign({ k }, p ? { p } : {}, extra || {});
  const num = (v) => ({ k: "value", v });
  const C = (a, o, b) => ({ a, op: o, b });
  const base = { side: "long", logic: "all", entry: "next", sl: { type: "pct", v: 5 }, tg: { type: "pct", v: 10 }, trail: 0, maxBars: 20, exitConds: [], exitLogic: "any", cost: 0.1, atrLen: 14, lastEntryTime: 1500, squareOff: 1515 };
  const PRESETS = [
    { id: "golden", tf: "daily", name: "Golden cross (SMA 50 crosses above SMA 200)", s: { conds: [C(op("sma", [50]), "xa", op("sma", [200]))], sl: { type: "pct", v: 8 }, tg: { type: "pct", v: 20 }, maxBars: 120 } },
    { id: "rsi", tf: "daily", name: "RSI oversold bounce in an uptrend", s: { conds: [C(op("rsi", [14]), "xa", num(30)), C(op("close"), ">", op("sma", [200]))], sl: { type: "pct", v: 5 }, tg: { type: "pct", v: 10 }, maxBars: 20 } },
    { id: "52w", tf: "daily", name: "52-week high breakout on volume", s: { conds: [C(op("close"), ">", op("hh", [250])), C(op("volume"), ">", op("avgvol", [20], { mul: 1.5 }))], sl: { type: "pct", v: 7 }, tg: { type: "pct", v: 15 }, trail: 8, maxBars: 60 } },
    { id: "ema", tf: "daily", name: "EMA 9 crosses above EMA 21", s: { conds: [C(op("ema", [9]), "xa", op("ema", [21]))], sl: { type: "pct", v: 3 }, tg: { type: "pct", v: 6 }, maxBars: 15 } },
    { id: "st", tf: "daily", name: "Supertrend (10,3) turns bullish", s: { conds: [C(op("close"), "xa", op("st", [10, 3]))], sl: { type: "atr", v: 2 }, tg: { type: "r", v: 2 }, maxBars: 30 } },
    { id: "bb", tf: "daily", name: "Bollinger lower-band bounce, exit at middle band", s: { conds: [C(op("close"), "xa", op("bbl", [20, 2]))], sl: { type: "pct", v: 4 }, tg: { type: "none", v: 0 }, exitConds: [C(op("close"), ">", op("bbm", [20]))], maxBars: 20 } },
    { id: "macd", tf: "daily", name: "MACD crosses signal above zero", s: { conds: [C(op("macd", [12, 26]), "xa", op("macds", [12, 26, 9])), C(op("macd", [12, 26]), ">", num(0))], sl: { type: "pct", v: 5 }, tg: { type: "pct", v: 10 }, maxBars: 30 } },
    { id: "engulf", tf: "daily", name: "Bullish engulfing when RSI < 40", s: { conds: [{ pat: "bull_engulf" }, C(op("rsi", [14]), "<", num(40))], sl: { type: "level", v: 0, op: op("ll", [5]) }, tg: { type: "r", v: 2 }, maxBars: 15 } },
    { id: "vbo", tf: "daily", name: "20-day breakout with 2× volume", s: { conds: [C(op("close"), ">", op("hh", [20])), C(op("volume"), ">", op("avgvol", [20], { mul: 2 }))], sl: { type: "pct", v: 5 }, tg: { type: "pct", v: 12 }, maxBars: 30 } },
    { id: "nr7", tf: "daily", name: "NR7 narrow-range candle, stop below its low", s: { conds: [{ pat: "nr7" }], entry: "next", sl: { type: "level", v: 0, op: op("low") }, tg: { type: "r", v: 2 }, maxBars: 10 } },
    { id: "death", tf: "daily", name: "Short: death cross (SMA 50 below SMA 200)", s: { side: "short", conds: [C(op("sma", [50]), "xb", op("sma", [200]))], sl: { type: "pct", v: 8 }, tg: { type: "pct", v: 15 }, maxBars: 60 } },
    { id: "orb", tf: "intraday", name: "Opening range breakout (first 15-min candle)", s: { conds: [C(op("close"), "xa", op("orh", [1])), C(op("time"), "<=", num(1100))], sl: { type: "level", v: 0, op: op("orl", [1]) }, tg: { type: "r", v: 2 }, maxBars: 0, cost: 0.05 } },
    { id: "vwap", tf: "intraday", name: "Price crosses above VWAP with RSI > 55", s: { conds: [C(op("close"), "xa", op("vwap")), C(op("rsi", [14]), ">", num(55)), C(op("time"), ">=", num(945))], sl: { type: "pct", v: 0.7 }, tg: { type: "pct", v: 1.4 }, maxBars: 0, cost: 0.05 } },
    { id: "pdh", tf: "intraday", name: "Previous day high breakout", s: { conds: [C(op("close"), "xa", op("pdh"))], sl: { type: "pct", v: 1 }, tg: { type: "pct", v: 2 }, maxBars: 0, cost: 0.05 } },
    { id: "iema", tf: "intraday", name: "EMA 9/21 crossover (15-min)", s: { conds: [C(op("ema", [9]), "xa", op("ema", [21])), C(op("close"), ">", op("vwap"))], sl: { type: "pct", v: 0.8 }, tg: { type: "pct", v: 1.6 }, maxBars: 0, cost: 0.05 } },
    { id: "gapfill", tf: "intraday", name: "Short: gap-up > 2% fails below day open", s: { side: "short", conds: [], sl: { type: "pct", v: 1 }, tg: { type: "pct", v: 2 }, maxBars: 0, cost: 0.05 } },
  ];
  // gap operand is only defined on a day's first bar intraday; make the gapfill preset use prior-bar logic instead
  PRESETS.find((p) => p.id === "gapfill").s.conds = [C(op("dopen"), ">", op("pdc", null, { mul: 1.02 })), C(op("close"), "xb", op("dopen"))];

  const blank = () => JSON.parse(JSON.stringify(Object.assign({ tf: "daily", universe: "50", custom: "", from: "", to: "" }, base, PRESETS[1].s)));
  let S = blank();

  /* ---------- operand select ---------- */
  const GROUPS = [
    ["Price", ["close", "open", "high", "low", "roc", "gap", "body", "range"]],
    ["Moving averages", ["sma", "ema", "st"]],
    ["Momentum", ["rsi", "macd", "macds", "macdh", "stk", "std", "adx", "pdi", "mdi"]],
    ["Bands & volatility", ["bbu", "bbm", "bbl", "atr"]],
    ["Breakout levels", ["hh", "ll", "hc", "lc"]],
    ["Volume", ["volume", "avgvol"]],
    ["Intraday only", ["vwap", "dopen", "pdh", "pdl", "pdc", "orh", "orl", "time"]],
    ["Number", ["value"]],
  ];
  const opLabel = (o) => {
    if (!o) return "?";
    if (o.k === "value") return String(o.v);
    const d = O[o.k]; if (!d) return o.k;
    const p = d.params.map((pp, i) => (o.p && o.p[i] != null ? o.p[i] : pp.d));
    let s = d.label.replace(/ \((prev N bars|intraday|HHMM, intraday|first N bars)\)/, "") + (p.length ? `(${p.join(",")})` : "");
    if (o.k === "hh" && p[0] >= 240) s = `${p[0]}-day high`;
    if (Number(o.off)) s += ` ${o.off} bar${o.off > 1 ? "s" : ""} ago`;
    if (o.mul != null && o.mul !== "" && Number(o.mul) !== 1) s += ` × ${o.mul}`;
    return s;
  };
  const OPS = { ">": "is above", "<": "is below", ">=": "is at or above", "<=": "is at or below", xa: "crosses above", xb: "crosses below" };
  const condLabel = (c) => c.pat ? `${c.not ? "not " : ""}${P[c.pat].label}` : `${opLabel(c.a)} ${OPS[c.op]} ${opLabel(c.b)}`;

  function operandEditor(o, onChange, allowValue = true) {
    const wrap = document.createElement("span"); wrap.className = "opnd";
    const sel = document.createElement("select");
    GROUPS.forEach(([g, ks]) => {
      if (!allowValue && g === "Number") return;
      const og = document.createElement("optgroup"); og.label = g;
      ks.forEach((k) => { const opt = new Option(O[k].label, k); og.appendChild(opt); });
      sel.appendChild(og);
    });
    sel.value = o.k;
    sel.onchange = () => {
      o.k = sel.value; o.p = O[o.k].params.map((pp) => pp.d);
      if (o.k === "value") { o.v = o.v ?? 0; delete o.off; delete o.mul; }
      onChange(true);
    };
    wrap.appendChild(sel);
    if (o.k === "value") {
      const inp = document.createElement("input"); inp.type = "number"; inp.step = "any"; inp.value = o.v ?? 0; inp.style.width = "72px";
      inp.oninput = () => { o.v = Number(inp.value); onChange(false); };
      wrap.appendChild(inp); return wrap;
    }
    O[o.k].params.forEach((pp, i) => {
      const inp = document.createElement("input"); inp.type = "number"; inp.step = "any"; inp.title = pp.n;
      inp.value = o.p && o.p[i] != null ? o.p[i] : pp.d; inp.placeholder = pp.n;
      inp.oninput = () => { o.p = o.p || O[o.k].params.map((q) => q.d); o.p[i] = Number(inp.value); onChange(false); };
      wrap.appendChild(inp);
    });
    const more = document.createElement("span"); more.className = "mini";
    more.innerHTML = `<span title="Look at the value N candles ago">ago</span> <input type="number" min="0" style="width:40px" value="${o.off || 0}"> × <input type="number" step="any" style="width:52px" value="${o.mul ?? 1}">`;
    const used = Number(o.off) || (o.mul != null && o.mul !== "" && Number(o.mul) !== 1);
    if (!used) {
      more.style.display = "none";
      const t = document.createElement("button"); t.type = "button"; t.className = "btn ghost small"; t.textContent = "⋯"; t.title = "Options: value N candles ago, or multiply (e.g. 1.5 × average volume)";
      t.onclick = () => { more.style.display = ""; t.remove(); };
      wrap.appendChild(t);
    }
    const [offI, mulI] = more.querySelectorAll("input");
    offI.title = "Look at the value N candles ago (0 = current candle)"; mulI.title = "Multiply the value, e.g. 1.5 × average volume";
    offI.oninput = () => { o.off = Number(offI.value) || 0; onChange(false); };
    mulI.oninput = () => { o.mul = mulI.value === "" ? 1 : Number(mulI.value); onChange(false); };
    wrap.appendChild(more);
    return wrap;
  }

  function condEditor(list, idx, container, rerender) {
    const c = list[idx];
    const box = document.createElement("div"); box.className = "cond";
    const top = document.createElement("div"); top.className = "top"; box.appendChild(top);
    const changed = (structural) => { if (structural) rerender(); updateSummary(); persist(); };
    if (c.pat) {
      const lab = document.createElement("span"); lab.textContent = "Candle is"; lab.className = "hint";
      const notSel = document.createElement("select"); notSel.innerHTML = `<option value="">a</option><option value="1">NOT a</option>`; notSel.value = c.not ? "1" : "";
      notSel.onchange = () => { c.not = !!notSel.value; changed(false); };
      const ps = document.createElement("select");
      Object.entries(P).forEach(([k, v]) => ps.appendChild(new Option(v.label, k))); ps.value = c.pat;
      ps.onchange = () => { c.pat = ps.value; changed(false); };
      top.append(lab, notSel, ps);
    } else {
      top.appendChild(operandEditor(c.a, changed, false));
      const os = document.createElement("select"); os.className = "opsel";
      Object.entries(OPS).forEach(([k, v]) => os.appendChild(new Option(v, k))); os.value = c.op;
      os.onchange = () => { c.op = os.value; changed(false); };
      top.appendChild(os);
      top.appendChild(operandEditor(c.b, changed, true));
    }
    const x = document.createElement("button"); x.className = "btn ghost small x"; x.textContent = "✕"; x.title = "Remove";
    x.onclick = () => { list.splice(idx, 1); rerender(); updateSummary(); persist(); };
    top.appendChild(x);
    container.appendChild(box);
  }
  function renderConds() {
    const box = $("#conds"); box.innerHTML = "";
    S.conds.forEach((_, i) => condEditor(S.conds, i, box, renderConds));
    if (!S.conds.length) box.innerHTML = `<div class="hint" style="margin-bottom:8px">No conditions yet — add one below or load a ready-made strategy.</div>`;
    const eb = $("#exitConds"); eb.innerHTML = "";
    S.exitConds.forEach((_, i) => condEditor(S.exitConds, i, eb, renderConds));
  }
  $("#addCond").onclick = () => { S.conds.push(C(op("close"), ">", op("sma", [50]))); renderConds(); updateSummary(); persist(); };
  $("#addPat").onclick = () => { S.conds.push({ pat: "bull_engulf" }); renderConds(); updateSummary(); persist(); };
  $("#addExit").onclick = () => { S.exitConds.push(C(op("close"), "<", op("ema", [20]))); renderConds(); updateSummary(); persist(); };

  /* ---------- SL level operand ---------- */
  function renderSlLevel() {
    const box = $("#slLevel"); box.innerHTML = "";
    $("#slV").style.display = S.sl.type === "level" || S.sl.type === "none" ? "none" : "";
    $("#tgV").style.display = S.tg.type === "none" ? "none" : "";
    if (S.sl.type === "level") {
      S.sl.op = S.sl.op || op("ll", [10]);
      box.appendChild(operandEditor(S.sl.op, (st) => { if (st) renderSlLevel(); updateSummary(); persist(); }, false));
    }
  }

  /* ---------- form <-> state ---------- */
  const ymd = (v) => (v ? Number(v.replace(/-/g, "")) : "");
  const dstr = (n) => (n ? `${String(n).slice(0, 4)}-${String(n).slice(4, 6)}-${String(n).slice(6, 8)}` : "");
  function seg(id, key, cb) {
    const el = $(id);
    const paint = () => el.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.v === S[key]));
    el.onclick = (e) => { const b = e.target.closest("button"); if (!b) return; S[key] = b.dataset.v; paint(); cb && cb(); updateSummary(); persist(); };
    return paint;
  }
  const paintTf = seg("#tfSeg", "tf", () => { fillPresets(); tfUI(); });
  const paintSide = seg("#sideSeg", "side");
  function tfUI() {
    const intra = S.tf === "intraday";
    $("#intraRow").style.display = intra ? "" : "none";
    $("#maxHint").textContent = intra ? "15-min candles (0 = until square-off)" : "trading days (0 = no limit)";
    $("#rangeHint").textContent = intra ? "Intraday data covers only the last ~60 trading days (a free-data limit), so treat results as a quick check." : "Daily data goes back about 10 years. Leave the dates empty to test the full history.";
  }
  function fillForm() {
    paintTf(); paintSide(); tfUI();
    $("#universe").value = S.universe; $("#custom").value = S.custom || ""; $("#custom").style.display = S.universe === "custom" ? "" : "none";
    $("#from").value = dstr(S.from); $("#to").value = dstr(S.to);
    $("#logic").value = S.logic; $("#exitLogic").value = S.exitLogic || "any"; $("#entry").value = S.entry;
    $("#slType").value = S.sl.type; $("#slV").value = S.sl.v; $("#tgType").value = S.tg.type; $("#tgV").value = S.tg.v;
    ["trail", "maxBars", "cost", "atrLen", "lastEntryTime", "squareOff"].forEach((k) => ($("#" + k).value = S[k]));
    if (S.exitConds.length) $("#exitDetails").open = true;
    renderConds(); renderSlLevel(); updateSummary();
  }
  const bind = (id, fn, ev = "input") => { $(id).addEventListener(ev, () => { fn($(id).value); updateSummary(); persist(); }); };
  bind("#universe", (v) => { S.universe = v; $("#custom").style.display = v === "custom" ? "" : "none"; }, "change");
  bind("#custom", (v) => (S.custom = v));
  bind("#from", (v) => (S.from = ymd(v)), "change"); bind("#to", (v) => (S.to = ymd(v)), "change");
  bind("#logic", (v) => (S.logic = v), "change"); bind("#exitLogic", (v) => (S.exitLogic = v), "change"); bind("#entry", (v) => (S.entry = v), "change");
  bind("#slType", (v) => { S.sl.type = v; renderSlLevel(); }, "change"); bind("#slV", (v) => (S.sl.v = Number(v)));
  bind("#tgType", (v) => { S.tg.type = v; renderSlLevel(); }, "change"); bind("#tgV", (v) => (S.tg.v = Number(v)));
  ["trail", "maxBars", "cost", "atrLen", "lastEntryTime", "squareOff"].forEach((k) => bind("#" + k, (v) => (S[k] = Number(v))));

  function updateSummary() {
    const side = S.side === "short" ? "Sell short" : "Buy";
    const glue = S.logic === "any" ? " OR " : " AND ";
    const conds = S.conds.length ? S.conds.map(condLabel).join(glue) : "(no conditions)";
    const at = S.entry === "close" ? "at that candle's close" : "at the next candle's open";
    const sl = S.sl.type === "pct" ? `${S.sl.v}% stop` : S.sl.type === "atr" ? `${S.sl.v}×ATR stop` : S.sl.type === "level" ? `stop at ${opLabel(S.sl.op)}` : "no stop";
    const tg = S.tg.type === "pct" ? `${S.tg.v}% target` : S.tg.type === "atr" ? `${S.tg.v}×ATR target` : S.tg.type === "r" ? `${S.tg.v}R target` : "no fixed target";
    const extra = [S.trail > 0 ? `${S.trail}% trailing stop` : "", S.maxBars > 0 ? `exit after ${S.maxBars} ${S.tf === "intraday" ? "candles" : "days"}` : "", S.tf === "intraday" ? `square off ${fmtT(S.squareOff)}` : "", S.exitConds.length ? "exit condition" : ""].filter(Boolean).join(", ");
    $("#summary").innerHTML = `<b>${side}</b> when ${esc(conds)}, ${at}. ${esc(sl)}, ${esc(tg)}${extra ? ", " + esc(extra) : ""}.`;
  }
  const fmtT = (n) => { const s = String(n).padStart(4, "0"); return s.slice(0, 2) + ":" + s.slice(2); };

  /* ---------- presets / saved / share ---------- */
  function fillPresets() {
    const sel = $("#preset"); sel.innerHTML = `<option value="">Load a ready-made strategy…</option>`;
    PRESETS.filter((p) => p.tf === S.tf).forEach((p) => sel.appendChild(new Option(p.name, p.id)));
  }
  $("#preset").onchange = (e) => {
    const p = PRESETS.find((x) => x.id === e.target.value); if (!p) return;
    const keep = { tf: S.tf, universe: S.universe, custom: S.custom, from: S.from, to: S.to };
    S = JSON.parse(JSON.stringify(Object.assign({}, base, p.s, keep, { tf: p.tf, name: p.name })));
    S.exitConds = S.exitConds || [];
    fillForm(); persist();
  };
  function persist() { store.set("bt_last", S); }
  function savedList() { return store.get("bt_saved", {}); }
  function fillSaved() {
    const sel = $("#savedSel"), all = savedList();
    sel.innerHTML = `<option value="">Saved strategies…</option>` + Object.keys(all).sort().map((k) => `<option>${esc(k)}</option>`).join("") + (Object.keys(all).length ? `<option value="__del">Delete a saved strategy…</option>` : "");
  }
  $("#saveBtn").onclick = () => {
    const name = prompt("Name this strategy:", S.name || ""); if (!name) return;
    const all = savedList(); S.name = name; all[name] = JSON.parse(JSON.stringify(S)); store.set("bt_saved", all); fillSaved(); status(`Saved “${name}” in this browser.`);
  };
  $("#savedSel").onchange = (e) => {
    const all = savedList(), v = e.target.value; e.target.value = "";
    if (v === "__del") { const n = prompt("Type the name to delete:\n" + Object.keys(all).join("\n")); if (n && all[n]) { delete all[n]; store.set("bt_saved", all); fillSaved(); } return; }
    if (all[v]) { S = JSON.parse(JSON.stringify(all[v])); S.exitConds = S.exitConds || []; fillForm(); fillPresets(); persist(); }
  };
  $("#shareBtn").onclick = async () => {
    const url = location.origin + location.pathname + "#s=" + btoa(unescape(encodeURIComponent(JSON.stringify(S))));
    try { await navigator.clipboard.writeText(url); status("Link copied — open it anywhere to load this exact strategy."); }
    catch { prompt("Copy this link:", url); }
  };

  /* ---------- data info ---------- */
  let UNIVERSE = [];
  fetch("data/meta.json", { cache: "no-store" }).then((r) => r.json()).then((m) => {
    $("#dataInfo").textContent = `Nifty 500 · ${m.stocks} stocks · data updated ${new Date(m.updated).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}`;
  }).catch(() => ($("#dataInfo").textContent = "No price data yet — run the GitHub Action once"));
  fetch("data/universe.json", { cache: "no-store" }).then((r) => r.json()).then((u) => (UNIVERSE = u)).catch(() => {});

  /* ---------- running ---------- */
  const worker = new Worker("worker.js");
  let runId = 0, lastResult = null;
  const status = (t) => ($("#status").textContent = t);
  function pickStocks() {
    const avail = UNIVERSE.filter((u) => (S.tf === "intraday" ? u.it : u.dy));
    if (S.universe === "custom") {
      const want = new Set(String(S.custom).toUpperCase().split(/[\s,;]+/).filter(Boolean));
      return avail.filter((u) => want.has(u.s));
    }
    return avail.filter((u) => u.u <= Number(S.universe));
  }
  function validate() {
    if (!S.conds.length) return "Add at least one entry condition.";
    const intraOnly = (o) => o && O[o.k] && O[o.k].intra;
    if (S.tf === "daily") {
      const all = [...S.conds, ...S.exitConds].flatMap((c) => (c.pat ? [] : [c.a, c.b]));
      if (S.sl.type === "level") all.push(S.sl.op);
      const bad = all.find(intraOnly);
      if (bad) return `“${O[bad.k].label}” only works with 15-min intraday data. Switch to intraday or pick another indicator.`;
    }
    if (S.sl.type === "none" && S.tg.type === "none" && !S.maxBars && !S.exitConds.length && S.tf === "daily" && !S.trail) return "Add at least one way to exit: a stop loss, target, trailing stop, max hold or exit condition.";
    return null;
  }
  $("#runBtn").onclick = () => {
    const err = validate(); if (err) { status(err); return; }
    const stocks = pickStocks();
    if (!stocks.length) { status(UNIVERSE.length ? "No matching stocks — check the symbols in your list." : "Price data isn't available yet."); return; }
    const id = ++runId;
    $("#runBtn").disabled = true; $("#prog").style.display = "block"; $("#prog b").style.width = "0";
    status(`Loading ${stocks.length} stocks… (first run downloads the data; later runs are instant)`);
    worker.postMessage({ type: "run", id, tf: S.tf, stocks: stocks.map((s) => ({ s: s.s, f: s.f })), strategy: JSON.parse(JSON.stringify(S)) });
  };
  worker.onmessage = (ev) => {
    const m = ev.data; if (m.id !== runId) return;
    if (m.type === "progress") {
      $("#prog b").style.width = (m.phase === "load" ? 70 * m.done / m.total : 70 + 30 * m.done / m.total) + "%";
      status(m.phase === "load" ? `Loading price data ${m.done}/${m.total}…` : `Testing ${m.done}/${m.total} stocks…`);
      return;
    }
    $("#runBtn").disabled = false; $("#prog").style.display = "none";
    if (m.type === "error") { status("Something went wrong: " + m.message); return; }
    lastResult = m; render(m);
    status(`Done: ${m.tested} stocks, ${m.bars.toLocaleString("en-IN")} candles in ${(m.ms / 1000).toFixed(1)}s.` + (m.failed.length ? ` ${m.failed.length} stock files could not be loaded.` : ""));
  };

  /* ---------- rendering ---------- */
  const f1 = (x) => (isFinite(x) ? x.toFixed(1) : "∞");
  const f2 = (x) => (isFinite(x) ? x.toFixed(2) : "∞");
  const pct = (x, d = 2) => `${x > 0 ? "+" : ""}${x.toFixed(d)}%`;
  const cls = (x) => (x > 0 ? "pos" : x < 0 ? "neg" : "");
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fmtD(k) {
    const s = String(k); if (!k) return "—";
    const d = `${s.slice(6, 8)} ${MON[+s.slice(4, 6) - 1]}`;
    return s.length > 8 ? `${d} ${s.slice(8, 10)}:${s.slice(10, 12)}` : `${d} ${s.slice(0, 4)}`;
  }
  const REASONS = [
    ["target", "Target hit", "var(--good)"], ["sl", "Stop loss hit", "var(--bad)"], ["trail", "Trailing stop", "color-mix(in srgb, var(--bad) 55%, var(--panel))"],
    ["signal", "Exit condition", "var(--series)"], ["time", "Max hold reached", "var(--neutral)"], ["eod", "Squared off (end of day)", "color-mix(in srgb, var(--neutral) 60%, var(--panel))"],
  ];

  function render(m) {
    const st = m.stats;
    $("#placeholder").style.display = "none"; $("#out").style.display = "";
    const unit = S.tf === "intraday" ? "candles" : "days";
    const tiles = [
      ["Trades", st.trades.toLocaleString("en-IN"), `${st.openTrades} still open · ${m.tested} stocks`],
      ["Win rate", `${f1(st.winRate)}%`, `${st.wins} won · ${st.losses} lost`, st.winRate >= 50 ? "pos" : "neg"],
      ["Target hit", st.trades ? `${f1(100 * st.target / st.trades)}%` : "—", `${st.target} trades`],
      ["Stop loss hit", st.trades ? `${f1(100 * (st.sl + st.trail) / st.trades)}%` : "—", `${st.sl} SL${st.trail ? ` + ${st.trail} trailing` : ""}`],
      ["Avg win / avg loss", `${pct(st.avgWin, 1)} / ${pct(st.avgLoss, 1)}`, `best ${pct(st.best, 1)} · worst ${pct(st.worst, 1)}`],
      ["Expectancy / trade", pct(st.avgRet), "average net return per trade", cls(st.avgRet)],
      ["Profit factor", f2(st.profitFactor), "total gains ÷ total losses", st.profitFactor >= 1 ? "pos" : "neg"],
      ["Avg holding", `${f1(st.avgBars)} ${unit}`, `max ${st.maxLossStreak} losses in a row`],
    ];
    $("#kpis").innerHTML = tiles.map(([l, v, s, c]) => `<div class="kpi"><div class="l">${l}</div><div class="v ${c || ""}">${v}</div><div class="s">${s}</div></div>`).join("");

    const parts = REASONS.map(([k, label, col]) => [k, label, col, st[k] || 0]).filter((p) => p[3] > 0);
    $("#stack").innerHTML = parts.map(([k, label, col, n]) => `<span title="${label}: ${n}" style="flex:${n};background:${col}"></span>`).join("") || `<span style="flex:1;background:var(--soft)"></span>`;
    $("#stackLegend").innerHTML = parts.map(([k, label, col, n]) => `<span><i style="background:${col}"></i>${label} <b>${n}</b> (${f1(100 * n / st.trades)}%)</span>`).join("");
    const notes = [];
    if (st.ambiguous) notes.push(`<b>${st.ambiguous}</b> trades touched both the stop and the target inside the same candle. The real order is unknown from candle data, so they are counted as <b>stop-loss hits</b> (the cautious assumption).`);
    notes.push(`Costs of ${S.cost}% per trade are already deducted. A gap through your stop exits at the opening price, like a real order would.`);
    notes.push(`Results use today's ${S.universe === "custom" ? "list" : "Nifty " + S.universe} stocks for the whole period, so companies that dropped out of the index are missing (survivorship bias) — real results are usually a bit worse.`);
    if (S.tf === "intraday") notes.push("Intraday results cover only the last ~60 trading days, which is a small sample.");
    if (st.trades < 30) notes.push(`Only ${st.trades} trades — too few to trust the win rate. Widen the date range or the stock list.`);
    if (m.errors.length) notes.push("Problems: " + m.errors.map(esc).join("; "));
    $("#notes").innerHTML = notes.map((n) => `<div style="margin:3px 0">• ${n}</div>`).join("");
    drawEquity(st);
    renderTab();
  }

  const perTrade = () => Math.max(1, Number(store.get("bt_amt", 10000)) || 10000);
  const inr = (x) => (x < 0 ? "−₹" : "₹") + Math.abs(Math.round(x)).toLocaleString("en-IN");
  const inrShort = (x) => { const a = Math.abs(x), sg = x < 0 ? "−" : ""; return a >= 1e7 ? `${sg}₹${+(a / 1e7).toFixed(2)}Cr` : a >= 1e5 ? `${sg}₹${+(a / 1e5).toFixed(2)}L` : a >= 1e3 ? `${sg}₹${+(a / 1e3).toFixed(1)}k` : `${sg}₹${Math.round(a)}`; };
  const toMs = (k) => { const s = String(k); return Date.UTC(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8), s.length > 8 ? +s.slice(8, 10) : 0, s.length > 8 ? +s.slice(10, 12) : 0); };
  function drawEquity(st) {
    const box = $("#eq"), amt = perTrade();
    const pts = st.curve.map(([k, e]) => [k, e * amt / 100]);
    if (!pts.length) { box.innerHTML = `<div class="empty">No closed trades.</div>`; return; }
    let peak = 0, dd = 0; for (const p of pts) { peak = Math.max(peak, p[1]); dd = Math.min(dd, p[1] - peak); }
    const intra = String(pts[0][0]).length > 8;
    // intraday: compress to trading-session time so nights/weekends don't leave gaps
    const xs = intra ? pts.map((_, i) => i) : pts.map((p) => toMs(p[0]));
    const W = 800, H = 260, L = 64, R = 12, T = 12, B = 26;
    const ys = pts.map((p) => p[1]).concat([0]), ymin = Math.min(...ys), ymax = Math.max(...ys), span = ymax - ymin || 1;
    const x0 = xs[0], x1 = xs[xs.length - 1], xspan = x1 - x0 || 1;
    const sx = (x) => L + (W - L - R) * (pts.length === 1 ? 0.5 : (x - x0) / xspan);
    const sy = (v) => T + (H - T - B) * (1 - (v - ymin) / span);
    const step = niceStep(span / 4), ticks = [];
    for (let v = Math.ceil(ymin / step) * step; v <= ymax + 1e-9; v += step) ticks.push(v);
    const path = pts.map((p, i) => `${i ? "L" : "M"}${sx(xs[i]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("");
    // x labels: years for daily, dates for intraday
    const xl = []; let lastK = "";
    pts.forEach((p, i) => { const k = String(p[0]).slice(0, intra ? 8 : 4); if (k !== lastK) { xl.push([xs[i], k]); lastK = k; } });
    const every = Math.max(1, Math.ceil(xl.length / 8));
    const col = pts[pts.length - 1][1] >= 0 ? "var(--series)" : "var(--bad)";
    box.innerHTML = `<div class="row" style="margin-bottom:4px"><label>Amount per trade ₹</label><input type="number" id="amt" value="${amt}" min="1" step="1000" style="width:100px">
      <span class="hint">Final P&amp;L <b class="${cls(pts[pts.length - 1][1])}">${inr(pts[pts.length - 1][1])}</b> on ${pts.length.toLocaleString("en-IN")} trades · worst drawdown <b class="neg">${inr(dd)}</b></span></div>
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Equity curve">
      ${ticks.map((v) => `<line x1="${L}" x2="${W - R}" y1="${sy(v)}" y2="${sy(v)}" stroke="var(--grid)" stroke-width="1"/><text x="${L - 6}" y="${sy(v) + 4}" text-anchor="end" font-size="11" fill="var(--muted)">${inrShort(v)}</text>`).join("")}
      <line x1="${L}" x2="${W - R}" y1="${sy(0)}" y2="${sy(0)}" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 3"/>
      ${xl.filter((_, k) => k % every === 0).map(([x, k]) => `<text x="${sx(x)}" y="${H - 6}" font-size="11" fill="var(--muted)" text-anchor="middle">${intra ? fmtD(k).slice(0, 6) : k}</text>`).join("")}
      <path d="${path}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round"/>
      <line id="xh" y1="${T}" y2="${H - B}" stroke="var(--muted)" stroke-width="1" style="display:none"/>
      <circle id="xd" r="4" fill="${col}" stroke="var(--panel)" stroke-width="2" style="display:none"/>
      <rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent" id="hit"/>
    </svg>`;
    $("#amt").onchange = (e) => { store.set("bt_amt", Math.max(1, Number(e.target.value) || 10000)); drawEquity(st); };
    const svg = box.querySelector("svg"), tip = $("#tip");
    const move = (e) => {
      const r = svg.getBoundingClientRect(), x = x0 + ((e.clientX - r.left) * W / r.width - L) / (W - L - R) * xspan;
      let lo = 0, hi = xs.length - 1; while (lo < hi) { const mid = (lo + hi) >> 1; if (xs[mid] < x) lo = mid + 1; else hi = mid; }
      const i = lo > 0 && Math.abs(xs[lo - 1] - x) < Math.abs(xs[lo] - x) ? lo - 1 : lo;
      const X = sx(xs[i]), Y = sy(pts[i][1]);
      const xh = svg.querySelector("#xh"); xh.setAttribute("x1", X); xh.setAttribute("x2", X); xh.style.display = "";
      const d = svg.querySelector("#xd"); d.setAttribute("cx", X); d.setAttribute("cy", Y); d.style.display = "";
      tip.style.display = "block"; tip.style.left = (r.left + X * r.width / W + scrollX) + "px"; tip.style.top = (r.top + Y * r.height / H + scrollY - 8) + "px";
      tip.textContent = `${fmtD(pts[i][0])} · after ${i + 1} trades · ${inr(pts[i][1])}`;
    };
    svg.querySelector("#hit").addEventListener("pointermove", move);
    svg.querySelector("#hit").addEventListener("pointerleave", () => { tip.style.display = "none"; svg.querySelector("#xh").style.display = "none"; svg.querySelector("#xd").style.display = "none"; });
  }
  function niceStep(x) { const p = Math.pow(10, Math.floor(Math.log10(x || 1))), n = x / p; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p; }

  /* ---------- tabs ---------- */
  let tab = "signals", tradePage = 0, tradeFilter = "", tradeSearch = "", stockSort = "tot";
  $("#tabs").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; tab = b.dataset.t; $("#tabs").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b)); renderTab(); };
  function renderTab() {
    const m = lastResult; if (!m) return;
    const body = $("#tabBody"), st = m.stats;
    if (tab === "signals") {
      const sg = m.signals.slice().sort((a, b) => b.chg - a.chg);
      const when = sg.length ? fmtD(sg[0].at) : "";
      body.innerHTML = sg.length ? `<div class="hint" style="margin-bottom:6px">${sg.length} stock${sg.length > 1 ? "s" : ""} meet your entry rules on the latest candle (${when}). Levels below assume entry at that close.</div>
        <div class="tbl"><table><thead><tr><th>Stock</th><th>Close</th><th>Day chg</th><th>Stop loss</th><th>Target</th><th>Past trades</th><th>Past win rate</th></tr></thead><tbody>
        ${sg.map((s) => { const h = st.symbols.find((x) => x.s === s.sym); return `<tr><td><b>${esc(s.sym)}</b></td><td>${s.close.toFixed(2)}</td><td class="${cls(s.chg)}">${pct(s.chg)}</td><td>${s.sl ?? "—"}</td><td>${s.tg ?? "—"}</td><td>${h ? h.n : 0}</td><td>${h ? f1(h.wr) + "%" : "—"}</td></tr>`; }).join("")}
        </tbody></table></div>` : `<div class="empty">No stock meets these rules on the latest candle.</div>`;
    } else if (tab === "years") {
      const max = Math.max(1, ...st.years.map((y) => Math.abs(y.tot)));
      body.innerHTML = `<div class="tbl"><table class="bars"><thead><tr><th>${S.tf === "intraday" ? "Month" : "Year"}</th><th>Trades</th><th>Win rate</th><th>Avg / trade</th><th>Total</th><th></th></tr></thead><tbody>
        ${st.years.map((y) => `<tr><td>${y.y.length > 4 ? MON[+y.y.slice(4) - 1] + " " + y.y.slice(0, 4) : y.y}</td><td>${y.n}</td><td>${f1(y.wr)}%</td><td class="${cls(y.avg)}">${pct(y.avg)}</td><td class="${cls(y.tot)}">${pct(y.tot, 1)}</td>
        <td class="b" style="text-align:left"><span style="display:inline-block;width:50%;text-align:right">${y.tot < 0 ? `<span class="hb n" style="width:${100 * -y.tot / max}%"></span>` : ""}</span>${y.tot > 0 ? `<span class="hb" style="width:${50 * y.tot / max}%"></span>` : ""}</td></tr>`).join("")}
        </tbody></table></div>`;
    } else if (tab === "stocks") {
      const rows = st.symbols.slice().sort((a, b) => stockSort === "worst" ? a.tot - b.tot : stockSort === "n" ? b.n - a.n : stockSort === "wr" ? b.wr - a.wr || b.n - a.n : b.tot - a.tot);
      body.innerHTML = `<div class="row"><label>Sort</label><select id="ss"><option value="tot">Best total</option><option value="worst">Worst total</option><option value="wr">Highest win rate</option><option value="n">Most trades</option></select><span class="hint">${rows.length} stocks had trades</span></div>
        <div class="tbl"><table><thead><tr><th>Stock</th><th>Trades</th><th>Win rate</th><th>Avg / trade</th><th>Total</th></tr></thead><tbody>
        ${rows.slice(0, 40).map((r) => `<tr><td><b>${esc(r.s)}</b></td><td>${r.n}</td><td>${f1(r.wr)}%</td><td class="${cls(r.avg)}">${pct(r.avg)}</td><td class="${cls(r.tot)}">${pct(r.tot, 1)}</td></tr>`).join("")}
        </tbody></table></div>${rows.length > 40 ? `<div class="hint" style="margin-top:6px">Showing 40 of ${rows.length}. Download all trades for the full list.</div>` : ""}`;
      $("#ss").value = stockSort; $("#ss").onchange = (e) => { stockSort = e.target.value; renderTab(); };
    } else {
      let tr = m.trades.slice().sort((a, b) => (b.in || 0) - (a.in || 0));
      if (tradeFilter) tr = tr.filter((t) => (tradeFilter === "open" ? t.open : t.why === tradeFilter));
      if (tradeSearch) tr = tr.filter((t) => t.sym.includes(tradeSearch.toUpperCase()));
      const per = 50, pages = Math.max(1, Math.ceil(tr.length / per)); tradePage = Math.min(tradePage, pages - 1);
      body.innerHTML = `<div class="row"><input type="text" id="tsrch" placeholder="Stock…" value="${esc(tradeSearch)}" style="width:110px">
        <select id="tflt"><option value="">All exits</option>${REASONS.map(([k, l]) => `<option value="${k}">${l}</option>`).join("")}<option value="open">Still open</option></select>
        <span class="spacer"></span><button class="btn small" id="csv">Download CSV</button></div>
        <div class="tbl"><table><thead><tr><th>Stock</th><th>Entry</th><th>Entry ₹</th><th>Stop</th><th>Target</th><th>Exit</th><th>Exit ₹</th><th>Result</th><th>Why</th><th>${S.tf === "intraday" ? "Candles" : "Days"}</th></tr></thead><tbody>
        ${tr.slice(tradePage * per, tradePage * per + per).map((t) => `<tr><td><b>${esc(t.sym)}</b></td><td>${fmtD(t.in)}</td><td>${t.ep}</td><td>${t.sl ?? "—"}</td><td>${t.tg ?? "—"}</td><td>${t.open ? "open" : fmtD(t.out)}</td><td>${t.open ? t.last : t.xp}</td>
          <td class="${cls(t.ret)}">${pct(t.ret)}</td><td><span class="why ${t.open ? "" : t.why}">${t.open ? "open" : (REASONS.find((r) => r[0] === t.why) || [0, t.why])[1]}${t.amb ? " *" : ""}</span></td><td>${t.bars}</td></tr>`).join("")}
        </tbody></table></div>
        <div class="pager"><span>${tr.length.toLocaleString("en-IN")} trades · page ${tradePage + 1}/${pages}</span><button class="btn small" id="pp">‹ Prev</button><button class="btn small" id="pn">Next ›</button></div>`;
      $("#tflt").value = tradeFilter;
      $("#tflt").onchange = (e) => { tradeFilter = e.target.value; tradePage = 0; renderTab(); };
      $("#tsrch").onchange = (e) => { tradeSearch = e.target.value.trim(); tradePage = 0; renderTab(); };
      $("#pp").onclick = () => { tradePage = Math.max(0, tradePage - 1); renderTab(); };
      $("#pn").onclick = () => { tradePage = Math.min(pages - 1, tradePage + 1); renderTab(); };
      $("#csv").onclick = () => downloadCsv(m.trades);
    }
  }
  function downloadCsv(trades) {
    const head = ["stock", "signal", "entry_time", "entry_price", "stop", "target", "exit_time", "exit_price", "return_pct", "exit_reason", "bars_held", "same_candle_sl_and_target"];
    const lines = [head.join(",")].concat(trades.map((t) => [t.sym, t.sig, t.in, t.ep, t.sl ?? "", t.tg ?? "", t.open ? "" : t.out, t.open ? t.last : t.xp, t.ret, t.open ? "open" : t.why, t.bars, t.amb ? "yes" : ""].join(",")));
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
    a.download = `backtest-${(S.name || "strategy").replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.csv`; a.click();
  }

  /* ---------- boot ---------- */
  try {
    if (location.hash.startsWith("#s=")) S = JSON.parse(decodeURIComponent(escape(atob(location.hash.slice(3)))));
    else { const last = store.get("bt_last", null); if (last && last.conds) S = last; }
  } catch {}
  S = Object.assign(blank(), S); S.exitConds = S.exitConds || [];
  fillPresets(); fillSaved(); fillForm();
})();
