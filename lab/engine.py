"""Simulation engine. A decision made on the close of bar t is executed on the close of bar t+1,
so no rule can use information it would not have had."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def rebalance(cash: float, units: np.ndarray, px: np.ndarray, weights: np.ndarray, cost: float):
    """Move a portfolio to target weights at prices px. The fee is paid out of the same money.
    Returns (new_units, new_cash, fee, delta_units, portfolio value before the trade)."""
    value = cash + float((units * px).sum())
    fee = 0.0
    for _ in range(8):
        want = weights * (value - fee) / px
        delta = want - units
        fee = float((np.abs(delta) * px).sum()) * cost
    return want, value - fee - float((want * px).sum()), fee, delta, value


def simulate(prices: pd.DataFrame, targets: pd.DataFrame, cost: float, capital: float):
    """Backtest. prices: one column per asset, no gaps. targets: desired portfolio weights, a row only
    on bars where the rule wants to change the portfolio (other rows NaN). Weights may be negative.
    Returns (equity series, list of trades, final position weights)."""
    prices = prices.astype(float)
    targets = targets.reindex(prices.index)
    cols = list(prices.columns)
    p = prices.to_numpy()
    t = targets[cols].to_numpy()
    units = np.zeros(len(cols))
    cash = capital
    pending = None
    equity = np.empty(len(p))
    trades = []
    for i in range(len(p)):
        px = p[i]
        if pending is not None:
            units, cash, fee, delta, value = rebalance(cash, units, px, pending, cost)
            for j, c in enumerate(cols):
                traded = abs(delta[j]) * px[j]
                if traded > 0.001 * value:  # fees on smaller adjustments are still charged
                    trades.append({"time": prices.index[i], "asset": c,
                                   "side": "BUY" if delta[j] > 0 else "SELL",
                                   "units": float(abs(delta[j])), "price": float(px[j]),
                                   "value": float(traded), "fee": float(traded * cost)})
            pending = None
        equity[i] = cash + float((units * px).sum())
        if not np.isnan(t[i]).all():
            pending = np.nan_to_num(t[i])
    last = p[-1] if len(p) else np.zeros(len(cols))
    total = cash + float((units * last).sum())
    position = {c: float(units[j] * last[j] / total) for j, c in enumerate(cols)
                if total > 0 and abs(units[j] * last[j] / total) > 0.005}
    return pd.Series(equity, index=prices.index), trades, position


def changes_only(weights: pd.DataFrame) -> pd.DataFrame:
    """Keep a target row only when the desired weights differ from the previous bar."""
    w = weights.fillna(0.0)
    changed = (w != w.shift(1)).any(axis=1)
    out = weights.where(changed, np.nan)
    return out


# ---------- Black-Scholes (zero interest rate) for the two model-priced option strategies ----------

def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(spot: float, strike: float, years: float, vol: float, kind: str) -> float:
    if years <= 0 or vol <= 0:
        return max(spot - strike, 0.0) if kind == "call" else max(strike - spot, 0.0)
    d1 = (math.log(spot / strike) + 0.5 * vol * vol * years) / (vol * math.sqrt(years))
    d2 = d1 - vol * math.sqrt(years)
    call = spot * _ncdf(d1) - strike * _ncdf(d2)
    return call if kind == "call" else call - spot + strike


def option_roll(kind, cash, shares, n, strike, s, v, stock_cost, haircut, days=21, otm=0.02):
    """Settle the expiring option (if any) and sell the next one at spot s and volatility v.
    Returns (cash, shares, n, strike, trade rows without timestamps)."""
    rows = []
    if n > 0:
        pay = max(s - strike, 0.0) if kind == "call" else max(strike - s, 0.0)
        cash -= n * pay
        rows.append({"asset": f"SPY {kind} {strike:.2f}", "side": "EXPIRE", "units": n, "price": pay,
                     "value": n * pay, "fee": 0.0})
    value = cash + shares * s
    if kind == "call":
        fee = abs(value / s - shares) * s * stock_cost
        shares, cash = (value - fee) / s, 0.0
        n, strike = shares, s * (1 + otm)
    else:
        strike = s * (1 - otm)
        n = value / strike
    model = bs_price(s, strike, days / 252, v, kind)
    cash += n * model * (1 - haircut)
    rows.append({"asset": f"SPY {kind} {strike:.2f}", "side": "SELL", "units": n,
                 "price": model * (1 - haircut), "value": n * model * (1 - haircut),
                 "fee": n * model * haircut})
    return cash, shares, n, strike, rows


def option_value(kind, cash, shares, n, strike, s, v, days_left):
    return cash + shares * s - n * bs_price(s, strike, days_left / 252, v, kind)


def simulate_option_writer(spot: pd.Series, vol: pd.Series, kind: str, capital: float,
                           stock_cost: float, haircut: float, days: int = 21, otm: float = 0.02):
    """kind='call': hold the shares and sell a monthly call 2% above the price (covered call).
    kind='put': hold cash and sell a monthly put 2% below the price (cash-secured put).
    Option prices come from the model, using the VIX index as volatility. Approximate."""
    df = pd.concat([spot.rename("s"), vol.rename("v")], axis=1).dropna()
    s, v, idx = df["s"].to_numpy(), df["v"].to_numpy(), df.index
    equity = np.empty(len(s))
    trades = []
    shares = n = strike = 0.0
    cash = capital
    left = 0
    for i in range(len(s)):
        if left == 0:
            cash, shares, n, strike, rows = option_roll(kind, cash, shares, n, strike, s[i], v[i],
                                                        stock_cost, haircut, days, otm)
            trades += [dict(r, time=idx[i]) for r in rows]
            left = days
        equity[i] = option_value(kind, cash, shares, n, strike, s[i], v[i], left)
        left -= 1
    label = "shares + short call" if kind == "call" else "cash + short put"
    position = f"{label}, strike {strike:.2f}, {max(left, 0)} trading days left"
    return pd.Series(equity, index=idx), trades, position


# ---------- statistics ----------

def stats(equity: pd.Series, periods_per_year: float) -> dict:
    eq = equity.dropna()
    if len(eq) < 2:
        return {}
    r = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    total = eq.iloc[-1] / eq.iloc[0] - 1
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1 if years > 0 and eq.iloc[-1] > 0 else float("nan")
    dd = (eq / eq.cummax() - 1).min()
    vol = r.std() * math.sqrt(periods_per_year)
    sharpe = (r.mean() * periods_per_year) / vol if vol > 0 else float("nan")
    return {"start": str(eq.index[0])[:10], "end": str(eq.index[-1])[:10], "years": round(years, 2),
            "total_return": float(total), "cagr": float(cagr), "max_drawdown": float(dd),
            "volatility": float(vol), "sharpe": float(sharpe)}
