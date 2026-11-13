"""Pure logic of the experiment: event timeline, point-in-time links, trade selection, matched
decoys, costs and statistics. No network access in this file."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (BOOTSTRAP, BORROW_YEAR, BUCKETS, COST_SIDE, CUTOFF_MINUTES, HOLD_DAYS, MAX_NAMES,
                     MIN_DOLLAR_VOLUME, SEED, SHORT_MIN_DOLLAR_VOLUME, SHORT_MIN_PRICE, TRIGGER)


def timeline(accepted: pd.Timestamp, days: pd.DatetimeIndex, hold: int = HOLD_DAYS):
    """accepted: SEC acceptance time read as New York time (the later, conservative reading).
    Returns (prev, t1, t2, exit) trading days, or None if the window runs past the price data.
    prev -> t1 measures the customer's reaction; the trade is entered at t2 and closed at exit."""
    day = accepted.normalize()
    minutes = accepted.hour * 60 + accepted.minute
    i = days.searchsorted(day)
    same_day = i < len(days) and days[i] == day and minutes <= CUTOFF_MINUTES
    if not same_day:
        i = days.searchsorted(day, side="right")
    if i < 1 or i + 1 + hold >= len(days):
        return None
    return days[i - 1], days[i], days[i + 1], days[i + 1 + hold]


def build_links(rows, filers) -> pd.DataFrame:
    """rows: verified disclosures. filers: {cik: {"ticker", "sic", "tenk": [filing dates]}}.
    A link is usable from the day after the report was filed until the supplier's next annual report."""
    out = []
    for r in rows:
        info = filers.get(r["supplier_cik"], {})
        filed = pd.Timestamp(r["file_date"])
        later = sorted(pd.Timestamp(d) for d in info.get("tenk", []) if pd.Timestamp(d) > filed)
        end = (later[0] if later else filed + pd.Timedelta(days=456)) + pd.Timedelta(days=1)
        out.append({"customer": r["customer"], "supplier_cik": r["supplier_cik"],
                    "supplier": (info.get("ticker") or "").replace(".", "-"), "sic": info.get("sic") or r.get("sic"),
                    "pct": float(r["pct"]), "valid_from": filed + pd.Timedelta(days=1), "valid_to": end,
                    "adsh": r["adsh"]})
    df = pd.DataFrame(out)
    if df.empty:
        return df
    df = df[df["supplier_cik"] != df["customer"].map(lambda c: filers.get("ticker:" + c, {}).get("cik", ""))]
    return df.drop_duplicates(["customer", "supplier_cik", "adsh"]).reset_index(drop=True)


def bucket(dollar_volume: float) -> str:
    for floor, name in BUCKETS:
        if dollar_volume >= floor:
            return name
    return "small"


def customer_events(filings, adj, days, sector_of, trigger=TRIGGER, hold=HOLD_DAYS) -> pd.DataFrame:
    """filings: {customer ticker: [acceptance timestamps of its 8-Ks]}. One row per (customer, t1)."""
    rows = []
    for cust, stamps in filings.items():
        if cust not in adj.columns:
            continue
        etf = sector_of.get(cust, "SPY")
        for ts in stamps:
            tl = timeline(pd.Timestamp(ts), days, hold)
            if tl is None:
                continue
            prev, t1, t2, exit_ = tl
            c0, c1 = adj.at[prev, cust], adj.at[t1, cust]
            e0, e1 = adj.at[prev, etf], adj.at[t1, etf]
            if not (np.isfinite(c0) and np.isfinite(c1)):
                continue
            if not (np.isfinite(e0) and np.isfinite(e1)):
                e0, e1 = adj.at[prev, "SPY"], adj.at[t1, "SPY"]
            move = (c1 / c0 - 1) - (e1 / e0 - 1)
            if abs(move) >= trigger:
                rows.append({"customer": cust, "t0": pd.Timestamp(ts), "prev": prev, "t1": t1, "t2": t2,
                             "exit": exit_, "trigger": float(move), "sector": etf})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("t0").drop_duplicates(["customer", "t1"]).reset_index(drop=True)


def select(ev, links, adj, raw, dv, sector_of, universe):
    """Chooses up to MAX_NAMES verified suppliers for an event and one matched decoy for each.
    universe: {sector: [tickers]} of companies that could serve as decoys.
    Uses only what is known at t1, plus the existence of an entry price at t2.
    Returns (direction, [(supplier, decoy, supplier volume, decoy volume)])."""
    direction = 1 if ev.trigger > 0 else -1
    volume, entry = dv.loc[ev.t1], adj.loc[ev.t2]
    ok = (volume >= MIN_DOLLAR_VOLUME) & entry.notna()
    if direction < 0:   # a short needs a borrowable, liquid share
        ok &= (raw.loc[ev.t1] >= SHORT_MIN_PRICE) & (volume >= SHORT_MIN_DOLLAR_VOLUME)
    known = links[(links["customer"] == ev.customer) & (links["valid_from"] <= ev.t1)]
    live = known[known["valid_to"] > ev.t1].sort_values(["pct", "supplier"], ascending=[False, True])
    ever_linked = set(known["supplier"])
    pairs, used = [], {ev.customer}
    for tk in live["supplier"].drop_duplicates():
        if len(pairs) >= MAX_NAMES:
            break
        if not tk or tk in used or tk not in ok.index or not ok[tk]:
            continue
        cands = [c for c in universe.get(sector_of.get(tk, "SPY"), [])
                 if c not in used and c not in ever_linked and c != tk and c in ok.index and ok[c]]
        if not cands:
            continue
        gaps = np.abs(np.log(volume[cands].to_numpy(dtype=float)) - np.log(float(volume[tk])))
        decoy = cands[int(np.argmin(gaps))]          # cands is sorted, so ties resolve alphabetically
        used.update({tk, decoy})
        pairs.append((tk, decoy, float(volume[tk]), float(volume[decoy])))
    return direction, pairs


