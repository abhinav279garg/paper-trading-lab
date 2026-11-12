"""Settings for the paper-trading lab. Simulated money only: nothing here places orders."""

START_CAPITAL = 10.0           # euros per strategy (simulated)
LIVE_START = "2026-11-12"      # the day the paper portfolio went live
BACKTEST_START = "2018-01-01"
DOWNLOAD_START = "2016-01-01"  # extra history so indicators are warmed up

# Yahoo Finance symbols. Everything priced in USD is converted to EUR with EURUSD.
SYMBOLS = {
    "BTC": "BTC-EUR", "ETH": "ETH-EUR",
    "SPY": "SPY", "QQQ": "QQQ", "EFA": "EFA", "TLT": "TLT", "GLD": "GLD",
    "ES": "ES=F", "GC": "GC=F", "BZ": "BZ=F",
    "VIX": "^VIX", "EURUSD": "EURUSD=X",
    "AAPL": "AAPL", "MSFT": "MSFT", "NVDA": "NVDA", "AMZN": "AMZN", "GOOGL": "GOOGL",
    "META": "META", "JPM": "JPM", "XOM": "XOM", "JNJ": "JNJ", "PG": "PG", "KO": "KO", "WMT": "WMT",
}
ALREADY_EUR = {"BTC", "ETH"}
NOT_A_PRICE = {"VIX", "EURUSD"}
STOCKS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "XOM", "JNJ", "PG", "KO", "WMT"]
ROTATION_ETFS = ["SPY", "QQQ", "EFA", "TLT", "GLD"]
FUTURES = ["ES", "GC", "BZ"]

# Cost per unit of traded value (fee plus slippage), charged on every buy and sell.
COST = {
    "crypto": 0.0030,   # ~0.25% exchange taker fee + spread
    "equity": 0.0010,   # percentage only; a flat 1 euro broker fee on a 10 euro order would be 10%
    "futures": 0.0005,
    "option_haircut": 0.05,  # share of the model premium lost to the bid/ask spread
}
