import re

CRYPTO_QUOTES = ("USDT", "USDC", "FDUSD", "BUSD", "BTC", "ETH")
FX_CCY = {"USD", "EUR", "JPY", "GBP", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK", "DKK",
          "SGD", "HKD", "MXN", "ZAR", "TRY", "PLN", "CZK", "HUF", "CNH"}
METALS = {"XAU", "XAG", "XPT", "XPD"}


def clean(symbol: str) -> str:
    s = symbol.upper().split(":")[-1]
    return re.sub(r"[^A-Z0-9]", "", s)


def route_source(symbol: str) -> str:
    """auto routing: crypto pairs -> binance, FX/metals -> dukascopy, else yfinance.
    'EXCH:SYM' with EXCH a ccxt id (e.g. BYBIT:BTC/USDT) -> ccxt."""
    if ":" in symbol and "/" in symbol:
        return "ccxt"
    s = clean(symbol)
    if len(s) == 6 and (s[:3] in FX_CCY | METALS) and s[3:] in FX_CCY:
        return "dukascopy"
    if any(s.endswith(q) and len(s) > len(q) for q in CRYPTO_QUOTES):
        return "binance"
    return "yfinance"
