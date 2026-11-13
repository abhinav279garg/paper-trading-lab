"""Forward paper-trading engine. Unlike the backtest, nothing here is recomputed from history.

Each run does two things, in this order:
  1. FILL  - an order recorded by an earlier run is filled at the close of the first price bar that
             finished AFTER the order was recorded. The observed price and fee are written down.
  2. ORDER - the rules are evaluated on the latest finished bar and any new intended order is
             written down, to be filled by a later run.
So every order is on record (and committed to git) before the price it fills at exists.

Every record carries the git commit that produced it and a hash of the rule code. If the rule code
changes, the current record is archived untouched and a new one starts from scratch.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil

import numpy as np
import pandas as pd

from .config import START_CAPITAL
from .engine import option_roll, option_value, rebalance

ROOT = os.path.dirname(os.path.dirname(__file__))
LIVE_DIR = os.path.join(ROOT, "results", "live")
RULE_FILES = ["config.py", "engine.py", "strategies.py", "live.py"]
ORDER_FIELDS = ["order_id", "recorded_at", "strategy_id", "signal_bar", "instruction", "supersedes",
                "rules_hash", "commit"]
FILL_FIELDS = ["order_id", "recorded_at", "strategy_id", "fill_bar", "bar_closed_at", "asset", "side",
               "units", "price", "value", "fee", "rules_hash", "commit"]
EQUITY_FIELDS = ["recorded_at", "strategy_id", "bar", "value", "benchmark_value", "rules_hash", "commit"]


def rules_hash() -> str:
    h = hashlib.sha256()
    for name in RULE_FILES:
        h.update(open(os.path.join(os.path.dirname(__file__), name), "rb").read())
    return h.hexdigest()[:12]


def close_time(index: pd.DatetimeIndex, freq: str) -> pd.DatetimeIndex:
    """When a bar's closing price becomes final (UTC)."""
    if freq == "hourly":
        return index + pd.Timedelta(hours=1)
    if freq == "crypto_daily":
        return index + pd.Timedelta(days=1)
    return index + pd.Timedelta(hours=21, minutes=30)   # US markets


def _append(path, fields, rows):
    if not rows:
        return
    fresh = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if fresh:
            w.writeheader()
        w.writerows(rows)


def read_csv(name, live_dir=None):
    path = os.path.join(live_dir or LIVE_DIR, name)
    return list(csv.DictReader(open(path))) if os.path.exists(path) else []


def load_state(live_dir=None):
    path = os.path.join(live_dir or LIVE_DIR, "state.json")
    return json.load(open(path)) if os.path.exists(path) else None


def _new_order(st, sid, signal_bar, instruction, now, meta, orders):
    st["order_seq"] = st.get("order_seq", 0) + 1
    oid = f"{sid}-{st['order_seq']:05d}"
    old = st.get("pending")
    st["pending"] = {"order_id": oid, "recorded_at": str(now), "instruction": instruction}
    orders.append({"order_id": oid, "recorded_at": str(now), "strategy_id": sid, "signal_bar": str(signal_bar),
                   "instruction": json.dumps(instruction, sort_keys=True),
                   "supersedes": old["order_id"] if old else "", **meta})


def _weights(sid, spec, st, now, meta, orders, fills):
    px = spec["prices"]
    px = px[close_time(px.index, spec["freq"]) <= now]
    if px.empty:
        return None
    cols = list(px.columns)
    if st.get("pending"):
        recorded = pd.Timestamp(st["pending"]["recorded_at"])
        later = px.index[close_time(px.index, spec["freq"]) > recorded]
        if len(later):
            bar = later[0]
            p = px.loc[bar].to_numpy(dtype=float)
            units = np.array([st["units"].get(c, 0.0) for c in cols])
            target = np.array([st["pending"]["instruction"].get(c, 0.0) for c in cols])
            units_new, cash, fee, delta, value = rebalance(st["cash"], units, p, target, spec["cost"])
            for j, c in enumerate(cols):
                traded = abs(delta[j]) * p[j]
                if traded > 0:
                    fills.append({"order_id": st["pending"]["order_id"], "recorded_at": str(now),
                                  "strategy_id": sid, "fill_bar": str(bar),
                                  "bar_closed_at": str(close_time(pd.DatetimeIndex([bar]), spec["freq"])[0]),
                                  "asset": c, "side": "BUY" if delta[j] > 0 else "SELL",
                                  "units": f"{abs(delta[j]):.10g}", "price": f"{p[j]:.8g}",
                                  "value": f"{traded:.6f}", "fee": f"{traded * spec['cost']:.6f}", **meta})
            st["cash"] = float(cash)
            st["units"] = {c: float(u) for c, u in zip(cols, units_new) if abs(u) > 1e-15}
            if float(np.abs(delta).sum()) > 0:
                st["fills"] = st.get("fills", 0) + 1
            st["pending"] = None
    t = spec["targets"].reindex(px.index).dropna(how="all")
    if len(t):
        bar = t.index[-1]
        if st.get("last_target_bar") is None or bar > pd.Timestamp(st["last_target_bar"]):
            row = {c: float(v) for c, v in t.loc[bar].fillna(0.0).items()}
            _new_order(st, sid, bar, row, now, meta, orders)
            st["last_target_bar"] = str(bar)
    last = px.iloc[-1]
    value = st["cash"] + sum(u * float(last[c]) for c, u in st["units"].items())
    holding = {c: u * float(last[c]) / value for c, u in st["units"].items() if abs(u * float(last[c]) / value) > 0.005}
    return px.index[-1], float(value), holding


