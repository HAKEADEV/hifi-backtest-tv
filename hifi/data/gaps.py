import pandas as pd


def gap_report(df: pd.DataFrame, tf: str, weekend_ok=True) -> dict:
    """Find missing bars. Gaps spanning a Saturday (UTC) are counted as weekend."""
    step = pd.Timedelta(tf)
    d = df.index.to_series().diff()
    gaps = d[d > step]
    rows = []
    for end, dt in gaps.items():
        start = end - dt
        weekend = any(x.weekday() == 5 for x in pd.date_range(start, end, freq="6h"))
        rows.append({"from": start, "to": end, "missing_bars": int(dt / step) - 1, "weekend": weekend})
    g = pd.DataFrame(rows, columns=["from", "to", "missing_bars", "weekend"])
    unexpected = g[~g["weekend"].astype(bool)] if (weekend_ok and len(g)) else g
    return {"bars": len(df), "start": df.index.min(), "end": df.index.max(),
            "gaps": len(g), "weekend_gaps": int(g["weekend"].sum()) if len(g) else 0,
            "unexpected_gaps": len(unexpected),
            "unexpected_missing_bars": int(unexpected["missing_bars"].sum()) if len(unexpected) else 0,
            "table": unexpected.sort_values("missing_bars", ascending=False).head(10)}
