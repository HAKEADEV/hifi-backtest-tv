"""Download free public klines from data.binance.vision (not committed).
Reference = USDT-M futures BTCUSDT (stands in for a 'broker' feed),
candidate = spot BTCUSDT (stands in for the TradingView feed),
alternate = spot BTCFDUSD (a different venue/quote to show feed-swap impact)."""
import io, urllib.request, zipfile
from pathlib import Path

MONTHS = ["2025-06", "2025-07", "2025-08", "2025-09"]
SRC = {
    "futures_BTCUSDT": "https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-{m}.zip",
    "spot_BTCUSDT": "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-{m}.zip",
    "spot_BTCFDUSD": "https://data.binance.vision/data/spot/monthly/klines/BTCFDUSD/15m/BTCFDUSD-15m-{m}.zip",
}
root = Path(__file__).parent / "data"
for name, url in SRC.items():
    d = root / name; d.mkdir(parents=True, exist_ok=True)
    for m in MONTHS:
        dst = d / f"{m}.csv"
        if dst.exists():
            continue
        with urllib.request.urlopen(url.format(m=m)) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
            dst.write_bytes(z.read(z.namelist()[0]))
        print("got", dst)
