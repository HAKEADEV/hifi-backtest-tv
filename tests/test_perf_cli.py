import pandas as pd
import yaml
from hifi.replica import Context, run_rule
from hifi.replica.ema_cross import EmaCross
from hifi.perf import r_outcomes, random_baseline, spread_series
from hifi import cli


def test_costs_reduce_R(bars):
    s = run_rule(EmaCross(), bars, Context())
    z = r_outcomes(bars, s)["R"].mean()
    c = r_outcomes(bars, s, spread=spread_series(bars, {"type": "fixed", "pips": 2}, 0.0001))["R"].mean()
    assert c < z
    rb = random_baseline(bars, s, n_sims=20)
    assert 0 < rb["p_value"] <= 1


def test_cli_end_to_end(tmp_path, bars):
    def dump(df, name):
        p = tmp_path / f"{name}.csv"
        out = df.copy(); out.insert(0, "t", ((df.index - pd.Timestamp(0, tz="UTC")) // pd.Timedelta("1ms")))
        out[["t", "open", "high", "low", "close", "volume"]].to_csv(p, header=False, index=False)
        return str(p)
    noisy = bars.copy(); noisy[["open", "high", "low", "close"]] += 0.00005
    cfg = {"output": str(tmp_path / "out"), "bar": "15min",
           "feeds": {"reference": {"type": "binance", "path": dump(bars, "r")},
                     "candidate": {"type": "binance", "path": dump(noisy, "c")}},
           "rule": {"id": "ema_cross", "params": {"htf_tf": "4h"}},
           "perf": {"random_sims": 10, "walk_forward": {"grid": {"fast": [5, 9], "slow": [21]}}}}
    (tmp_path / "c.yaml").write_text(yaml.safe_dump(cfg))
    cli.main(["run", "--config", str(tmp_path / "c.yaml")])
    assert (tmp_path / "out" / "REPORT.md").exists() and (tmp_path / "out" / "equity.png").exists()
