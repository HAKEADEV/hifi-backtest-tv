"""Feed loaders. Every loader returns the canonical schema (UTC index)."""
from pathlib import Path
import glob
import pandas as pd
from ..schema import normalize
from .timez import from_server_time


def _files(path):
    p = str(path)
    return sorted(glob.glob(p)) if any(c in p for c in "*?[") else [p]


def load_mt5_csv(path, server_tz="NY+7", price="bid") -> pd.DataFrame:
    """MT5 'Export bars' CSV (tab separated, <DATE> <TIME> <OPEN>...). Times are
    broker server time; MT5 bars are BID prices. ``server_tz`` is 'NY+7'
    (DST-aware, the common FX convention) or a fixed offset like '+2'."""
    frames = []
    for f in _files(path):
        df = pd.read_csv(f, sep=None, engine="python")
        df.columns = [c.strip("<>").lower() for c in df.columns]
        t = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
        vol = df["tickvol"] if "tickvol" in df else df.get("vol", 0)
        frames.append(pd.DataFrame({"open": df["open"].values, "high": df["high"].values,
                                    "low": df["low"].values, "close": df["close"].values,
                                    "volume": pd.Series(vol).values}, index=t))
    out = pd.concat(frames)
    out.index = from_server_time(out.index, server_tz)
    return normalize(out)


def load_histdata(path) -> pd.DataFrame:
    """HistData.com ASCII M1: 'YYYYMMDD HHMMSS;O;H;L;C;V', timestamps in EST
    WITHOUT daylight saving (fixed UTC-5). Prices are bid."""
    frames = []
    for f in _files(path):
        df = pd.read_csv(f, sep=";", header=None, names=["t", "open", "high", "low", "close", "volume"])
        t = pd.to_datetime(df["t"], format="%Y%m%d %H%M%S") + pd.Timedelta(hours=5)
        frames.append(df.drop(columns="t").set_index(t))
    return normalize(pd.concat(frames))


def load_dukascopy(path) -> pd.DataFrame:
    """Dukascopy CSV export: 'Gmt time,Open,High,Low,Close,Volume' with
    'DD.MM.YYYY HH:MM:SS.fff' in GMT. Choose BID or ASK when exporting."""
    frames = []
    for f in _files(path):
        df = pd.read_csv(f)
        df.columns = [c.strip().lower() for c in df.columns]
        tcol = [c for c in df.columns if "time" in c][0]
        t = pd.to_datetime(df[tcol], format="%d.%m.%Y %H:%M:%S.%f", utc=True)
        frames.append(df.drop(columns=tcol).set_index(t))
    out = normalize(pd.concat(frames))
    return out[out["volume"] > 0] if (out["volume"] > 0).any() else out  # drop flat filler bars


def load_binance(path) -> pd.DataFrame:
    """data.binance.vision kline CSV (no header; open_time in ms, or us since 2025)."""
    frames = []
    for f in _files(path):
        df = pd.read_csv(f, header=None)
        if not str(df.iloc[0, 0]).isdigit():
            df = df.iloc[1:]
        ot = df[0].astype("int64")
        unit = "us" if ot.iloc[0] > 10**14 else "ms"
        t = pd.to_datetime(ot, unit=unit, utc=True)
        frames.append(pd.DataFrame({"open": df[1].values, "high": df[2].values, "low": df[3].values,
                                    "close": df[4].values, "volume": df[5].values}, index=t))
    return normalize(pd.concat(frames))


def load_hifi_csv(path, time_mode="utc", server_tz="NY+7") -> pd.DataFrame:
    """CSV written by `hifi fetch` (time,open,high,low,close,volume)."""
    frames = [pd.read_csv(f, parse_dates=["time"], index_col="time") for f in _files(path)]
    out = pd.concat(frames)
    if time_mode == "broker":
        out.index = from_server_time(out.index, server_tz)
    return normalize(out)


def load_tradingview(path, tz="UTC") -> pd.DataFrame:
    """TradingView 'Export chart data' CSV: time (unix seconds or ISO8601 with offset),
    open, high, low, close[, Volume, indicator columns...]. Extra columns are ignored."""
    frames = []
    for f in _files(path):
        df = pd.read_csv(f)
        df.columns = [c.strip().lower() for c in df.columns]
        t = df["time"]
        if pd.api.types.is_numeric_dtype(t):
            idx = pd.to_datetime(t, unit="s", utc=True)
        else:
            idx = pd.to_datetime(t, utc=False)
            idx = pd.DatetimeIndex(idx)
            idx = idx.tz_localize(tz) if idx.tz is None else idx
        frames.append(pd.DataFrame({c: df[c].values for c in ["open", "high", "low", "close"]} |
                                   {"volume": df["volume"].values if "volume" in df else 0.0},
                                   index=pd.DatetimeIndex(idx)))
    return normalize(pd.concat(frames))


def load_tds_csv(path, columns=("date", "time", "open", "high", "low", "close", "volume"), sep=",",
                 header=None, time_format=None, server_tz="0") -> pd.DataFrame:
    """Tick Data Suite / MT-style bar export. ``columns`` names each column in order
    (use 'datetime' for a single combined column, '_' to skip). ``server_tz`` is the
    GMT offset chosen at export ('0', '+2' or 'NY+7')."""
    frames = []
    for f in _files(path):
        df = pd.read_csv(f, sep=sep, header=header, names=list(columns) if header is None else None)
        if header is not None:
            df.columns = list(columns)
        if "datetime" in df:
            t = pd.to_datetime(df["datetime"].astype(str), format=time_format)
        else:
            t = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), format=time_format)
        frames.append(pd.DataFrame({c: df[c].values for c in ["open", "high", "low", "close"]} |
                                   {"volume": df["volume"].values if "volume" in df else 0.0},
                                   index=pd.DatetimeIndex(t)))
    out = pd.concat(frames)
    out.index = from_server_time(out.index, server_tz)
    return normalize(out)


LOADERS = {"mt5": load_mt5_csv, "histdata": load_histdata, "dukascopy": load_dukascopy, "binance": load_binance,
           "hifi": load_hifi_csv, "tradingview": load_tradingview, "tds": load_tds_csv}


def load(spec: dict) -> pd.DataFrame:
    """spec = {type: mt5|histdata|dukascopy|binance|hifi|tradingview|tds, path: glob, ...loader kwargs}"""
    spec = dict(spec)
    kind = spec.pop("type")
    return LOADERS[kind](**spec)
