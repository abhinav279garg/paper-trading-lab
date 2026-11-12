import numpy as np
import pandas as pd

from lab.engine import bs_price, changes_only, simulate, simulate_option_writer


def _prices(n=300, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.DataFrame({"A": 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n))),
                         "B": 50 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))}, index=idx)


def test_buy_and_hold_matches_price_minus_fee():
    px = _prices()[["A"]]
    t = changes_only(pd.DataFrame({"A": 1.0}, index=px.index))
    eq, trades, pos = simulate(px, t, 0.001, 10.0)
    # bought on bar 1 at its close, fee 0.1% of the amount bought
    expected = 10.0 / 1.001 * px["A"].iloc[-1] / px["A"].iloc[1]
    assert abs(eq.iloc[-1] - expected) < 1e-9
    assert len(trades) == 1 and abs(pos["A"] - 1.0) < 1e-9


def test_no_cost_no_position_keeps_capital():
    px = _prices()
    t = pd.DataFrame(np.nan, index=px.index, columns=px.columns)
    eq, trades, _ = simulate(px, t, 0.01, 10.0)
    assert (eq == 10.0).all() and not trades


def test_no_lookahead():
    px = _prices()
    sig = (px["A"] > px["A"].rolling(20).mean()).astype(float).to_frame("A")
    eq1, _, _ = simulate(px[["A"]], changes_only(sig), 0.001, 10.0)
    px2 = px.copy()
    px2.iloc[200:] *= 3.0  # change the future
    sig2 = (px2["A"] > px2["A"].rolling(20).mean()).astype(float).to_frame("A")
    eq2, _, _ = simulate(px2[["A"]], changes_only(sig2), 0.001, 10.0)
    assert np.allclose(eq1.iloc[:200], eq2.iloc[:200])


def test_cash_never_negative_when_fully_invested():
    px = _prices()
    t = pd.DataFrame(np.nan, index=px.index, columns=px.columns)
    t.iloc[::20] = [0.5, 0.5]
    eq, trades, pos = simulate(px, t, 0.003, 10.0)
    assert sum(pos.values()) <= 1.0 + 1e-9 and eq.min() > 0


def test_short_position_profits_when_price_falls():
    idx = pd.date_range("2020-01-01", periods=4, freq="D")
    px = pd.DataFrame({"A": [100.0, 100.0, 90.0, 90.0]}, index=idx)
    t = pd.DataFrame({"A": [-1.0, np.nan, np.nan, np.nan]}, index=idx)
    eq, _, _ = simulate(px, t, 0.0, 10.0)
    assert abs(eq.iloc[-1] - 11.0) < 1e-9


def test_put_call_parity_and_expiry_value():
    c, p = bs_price(100, 105, 0.25, 0.2, "call"), bs_price(100, 105, 0.25, 0.2, "put")
    assert abs((c - p) - (100 - 105)) < 1e-9
    assert bs_price(110, 105, 0, 0.2, "call") == 5 and bs_price(110, 105, 0, 0.2, "put") == 0


def test_covered_call_caps_upside_and_put_loses_in_crash():
    idx = pd.date_range("2020-01-01", periods=22, freq="B")
    vol = pd.Series(0.2, index=idx)
    up = pd.Series(np.linspace(100, 120, 22), index=idx)
    eq, _, _ = simulate_option_writer(up, vol, "call", 10.0, 0.0, 0.0)
    assert 10.2 < eq.iloc[-1] < 10.2 * 1.03   # capped near the +2% strike plus premium
    down = pd.Series(np.linspace(100, 70, 22), index=idx)
    eq, _, _ = simulate_option_writer(down, vol, "put", 10.0, 0.0, 0.0)
    assert 7.0 < eq.iloc[-1] < 7.6            # carries almost the full fall
