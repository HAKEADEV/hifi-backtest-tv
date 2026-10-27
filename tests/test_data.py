import pandas as pd
from hifi.data import load_mt5_csv, load_histdata, load_dukascopy, load_binance, to_server_time, gap_report
from hifi.data.timez import from_server_time


def test_server_time_dst():
    utc = pd.DatetimeIndex(["2024-01-15 12:00", "2024-07-15 12:00"], tz="UTC")
    st = to_server_time(utc)
    assert list(st.hour) == [14, 15]           # UTC+2 winter, UTC+3 summer
    assert (from_server_time(st) == utc).all()


def test_loaders(tmp_path):
    (tmp_path / "mt5.csv").write_text("<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\n"
                                      "2024.07.15\t15:00:00\t1.1\t1.2\t1.0\t1.15\t10\n")
    assert load_mt5_csv(tmp_path / "mt5.csv").index[0] == pd.Timestamp("2024-07-15 12:00", tz="UTC")
    (tmp_path / "hd.csv").write_text("20240715 070000;1.1;1.2;1.0;1.15;0\n")
    assert load_histdata(tmp_path / "hd.csv").index[0] == pd.Timestamp("2024-07-15 12:00", tz="UTC")
    (tmp_path / "dk.csv").write_text("Gmt time,Open,High,Low,Close,Volume\n15.07.2024 12:00:00.000,1.1,1.2,1.0,1.15,5\n")
    assert load_dukascopy(tmp_path / "dk.csv").index[0] == pd.Timestamp("2024-07-15 12:00", tz="UTC")
    (tmp_path / "bn.csv").write_text("1721044800000,1.1,1.2,1.0,1.15,5,0,0,0,0,0,0\n")
    assert load_binance(tmp_path / "bn.csv").index[0] == pd.Timestamp("2024-07-15 12:00", tz="UTC")


def test_gap_report(bars):
    g = gap_report(bars.drop(bars.index[100:105]), "15min")
    assert g["unexpected_missing_bars"] == 5
