# HiFi Backtest for TradingView

High-fidelity backtest **parity** toolkit. Goal: make a TradingView (Pine) replica
of a strategy reproduce your MT5 broker results closely enough (~95%+ signal match)
that TradingView-side backtests can be trusted — and find out *why* when they don't.

It contains **no trading logic** beyond a textbook EMA-cross example. Bring your own rule.

## Pipeline
1. **data/** – loaders for MT5 bar export (bid), HistData (EST, no DST), Dukascopy (GMT), Binance klines → one UTC schema; broker server time (NY+7, DST-aware); gap / weekend report.
2. **replica/** – `Rule` interface: signals on *closed* bars only; `htf()` mimics `request.security` (confirmed = non-repainting, or `lookahead` to measure repaint leakage); HTF buckets follow broker midnight.
3. **match/** – reference vs candidate signals matched by rule id + side within ±N bars: recall, precision, exact-time share, median price diff, side mismatches, per-rule table, and outcome gap (R) of matched vs unmatched signals.
4. **factors/** – one-at-a-time sweep (feed swap, UTC vs broker time, fixed +2 vs DST, HTF lookahead, eval price, pip size) ranked by match-rate impact.
5. **perf/** – ATR-normalised outcomes, cost scenarios (zero / fixed / time-of-day spread), random-entry baseline p-value, rolling walk-forward.
6. **report/** – `REPORT.md` + PNG charts.

## Quick start
```bash
make install          # venv + editable install
make test             # pytest
make demo             # downloads free Binance data, runs examples/config.demo.yaml
hifi run --config your_config.yaml
```

## Using it with your own strategy
1. Export bars from MT5 (*View → Symbols → Bars → Export*), set `type: mt5` as `reference`.
2. Export the TradingView chart data (or a feed close to it: same provider as your broker) as `candidate`.
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
`examples/sample_output/REPORT.md` — EMA cross on BTCUSDT 15m, Jun–Sep 2025,
Binance USDT-M futures as "reference" vs spot as "candidate" (BTCFDUSD spot as alternate feed).
Crypto trades 24/7, so timezone factors are small here; on FX they are usually large.

## Limitations
- Outcome model is deliberately simple (symmetric ±k·ATR, stop-first on ambiguous bars).
- No tick-level fill simulation; bar data only.
- `htf()` covers time-based resampling only (no session templates / custom sessions).
- Matching is greedy nearest-first per rule.

MIT License.
