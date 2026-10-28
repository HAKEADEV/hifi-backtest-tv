"""`hifi run --config config.yaml` — full parity + performance pipeline."""
import argparse
import dataclasses
from pathlib import Path
import pandas as pd
import yaml

from .data import load, gap_report
from .replica import RULES, Context, run_rule
from .match import match_signals, match_stats, perf_gap
from .factors import sweep
from .perf import r_outcomes, summary, random_baseline, walk_forward, spread_series
from .report import charts, write_report


def run(cfg: dict):
    out = Path(cfg.get("output", "out"))
    bar, tol = cfg["bar"], cfg.get("match", {}).get("tol_bars", 1)
    ctx = Context(pip_size=cfg.get("pip_size", 0.0001), server_tz=str(cfg.get("server_tz", "NY+7")),
                  htf_mode=cfg.get("htf_mode", "confirmed"), eval_price=cfg.get("eval_price", "close"))
    feeds = {k: load(v) for k, v in cfg["feeds"].items()}
    lo = max(f.index.min() for f in feeds.values()); hi = min(f.index.max() for f in feeds.values())
    feeds = {k: f[(f.index >= lo) & (f.index <= hi)] for k, f in feeds.items()}
    gaps = pd.DataFrame([{"feed": k, **{x: v for x, v in gap_report(f, bar).items() if x != "table"}}
                         for k, f in feeds.items()])

    rc = cfg["rule"]
    make = lambda **p: RULES[rc["id"]](**{**rc.get("params", {}), **p})
    rule = make()
    ref = run_rule(rule, feeds["reference"], ctx)
    cand = run_rule(rule, feeds["candidate"], ctx)
    m = match_signals(ref, cand, bar, tol)
    stats = match_stats(m, ctx.pip_size)

    pc = cfg.get("perf", {})
    kw = dict(k=pc.get("k_atr", 1.0), horizon=pc.get("horizon", 32))
    ref_r = r_outcomes(feeds["reference"], ref, **kw)
    gap = perf_gap(m, {(t, int(s)): r for t, s, r in zip(ref_r.time, ref_r.side, ref_r.R)})
    sw = sweep(rule, ref, feeds, ctx, bar, tol)

    rows, equity = [], {}
    for sc in pc.get("costs", [{"name": "zero", "type": "zero"}]):
        sp = spread_series(feeds["candidate"], sc, ctx.pip_size)
        res = r_outcomes(feeds["candidate"], cand, spread=sp, **kw)
        rows.append({"scenario": sc["name"], **summary(res)})
        equity[sc["name"]] = res.set_index("time")["R"].fillna(0).cumsum()
    perf = pd.DataFrame(rows)
    nsim = pc.get("random_sims", 300)
    rnd = random_baseline(feeds["candidate"], cand, n_sims=nsim, **kw)
    wfc = pc.get("walk_forward")
    wf = pd.DataFrame()
    if wfc:
        grid = [dict(zip(wfc["grid"], v)) for v in pd.MultiIndex.from_product(wfc["grid"].values())]
        wf = walk_forward(feeds["candidate"], make, grid, ctx, wfc.get("train_weeks", 4), wfc.get("test_weeks", 1), **kw)

    files = charts(out, sw, equity, rnd, wf)
    m.to_csv(out / "matches.csv", index=False)
    write_report(out, {"title": cfg.get("title", ""), "rule": rc["id"], "bar": bar, "tol": tol,
                       "start": lo, "end": hi, "gaps": gaps, "stats": stats, "gap": gap, "sweep": sw,
                       "perf": perf, "rnd": rnd, "rnd_n": nsim, "wf": wf}, files)
    print(stats.loc["ALL"].to_string())
    print(f"report: {out / 'REPORT.md'}")
    return {"stats": stats, "sweep": sw, "perf": perf, "rnd": rnd, "wf": wf}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hifi")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--config", required=True)
    f = sub.add_parser("fetch", help="download bars automatically (no login)")
    f.add_argument("--symbol", required=True, help="EURUSD, XAUUSD, BTCUSDT, AAPL, BYBIT:BTC/USDT ...")
    f.add_argument("--tf", default="15m")
    f.add_argument("--from", dest="start", required=True)
    f.add_argument("--to", dest="end", required=True)
    f.add_argument("--source", default="auto", choices=["auto", "dukascopy", "binance", "ccxt", "yfinance"])
    f.add_argument("--side", default="bid", choices=["bid", "ask", "mid"], help="dukascopy only")
    f.add_argument("--market", default="spot", choices=["spot", "futures"], help="binance only")
    f.add_argument("--time", dest="time_mode", default="utc", choices=["utc", "broker"],
                   help="broker = NY+7 with DST (MT-style server time)")
    f.add_argument("--cache", default=".hifi_cache/dukascopy")
    f.add_argument("--workers", type=int, default=2, help="parallel downloads (Dukascopy rate-limits; keep low)")
    f.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        from .fetch import fetch, write_csv
        src, df = fetch(a.symbol, a.tf, a.start, a.end, a.source, a.side, a.market, a.cache, a.workers)
        p = write_csv(df, a.out, a.time_mode)
        print(f"{src}: {len(df)} bars {df.index.min()} -> {df.index.max()} -> {p}")
        return
    cfg = yaml.safe_load(Path(a.config).read_text())
    run(cfg)


if __name__ == "__main__":
    main()
