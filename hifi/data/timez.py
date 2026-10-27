"""Broker server time. Most FX brokers run 'New York + 7h': UTC+2 in winter,
UTC+3 during US DST, so the daily bar always opens at 17:00 New York."""
import pandas as pd


def server_offset_hours(idx_utc: pd.DatetimeIndex, server_tz="NY+7"):
    idx_utc = pd.DatetimeIndex(idx_utc)
    if server_tz == "NY+7":
        ny = idx_utc.tz_convert("America/New_York")
        return pd.Index([o.total_seconds() / 3600 for o in ny.map(lambda x: x.utcoffset())]) + 7
    return pd.Index([float(server_tz)] * len(idx_utc))


def to_server_time(idx_utc, server_tz="NY+7") -> pd.DatetimeIndex:
    """UTC -> naive broker server wall-clock."""
    idx_utc = pd.DatetimeIndex(idx_utc)
    off = server_offset_hours(idx_utc, server_tz)
    return (idx_utc.tz_convert(None) + pd.to_timedelta(off, unit="h"))


def from_server_time(idx_naive, server_tz="NY+7") -> pd.DatetimeIndex:
    """Naive broker wall-clock -> UTC."""
    idx = pd.DatetimeIndex(idx_naive)
    if server_tz == "NY+7":
        ny = (idx - pd.Timedelta(hours=7)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward")
        return ny.tz_convert("UTC")
    return (idx - pd.Timedelta(hours=float(server_tz))).tz_localize("UTC")


def daily_offset(server_tz="NY+7"):
    """Resample offset so HTF buckets align to the broker day (approx: winter offset)."""
    return pd.Timedelta(hours=-2) if server_tz == "NY+7" else pd.Timedelta(hours=-float(server_tz))
