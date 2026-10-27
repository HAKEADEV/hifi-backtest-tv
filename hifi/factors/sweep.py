"""One-at-a-time factor sweep: start from the baseline replica settings, flip a
single factor, and measure how much the match rate vs the reference moves.
Large deltas = factors you must pin down before trusting TradingView results."""
import dataclasses
import pandas as pd
from ..replica.base import run_rule
from ..match.matcher import match_signals, match_stats

DEFAULT_FACTORS = {
    "feed_swap": "use the alternate feed instead of the candidate feed",
    "timezone_utc": "HTF/day buckets in UTC instead of broker NY+7 (DST-aware)",
    "timezone_fixed_+2": "fixed UTC+2 server time (ignores DST)",
    "htf_lookahead": "HTF values taken from the still-forming bar (repaint)",
    "eval_next_open": "evaluate signal price at next bar open instead of close",
    "pip_size_x10": "pip size 10x (common JPY / metals mistake)",
}


def sweep(rule, ref_sigs, feeds: dict, base_ctx, bar, tol_bars=1, factors=None):
    factors = factors or list(DEFAULT_FACTORS)

    def score(df, ctx):
        st = match_stats(match_signals(ref_sigs, run_rule(rule, df, ctx), bar, tol_bars), ctx.pip_size)
        return st.loc["ALL"]

    base = score(feeds["candidate"], base_ctx)
    rows = [{"factor": "baseline", "description": "candidate feed, broker time, confirmed HTF",
             **base.to_dict()}]
    for f in factors:
        ctx, df = dataclasses.replace(base_ctx), feeds["candidate"]
        if f == "feed_swap":
            if "alternate" not in feeds:
                continue
            df = feeds["alternate"]
        elif f == "timezone_utc":
            ctx.server_tz = "0"
        elif f == "timezone_fixed_+2":
            ctx.server_tz = "2"
        elif f == "htf_lookahead":
            ctx.htf_mode = "lookahead"
        elif f == "eval_next_open":
            ctx.eval_price = "next_open"
        elif f == "pip_size_x10":
            ctx.pip_size = base_ctx.pip_size * 10
        s = score(df, ctx)
        rows.append({"factor": f, "description": DEFAULT_FACTORS.get(f, ""), **s.to_dict()})
    t = pd.DataFrame(rows)
    t["recall_delta"] = t["recall"] - base["recall"]
    t["precision_delta"] = t["precision"] - base["precision"]
    t["impact"] = t[["recall_delta", "precision_delta"]].abs().max(axis=1)
    return pd.concat([t.iloc[:1], t.iloc[1:].sort_values("impact", ascending=False)]).reset_index(drop=True)
