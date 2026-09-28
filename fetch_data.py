#!/usr/bin/env python3
"""
Downloads price history for the Nifty 500 and writes compact JSON files the
backtester page reads.

  site/data/daily/<SYM>.json     ~10 years of daily candles (split-adjusted)
  site/data/intraday/<SYM>.json  last ~60 days of 15-minute candles
  site/data/universe.json        stock list with index tier (50/100/200/500)
  site/data/meta.json            last update time + any failures

Source: Yahoo Finance chart API (free, no key). Standard library only.
If a download fails, the previous day's file (restored from the Actions cache)
is kept, so one bad night never empties the site.
"""
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
SITE = ROOT / "site"
DATA = SITE / "data"
CACHE = ROOT / ".data-cache"          # restored/saved by actions/cache
UNIVERSE = ROOT / "data" / "universe.json"
IST = timezone(timedelta(hours=5, minutes=30))

DAILY_RANGE = os.environ.get("DAILY_RANGE", "10y")
INTRA_RANGE = "60d"                   # Yahoo's maximum for 15-minute bars
WORKERS = 6
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
HOSTS = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def fname(sym):
    return sym.replace("&", "_") + ".json"


def yahoo(sym, rng, interval):
    q = urllib.parse.quote(sym + ".NS", safe=".-")
    last = None
    for attempt in range(4):
        host = HOSTS[attempt % 2]
        url = f"https://{host}/v8/finance/chart/{q}?range={rng}&interval={interval}&includePrePost=false&events=div%2Csplit"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.load(r)
            res = j["chart"]["result"]
            if not res:
                raise ValueError(j["chart"].get("error"))
            return res[0]
        except Exception as e:  # 429 / network: back off and retry
            last = e
            time.sleep(2 + attempt * 3)
    raise last


def r2(x):
    return None if x is None else round(float(x), 2)


def pack_daily(res):
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    out = {"d": [], "o": [], "h": [], "l": [], "c": [], "v": []}
    for i, t in enumerate(ts):
        o, h, l, c, v = q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]
        if None in (o, h, l, c) or c <= 0:
            continue
        d = int(datetime.fromtimestamp(t, IST).strftime("%Y%m%d"))
        if out["d"] and out["d"][-1] == d:      # Yahoo sometimes repeats today's bar
            for k, val in zip("ohlcv", (o, h, l, c, v)):
                out[k][-1] = r2(val) if k != "v" else int(val or 0)
            continue
        out["d"].append(d)
        out["o"].append(r2(o)); out["h"].append(r2(h)); out["l"].append(r2(l)); out["c"].append(r2(c))
        out["v"].append(int(v or 0))
    return out


def pack_intraday(res):
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    out = {"t": [], "o": [], "h": [], "l": [], "c": [], "v": []}
    for i, t in enumerate(ts):
        o, h, l, c, v = q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]
        if None in (o, h, l, c) or c <= 0:
            continue
        dt = datetime.fromtimestamp(t, IST)
        if dt.hour * 100 + dt.minute < 915 or dt.hour * 100 + dt.minute > 1529:
            continue
        out["t"].append(int(dt.strftime("%Y%m%d%H%M")))
        out["o"].append(r2(o)); out["h"].append(r2(h)); out["l"].append(r2(l)); out["c"].append(r2(c))
        out["v"].append(int(v or 0))
    return out


def job(args):
    sym, kind = args
    rng, iv, pack = (DAILY_RANGE, "1d", pack_daily) if kind == "daily" else (INTRA_RANGE, "15m", pack_intraday)
    dest = DATA / kind / fname(sym)
    try:
        data = pack(yahoo(sym, rng, iv))
        n = len(data["c"])
        if n < (30 if kind == "daily" else 25):
            raise ValueError(f"only {n} bars")
        dest.write_text(json.dumps(data, separators=(",", ":")))
        return sym, kind, n, None
    except Exception as e:
        cached = CACHE / kind / fname(sym)
        if cached.exists():
            shutil.copy(cached, dest)
            return sym, kind, -1, f"{e} (kept previous data)"
        return sym, kind, 0, str(e)


def main():
    universe = json.loads(UNIVERSE.read_text())
    if os.environ.get("LIMIT"):
        universe = universe[: int(os.environ["LIMIT"])]
    shutil.rmtree(SITE, ignore_errors=True)
    shutil.copytree(ROOT / "docs", SITE)
    for k in ("daily", "intraday"):
        (DATA / k).mkdir(parents=True, exist_ok=True)

    jobs = [(u["s"], k) for u in universe for k in ("daily", "intraday")]
    started = time.time()
    results, fails = {}, []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, (sym, kind, n, err) in enumerate(ex.map(job, jobs), 1):
            results.setdefault(sym, {})[kind] = n
            if err:
                fails.append(f"{sym} {kind}: {err}")
            if i % 100 == 0:
                log(f"{i}/{len(jobs)} done, {len(fails)} issues, {time.time()-started:.0f}s")

    live = []
    for u in universe:
        r = results.get(u["s"], {})
        u = dict(u, f=fname(u["s"]), dy=r.get("daily", 0) != 0, it=r.get("intraday", 0) != 0)
        if u["dy"] or u["it"]:
            live.append(u)
    (DATA / "universe.json").write_text(json.dumps(live, separators=(",", ":")))
    (DATA / "meta.json").write_text(json.dumps({
        "updated": datetime.now(IST).isoformat(timespec="minutes"),
        "stocks": len(live), "daily_range": DAILY_RANGE, "intraday": "15m, last 60 days",
        "issues": fails[:200], "issue_count": len(fails),
    }, indent=1))

    # refresh the cache for tomorrow's fallback
    for k in ("daily", "intraday"):
        shutil.rmtree(CACHE / k, ignore_errors=True)
        shutil.copytree(DATA / k, CACHE / k)

    ok_d = sum(1 for u in live if u["dy"]); ok_i = sum(1 for u in live if u["it"])
    log(f"Done in {time.time()-started:.0f}s: {ok_d} daily, {ok_i} intraday, {len(fails)} issues")
    for f in fails[:15]:
        log("  !", f)
    if ok_d < len(universe) * 0.5:
        log("Too many failures — not publishing a broken site")
        sys.exit(1)


if __name__ == "__main__":
    main()
