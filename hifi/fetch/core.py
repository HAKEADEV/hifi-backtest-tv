import io, urllib.request, zipfile
from pathlib import Path
import pandas as pd
from .route import route_source, clean
from .dukascopy import fetch_dukascopy
from ..data.timez import to_server_time

TF = {"1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min",
      "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1D"}


def _binance(symbol, tf, start, end, market="spot"):
    s = clean(symbol)
    base = ("https://data.binance.vision/data/futures/um" if market == "futures"
            else "https://data.binance.vision/data/spot")
    frames = []
    for m in pd.period_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta("1ns"), freq="M"):
        url = f"{base}/monthly/klines/{s}/{tf}/{s}-{tf}-{m}.zip"
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
        except urllib.error.HTTPError:
            continue
        df = pd.read_csv(z.open(z.namelist()[0]), header=None)
        if not str(df.iloc[0, 0]).isdigit():
            df = df.iloc[1:]
        ot = df[0].astype("int64")
        t = pd.to_datetime(ot, unit="us" if ot.iloc[0] > 10**14 else "ms", utc=True)
        frames.append(pd.DataFrame({c: df[i].astype(float).values for i, c in
                                    enumerate(["open", "high", "low", "close", "volume"], 1)}, index=t))
    if not frames:
        raise RuntimeError(f"no Binance monthly data for {s} {tf}")
    return pd.concat(frames)


def _ccxt(symbol, tf, start, end):
    import ccxt  # optional: pip install ccxt
    ex_id, pair = symbol.split(":", 1)
    ex = getattr(ccxt, ex_id.lower())()
    since, stop, rows = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000), \
        int(pd.Timestamp(end, tz="UTC").timestamp() * 1000), []
    while since < stop:
        b = ex.fetch_ohlcv(pair, tf, since=since, limit=1000)
        if not b:
            break
        rows += b
        since = b[-1][0] + 1
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume"]).drop_duplicates("t")
    return df.set_index(pd.to_datetime(df.pop("t"), unit="ms", utc=True))


def _yf(symbol, tf, start, end):
    import yfinance as yf  # optional: pip install yfinance
    df = yf.download(symbol, start=start, end=end, interval=tf, progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    df.index = pd.DatetimeIndex(df.index).tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    return df


def fetch(symbol, tf, start, end, source="auto", side="bid", market="spot", cache_dir=".hifi_cache/dukascopy", workers=2):
    src = route_source(symbol) if source == "auto" else source
    if src == "dukascopy":
        df = fetch_dukascopy(clean(symbol), TF[tf], start, end, side=side, cache_dir=cache_dir, workers=workers)
    elif src == "binance":
        df = _binance(symbol, tf, start, end, market)
    elif src == "ccxt":
        df = _ccxt(symbol, tf, start, end)
    elif src == "yfinance":
        df = _yf(symbol, tf, start, end)
    else:
        raise ValueError(src)
    s, e = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    df = df[(df.index >= s) & (df.index < e)]
    df.index.name = "time"
    return src, df


def write_csv(df, out, time_mode="utc", server_tz="NY+7"):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    d = df.copy()
    d.index = to_server_time(d.index, server_tz) if time_mode == "broker" else d.index.tz_convert(None)
    d.index.name = "time"
    d.to_csv(out, date_format="%Y-%m-%d %H:%M:%S", float_format="%.10g")
    return out
