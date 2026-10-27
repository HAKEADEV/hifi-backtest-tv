"""Performance helpers, all in ATR units so different symbols are comparable.

Outcome model (simple, documented): enter at next bar open; target +k*ATR,
stop -k*ATR (symmetric => 1R each way); exit at horizon if neither is hit
(fractional R). If both are touched inside one bar the STOP is assumed first
(conservative). Costs are a round-trip spread in price, converted to R.
"""
import numpy as np
import pandas as pd


def atr(df, n=14):
    pc = df["close"].shift(1)
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()  # Wilder / Pine ta.atr


def spread_series(df, scenario: dict, pip_size):
    """scenario: {type: zero} | {type: fixed, pips: x} | {type: tod, pips_by_hour: {h: x}, default: y} (UTC hours)."""
    t = scenario.get("type", "zero")
    if t == "zero":
        return pd.Series(0.0, index=df.index)
    if t == "fixed":
        return pd.Series(scenario["pips"] * pip_size, index=df.index)
    tbl = {int(k): v for k, v in scenario["pips_by_hour"].items()}
    return pd.Series([tbl.get(h, scenario.get("default", 0)) * pip_size for h in df.index.hour], index=df.index)


def r_outcomes(df, sigs, k=1.0, horizon=32, atr_len=14, spread=None):
    a = atr(df, atr_len).values
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    pos = df.index.get_indexer(sigs["time"])
    sp = spread.values if spread is not None else np.zeros(len(df))
    R, fwd = [], []
    for p, side in zip(pos, sigs["side"]):
        if p < 0 or p + 1 >= len(df) or not np.isfinite(a[p]) or a[p] == 0:
            R.append(np.nan); fwd.append(np.nan); continue
        e, risk = o[p + 1], k * a[p]
        tp, sl = e + side * risk, e - side * risk
        end = min(p + 1 + horizon, len(df))
        r = None
        for j in range(p + 1, end):
            if (side > 0 and l[j] <= sl) or (side < 0 and h[j] >= sl):
                r = -1.0; break
            if (side > 0 and h[j] >= tp) or (side < 0 and l[j] <= tp):
                r = 1.0; break
        if r is None:
            r = side * (c[end - 1] - e) / risk
        R.append(r - sp[p] / risk)
        fwd.append(side * (c[end - 1] - e) / a[p])
    out = sigs.copy()
    out["R"], out["fwd_atr"] = R, fwd
    return out


def summary(res):
    r = res["R"].dropna()
    win, loss = r[r > 0].sum(), -r[r < 0].sum()
    return {"trades": len(r), "mean_R": r.mean(), "hit_rate": (r > 0).mean(),
            "pf": win / loss if loss else np.inf, "total_R": r.sum(),
            "mean_fwd_atr": res["fwd_atr"].mean()}


def random_baseline(df, sigs, n_sims=500, seed=0, **kw):
    """Random entries with the same count and side mix; one-sided p = P(random >= actual)."""
    rng = np.random.default_rng(seed)
    actual = r_outcomes(df, sigs, **kw)["R"].mean()
    n = len(sigs)
    lo, hi = 50, len(df) - 50
    sims = []
    for _ in range(n_sims):
        idx = rng.integers(lo, hi, n)
        s = pd.DataFrame({"time": df.index[idx], "side": rng.permutation(sigs["side"].values)})
        sims.append(r_outcomes(df, s, **kw)["R"].mean())
    sims = np.array(sims)
    return {"actual_mean_R": actual, "random_mean_R": sims.mean(),
            "p_value": (np.sum(sims >= actual) + 1) / (n_sims + 1),
            "percentile": (sims < actual).mean() * 100, "sims": sims}


def walk_forward(df, make_rule, grid, ctx, train_weeks=4, test_weeks=1, **kw):
    """Re-optimise params on the last `train_weeks`, apply to the next `test_weeks`."""
    from ..replica.base import run_rule
    rows = []
    start = df.index[0].normalize() + pd.Timedelta(weeks=train_weeks)
    t = start
    cache = {}
    for g in grid:
        key = tuple(sorted(g.items()))
        res = r_outcomes(df, run_rule(make_rule(**g), df, ctx), **kw)
        cache[key] = res.set_index("time")["R"]
    while t + pd.Timedelta(weeks=test_weeks) <= df.index[-1]:
        tr0, te1 = t - pd.Timedelta(weeks=train_weeks), t + pd.Timedelta(weeks=test_weeks)
        best, bscore = None, -np.inf
        for key, r in cache.items():
            s = r[(r.index >= tr0) & (r.index < t)].dropna()
            if len(s) >= 5 and s.mean() > bscore:
                best, bscore = key, s.mean()
        if best is not None:
            r = cache[best]
            oos = r[(r.index >= t) & (r.index < te1)].dropna()
            rows.append({"test_start": t, "params": dict(best), "is_mean_R": bscore,
                         "oos_trades": len(oos), "oos_mean_R": oos.mean() if len(oos) else np.nan,
                         "oos_total_R": oos.sum()})
        t = te1
    return pd.DataFrame(rows)
