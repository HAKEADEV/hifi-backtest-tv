"""Signal matching between a reference (e.g. MT5 / broker) and a candidate
(e.g. TradingView replica). A pair matches when rule id and side agree and the
times are within ±tol bars. Greedy nearest-first, one-to-one."""
import numpy as np
import pandas as pd


def match_signals(ref: pd.DataFrame, cand: pd.DataFrame, bar: str, tol_bars=1) -> pd.DataFrame:
    step = pd.Timedelta(bar)
    rows, used = [], set()
    for rule in sorted(set(ref["rule"]) | set(cand["rule"])):
        r = ref[ref["rule"] == rule].reset_index()
        c = cand[cand["rule"] == rule].reset_index()
        ct = c["time"].values
        for _, x in r.iterrows():
            best = None
            if len(c):
                d = np.abs((pd.DatetimeIndex(c["time"]) - x["time"]) / step)
                for j in np.argsort(d):
                    if d[j] > tol_bars:
                        break
                    if (rule, j) in used:
                        continue
                    best = j
                    break
            if best is None:
                rows.append({"rule": rule, "ref_time": x["time"], "cand_time": pd.NaT, "ref_side": x["side"],
                             "cand_side": np.nan, "ref_price": x["price"], "cand_price": np.nan, "status": "ref_only"})
            else:
                used.add((rule, best))
                y = c.loc[best]
                rows.append({"rule": rule, "ref_time": x["time"], "cand_time": y["time"], "ref_side": x["side"],
                             "cand_side": y["side"], "ref_price": x["price"], "cand_price": y["price"],
                             "status": "matched" if y["side"] == x["side"] else "side_mismatch"})
        for j in range(len(c)):
            if (rule, j) not in used:
                y = c.loc[j]
                rows.append({"rule": rule, "ref_time": pd.NaT, "cand_time": y["time"], "ref_side": np.nan,
                             "cand_side": y["side"], "ref_price": np.nan, "cand_price": y["price"], "status": "cand_only"})
    cols = ["rule", "ref_time", "cand_time", "ref_side", "cand_side", "ref_price", "cand_price", "status"]
    return pd.DataFrame(rows, columns=cols)


def match_stats(m: pd.DataFrame, pip_size=0.0001) -> pd.DataFrame:
    """Per-rule and ALL rows: recall, precision, exact-time share, median |price diff| (pips), side mismatches."""
    def one(g):
        mt = g[g.status == "matched"]
        nref = int(g["ref_time"].notna().sum())
        ncand = int(g["cand_time"].notna().sum())
        return pd.Series({
            "ref": nref, "cand": ncand, "matched": len(mt),
            "recall": len(mt) / nref if nref else np.nan,
            "precision": len(mt) / ncand if ncand else np.nan,
            "exact_time": (mt.ref_time == mt.cand_time).mean() if len(mt) else np.nan,
            "median_price_diff_pips": (mt.ref_price - mt.cand_price).abs().median() / pip_size if len(mt) else np.nan,
            "side_mismatch": int((g.status == "side_mismatch").sum()),
        })
    per = m.groupby("rule").apply(one, include_groups=False)
    per.loc["ALL"] = one(m)
    return per


def perf_gap(m: pd.DataFrame, r_by_time: pd.Series) -> pd.DataFrame:
    """Mean outcome in R for reference signals that were matched vs unmatched.
    ``r_by_time``: Series indexed by (time, side)-> R, from perf.forward.r_outcomes."""
    ref = m[m.ref_time.notna()].copy()
    ref["R"] = [r_by_time.get((t, int(s)), np.nan) for t, s in zip(ref.ref_time, ref.ref_side)]
    ref["group"] = np.where(ref.status == "matched", "matched", "unmatched")
    g = ref.groupby("group")["R"].agg(["count", "mean"])
    allmean = ref["R"].mean()
    g.loc["ALL"] = [ref["R"].count(), allmean]
    g["impact_on_total_mean_R"] = np.nan
    if "unmatched" in g.index:
        g.loc["ALL", "impact_on_total_mean_R"] = allmean - g.loc["matched", "mean"] if "matched" in g.index else np.nan
    return g
