"""Pure-Python Dukascopy public tick feed (datafeed.dukascopy.com, hourly .bi5).
Each .bi5 is LZMA; records are 20 bytes big-endian: uint32 ms-in-hour, uint32 ask,
uint32 bid (price points), float32 ask volume, float32 bid volume. Month is 0-based."""
import lzma, struct, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd

URL = "https://datafeed.dukascopy.com/datafeed/{s}/{y}/{m:02d}/{d:02d}/{h:02d}h_ticks.bi5"
REC = np.dtype([("ms", ">u4"), ("ask", ">u4"), ("bid", ">u4"), ("askv", ">f4"), ("bidv", ">f4")])


def point_scale(symbol: str) -> float:
    s = symbol.upper()
    if s.endswith("JPY") or s.startswith(("XAU", "XAG", "XPT", "XPD")):
        return 1e3
    return 1e5


def decode_bi5(raw: bytes, hour_start: pd.Timestamp, scale: float) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame(columns=["bid", "ask", "bidv", "askv"])
    a = np.frombuffer(lzma.decompress(raw), dtype=REC)
    t = pd.Timestamp(hour_start) + pd.to_timedelta(a["ms"].astype("int64"), unit="ms")
    return pd.DataFrame({"bid": a["bid"] / scale, "ask": a["ask"] / scale,
                         "bidv": a["bidv"].astype(float), "askv": a["askv"].astype(float)},
                        index=pd.DatetimeIndex(t, name="time"))


def _get(url, cache: Path, tries=12):
    if cache.exists():
        return cache.read_bytes()
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 hifi-backtest"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(data)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_bytes(b"")
                return b""
            time.sleep(min(90, 5 * 2 ** i) if e.code == 429 else 3 + 3 * i)  # rate limited: back off
        except Exception:
            time.sleep(min(60, 3 + 3 * i))  # TLS resets happen when throttled
    raise RuntimeError(f"download failed: {url}")


def fetch_ticks(symbol, start, end, cache_dir=".hifi_cache/dukascopy", workers=2) -> pd.DataFrame:
    sym = symbol.upper()
    scale = point_scale(sym)
    hours = pd.date_range(pd.Timestamp(start, tz="UTC").floor("h"), pd.Timestamp(end, tz="UTC"),
                          freq="h", inclusive="left")
    hours = [h for h in hours if not (h.weekday() == 5 or (h.weekday() == 4 and h.hour >= 22)
                                      or (h.weekday() == 6 and h.hour < 21))]  # skip weekend

    def one(h):
        url = URL.format(s=sym, y=h.year, m=h.month - 1, d=h.day, h=h.hour)
        c = Path(cache_dir) / sym / f"{h:%Y%m%d%H}.bi5"
        return decode_bi5(_get(url, c), h, scale)

    with ThreadPoolExecutor(workers) as ex:
        parts = [p for p in ex.map(one, hours) if len(p)]
    return pd.concat(parts).sort_index() if parts else pd.DataFrame(columns=["bid", "ask", "bidv", "askv"])


def ticks_to_bars(ticks: pd.DataFrame, tf: str, side="bid") -> pd.DataFrame:
    if side == "mid":
        px = (ticks["bid"] + ticks["ask"]) / 2
        vol = ticks["bidv"] + ticks["askv"]
    else:
        px, vol = ticks[side], ticks[side + "v"]
    o = px.resample(tf, label="left", closed="left").ohlc()
    o["volume"] = vol.resample(tf, label="left", closed="left").sum()
    return o.dropna(subset=["open"])


def fetch_dukascopy(symbol, tf, start, end, side="bid", **kw) -> pd.DataFrame:
    return ticks_to_bars(fetch_ticks(symbol, start, end, **kw), tf, side)
