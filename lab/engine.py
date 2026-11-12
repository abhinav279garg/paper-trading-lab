"""Simulation engine. A decision made on the close of bar t is executed on the close of bar t+1,
so no rule can use information it would not have had."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def simulate(prices: pd.DataFrame, targets: pd.DataFrame, cost: float, capital: float):
    """prices: one column per asset. targets: desired portfolio weights, a row only on bars where
    the rule wants to change the portfolio (other rows NaN). Weights may be negative (short).
    Returns (equity series, list of trades)."""
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
        ok = ~np.isnan(px)
        if pending is not None and ok[pending != 0].all() and ok[units != 0].all():
            value = cash + float(np.nansum(units * px))
            safe = np.where(ok, px, 1.0)
            fee = 0.0
            for _ in range(8):  # the fee is paid out of the same money, so solve for it
                want = np.where(ok, pending * (value - fee) / safe, 0.0)
                delta = want - units
                traded = np.abs(delta) * np.where(ok, px, 0.0)
                fee = float(traded.sum()) * cost
            cash = value - fee - float(np.nansum(want * px))
            for j, c in enumerate(cols):
                if traded[j] > 0.001 * value:  # fees on smaller adjustments are still charged
                    trades.append({"time": prices.index[i], "asset": c,
                                   "side": "BUY" if delta[j] > 0 else "SELL",
                                   "units": float(abs(delta[j])), "price": float(px[j]),
                                   "value": float(traded[j]), "fee": float(traded[j] * cost)})
            units = want
            pending = None
        equity[i] = cash + float(np.nansum(units * np.nan_to_num(px)))
        if not np.isnan(t[i]).all():
            pending = np.nan_to_num(t[i])
    last = np.nan_to_num(p[-1]) if len(p) else np.zeros(len(cols))
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
            if n > 0:  # settle the expiring option
                pay = max(s[i] - strike, 0.0) if kind == "call" else max(strike - s[i], 0.0)
                cash -= n * pay
                trades.append({"time": idx[i], "asset": f"SPY {kind} {strike:.2f}", "side": "EXPIRE",
                               "units": n, "price": pay, "value": n * pay, "fee": 0.0})
            value = cash + shares * s[i]
            if kind == "call":
                new_shares = value / s[i]
                fee = abs(new_shares - shares) * s[i] * stock_cost
                new_shares = (value - fee) / s[i]
                shares, cash, n = new_shares, 0.0, new_shares
                strike = s[i] * (1 + otm)
            else:
                strike = s[i] * (1 - otm)
                n = value / strike
            prem = bs_price(s[i], strike, days / 252, v[i], kind) * (1 - haircut)
            fee_opt = bs_price(s[i], strike, days / 252, v[i], kind) * haircut * n
            cash += n * prem
            trades.append({"time": idx[i], "asset": f"SPY {kind} {strike:.2f}", "side": "SELL",
                           "units": n, "price": prem, "value": n * prem, "fee": fee_opt})
            left = days
        liability = n * bs_price(s[i], strike, left / 252, v[i], kind)
        equity[i] = cash + shares * s[i] - liability
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
