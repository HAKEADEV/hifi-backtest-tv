"""Example rule: plain EMA crossover with optional HTF trend filter.
Public textbook logic, included only to demonstrate the pipeline."""
import pandas as pd
from .base import Rule, register, htf


def ema(s, n):
    # Matches Pine ta.ema (alpha = 2/(n+1), seeded with first value; warmup hides seed bias)
    return s.ewm(span=n, adjust=False).mean()


@register
class EmaCross(Rule):
    id = "ema_cross"

    def __init__(self, fast=9, slow=21, htf_tf=None, htf_len=50):
        self.fast, self.slow, self.htf_tf, self.htf_len = fast, slow, htf_tf, htf_len
        self.warmup = slow * 5

    def signals(self, df, ctx):
        f, s = ema(df["close"], self.fast), ema(df["close"], self.slow)
        up = (f > s) & (f.shift(1) <= s.shift(1))
        dn = (f < s) & (f.shift(1) >= s.shift(1))
        if self.htf_tf:
            trend = htf(df, self.htf_tf, ctx, series=lambda h: ema(h["close"], self.htf_len))
            up &= df["close"] > trend
            dn &= df["close"] < trend
        return up.astype(int) - dn.astype(int)