def trade_return(tk, ev, direction, volume, adj, sector_of, exit_day=None):
    """Sector-adjusted, signed, after costs. A name that stops trading is closed at its last price."""
    exit_day = exit_day or ev.exit
    window = adj.loc[ev.t2:exit_day, tk].ffill()
    etf = sector_of.get(tk, "SPY")
    e = adj.loc[ev.t2:exit_day, etf]
    if not (np.isfinite(e.iloc[0]) and np.isfinite(e.iloc[-1])):
        e = adj.loc[ev.t2:exit_day, "SPY"]
    gross = direction * ((window.iloc[-1] / window.iloc[0] - 1) - (e.iloc[-1] / e.iloc[0] - 1))
    b = bucket(volume)
    days_held = (exit_day - ev.t2).days
    cost = 2 * COST_SIDE[b] + (BORROW_YEAR[b] * days_held / 365 if direction < 0 else 0.0)
    return float(gross), float(gross - cost)


def evaluate(events, links, adj, raw, dv, sector_of, universe, start=None, end=None):
    """Runs arm A and the placebo on events with start <= t1 < end. Returns (per-event, per-trade)."""
    ev_rows, tr_rows = [], []
    for ev in events.itertuples(index=False):
        if (start is not None and ev.t1 < pd.Timestamp(start)) or (end is not None and ev.t1 >= pd.Timestamp(end)):
            continue
        direction, pairs = select(ev, links, adj, raw, dv, sector_of, universe)
        if not pairs:
            continue
        a, p = [], []
        for tk, decoy, vol, dvol in pairs:
            ga, na = trade_return(tk, ev, direction, vol, adj, sector_of)
            gp, npl = trade_return(decoy, ev, direction, dvol, adj, sector_of)
            a.append(na)
            p.append(npl)
            tr_rows.append({"customer": ev.customer, "t1": ev.t1.date(), "t2": ev.t2.date(), "exit": ev.exit.date(),
                            "direction": direction, "supplier": tk, "decoy": decoy,
                            "supplier_gross": round(ga, 6), "supplier_net": round(na, 6),
                            "decoy_gross": round(gp, 6), "decoy_net": round(npl, 6)})
        ev_rows.append({"customer": ev.customer, "t1": ev.t1, "sector": ev.sector, "direction": direction,
                        "trigger": ev.trigger, "names": len(pairs), "arm_a": float(np.mean(a)),
                        "placebo": float(np.mean(p)), "diff": float(np.mean(a) - np.mean(p))})
    return pd.DataFrame(ev_rows), pd.DataFrame(tr_rows)


def candidates(events, links, adj, raw, dv, sector_of, universe):
    """Events that would produce at least one trade. Looks at no outcome prices."""
    keep = []
    for ev in events.itertuples(index=False):
        _, pairs = select(ev, links, adj, raw, dv, sector_of, universe)
        if pairs:
            keep.append({"customer": ev.customer, "t1": ev.t1, "sector": ev.sector, "names": len(pairs)})
    return pd.DataFrame(keep)


def cluster_key(df):
    iso = df["t1"].dt.isocalendar()
    return df["sector"] + "-" + iso["year"].astype(str) + "-" + iso["week"].astype(str)


def summarize(per_event: pd.DataFrame, col="diff"):
    """Mean with a 90% interval from resampling whole clusters (same sector, same week)."""
    if per_event.empty:
        return {"events": 0}
    keys = cluster_key(per_event)
    groups = [g[col].to_numpy() for _, g in per_event.groupby(keys)]
    sums = np.array([g.sum() for g in groups])
    counts = np.array([len(g) for g in groups])
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(groups), size=(BOOTSTRAP, len(groups)))
    means = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    x = per_event[col].to_numpy()
    top = np.sort(x)[::-1][:10].sum()
    return {"events": int(len(x)), "clusters": int(len(groups)), "mean": float(x.mean()),
            "low90": float(np.percentile(means, 5)), "high90": float(np.percentile(means, 95)),
            "share_positive": float((x > 0).mean()), "median": float(np.median(x)),
            "top10_share_of_total": float(top / x.sum()) if x.sum() > 0 else None}


def decide(stats, min_edge, arm_a_mean=None):
    """GO needs all three: the difference is reliably above zero, it is large enough, and arm A itself
    made money against its sector after costs (costs cancel out of the difference, so this is separate)."""
    if not stats.get("events"):
        return "INCONCLUSIVE"
    if stats["high90"] < min_edge:
        return "STOP"
    if stats["low90"] > 0 and stats["mean"] >= min_edge and (arm_a_mean is None or arm_a_mean > 0):
        return "GO"
    return "INCONCLUSIVE"