def _option(sid, spec, st, now, meta, orders, fills):
    df = pd.concat([spec["spot"].rename("s"), spec["vol"].rename("v")], axis=1).dropna()
    df = df[close_time(df.index, spec["freq"]) <= now]
    if df.empty:
        return None
    kind = spec["opt"]
    if st.get("last_bar") is None:              # first run: start flat, place the opening order
        st.update({"shares": 0.0, "n": 0.0, "strike": 0.0, "left": 0, "last_bar": str(df.index[-1])})
        _new_order(st, sid, df.index[-1], {"action": f"sell 21-day {kind}, 2% out of the money"}, now, meta, orders)
    for bar in df.index[df.index > pd.Timestamp(st["last_bar"])]:
        s, v = float(df.loc[bar, "s"]), float(df.loc[bar, "v"])
        closed = close_time(pd.DatetimeIndex([bar]), spec["freq"])[0]
        if st.get("pending") and closed > pd.Timestamp(st["pending"]["recorded_at"]):
            cash, shares, n, strike, rows = option_roll(kind, st["cash"], st["shares"], st["n"], st["strike"],
                                                        s, v, spec["stock_cost"], spec["haircut"])
            for r in rows:
                fills.append({"order_id": st["pending"]["order_id"], "recorded_at": str(now), "strategy_id": sid,
                              "fill_bar": str(bar), "bar_closed_at": str(closed), "asset": r["asset"],
                              "side": r["side"], "units": f"{r['units']:.10g}", "price": f"{r['price']:.8g}",
                              "value": f"{r['value']:.6f}", "fee": f"{r['fee']:.6f}", **meta})
            st.update({"cash": float(cash), "shares": float(shares), "n": float(n), "strike": float(strike),
                       "left": 21, "pending": None, "fills": st.get("fills", 0) + 1})
        if st["left"] > 0:
            st["left"] -= 1
        if st["left"] == 0 and st["n"] > 0 and not st.get("pending"):
            _new_order(st, sid, bar, {"action": f"settle and sell next 21-day {kind}, 2% out of the money"},
                       now, meta, orders)
        st["last_bar"] = str(bar)
    s, v = float(df["s"].iloc[-1]), float(df["v"].iloc[-1])
    value = option_value(kind, st["cash"], st["shares"], st["n"], st["strike"], s, v, st["left"] + 1) \
        if st["n"] > 0 else st["cash"]
    if st["n"] > 0:
        label = "shares + short call" if kind == "call" else "cash + short put"
        holding = f"{label}, strike {st['strike']:.2f}, {st['left']} trading days left"
    else:
        holding = {}
    return df.index[-1], float(value), holding


def process(specs: dict, benchmarks: dict, now: pd.Timestamp, commit: str, only=None, live_dir=None,
            snapshot=True, current_hash=None):
    """specs: {strategy_id: spec}. benchmarks: {strategy_id: price series}. Returns (state, whether any order or fill was recorded)."""
    live_dir = live_dir or LIVE_DIR
    current_hash = current_hash or rules_hash()
    state = load_state(live_dir)
    if state and state["rules_hash"] != current_hash:
        archive = os.path.join(os.path.dirname(live_dir), "archive",
                               f"{state['started_at'][:10]}_rules-{state['rules_hash']}")
        os.makedirs(os.path.dirname(archive), exist_ok=True)
        shutil.move(live_dir, archive)
        state = None
    os.makedirs(live_dir, exist_ok=True)
    if state is None:
        state = {"rules_hash": current_hash, "started_at": str(now), "started_commit": commit, "strategies": {}}
    meta = {"rules_hash": current_hash, "commit": commit}
    orders, fills, equity = [], [], []
    have = {(r["strategy_id"], r["bar"]) for r in read_csv("equity.csv", live_dir)} if snapshot else set()
    for sid, spec in specs.items():
        if only and sid not in only:
            continue
        st = state["strategies"].setdefault(sid, {"cash": START_CAPITAL, "units": {}, "pending": None})
        result = (_option if spec["kind"] == "option" else _weights)(sid, spec, st, now, meta, orders, fills)
        if result is None:
            continue
        bar, value, holding = result
        bench = benchmarks[sid]
        bench = bench[close_time(bench.index, spec["freq"]) <= now].dropna()
        if st.get("benchmark_start") is None and len(bench):
            st["benchmark_start"] = float(bench.iloc[-1])
            st["start_bar"] = str(bench.index[-1])
        bench_value = START_CAPITAL * float(bench.iloc[-1]) / st["benchmark_start"] if len(bench) else float("nan")
        st["view"] = {"bar": str(bar), "value": round(value, 6), "benchmark_value": round(bench_value, 6),
                      "holding": holding if isinstance(holding, str) else {k: round(v, 4) for k, v in holding.items()}}
        key = (sid, str(bar)[:10])
        if snapshot and key not in have:
            equity.append({"recorded_at": str(now), "strategy_id": sid, "bar": key[1], "value": f"{value:.4f}",
                           "benchmark_value": f"{bench_value:.4f}", **meta})
    _append(os.path.join(live_dir, "orders.csv"), ORDER_FIELDS, orders)
    _append(os.path.join(live_dir, "fills.csv"), FILL_FIELDS, fills)
    _append(os.path.join(live_dir, "equity.csv"), EQUITY_FIELDS, equity)
    events = bool(orders or fills)
    if events or snapshot:   # an hourly check that finds nothing to do leaves the record untouched
        json.dump(state, open(os.path.join(live_dir, "state.json"), "w"), indent=1, sort_keys=True)
    return state, events
