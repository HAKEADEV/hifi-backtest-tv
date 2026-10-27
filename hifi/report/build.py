"""Markdown report + PNG charts."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _md(df, floatfmt=".3f"):
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else format(v, floatfmt))
    df = df.astype(str)
    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "".join("| " + " | ".join(r) + " |\n" for r in df.values)


def charts(out: Path, sweep_t, equity: dict, rnd, wf):
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    t = sweep_t.iloc[1:]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(t["factor"], t["recall_delta"] * 100, color="tab:red")
    ax.set_xlabel("recall change vs baseline (pct points)"); ax.set_title("Factor sweep: match-rate impact")
    ax.invert_yaxis(); fig.tight_layout(); fig.savefig(out / "factor_sweep.png", dpi=110); plt.close(fig)
    files["factor_sweep"] = "factor_sweep.png"
    fig, ax = plt.subplots(figsize=(8, 4))
    for name, s in equity.items():
        ax.plot(s.index, s.values, label=name)
    ax.set_ylabel("cumulative R"); ax.set_title("Equity by cost scenario"); ax.legend(); fig.autofmt_xdate()
    fig.tight_layout(); fig.savefig(out / "equity.png", dpi=110); plt.close(fig)
    files["equity"] = "equity.png"
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(rnd["sims"], bins=40, color="grey")
    ax.axvline(rnd["actual_mean_R"], color="tab:blue", label="strategy")
    ax.set_xlabel("mean R per trade"); ax.set_title(f"Random-entry baseline (p={rnd['p_value']:.3f})"); ax.legend()
    fig.tight_layout(); fig.savefig(out / "random_baseline.png", dpi=110); plt.close(fig)
    files["random"] = "random_baseline.png"
    if len(wf):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(wf["test_start"], wf["oos_total_R"].cumsum(), marker="o")
        ax.set_ylabel("cumulative OOS R"); ax.set_title("Walk-forward (out-of-sample)"); fig.autofmt_xdate()
        fig.tight_layout(); fig.savefig(out / "walk_forward.png", dpi=110); plt.close(fig)
        files["wf"] = "walk_forward.png"
    return files


def write_report(out: Path, R: dict, files: dict):
    L = [f"# HiFi Backtest report — {R['title']}", "",
         f"Rule `{R['rule']}` · bar `{R['bar']}` · {R['start']} → {R['end']} (UTC) · tolerance ±{R['tol']} bar(s)", "",
         "## 1. Data quality", "", _md(R["gaps"]), "",
         "## 2. Signal parity (reference vs candidate)", "", _md(R["stats"].reset_index()), "",
         "Outcome of reference signals, matched vs unmatched (R):", "", _md(R["gap"].reset_index()), "",
         "## 3. Factor sweep (one at a time, ranked by impact)", "", _md(R["sweep"]), "",
         f"![factor sweep]({files['factor_sweep']})", "",
         "## 4. Performance (candidate feed, ATR-normalised)", "", _md(R["perf"]), "",
         f"![equity]({files['equity']})", "",
         "### Random-entry baseline", "",
         f"Strategy mean R {R['rnd']['actual_mean_R']:.3f} vs random {R['rnd']['random_mean_R']:.3f}; "
         f"percentile {R['rnd']['percentile']:.1f}; one-sided p = {R['rnd']['p_value']:.3f} "
         f"({R['rnd_n']} sims, zero cost).", "", f"![random]({files['random']})", ""]
    if "wf" in files:
        wf = R["wf"].copy(); wf["params"] = wf["params"].astype(str)
        L += ["### Walk-forward", "", f"OOS total R: {wf['oos_total_R'].sum():.2f} over {len(wf)} windows; "
              f"in-sample mean R {wf['is_mean_R'].mean():.3f} vs OOS {wf['oos_mean_R'].mean():.3f}.", "",
              _md(wf), "", f"![wf]({files['wf']})", ""]
    L += ["## Notes", "", "- Outcome model: entry next open, ±k·ATR target/stop, stop-first on ambiguous bars, horizon exit.",
          "- Parity first, performance second: do not interpret performance until section 2 is ~95%+."]
    (out / "REPORT.md").write_text("\n".join(L))
