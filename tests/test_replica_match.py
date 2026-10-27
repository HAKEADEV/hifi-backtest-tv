import pandas as pd
from hifi.replica import Context, run_rule, htf
from hifi.replica.ema_cross import EmaCross
from hifi.match import match_signals, match_stats


def test_no_lookahead(bars):
    """Changing the future must not change past signals (confirmed HTF)."""
    rule, ctx = EmaCross(htf_tf="4h"), Context()
    full = run_rule(rule, bars, ctx)
    cut = bars.index[2000]
    part = run_rule(rule, bars[bars.index <= cut], ctx)
    a = full[full.time < cut - pd.Timedelta("15min")].reset_index(drop=True)
    b = part[part.time < cut - pd.Timedelta("15min")].reset_index(drop=True)
    pd.testing.assert_frame_equal(a[["time", "side"]], b[["time", "side"]])


def test_lookahead_leaks(bars):
    ctx_c, ctx_l = Context(), Context(htf_mode="lookahead")
    a = htf(bars, "4h", ctx_c); b = htf(bars, "4h", ctx_l)
    # broker H4 bucket 02:00-06:00 UTC (winter): at 04:00 lookahead already sees the 05:45 close
    assert b.iloc[16] == bars["close"].iloc[23] and a.iloc[16] != b.iloc[16]


def test_match_self_and_shift(bars):
    s = run_rule(EmaCross(), bars, Context())
    st = match_stats(match_signals(s, s, "15min"))
    assert st.loc["ALL", "recall"] == 1 and st.loc["ALL", "exact_time"] == 1
    sh = s.copy(); sh["time"] += pd.Timedelta("15min")
    st = match_stats(match_signals(s, sh, "15min", tol_bars=1))
    assert st.loc["ALL", "recall"] == 1 and st.loc["ALL", "exact_time"] == 0
    flip = s.copy(); flip["side"] *= -1
    assert match_stats(match_signals(s, flip, "15min")).loc["ALL", "side_mismatch"] == len(s)
