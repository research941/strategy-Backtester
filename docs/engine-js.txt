/* Strategy backtest engine — runs in a Web Worker (and in Node for tests).
 * Bars: {o,h,l,c,v, d|t}. Daily bars use d=YYYYMMDD, intraday t=YYYYMMDDHHMM.
 * A strategy is plain JSON (see defaultStrategy in app.js).
 */
(function (root) {
  "use strict";
  const NaN_ = NaN;

  /* ---------------- indicator maths (all return Float64Array, NaN = not ready) ---------------- */
  function sma(src, n) {
    const out = new Float64Array(src.length).fill(NaN_);
    let s = 0, cnt = 0;
    for (let i = 0; i < src.length; i++) {
      const x = src[i];
      s += x; cnt++;
      if (cnt > n) { s -= src[i - n]; cnt = n; }
      if (cnt === n) out[i] = s / n;
    }
    return out;
  }
  function ema(src, n) {
    const out = new Float64Array(src.length).fill(NaN_);
    const k = 2 / (n + 1);
    let prev = NaN_, s = 0;
    for (let i = 0; i < src.length; i++) {
      if (i < n - 1) { s += src[i]; continue; }
      if (i === n - 1) { s += src[i]; prev = s / n; out[i] = prev; continue; }
      prev = src[i] * k + prev * (1 - k); out[i] = prev;
    }
    return out;
  }
  function wilder(src, n) { // Wilder's smoothing (RMA) on a series that may start with NaN
    const out = new Float64Array(src.length).fill(NaN_);
    let prev = NaN_, s = 0, cnt = 0;
    for (let i = 0; i < src.length; i++) {
      const x = src[i];
      if (isNaN(x)) continue;
      if (isNaN(prev)) { s += x; cnt++; if (cnt === n) { prev = s / n; out[i] = prev; } continue; }
      prev = (prev * (n - 1) + x) / n; out[i] = prev;
    }
    return out;
  }
  function rsi(c, n) {
    const up = new Float64Array(c.length).fill(NaN_), dn = new Float64Array(c.length).fill(NaN_);
    for (let i = 1; i < c.length; i++) { const d = c[i] - c[i - 1]; up[i] = d > 0 ? d : 0; dn[i] = d < 0 ? -d : 0; }
    const au = wilder(up, n), ad = wilder(dn, n), out = new Float64Array(c.length).fill(NaN_);
    for (let i = 0; i < c.length; i++) {
      if (isNaN(au[i])) continue;
      out[i] = ad[i] === 0 ? 100 : 100 - 100 / (1 + au[i] / ad[i]);
    }
    return out;
  }
  function trueRange(b) {
    const tr = new Float64Array(b.c.length).fill(NaN_);
    for (let i = 0; i < b.c.length; i++) {
      tr[i] = i === 0 ? b.h[i] - b.l[i]
        : Math.max(b.h[i] - b.l[i], Math.abs(b.h[i] - b.c[i - 1]), Math.abs(b.l[i] - b.c[i - 1]));
    }
    return tr;
  }
  function atr(b, n) { return wilder(trueRange(b), n); }
  function stdev(src, n) {
    const out = new Float64Array(src.length).fill(NaN_);
    for (let i = n - 1; i < src.length; i++) {
      let m = 0; for (let j = i - n + 1; j <= i; j++) m += src[j]; m /= n;
      let v = 0; for (let j = i - n + 1; j <= i; j++) v += (src[j] - m) ** 2;
      out[i] = Math.sqrt(v / n);
    }
    return out;
  }
  // highest / lowest over the PREVIOUS n bars (current bar excluded) — natural for breakouts
  function rollExtremePrev(src, n, isMax) {
    const out = new Float64Array(src.length).fill(NaN_);
    const dq = [];
    for (let i = 0; i < src.length; i++) {
      // window for bar i is [i-n, i-1]
      while (dq.length && dq[0] < i - n) dq.shift();
      if (i >= n) out[i] = src[dq[0]];
      while (dq.length && (isMax ? src[dq[dq.length - 1]] <= src[i] : src[dq[dq.length - 1]] >= src[i])) dq.pop();
      dq.push(i);
    }
    return out;
  }
  function adx(b, n) {
    const len = b.c.length, pdm = new Float64Array(len).fill(NaN_), mdm = new Float64Array(len).fill(NaN_);
    for (let i = 1; i < len; i++) {
      const up = b.h[i] - b.h[i - 1], dn = b.l[i - 1] - b.l[i];
      pdm[i] = up > dn && up > 0 ? up : 0; mdm[i] = dn > up && dn > 0 ? dn : 0;
    }
    const tr = trueRange(b); tr[0] = NaN_;
    const str = wilder(tr, n), sp = wilder(pdm, n), sm = wilder(mdm, n);
    const dx = new Float64Array(len).fill(NaN_), pdi = new Float64Array(len).fill(NaN_), mdi = new Float64Array(len).fill(NaN_);
    for (let i = 0; i < len; i++) {
      if (isNaN(str[i]) || str[i] === 0) continue;
      pdi[i] = 100 * sp[i] / str[i]; mdi[i] = 100 * sm[i] / str[i];
      const s = pdi[i] + mdi[i]; dx[i] = s === 0 ? 0 : 100 * Math.abs(pdi[i] - mdi[i]) / s;
    }
    return { adx: wilder(dx, n), pdi, mdi };
  }
  function stoch(b, n, dN) {
    const len = b.c.length, k = new Float64Array(len).fill(NaN_);
    for (let i = n - 1; i < len; i++) {
      let hh = -Infinity, ll = Infinity;
      for (let j = i - n + 1; j <= i; j++) { if (b.h[j] > hh) hh = b.h[j]; if (b.l[j] < ll) ll = b.l[j]; }
      k[i] = hh === ll ? 50 : 100 * (b.c[i] - ll) / (hh - ll);
    }
    const d = new Float64Array(len).fill(NaN_);
    for (let i = n - 1 + dN - 1; i < len; i++) { let s = 0; for (let j = i - dN + 1; j <= i; j++) s += k[j]; d[i] = s / dN; }
    return { k, d };
  }
  function supertrend(b, n, mult) {
    const len = b.c.length, a = atr(b, n), st = new Float64Array(len).fill(NaN_);
    let fu = NaN_, fl = NaN_, dir = 1;
    for (let i = 0; i < len; i++) {
      if (isNaN(a[i])) continue;
      const mid = (b.h[i] + b.l[i]) / 2, bu = mid + mult * a[i], bl = mid - mult * a[i];
      if (isNaN(fu)) { fu = bu; fl = bl; dir = b.c[i] >= mid ? 1 : -1; }
      else {
        fu = (bu < fu || b.c[i - 1] > fu) ? bu : fu;
        fl = (bl > fl || b.c[i - 1] < fl) ? bl : fl;
        if (dir === 1 && b.c[i] < fl) dir = -1; else if (dir === -1 && b.c[i] > fu) dir = 1;
      }
      st[i] = dir === 1 ? fl : fu;
    }
    return st;
  }

  /* ---------------- intraday helpers ---------------- */
  const dayOf = (b, i) => (b.t ? Math.floor(b.t[i] / 10000) : b.d[i]);
  const hhmm = (b, i) => (b.t ? b.t[i] % 10000 : 1530);
  function dayArrays(b) { // per-bar: day open, prev-day H/L/C, opening range, vwap
    const len = b.c.length;
    const res = { dopen: new Float64Array(len).fill(NaN_), pdh: new Float64Array(len).fill(NaN_), pdl: new Float64Array(len).fill(NaN_),
      pdc: new Float64Array(len).fill(NaN_), vwap: new Float64Array(len).fill(NaN_), barNo: new Int32Array(len), dhigh: new Float64Array(len), dlow: new Float64Array(len) };
    let cur = -1, dOpen = NaN_, dH = -Infinity, dL = Infinity, dC = NaN_, pH = NaN_, pL = NaN_, pC = NaN_, pv = 0, vv = 0, k = 0;
    for (let i = 0; i < len; i++) {
      const day = dayOf(b, i);
      if (day !== cur) {
        if (cur !== -1) { pH = dH; pL = dL; pC = dC; }
        cur = day; dOpen = b.o[i]; dH = -Infinity; dL = Infinity; pv = 0; vv = 0; k = 0;
      }
      dH = Math.max(dH, b.h[i]); dL = Math.min(dL, b.l[i]); dC = b.c[i];
      const tp = (b.h[i] + b.l[i] + b.c[i]) / 3; pv += tp * b.v[i]; vv += b.v[i];
      res.dopen[i] = dOpen; res.pdh[i] = pH; res.pdl[i] = pL; res.pdc[i] = pC;
      res.vwap[i] = vv > 0 ? pv / vv : tp; res.barNo[i] = k++; res.dhigh[i] = dH; res.dlow[i] = dL;
    }
    return res;
  }
  function openingRange(b, days, nBars, isHigh) {
    const len = b.c.length, out = new Float64Array(len).fill(NaN_);
    let start = 0;
    for (let i = 0; i < len; i++) {
      if (days.barNo[i] === 0) start = i;
      if (days.barNo[i] >= nBars) {
        let x = isHigh ? -Infinity : Infinity;
        for (let j = start; j < start + nBars; j++) x = isHigh ? Math.max(x, b.h[j]) : Math.min(x, b.l[j]);
        out[i] = x;
      }
    }
    return out;
  }

  /* ---------------- operand catalogue ---------------- */
  // Each: label, params [{name,def}], intraday-only flag, compute(bars, p, ctx) -> Float64Array
  const OPERANDS = {
    close: { label: "Close", params: [], f: (b) => b.c },
    open: { label: "Open", params: [], f: (b) => b.o },
    high: { label: "High", params: [], f: (b) => b.h },
    low: { label: "Low", params: [], f: (b) => b.l },
    volume: { label: "Volume", params: [], f: (b) => b.v },
    sma: { label: "SMA", params: [{ n: "period", d: 20 }], f: (b, p) => sma(b.c, p[0]) },
    ema: { label: "EMA", params: [{ n: "period", d: 20 }], f: (b, p) => ema(b.c, p[0]) },
    rsi: { label: "RSI", params: [{ n: "period", d: 14 }], f: (b, p) => rsi(b.c, p[0]) },
    macd: { label: "MACD line", params: [{ n: "fast", d: 12 }, { n: "slow", d: 26 }], f: (b, p) => { const f = ema(b.c, p[0]), s = ema(b.c, p[1]); return f.map((x, i) => x - s[i]); } },
    macds: { label: "MACD signal", params: [{ n: "fast", d: 12 }, { n: "slow", d: 26 }, { n: "signal", d: 9 }], f: (b, p) => {
      const f = ema(b.c, p[0]), s = ema(b.c, p[1]); const m = f.map((x, i) => x - s[i]);
      const first = m.findIndex((x) => !isNaN(x)); const out = new Float64Array(m.length).fill(NaN_);
      if (first < 0) return out; const e = ema(m.slice(first), p[2]); out.set(e, first); return out; } },
    macdh: { label: "MACD histogram", params: [{ n: "fast", d: 12 }, { n: "slow", d: 26 }, { n: "signal", d: 9 }], f: (b, p, ctx) => {
      const m = ctx.get({ k: "macd", p: [p[0], p[1]] }), s = ctx.get({ k: "macds", p }); return m.map((x, i) => x - s[i]); } },
    bbu: { label: "Bollinger upper", params: [{ n: "period", d: 20 }, { n: "std dev", d: 2 }], f: (b, p) => { const m = sma(b.c, p[0]), s = stdev(b.c, p[0]); return m.map((x, i) => x + p[1] * s[i]); } },
    bbm: { label: "Bollinger middle", params: [{ n: "period", d: 20 }], f: (b, p) => sma(b.c, p[0]) },
    bbl: { label: "Bollinger lower", params: [{ n: "period", d: 20 }, { n: "std dev", d: 2 }], f: (b, p) => { const m = sma(b.c, p[0]), s = stdev(b.c, p[0]); return m.map((x, i) => x - p[1] * s[i]); } },
    atr: { label: "ATR", params: [{ n: "period", d: 14 }], f: (b, p) => atr(b, p[0]) },
    adx: { label: "ADX", params: [{ n: "period", d: 14 }], f: (b, p) => adx(b, p[0]).adx },
    pdi: { label: "+DI", params: [{ n: "period", d: 14 }], f: (b, p) => adx(b, p[0]).pdi },
    mdi: { label: "−DI", params: [{ n: "period", d: 14 }], f: (b, p) => adx(b, p[0]).mdi },
    stk: { label: "Stochastic %K", params: [{ n: "period", d: 14 }], f: (b, p) => stoch(b, p[0], 3).k },
    std: { label: "Stochastic %D", params: [{ n: "period", d: 14 }, { n: "smooth", d: 3 }], f: (b, p) => stoch(b, p[0], p[1]).d },
    st: { label: "Supertrend", params: [{ n: "period", d: 10 }, { n: "mult", d: 3 }], f: (b, p) => supertrend(b, p[0], p[1]) },
    hh: { label: "Highest high (prev N bars)", params: [{ n: "bars", d: 20 }], f: (b, p) => rollExtremePrev(b.h, p[0], true) },
    ll: { label: "Lowest low (prev N bars)", params: [{ n: "bars", d: 20 }], f: (b, p) => rollExtremePrev(b.l, p[0], false) },
    hc: { label: "Highest close (prev N bars)", params: [{ n: "bars", d: 20 }], f: (b, p) => rollExtremePrev(b.c, p[0], true) },
    lc: { label: "Lowest close (prev N bars)", params: [{ n: "bars", d: 20 }], f: (b, p) => rollExtremePrev(b.c, p[0], false) },
    avgvol: { label: "Avg volume (prev N bars)", params: [{ n: "bars", d: 20 }], f: (b, p) => { const s = sma(b.v, p[0]); const out = new Float64Array(s.length).fill(NaN_); for (let i = 1; i < s.length; i++) out[i] = s[i - 1]; return out; } },
    roc: { label: "% change over N bars", params: [{ n: "bars", d: 1 }], f: (b, p) => { const out = new Float64Array(b.c.length).fill(NaN_); for (let i = p[0]; i < b.c.length; i++) out[i] = 100 * (b.c[i] / b.c[i - p[0]] - 1); return out; } },
    gap: { label: "Gap % (open vs prev close)", params: [], f: (b) => { const out = new Float64Array(b.c.length).fill(NaN_); for (let i = 1; i < b.c.length; i++) { const pc = b.t ? (b.__days.barNo[i] === 0 ? b.c[i - 1] : NaN_) : b.c[i - 1]; out[i] = 100 * (b.o[i] / pc - 1); } return out; } },
    body: { label: "Candle body %", params: [], f: (b) => b.c.map((c, i) => 100 * (c - b.o[i]) / b.o[i]) },
    range: { label: "Candle range %", params: [], f: (b) => b.c.map((c, i) => 100 * (b.h[i] - b.l[i]) / b.o[i]) },
    // intraday-only
    vwap: { label: "VWAP (intraday)", params: [], intra: true, f: (b) => b.__days.vwap },
    dopen: { label: "Day open (intraday)", params: [], intra: true, f: (b) => b.__days.dopen },
    pdh: { label: "Prev day high (intraday)", params: [], intra: true, f: (b) => b.__days.pdh },
    pdl: { label: "Prev day low (intraday)", params: [], intra: true, f: (b) => b.__days.pdl },
    pdc: { label: "Prev day close (intraday)", params: [], intra: true, f: (b) => b.__days.pdc },
    orh: { label: "Opening range high (first N bars)", params: [{ n: "bars", d: 1 }], intra: true, f: (b, p) => openingRange(b, b.__days, p[0], true) },
    orl: { label: "Opening range low (first N bars)", params: [{ n: "bars", d: 1 }], intra: true, f: (b, p) => openingRange(b, b.__days, p[0], false) },
    time: { label: "Time (HHMM, intraday)", params: [], intra: true, f: (b) => Float64Array.from(b.t, (t) => t % 10000) },
    value: { label: "Number", params: [], value: true },
  };

  const PATTERNS = {
    bull_engulf: { label: "Bullish engulfing", f: (b, i) => i > 0 && b.c[i - 1] < b.o[i - 1] && b.c[i] > b.o[i] && b.c[i] >= b.o[i - 1] && b.o[i] <= b.c[i - 1] },
    bear_engulf: { label: "Bearish engulfing", f: (b, i) => i > 0 && b.c[i - 1] > b.o[i - 1] && b.c[i] < b.o[i] && b.o[i] >= b.c[i - 1] && b.c[i] <= b.o[i - 1] },
    hammer: { label: "Hammer", f: (b, i) => { const body = Math.abs(b.c[i] - b.o[i]), rng = b.h[i] - b.l[i], lw = Math.min(b.o[i], b.c[i]) - b.l[i], uw = b.h[i] - Math.max(b.o[i], b.c[i]); return rng > 0 && body > 0 && lw >= 2 * body && uw <= body * 0.5; } },
    shooting_star: { label: "Shooting star", f: (b, i) => { const body = Math.abs(b.c[i] - b.o[i]), rng = b.h[i] - b.l[i], lw = Math.min(b.o[i], b.c[i]) - b.l[i], uw = b.h[i] - Math.max(b.o[i], b.c[i]); return rng > 0 && body > 0 && uw >= 2 * body && lw <= body * 0.5; } },
    doji: { label: "Doji", f: (b, i) => { const rng = b.h[i] - b.l[i]; return rng > 0 && Math.abs(b.c[i] - b.o[i]) <= 0.1 * rng; } },
    inside_bar: { label: "Inside bar", f: (b, i) => i > 0 && b.h[i] < b.h[i - 1] && b.l[i] > b.l[i - 1] },
    outside_bar: { label: "Outside bar", f: (b, i) => i > 0 && b.h[i] > b.h[i - 1] && b.l[i] < b.l[i - 1] },
    three_white: { label: "Three white soldiers", f: (b, i) => i > 1 && [0, 1, 2].every((k) => b.c[i - k] > b.o[i - k]) && b.c[i] > b.c[i - 1] && b.c[i - 1] > b.c[i - 2] },
    three_black: { label: "Three black crows", f: (b, i) => i > 1 && [0, 1, 2].every((k) => b.c[i - k] < b.o[i - k]) && b.c[i] < b.c[i - 1] && b.c[i - 1] < b.c[i - 2] },
    bull_candle: { label: "Green candle", f: (b, i) => b.c[i] > b.o[i] },
    bear_candle: { label: "Red candle", f: (b, i) => b.c[i] < b.o[i] },
    nr7: { label: "NR7 (narrowest range of 7)", f: (b, i) => { if (i < 6) return false; const r = b.h[i] - b.l[i]; for (let k = 1; k < 7; k++) if (b.h[i - k] - b.l[i - k] <= r) return false; return true; } },
  };

  /* ---------------- per-symbol evaluation context ---------------- */
  function makeCtx(bars) {
    const cache = new Map();
    if (bars.t && !bars.__days) bars.__days = dayArrays(bars);
    const ctx = {
      get(op) {
        const def = OPERANDS[op.k];
        if (!def) throw new Error("Unknown indicator " + op.k);
        const p = def.params.map((pp, i) => Number(op.p && op.p[i] != null ? op.p[i] : pp.d));
        const key = op.k + ":" + p.join(",");
        if (!cache.has(key)) {
          if (def.intra && !bars.t) throw new Error(def.label + " only works on intraday data");
          cache.set(key, def.f(bars, p, ctx));
        }
        return cache.get(key);
      },
      val(op, i) { // operand value at bar i, honouring offset and multiplier
        if (op.k === "value") return Number(op.v);
        const j = i - (Number(op.off) || 0);
        if (j < 0) return NaN_;
        const x = ctx.get(op)[j];
        return op.mul != null && op.mul !== "" && Number(op.mul) !== 1 ? x * Number(op.mul) : x;
      },
    };
    return ctx;
  }

  function evalCond(cond, ctx, bars, i) {
    if (cond.pat) {
      const P = PATTERNS[cond.pat]; if (!P) return false;
      const r = P.f(bars, i); return cond.not ? !r : r;
    }
    const a = ctx.val(cond.a, i), b = ctx.val(cond.b, i);
    if (isNaN(a) || isNaN(b)) return false;
    switch (cond.op) {
      case ">": return a > b;
      case "<": return a < b;
      case ">=": return a >= b;
      case "<=": return a <= b;
      case "xa": case "xb": {
        if (i < 1) return false;
        const pa = ctx.val(cond.a, i - 1), pb = ctx.val(cond.b, i - 1);
        if (isNaN(pa) || isNaN(pb)) return false;
        return cond.op === "xa" ? pa <= pb && a > b : pa >= pb && a < b;
      }
    }
    return false;
  }
  function evalGroup(conds, logic, ctx, bars, i) {
    if (!conds || !conds.length) return false;
    if (logic === "any") return conds.some((c) => evalCond(c, ctx, bars, i));
    return conds.every((c) => evalCond(c, ctx, bars, i));
  }

  /* ---------------- trade simulation for one symbol ---------------- */
  function barKey(bars, i) { return bars.t ? bars.t[i] : bars.d[i]; }

  function simulate(sym, bars, s) {
    const ctx = makeCtx(bars);
    const n = bars.c.length, trades = [];
    const long = s.side !== "short";
    const intra = !!bars.t;
    const from = Number(s.from) || 0, to = Number(s.to) || 99999999;
    const inRange = (i) => { const d = intra ? Math.floor(bars.t[i] / 10000) : bars.d[i]; return d >= from && d <= to; };
    const lastEntry = Number(s.lastEntryTime) || 1500, sqoff = Number(s.squareOff) || 1515;
    const atrArr = (s.sl.type === "atr" || s.tg.type === "atr") ? ctx.get({ k: "atr", p: [Number(s.atrLen) || 14] }) : null;
    const hasExitConds = s.exitConds && s.exitConds.length;

    let i = 0;
    while (i < n) {
      // ---- look for an entry signal on bar i ----
      if (!inRange(i) || (intra && hhmm(bars, i) > lastEntry) || !evalGroup(s.conds, s.logic, ctx, bars, i)) { i++; continue; }
      let e = s.entry === "close" ? i : i + 1;
      if (e >= n) { trades.push({ sym, sig: barKey(bars, i), open: true, pending: true }); break; }
      if (intra && s.entry !== "close" && dayOf(bars, e) !== dayOf(bars, i)) { i++; continue; } // no overnight carry into next session
      const ep = s.entry === "close" ? bars.c[i] : bars.o[e];
      const a = atrArr ? atrArr[i] : NaN_;
      const dir = long ? 1 : -1;
      // stop & target prices
      let stop = null, target = null;
      if (s.sl.type === "pct") stop = ep * (1 - dir * s.sl.v / 100);
      else if (s.sl.type === "atr" && !isNaN(a)) stop = ep - dir * s.sl.v * a;
      else if (s.sl.type === "level") { const lv = ctx.val(s.sl.op, i); if (!isNaN(lv) && (long ? lv < ep : lv > ep)) stop = lv; }
      if (s.tg.type === "pct") target = ep * (1 + dir * s.tg.v / 100);
      else if (s.tg.type === "atr" && !isNaN(a)) target = ep + dir * s.tg.v * a;
      else if (s.tg.type === "r" && stop != null) target = ep + dir * s.tg.v * Math.abs(ep - stop);
      const initStop = stop;
      const trail = Number(s.trail) || 0;
      let best = ep, exitPx = null, reason = null, j = s.entry === "close" ? i + 1 : e, ambiguous = false;
      const maxBars = Number(s.maxBars) || 0;

      for (; j < n; j++) {
        const O = bars.o[j], H = bars.h[j], L = bars.l[j], C = bars.c[j];
        const onEntryBar = j === e && s.entry !== "close";
        // gap through levels at the open (not on the entry bar, where the open IS the entry)
        if (!onEntryBar) {
          if (stop != null && (long ? O <= stop : O >= stop)) { exitPx = O; reason = stop !== initStop ? "trail" : "sl"; break; }
          if (target != null && (long ? O >= target : O <= target)) { exitPx = O; reason = "target"; break; }
        }
        const hitS = stop != null && (long ? L <= stop : H >= stop);
        const hitT = target != null && (long ? H >= target : L <= target);
        if (hitS && hitT) { exitPx = stop; reason = stop !== initStop ? "trail" : "sl"; ambiguous = true; break; } // conservative
        if (hitS) { exitPx = stop; reason = stop !== initStop ? "trail" : "sl"; break; }
        if (hitT) { exitPx = target; reason = "target"; break; }
        const held = j - e + 1;
        if (hasExitConds && evalGroup(s.exitConds, s.exitLogic, ctx, bars, j)) { exitPx = C; reason = "signal"; break; }
        if (maxBars && held >= maxBars) { exitPx = C; reason = "time"; break; }
        if (intra && (hhmm(bars, j) >= sqoff || j === n - 1 || dayOf(bars, j + 1) !== dayOf(bars, j))) {
          if (j === n - 1 && hhmm(bars, j) < sqoff) break; // today's session still running
          exitPx = C; reason = "eod"; break;
        }
        // trailing stop moves after the bar closes
        if (trail > 0) {
          best = long ? Math.max(best, H) : Math.min(best, L);
          const ts = best * (1 - dir * trail / 100);
          if (stop == null || (long ? ts > stop : ts < stop)) stop = ts;
        }
      }
      if (reason == null) { // still open at end of data
        trades.push({ sym, sig: barKey(bars, i), in: barKey(bars, e), ep: +ep.toFixed(2), sl: stop == null ? null : +stop.toFixed(2), tg: target == null ? null : +target.toFixed(2), open: true, last: bars.c[n - 1], ret: +(dir * (bars.c[n - 1] / ep - 1) * 100).toFixed(2), bars: n - e });
        break;
      }
      const gross = dir * (exitPx / ep - 1) * 100;
      const ret = gross - (Number(s.cost) || 0);
      trades.push({ sym, sig: barKey(bars, i), in: barKey(bars, e), out: barKey(bars, j), ep: +ep.toFixed(2), xp: +exitPx.toFixed(2),
        sl: initStop == null ? null : +initStop.toFixed(2), tg: target == null ? null : +target.toFixed(2),
        ret: +ret.toFixed(3), why: reason, bars: j - e + 1, amb: ambiguous || undefined });
      i = j + 1; // one position per stock at a time; look for the next signal after exit
    }
    return trades;
  }

  /* ---------------- which stocks match right now ---------------- */
  function lastSignal(sym, bars, s) {
    const ctx = makeCtx(bars), i = bars.c.length - 1;
    if (i < 1) return null;
    if (!evalGroup(s.conds, s.logic, ctx, bars, i)) return null;
    const long = s.side !== "short", dir = long ? 1 : -1, ep = bars.c[i];
    let sl = null, tg = null;
    const a = (s.sl.type === "atr" || s.tg.type === "atr") ? ctx.get({ k: "atr", p: [Number(s.atrLen) || 14] })[i] : NaN_;
    if (s.sl.type === "pct") sl = ep * (1 - dir * s.sl.v / 100); else if (s.sl.type === "atr") sl = ep - dir * s.sl.v * a;
    else if (s.sl.type === "level") sl = ctx.val(s.sl.op, i);
    if (s.tg.type === "pct") tg = ep * (1 + dir * s.tg.v / 100); else if (s.tg.type === "atr") tg = ep + dir * s.tg.v * a;
    else if (s.tg.type === "r" && sl != null) tg = ep + dir * s.tg.v * Math.abs(ep - sl);
    return { sym, at: barKey(bars, i), close: ep, sl: sl == null || isNaN(sl) ? null : +sl.toFixed(2), tg: tg == null || isNaN(tg) ? null : +tg.toFixed(2), chg: +(100 * (ep / bars.c[i - 1] - 1)).toFixed(2) };
  }

  /* ---------------- statistics ---------------- */
  function stats(all) {
    const closed = all.filter((t) => !t.open).sort((a, b) => a.out - b.out || a.in - b.in);
    const open = all.filter((t) => t.open && !t.pending);
    const N = closed.length, r = closed.map((t) => t.ret);
    const wins = r.filter((x) => x > 0), losses = r.filter((x) => x <= 0);
    const cnt = (w) => closed.filter((t) => t.why === w).length;
    const sum = (a) => a.reduce((x, y) => x + y, 0);
    const avg = (a) => (a.length ? sum(a) / a.length : 0);
    let eq = 0, peak = 0, mdd = 0, streak = 0, maxStreak = 0;
    const curve = [];
    for (const t of closed) {
      eq += t.ret; peak = Math.max(peak, eq); mdd = Math.min(mdd, eq - peak);
      if (t.ret <= 0) { streak++; maxStreak = Math.max(maxStreak, streak); } else streak = 0;
      curve.push([t.out, +eq.toFixed(2)]);
    }
    const byYear = {};
    for (const t of closed) {
      const k = String(t.out).length > 8 ? String(t.out).slice(0, 6) : String(t.out).slice(0, 4); // intraday: by month
      (byYear[k] = byYear[k] || []).push(t.ret);
    }
    const bySym = {};
    for (const t of closed) (bySym[t.sym] = bySym[t.sym] || []).push(t.ret);
    const symRows = Object.entries(bySym).map(([s, a]) => ({ s, n: a.length, wr: 100 * a.filter((x) => x > 0).length / a.length, avg: avg(a), tot: sum(a) }));
    const gw = sum(wins), gl = -sum(losses);
    return {
      trades: N, openTrades: open.length, wins: wins.length, losses: losses.length,
      winRate: N ? 100 * wins.length / N : 0,
      target: cnt("target"), sl: cnt("sl"), trail: cnt("trail"), time: cnt("time"), signal: cnt("signal"), eod: cnt("eod"),
      ambiguous: closed.filter((t) => t.amb).length,
      avgWin: avg(wins), avgLoss: avg(losses), avgRet: avg(r), best: N ? Math.max(...r) : 0, worst: N ? Math.min(...r) : 0,
      profitFactor: gl > 0 ? gw / gl : (gw > 0 ? Infinity : 0),
      totalRet: sum(r), maxDD: mdd, maxLossStreak: maxStreak,
      avgBars: avg(closed.map((t) => t.bars)),
      curve, years: Object.entries(byYear).sort().map(([y, a]) => ({ y, n: a.length, wr: 100 * a.filter((x) => x > 0).length / a.length, avg: avg(a), tot: sum(a) })),
      symbols: symRows,
    };
  }

  const api = { OPERANDS, PATTERNS, simulate, lastSignal, stats, makeCtx, evalCond, _ind: { sma, ema, rsi, atr, adx, stoch, supertrend, rollExtremePrev, stdev } };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.BT = api;
})(typeof self !== "undefined" ? self : this);
