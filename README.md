# HiFi Backtest for TradingView

High-fidelity backtest toolkit. **Fetch clean market data automatically (no login, no exports)**
and validate what your TradingView (Pine) strategy does against it — then find out *why* results
differ (feed, time zone, gaps, HTF handling, costs). Comparing against an MT5 broker is **optional**.

It contains **no trading logic** beyond a textbook EMA-cross example. Bring your own rule.

## Quick start
```bash
git clone https://github.com/HAKEADEV/hifi-backtest-tv && cd hifi-backtest-tv
python3 -m venv .venv && .venv/bin/pip install -e .[dev]      # or: make install
.venv/bin/python -m pytest -q                                   # make test

# 1) fetch data automatically (source picked from the symbol)
.venv/bin/hifi fetch --symbol EURUSD  --tf 15m --from 2025-01-06 --to 2025-01-13 --out examples/data/EURUSD_15m_bid.csv
.venv/bin/hifi fetch --symbol BTCUSDT --tf 15m --from 2025-06-01 --to 2025-07-01 --out examples/data/BTCUSDT_15m.csv

# 2) run the validation pipeline
make demo-fx      # EURUSD, Dukascopy BID vs MID
make demo         # BTCUSDT, Binance futures vs spot
.venv/bin/hifi run --config your_config.yaml
```
Requirements: Python 3.10+, internet. Nothing else (no Node, browser, MT5 or API keys).

### `hifi fetch`
| symbol looks like | `--source auto` picks | notes |
|---|---|---|
| `EURUSD`, `USDJPY`, `XAUUSD`, `OANDA:EURUSD` | **dukascopy** (default for FX & metals) | public hourly tick files → bars; `--side bid|ask|mid` (default bid) |
| `BTCUSDT`, `ETHFDUSD` | binance | data.binance.vision monthly klines; `--market spot|futures` |
| `BYBIT:BTC/USDT`, `OKX:ETH/USDT` | ccxt | `pip install -e .[exchanges]` |
| `AAPL`, `^GSPC` | yfinance | `pip install -e .[stocks]`; short intraday history |

Output: CSV `time,open,high,low,close,volume`, bar open time in **UTC**; `--time broker` writes
NY+7 server time (DST-aware, MT-style). Raw Dukascopy files are cached in `.hifi_cache/` so re-runs
and other sides are instant. Dukascopy rate-limits aggressively: keep `--workers` low (default 2);
a week of 15m ≈ 120 hourly files and can take several minutes.

Load fetched files with `{type: hifi, path: ...}` and TradingView exports with `{type: tradingview, ...}`.
See **[docs/TRADINGVIEW.md](docs/TRADINGVIEW.md)** for symbol matching, CSV export, time/gap alignment and Basic-plan limits.

### Optional: MT5 / Tick Data Suite
Want to confirm your broker data too? Export MT5 bars (`type: mt5`) or Tick Data Suite CSVs (`type: tds`,
see `optional/tick_data_suite/`). Not needed for TradingView validation.

## Pipeline
0. **fetch/** – `hifi fetch`: Dukascopy ticks (pure Python bi5 decoder), Binance, ccxt, yfinance → normalized CSV.
1. **data/** – loaders for hifi CSV, TradingView export, MT5 bar export (bid), Tick Data Suite, HistData (EST, no DST), Dukascopy (GMT), Binance klines → one UTC schema; broker server time (NY+7, DST-aware); gap / weekend report.
2. **replica/** – `Rule` interface: signals on *closed* bars only; `htf()` mimics `request.security` (confirmed = non-repainting, or `lookahead` to measure repaint leakage); HTF buckets follow broker midnight.
3. **match/** – reference vs candidate signals matched by rule id + side within ±N bars: recall, precision, exact-time share, median price diff, side mismatches, per-rule table, and outcome gap (R) of matched vs unmatched signals.
4. **factors/** – one-at-a-time sweep (feed swap, UTC vs broker time, fixed +2 vs DST, HTF lookahead, eval price, pip size) ranked by match-rate impact.
5. **perf/** – ATR-normalised outcomes, cost scenarios (zero / fixed / time-of-day spread), random-entry baseline p-value, rolling walk-forward.
6. **report/** – `REPORT.md` + PNG charts.

## Using it with your own strategy
1. `hifi fetch` your symbol as `reference` (`type: hifi`). Optional: MT5 bar export (`type: mt5`) instead.
2. Export the TradingView chart data as `candidate` (`type: tradingview`).
3. Implement your rule in `hifi/replica/your_rule.py` (subclass `Rule`, decorate with `@register`) and its Pine twin.
   Alternatively compare **signal exports** directly with `hifi.match.match_signals`.
4. Run, read section 2 first. Fix the top factors in section 3 until parity is ~95%; only then read section 4.

## Parity checklist (learned the hard way)
- Pick the data provider closest to your broker; feed differences dominate everything else.
- Align HTF/day boundaries to broker server time (NY+7 incl. DST), not UTC.
- Use confirmed HTF values (`request.security(..., expr[1], lookahead=barmerge.lookahead_on)`).
- MT5 bars are bid; TradingView FX feeds are often mid — expect a constant offset in price.
- Model costs explicitly and always compare against random entries.

## Demo
`make demo-fx` — EURUSD 15m, one week (2025-01-06..13), Dukascopy BID (reference) vs MID (candidate), ASK as alternate.
No committed sample output yet: Dukascopy rate-limited the generating host during generation; run it locally.

`examples/sample_output/REPORT.md` — EMA cross on BTCUSDT 15m, Jun–Sep 2025,
Binance USDT-M futures as "reference" vs spot as "candidate" (BTCFDUSD spot as alternate feed).
Crypto trades 24/7, so timezone factors are small here; on FX they are usually large.

## Limitations
- Outcome model is deliberately simple (symmetric ±k·ATR, stop-first on ambiguous bars).
- No tick-level fill simulation; bar data only.
- `htf()` covers time-based resampling only (no session templates / custom sessions).
- Matching is greedy nearest-first per rule.

MIT License. See NOTICE: no market data is included; fetched data is subject to each provider's terms.
