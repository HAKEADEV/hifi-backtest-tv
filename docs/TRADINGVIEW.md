# Validating on TradingView

HiFi's main job: give you an automatically fetched, clean reference feed so you can
check that what your Pine script does on TradingView is what it *would* do on clean data —
and see which environment factors (feed, time zone, gaps, HTF handling) move the result.

## 1. Pick the TradingView symbol that matches the source

| `hifi fetch` source | Good TradingView symbols | Notes |
|---|---|---|
| dukascopy (FX, metals) | `OANDA:EURUSD`, `FX:EURUSD`, `FXCM:EURUSD`, `OANDA:XAUUSD` (no Dukascopy feed on TV) | TV FX feeds are usually **mid** or provider bid; fetch `--side mid` and `--side bid` and compare both. Expect small price offsets and different tick volume. |
| binance (crypto) | `BINANCE:BTCUSDT` (spot), `BINANCE:BTCUSDT.P` (USDT-M perp, use `--market futures`) | Same venue → near-identical bars. |
| ccxt (`BYBIT:BTC/USDT`, `OKX:...`) | `BYBIT:BTCUSDT`, `OKX:BTCUSDT` | Same exchange on both sides. |
| yfinance (stocks / indices) | `NASDAQ:AAPL`, `NYSE:...` | Intraday history on Yahoo is short (1m ≈ 7 days, ≤1h ≈ 730 days). |

## 2. Export the TradingView chart
1. Open the chart with the same symbol + timeframe, add your indicator/strategy.
2. Chart menu (▾ next to the layout name) → **Export chart data…** → time format **UNIX timestamp** (or ISO).
3. Load it in a config:
```yaml
feeds:
  reference: {type: hifi, path: "examples/data/EURUSD_15m_mid.csv"}   # from hifi fetch
  candidate: {type: tradingview, path: "exports/OANDA_EURUSD, 15.csv"} # TV export
```
Indicator columns in the export are ignored by the loader (you can read them yourself to compare plotted values).

## 3. Align time and gaps
- `hifi fetch` writes **UTC** by default; `--time broker` writes NY+7 (DST-aware, the common MT broker clock). TV exports in UNIX time are UTC; ISO exports carry their offset.
- Daily / 4h bars on TV for FX start at 17:00 New York; set `server_tz: "NY+7"` so HTF buckets match.
- `REPORT.md` section 1 lists missing bars per feed. Dukascopy omits zero-tick periods (holidays, rollover minutes).
- Matching uses ±`tol_bars` (default 1) to absorb one-bar offsets.

## 4. TradingView Basic (free) limits that matter
- Max 2 indicators per chart, scripts cannot be saved privately on some flows, no second-based charts,
  no Bar Magnifier / Deep Backtesting, limited history bars (≈5k on Basic). Export what is visible.
- For longer history use `hifi fetch` and run the Python replica; use TV for spot checks.

## Optional: MT5 / Tick Data Suite
If you also want to confirm your MT5 broker data, see `optional/tick_data_suite/` and the `mt5` / `tds` loaders. Not required.
