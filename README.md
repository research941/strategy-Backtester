# Strategy Backtester (Nifty 500)

Test any trading rule on Nifty 500 stocks and see its **win rate, how often the target was hit,
how often the stop loss was hit**, the equity curve, results by year and by stock, every single trade,
and which stocks match your rule **today**.

- **Daily** candles, about 10 years of history
- **15-minute intraday** candles, last ~60 trading days (the free-data limit)
- Free: GitHub downloads fresh prices every weekday after the market closes; the backtest runs in your browser

---

## One-time setup (about 10 minutes)

1. **New repository**: on GitHub click **+ → New repository**, name it `Strategy-Backtester`,
   choose **Public**, click **Create repository**.
2. **Upload files**: click **uploading an existing file** and drag in `fetch_data.py`, `README.md`,
   and the **`docs`** and **`data`** folders. Click **Commit changes**.
   Check that `docs` has 4 files (`index.html`, `app.js`, `engine.js`, `worker.js`) and `data` has `universe.json`.
3. **Add the automation file** (GitHub usually skips the hidden `.github` folder when you drag and drop):
   **Add file → Create new file**, name it exactly `.github/workflows/update-data.yml`,
   paste the contents of that file from the zip, and click **Commit changes**.
4. **Turn on the website**: **Settings → Pages → Build and deployment → Source: “GitHub Actions”**.
   (Not “Deploy from a branch” — this site is published by the workflow.)
5. **First data download**: **Actions** tab → *Update price data & publish site* → **Run workflow**.
   It takes about 5–15 minutes, because it downloads 500 stocks × 2 timeframes.
6. **Open the site**: `https://<your-username>.github.io/Strategy-Backtester/`.
   The name is **case-sensitive**: it must match the repository name exactly.

After that, data refreshes automatically at about 4:15 PM IST every weekday.

---

## How to use it

1. **Market**: Daily or 15-min intraday, which stocks (Nifty 50/100/200/500 or your own list), date range.
2. **Entry rules**: load a ready-made strategy or build your own:
   `[indicator] [is above / is below / crosses above / crosses below] [indicator or number]`.
   Add as many conditions as you like, and choose whether ALL or ANY of them must be true. Candle patterns are available too.
   The **⋯** button next to an indicator lets you use its value N candles ago, or multiply it (e.g. `Volume > 1.5 × Avg volume(20)`).
3. **Exit rules**: stop loss (% / ATR / an indicator level such as “lowest low of 10 days”), target (% / ATR / R-multiple),
   trailing stop, maximum holding period, and optional exit conditions. Intraday trades are squared off at your chosen time.
4. **Run backtest**. The first run downloads the price data (Nifty 500 daily is about 15–20 MB); later runs take about 1 second.

**Save** keeps a strategy in your browser. **Copy link** gives you a URL that opens the exact same strategy on any device.

### Indicators available
Close/Open/High/Low, % change, gap %, candle body/range · SMA, EMA, Supertrend · RSI, MACD (line/signal/histogram),
Stochastic %K/%D, ADX, +DI/−DI · Bollinger bands, ATR · Highest high / lowest low / highest close / lowest close of the previous N candles ·
Volume, average volume · **Intraday:** VWAP, day open, previous-day high/low/close, opening range high/low, time of day ·
**Candle patterns:** bullish/bearish engulfing, hammer, shooting star, doji, inside/outside bar, three white soldiers,
three black crows, green/red candle, NR7.

---

## How the backtest works (so you can trust the numbers)

- **Signals are checked on the candle close.** By default you buy at the **next candle's open**, which is what you could actually do.
- **One position per stock at a time.** A new signal is only taken after the previous trade in that stock is closed.
- **Stop and target are checked on every candle's high and low.** If a candle **gaps** past your stop or target,
  the exit is at the opening price, like a real order.
- If **both the stop and the target fall inside one candle**, the real order is unknown, so it counts as a **stop-loss hit**
  (cautious). The report tells you how many trades this affected.
- **Costs** (default 0.1% per trade for delivery, 0.05% for intraday) are deducted from every trade.
- **Win rate** = trades that ended with a profit after costs ÷ closed trades. Trades still open at the end are shown separately.
- **Equity curve** = total profit or loss if you put the same ₹ amount into every trade.

### Limits to keep in mind
- **Survivorship bias:** it tests today's index members over the whole history. Stocks that fell out of the index
  (often the losers) are missing, so real results are usually a little worse.
- **Intraday history is only ~60 days**, because free sources don't provide more. Treat intraday results as a quick check.
- Prices are adjusted for splits and bonuses (Yahoo Finance data). Dividends are not added.
- Past results do not guarantee future results. This is a research tool, not investment advice.

## Files
| file | what it does |
|---|---|
| `fetch_data.py` | downloads prices from Yahoo Finance into `site/data/` (runs on GitHub) |
| `data/universe.json` | Nifty 500 list with index tier (50/100/200/500), from niftyindices.com |
| `docs/engine.js` | indicators, rule checking, trade simulation, statistics |
| `docs/worker.js` | runs backtests in the background so the page stays smooth |
| `docs/app.js`, `docs/index.html` | the web page |
| `.github/workflows/update-data.yml` | nightly download + publish |

To refresh the stock list after an index rebalance, replace `data/universe.json`, or just ask Claude to regenerate it.
