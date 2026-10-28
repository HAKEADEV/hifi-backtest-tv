import lzma, struct
import pandas as pd
from hifi.fetch import decode_bi5, route_source, point_scale
from hifi.fetch.dukascopy import ticks_to_bars
from hifi.fetch.core import write_csv
from hifi.data import load_tds_csv, load_tradingview, load_hifi_csv


def _bi5(recs):
    return lzma.compress(b"".join(struct.pack(">3I2f", *r) for r in recs), format=lzma.FORMAT_ALONE)


def test_bi5_decode_and_resample():
    h = pd.Timestamp("2025-01-06 10:00", tz="UTC")
    raw = _bi5([(0, 103558, 103556, 1.0, 2.0), (60_000, 103600, 103590, 1.0, 1.0),
                (16 * 60_000, 103500, 103490, 0.5, 0.5)])
    t = decode_bi5(raw, h, point_scale("EURUSD"))
    assert t.index[1] == h + pd.Timedelta(minutes=1)
    assert abs(t.bid.iloc[0] - 1.03556) < 1e-9 and abs(t.ask.iloc[0] - 1.03558) < 1e-9
    b = ticks_to_bars(t, "15min", "bid")
    assert len(b) == 2 and b.high.iloc[0] == 1.0359 and b.volume.iloc[0] == 3.0
    m = ticks_to_bars(t, "15min", "mid")
    assert abs(m.open.iloc[0] - 1.03557) < 1e-9
    assert decode_bi5(b"", h, 1e5).empty


def test_point_scale_and_routing():
    assert point_scale("USDJPY") == 1e3 and point_scale("XAUUSD") == 1e3 and point_scale("EURUSD") == 1e5
    assert route_source("EURUSD") == "dukascopy"
    assert route_source("OANDA:XAUUSD") == "dukascopy"
    assert route_source("BTCUSDT") == "binance"
    assert route_source("BINANCE:ETHUSDT") == "binance"
    assert route_source("BYBIT:BTC/USDT") == "ccxt"
    assert route_source("AAPL") == "yfinance"


def test_tds_tv_hifi_loaders(tmp_path):
    (tmp_path / "tds.csv").write_text("2024.07.15,15:00,1.1,1.2,1.0,1.15,10\n")
    df = load_tds_csv(tmp_path / "tds.csv", server_tz="NY+7")
    assert df.index[0] == pd.Timestamp("2024-07-15 12:00", tz="UTC")
    (tmp_path / "tds2.csv").write_text("dt;o;h;l;c\n2024-07-15 12:00:00;1;2;0.5;1.5\n")
    df2 = load_tds_csv(tmp_path / "tds2.csv", columns=("datetime", "open", "high", "low", "close"), sep=";", header=0)
    assert df2.index[0] == pd.Timestamp("2024-07-15 12:00", tz="UTC") and df2.volume.iloc[0] == 0
    (tmp_path / "tv.csv").write_text("time,open,high,low,close,EMA\n1721044800,1.1,1.2,1.0,1.15,1.1\n")
    assert load_tradingview(tmp_path / "tv.csv").index[0] == pd.Timestamp("2024-07-15 12:00", tz="UTC")
    (tmp_path / "tv2.csv").write_text("time,open,high,low,close\n2024-07-15T21:00:00+09:00,1,2,0.5,1.5\n")
    assert load_tradingview(tmp_path / "tv2.csv").index[0] == pd.Timestamp("2024-07-15 12:00", tz="UTC")
    bars = df.copy()
    write_csv(bars, tmp_path / "b.csv", "broker")
    assert load_hifi_csv(tmp_path / "b.csv", time_mode="broker").index[0] == bars.index[0]
    write_csv(bars, tmp_path / "u.csv")
    assert load_hifi_csv(tmp_path / "u.csv").index[0] == bars.index[0]
