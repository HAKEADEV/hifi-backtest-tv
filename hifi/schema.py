"""Canonical bar schema used everywhere.

A bar frame is a pandas DataFrame indexed by a tz-aware UTC DatetimeIndex named
``time`` (bar OPEN time) with float columns open, high, low, close, volume.
"""
import pandas as pd

COLS = ["open", "high", "low", "close", "volume"]


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "volume" not in df:
        df["volume"] = 0.0
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    df.index = idx.rename("time")
    df = df[COLS].astype(float)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def resample(df: pd.DataFrame, rule: str, offset=None) -> pd.DataFrame:
    """OHLCV resample. ``offset`` shifts bucket boundaries (e.g. broker-time days)."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = df.resample(rule, label="left", closed="left", offset=offset).agg(agg)
    return out.dropna(subset=["open"])
