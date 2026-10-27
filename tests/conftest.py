import numpy as np
import pandas as pd
import pytest
from hifi.schema import normalize


def make_bars(n=3000, seed=1, freq="15min", start="2024-03-04"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    c = 1.1 + np.cumsum(rng.normal(0, 0.0004, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.uniform(0, 0.0003, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.0003, n)
    return normalize(pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1.0}, index=idx))


@pytest.fixture
def bars():
    return make_bars()
