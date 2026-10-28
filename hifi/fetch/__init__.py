"""`hifi fetch`: automatic, login-free market data download -> normalized UTC CSV
(time,open,high,low,close,volume). Downloaded data is never committed; it is
subject to each provider's terms."""
from .route import route_source, CRYPTO_QUOTES  # noqa
from .dukascopy import decode_bi5, fetch_dukascopy, point_scale  # noqa
from .core import fetch, write_csv  # noqa
