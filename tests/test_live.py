import os

import numpy as np
import pandas as pd

from lab import live
from lab.engine import changes_only, simulate, simulate_option_writer


def _spec(n=120, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    px = pd.DataFrame({"A": 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n))),
                       "B": 50 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))}, index=idx)
    w = pd.DataFrame({"A": (px["A"] > px["A"].rolling(5).mean()).astype(float) * 0.5,
                      "B": (px["B"] > px["B"].rolling(8).mean()).astype(float) * 0.5})
    return {"kind": "weights", "prices": px, "targets": changes_only(w), "cost": 0.003, "freq": "crypto_daily"}


def _run(spec, tmp, start, stop, sid="x", **kw):
    idx = spec["prices"].index if spec["kind"] == "weights" else spec["spot"].index
    bench = spec["prices"]["A"] if spec["kind"] == "weights" else spec["spot"]
    state = None
    for bar in idx[start:stop]:
        now = live.close_time(pd.DatetimeIndex([bar]), spec["freq"])[0] + pd.Timedelta(minutes=47)
        state, _ = live.process({sid: spec}, {sid: bench}, now, "c0ffee", live_dir=str(tmp / "live"),
                                current_hash=kw.get("hash", "h1"))
    return state


def test_stepping_live_engine_matches_backtest(tmp_path):
    """Run every bar, the forward engine must reproduce the backtest from the same starting point."""
    spec = _spec()
    start = 40
    state = _run(spec, tmp_path, start, None)
    # backtest from the same point: flat, first order = the target standing at bar `start`
    px = spec["prices"].iloc[start:]
    t = spec["targets"].iloc[start:].copy()
    standing = spec["targets"].iloc[:start + 1].dropna(how="all").iloc[-1]
    t.iloc[0] = standing
    eq, _, _ = simulate(px, t, 0.003, 10.0)
    assert abs(state["strategies"]["x"]["view"]["value"] - eq.iloc[-1]) < 1e-5


def test_every_fill_happens_after_its_order_was_recorded(tmp_path):
    spec = _spec()
    _run(spec, tmp_path, 40, None)
    orders = {o["order_id"]: o for o in live.read_csv("orders.csv", str(tmp_path / "live"))}
    fills = live.read_csv("fills.csv", str(tmp_path / "live"))
    assert len(fills) > 10
    for f in fills:
        o = orders[f["order_id"]]
        assert pd.Timestamp(f["bar_closed_at"]) > pd.Timestamp(o["recorded_at"])   # price did not exist yet
        assert pd.Timestamp(f["fill_bar"]) > pd.Timestamp(o["signal_bar"])
        assert f["commit"] == "c0ffee" and f["rules_hash"] == "h1"


def test_missed_runs_delay_the_fill_instead_of_backdating_it(tmp_path):
    spec = _spec()
    idx = spec["prices"].index
    d = str(tmp_path / "live")
    t0 = idx[50] + pd.Timedelta(days=1, minutes=5)
    live.process({"x": spec}, {"x": spec["prices"]["A"]}, t0, "c", live_dir=d, current_hash="h")
    t1 = idx[57] + pd.Timedelta(days=1, minutes=5)       # a week with no runs
    live.process({"x": spec}, {"x": spec["prices"]["A"]}, t1, "c", live_dir=d, current_hash="h")
    first = live.read_csv("fills.csv", d)[0]
    assert pd.Timestamp(first["fill_bar"]) == idx[51]       # first bar closing after the order, not earlier
    assert pd.Timestamp(first["bar_closed_at"]) > t0


def test_rule_change_archives_old_record_and_restarts(tmp_path):
    spec = _spec()
    _run(spec, tmp_path, 40, 80, hash="old")
    old_fills = len(live.read_csv("fills.csv", str(tmp_path / "live")))
    state = _run(spec, tmp_path, 80, 82, hash="new")
    archived = os.listdir(tmp_path / "archive")
    assert len(archived) == 1 and archived[0].endswith("rules-old")
    assert len(live.read_csv("fills.csv", str(tmp_path / "archive" / archived[0]))) == old_fills
    assert state["rules_hash"] == "new" and state["strategies"]["x"].get("fills", 0) <= 1
    assert state["strategies"]["x"]["cash"] <= 10.0


def test_option_live_engine_matches_backtest(tmp_path):
    rng = np.random.default_rng(5)
    idx = pd.bdate_range("2025-01-01", periods=140)
    spot = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 140))), index=idx)
    vol = pd.Series(0.18, index=idx)
    for kind in ("call", "put"):
        spec = {"kind": "option", "opt": kind, "spot": spot, "vol": vol, "stock_cost": 0.001,
                "haircut": 0.05, "freq": "us_daily"}
        state = _run(spec, tmp_path / kind, 30, None)
        eq, _, _ = simulate_option_writer(spot.iloc[31:], vol.iloc[31:], kind, 10.0, 0.001, 0.05)
        assert abs(state["strategies"]["x"]["view"]["value"] - eq.iloc[-1]) < 1e-5
