"""Pluggable rule interface.

A Rule looks only at CLOSED bars. ``signals(df, ctx)`` returns a Series aligned
to df.index with +1 (buy), -1 (sell) or 0, where a non-zero at bar t means the
signal is known at the CLOSE of bar t (Pine: barstate.isconfirmed). Use
``htf()`` for higher-timeframe data instead of resampling yourself: it mimics
request.security(..., lookahead=barmerge.lookahead_off) on confirmed HTF bars.
"""
from dataclasses import dataclass, field
import pandas as pd
from ..schema import resample
from ..data.timez import to_server_time, from_server_time

RULES: dict = {}


def register(cls):
    RULES[cls.id] = cls
    return cls


@dataclass
class Context:
    htf_mode: str = "confirmed"      # "confirmed" (no repaint) | "lookahead" (leaks future)
    eval_price: str = "close"        # "close" | "next_open"
    pip_size: float = 0.0001
    server_tz: str = "NY+7"          # used to align daily HTF buckets to broker day
    params: dict = field(default_factory=dict)


def htf_bars(df: pd.DataFrame, tf: str, server_tz="NY+7") -> pd.DataFrame:
    """Resample to HTF with buckets on BROKER wall-clock (H4/D1 start at server
    midnight, DST-aware for NY+7). Index returned in UTC (bucket open)."""
    if pd.Timedelta(tf) < pd.Timedelta("4h"):
        return resample(df, tf)
    loc = df.copy()
    loc.index = to_server_time(df.index, server_tz).tz_localize("UTC")  # naive wall-clock as fake-UTC
    h = resample(loc, tf)
    h.index = from_server_time(h.index.tz_localize(None), server_tz)
    return h[~h.index.isna()]


def htf(df: pd.DataFrame, tf: str, ctx: Context, col="close", series=None) -> pd.Series:
    """Value of the HTF series as seen by each LTF bar.

    confirmed: only the last COMPLETED HTF bar is visible -> value changes on the
               first LTF bar after the HTF bar closes (TradingView non-repainting).
    lookahead: the still-forming HTF bar's FINAL value is visible (classic
               repaint / future leak, e.g. lookahead_on without [1]).
    ``series`` lets you pass a function f(htf_frame)->Series (e.g. an EMA on HTF).
    """
    h = htf_bars(df, tf, ctx.server_tz)
    v = series(h) if series else h[col]
    if ctx.htf_mode == "confirmed":
        # HTF bar labelled T is complete at T+tf; make it visible from then on.
        v = v.copy()
        v.index = v.index + pd.Timedelta(tf)
        ltf_close = df.index + (df.index[1] - df.index[0])
        out = v.reindex(v.index.union(ltf_close)).ffill().reindex(ltf_close)
        out.index = df.index
        return out
    return v.reindex(v.index.union(df.index)).ffill().reindex(df.index)


class Rule:
    id = "base"
    warmup = 0

    def signals(self, df: pd.DataFrame, ctx: Context) -> pd.Series:  # pragma: no cover
        raise NotImplementedError


def run_rule(rule: Rule, df: pd.DataFrame, ctx: Context) -> pd.DataFrame:
    """Return signal table: time (signal bar open time), rule, side, price."""
    s = rule.signals(df, ctx)
    s.iloc[: rule.warmup] = 0
    hit = s[s != 0]
    if ctx.eval_price == "next_open":
        price = df["open"].shift(-1).reindex(hit.index)
    else:
        price = df["close"].reindex(hit.index)
    out = pd.DataFrame({"time": hit.index, "rule": rule.id, "side": hit.values.astype(int),
                        "price": price.values})
    return out.dropna().reset_index(drop=True)
