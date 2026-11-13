"""Ten textbook rule-based strategies. They are experiments, not recommendations."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CALL_VOL_FACTOR, COST, FUTURES, PUT_VOL_FACTOR, ROTATION_ETFS, START_CAPITAL, STOCKS
from .engine import changes_only, simulate, simulate_option_writer


def _spec(px, targets, cost, freq):
    return {"kind": "weights", "prices": px, "targets": targets, "cost": cost, "freq": freq}


def _one(prices: pd.Series, signal: pd.Series, name: str) -> pd.DataFrame:
    return changes_only(signal.astype(float).to_frame(name)), prices.to_frame(name)


def btc_trend(d):
    p = d["BTC"].dropna()
    sig = (p.rolling(50).mean() > p.rolling(200).mean())
    t, px = _one(p, sig, "BTC")
    return _spec(px, t, COST["crypto"], "crypto_daily")


def eth_breakout(d):
    p = d["ETH"].dropna()
    hi, lo = p.rolling(20).max().shift(1), p.rolling(10).min().shift(1)
    pos, held = [], False
    for price, h, l in zip(p, hi, lo):
        if not held and price >= h:
            held = True
        elif held and price <= l:
            held = False
        pos.append(held)
    t, px = _one(p, pd.Series(pos, index=p.index), "ETH")
    return _spec(px, t, COST["crypto"], "crypto_daily")


def btc_intraday(hourly):
    p = hourly.dropna()
    z = (p - p.rolling(24).mean()) / p.rolling(24).std()
    pos, held, age = [], False, 0
    for v in z:
        if not held and v < -2:
            held, age = True, 0
        elif held and (v > 0 or age >= 12):
            held = False
        age += 1
        pos.append(held)
    t, px = _one(p, pd.Series(pos, index=p.index), "BTC")
    return _spec(px, t, COST["crypto"], "hourly")


def spy_hold(d):
    p = d["SPY"].dropna()
    t, px = _one(p, pd.Series(True, index=p.index), "SPY")
    return _spec(px, t, COST["equity"], "us_daily")


def _month_starts(index):
    """First trading bar of each month. Known on the day itself, so usable live without hindsight."""
    months = pd.Series(index.year * 12 + index.month, index=index)
    return index[(months != months.shift(1)).to_numpy()][1:]


def _rotation(prices, top, lookback, require_positive):
    # decided on the first trading day of each month, traded on the next close
    px = prices.dropna()
    mom = px.pct_change(lookback)
    t = pd.DataFrame(np.nan, index=px.index, columns=px.columns)
    for day in _month_starts(px.index):
        m = mom.loc[day]
        if m.isna().any():
            continue
        best = m.sort_values(ascending=False).head(top)
        if require_positive:
            best = best[best > 0]
        row = pd.Series(0.0, index=px.columns)
        row[best.index] = 1.0 / top
        t.loc[day] = row
    return px, t


def etf_rotation(d):
    px, t = _rotation(d[ROTATION_ETFS], top=2, lookback=126, require_positive=True)
    return _spec(px, t, COST["equity"], "us_daily")


def stock_momentum(d):
    px, t = _rotation(d[STOCKS], top=3, lookback=126, require_positive=False)
    return _spec(px, t, COST["equity"], "us_daily")


def spy_rsi2(d):
    p = d["SPY"].dropna()
    diff = p.diff()
    up = diff.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    down = (-diff.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / down.replace(0, np.nan))
    sma200, sma5 = p.rolling(200).mean(), p.rolling(5).mean()
    pos, held = [], False
    for price, r, long_avg, short_avg in zip(p, rsi, sma200, sma5):
        if not held and r < 10 and price > long_avg:
            held = True
        elif held and price > short_avg:
            held = False
        pos.append(held)
    t, px = _one(p, pd.Series(pos, index=p.index), "SPY")
    return _spec(px, t, COST["equity"], "us_daily")


def futures_trend(d):
    px = d[FUTURES].dropna()
    above = px > px.rolling(100).mean()
    w = above.astype(float) * 2 - 1          # +1 long, -1 short
    w[px.rolling(100).mean().isna()] = 0.0
    t = changes_only(w / len(FUTURES))
    return _spec(px, t, COST["futures"], "us_daily")


def _option(d, kind, factor):
    return {"kind": "option", "opt": kind, "spot": d["SPY"], "vol": d["VIX"] / 100 * factor,
            "stock_cost": COST["equity"], "haircut": COST["option_haircut"], "freq": "us_daily"}


def covered_call(d):
    return _option(d, "call", CALL_VOL_FACTOR)


def cash_secured_put(d):
    return _option(d, "put", PUT_VOL_FACTOR)


def backtest(spec):
    """Run a strategy spec over all its history. Returns (equity, trades, final position)."""
    if spec["kind"] == "option":
        return simulate_option_writer(spec["spot"], spec["vol"], spec["opt"], START_CAPITAL,
                                      spec["stock_cost"], spec["haircut"])
    return simulate(spec["prices"], spec["targets"], spec["cost"], START_CAPITAL)


# id, name, asset class, benchmark column, bars per year, function, uses hourly data
STRATEGIES = [
    ("btc_trend", "Bitcoin trend following (50/200-day)", "Crypto", "BTC", 365, btc_trend, False),
    ("eth_breakout", "Ether 20-day breakout", "Crypto", "ETH", 365, eth_breakout, False),
    ("btc_intraday", "Bitcoin intraday mean reversion (hourly)", "Day trading", "BTC", 24 * 365, btc_intraday, True),
    ("spy_hold", "S&P 500 ETF buy and hold (benchmark)", "ETF", "SPY", 252, spy_hold, False),
    ("etf_rotation", "ETF rotation, top 2 of 5, monthly", "ETF", "SPY", 252, etf_rotation, False),
    ("stock_momentum", "Stock momentum, top 3 of 12, monthly", "Stocks", "SPY", 252, stock_momentum, False),
    ("spy_rsi2", "Short-term mean reversion on S&P 500 ETF", "ETF", "SPY", 252, spy_rsi2, False),
    ("futures_trend", "Futures trend, S&P / gold / oil, long-short", "Futures", "SPY", 252, futures_trend, False),
    ("covered_call", "Covered call on S&P 500 ETF (model-priced)", "Options", "SPY", 252, covered_call, False),
    ("cash_secured_put", "Cash-secured put on S&P 500 ETF (model-priced)", "Options", "SPY", 252, cash_secured_put, False),
]
