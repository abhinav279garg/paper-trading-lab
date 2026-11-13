"""Settings for the paper-trading lab. Simulated money only: nothing here places orders."""

START_CAPITAL = 10.0           # euros per strategy (simulated)
BACKTEST_START = "2018-01-01"
SPLIT_DATE = "2022-01-01"      # the backtest is also reported as two separate halves (a consistency check)
DOWNLOAD_START = "2016-01-01"  # extra history so indicators are warmed up

# Yahoo Finance symbols. Everything priced in USD is converted to EUR with EURUSD.
SYMBOLS = {
    "BTC": "BTC-EUR", "ETH": "ETH-EUR",
    "SPY": "SPY", "QQQ": "QQQ", "EFA": "EFA", "TLT": "TLT", "GLD": "GLD",
    "ES": "ES=F", "GC": "GC=F", "BZ": "BZ=F",
    "VIX": "^VIX", "EURUSD": "EURUSD=X",
    "AAPL": "AAPL", "GOOGL": "GOOGL", "MSFT": "MSFT", "AMZN": "AMZN", "META": "META", "BRK": "BRK-B",
    "JNJ": "JNJ", "XOM": "XOM", "JPM": "JPM", "BAC": "BAC", "WFC": "WFC", "WMT": "WMT",
}
ALREADY_EUR = {"BTC", "ETH"}
NOT_A_PRICE = {"VIX", "EURUSD"}
# Point-in-time universe: the 12 largest US companies by market value at the end of 2017, i.e. chosen
# with information available at the start of the backtest, not with today's hindsight.
STOCKS = ["AAPL", "GOOGL", "MSFT", "AMZN", "META", "BRK", "JNJ", "XOM", "JPM", "BAC", "WFC", "WMT"]
ROTATION_ETFS = ["SPY", "QQQ", "EFA", "TLT", "GLD"]
FUTURES = ["ES", "GC", "BZ"]

# Cost per unit of traded value (fee plus slippage), charged on every buy and sell.
COST = {
    "crypto": 0.0030,   # ~0.25% exchange taker fee + spread
    "equity": 0.0010,   # percentage only; a flat 1 euro broker fee on a 10 euro order would be 10%
    "futures": 0.0005,
    "option_haircut": 0.05,  # share of the model premium lost to the bid/ask spread
}
# Options above the market price trade at lower implied volatility than the VIX index (the "skew").
# Without this adjustment the model overpays the covered-call seller. Rough assumption, not data.
CALL_VOL_FACTOR = 0.85
PUT_VOL_FACTOR = 1.00
