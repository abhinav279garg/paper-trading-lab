"""Steps 0 and 1 of docs/event-intelligence-spec.md. Runs in GitHub Actions in short, resumable
stages. Paper research only: no AI calls, no orders."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import random
import sys
import time
import traceback

import numpy as np
import pandas as pd

from . import core, links
from .config import (CUSTOMERS, DEV_START, ETFS, GATE0, HISTORY_START, HOLD_DAYS, HOLDOUT_START, MIN_EDGE,
                     TRIGGER, sector_etf)

HERE = os.path.dirname(__file__)
OUT = os.path.join(os.path.dirname(HERE), "results", "event_lab")
WORK = links.WORK
FILERS = os.path.join(WORK, "filers.json")
FROZEN = os.path.join(HERE, "FROZEN")


def code_hash():
    h = hashlib.sha256()
    for path in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        h.update(open(path, "rb").read())
    return h.hexdigest()[:12]


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    json.dump(obj, open(os.path.join(OUT, name), "w"), indent=1, default=str)


def load(name):
    path = os.path.join(OUT, name)
    return json.load(open(path)) if os.path.exists(path) else None


# ---------------------------------------------------------------- SEC metadata

def fetch_filer(sec, cik, want_8k):
    j = sec.get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    if not j:
        return {"cik": cik, "ticker": "", "sic": "", "tenk": [], "eightk": []}
    pages = [j["filings"]["recent"]]
    dates = pages[0].get("filingDate") or ["9999"]
    if min(dates) > HISTORY_START:
        for f in j["filings"].get("files", []):
            if f.get("filingTo", "9999") >= HISTORY_START:
                page = sec.get("https://data.sec.gov/submissions/" + f["name"])
                if page:
                    pages.append(page)
    tenk, eightk = set(), set()
    for pg in pages:
        for form, filed, accepted in zip(pg["form"], pg["filingDate"], pg["acceptanceDateTime"]):
            if filed < HISTORY_START:
                continue
            if form == "10-K":
                tenk.add(filed)
            elif want_8k and form == "8-K":
                eightk.add(accepted[:19])
    return {"cik": cik, "ticker": (j.get("tickers") or [""])[0], "sic": j.get("sic") or "",
            "name": j.get("name", ""), "tenk": sorted(tenk), "eightk": sorted(eightk)}


def filers_stage(sec, deadline, link_rows):
    filers = json.load(open(FILERS)) if os.path.exists(FILERS) else {}
    if "_customers_mapped" not in filers:
        table = sec.get("https://www.sec.gov/files/company_tickers.json") or {}
        by_ticker = {v["ticker"]: f"{int(v['cik_str']):010d}" for v in table.values()}
        for ticker, _ in CUSTOMERS:
            filers["ticker:" + ticker] = {"cik": by_ticker.get(ticker, "")}
        filers["_customers_mapped"] = True
    todo = [(filers["ticker:" + t]["cik"], True) for t, _ in CUSTOMERS if filers["ticker:" + t]["cik"]]
    todo += [(c, False) for c in sorted({r["supplier_cik"] for r in link_rows})]
    n = 0
    for cik, want_8k in todo:
        have = filers.get(cik)
        if have and (have.get("eightk") or not want_8k or have.get("_8k")):
            continue
        if time.time() > deadline:
            json.dump(filers, open(FILERS, "w"))
            return filers, False
        info = fetch_filer(sec, cik, want_8k)
        info["_8k"] = want_8k
        filers[cik] = info
        n += 1
        if n % 100 == 0:
            json.dump(filers, open(FILERS, "w"))
    json.dump(filers, open(FILERS, "w"))
    return filers, True


# ---------------------------------------------------------------- prices (never committed)

def load_prices(tickers):
    import yfinance as yf
    tickers = sorted(set(tickers))
    adj, raw, vol = [], [], []
    for i in range(0, len(tickers), 120):
        chunk = tickers[i:i + 120]
        for attempt in range(3):
            try:
                df = yf.download(chunk, start="2016-10-01", auto_adjust=False, progress=False, threads=True,
                                 group_by="column")
                if len(df):
                    break
            except Exception as exc:
                print("price chunk failed:", type(exc).__name__)
            time.sleep(10 * (attempt + 1))
        else:
            continue
        if not isinstance(df.columns, pd.MultiIndex):
            df.columns = pd.MultiIndex.from_product([df.columns, chunk])
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        adj.append(df["Adj Close"])
        raw.append(df["Close"])
        vol.append(df["Volume"])
        time.sleep(1.5)
    adj, raw, vol = (pd.concat(x, axis=1).dropna(how="all", axis=1) for x in (adj, raw, vol))
    if "SPY" not in adj.columns:
        raise RuntimeError("price download failed (no SPY)")
    days = adj["SPY"].dropna().index
    adj, raw, vol = adj.reindex(days), raw.reindex(days), vol.reindex(days)
    adj = adj.where(adj > 0)
    dv = (raw * vol).rolling(60, min_periods=20).median()
    return adj, raw, dv, days


# ---------------------------------------------------------------- analysis

def prepare(filers, link_rows):
    lk = core.build_links(link_rows, filers)
    cust_cik = {t: filers["ticker:" + t]["cik"] for t, _ in CUSTOMERS}
    sector_of = {e: e for e in ETFS}
    for t, cik in cust_cik.items():
        sector_of[t] = sector_etf(filers.get(cik, {}).get("sic"))
    for r in lk.itertuples(index=False):
        if r.supplier:
            sector_of.setdefault(r.supplier, sector_etf(r.sic))
    filings = {t: filers.get(cik, {}).get("eightk", []) for t, cik in cust_cik.items() if cik}
    return lk, sector_of, filings


def gate0(lk, cand, adj):
    years, rows = list(range(2018, 2027)), []
    for y in years:
        a, b = pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y + 1}-01-01")
        active = lk[(lk["valid_from"] < b) & (lk["valid_to"] > a)].drop_duplicates(["customer", "supplier_cik"])
        window = adj.loc[a:b]
        priced_names = set(window.columns[window.notna().sum() >= 20])
        listed = active[active["supplier"] != ""]
        priced = listed[listed["supplier"].isin(priced_names)]
        ev = cand[(cand["t1"] >= a) & (cand["t1"] < b)] if len(cand) else cand
        rows.append({"year": y, "verified_pairs_all": int(len(active)), "pairs": int(len(priced)),
                     "customers": int(priced["customer"].nunique()),
                     "top5_share": float(priced["customer"].value_counts().head(5).sum() / max(len(priced), 1)),
                     "sectors": int((priced["sic"].map(sector_etf).value_counts() >= 10).sum()),
                     "events": int(len(ev)),
                     "clusters": int(core.cluster_key(ev).nunique()) if len(ev) else 0,
                     "priced": float(len(priced) / max(len(active), 1))})
    full = [r for r in rows if 2018 <= r["year"] <= 2025]
    last = next(r for r in rows if r["year"] == 2025)
    checks = {}
    for key, level in GATE0.items():
        med = float(np.median([r[key] for r in full]))
        ok = (med <= level and last[key] <= level) if key == "top5_share" else (med >= level and last[key] >= level)
        checks[key] = {"level": level, "median_2018_2025": med, "year_2025": last[key], "pass": bool(ok)}
    return {"by_year": rows, "checks": checks, "pass": all(c["pass"] for c in checks.values())}


def run_period(label, start, end, lk, sector_of, filings, adj, raw, dv, days, universe, diagnostics):
    events = core.customer_events(filings, adj, days, sector_of)
    per_event, trades = core.evaluate(events, lk, adj, raw, dv, sector_of, universe, start, end)
    res = {"period": [start, end], "code_hash": code_hash(), "commit": os.environ.get("GITHUB_SHA", "local"),
           "primary_A_minus_placebo": core.summarize(per_event, "diff"),
           "arm_A_vs_sector": core.summarize(per_event, "arm_a"),
           "placebo_vs_sector": core.summarize(per_event, "placebo")}
    if len(per_event):
        res["long_events_A_minus_placebo"] = core.summarize(per_event[per_event["direction"] > 0], "diff")
        res["short_events_A_minus_placebo"] = core.summarize(per_event[per_event["direction"] < 0], "diff")
        res["by_year_mean_diff"] = {int(y): float(g["diff"].mean()) for y, g in per_event.groupby(per_event["t1"].dt.year)}
        res["distinct_customers"] = int(per_event["customer"].nunique())
        res["trades"] = int(len(trades))
        res["mean_gross_A"] = float(trades["supplier_gross"].mean())
        res["mean_cost_A"] = float((trades["supplier_gross"] - trades["supplier_net"]).mean())
    res["decision"] = core.decide(res["primary_A_minus_placebo"], MIN_EDGE, res["arm_A_vs_sector"].get("mean"))
    if diagnostics:   # reported for context only; plays no part in the decision
        diag = {}
        for trig, hold in ((TRIGGER, 1), (TRIGGER, 10), (0.02, HOLD_DAYS), (0.05, HOLD_DAYS)):
            ev2 = core.customer_events(filings, adj, days, sector_of, trigger=trig, hold=hold)
            pe2, _ = core.evaluate(ev2, lk, adj, raw, dv, sector_of, universe, start, end)
            diag[f"trigger_{trig:.0%}_hold_{hold}d"] = core.summarize(pe2, "diff")
        res["diagnostics_not_used_for_decision"] = diag
    trades.to_csv(os.path.join(OUT, f"trades_{label}.csv"), index=False)
    save(f"{label}.json", res)
    return res


def pct(x):
    return "n/a" if x is None else f"{x * 100:+.2f}%"


def report(stage, g0=None, dev=None, hold=None, counts=None):
    L = ["# Event experiment: decision report", "",
         "Paper research only. Specification: `docs/event-intelligence-spec.md`. "
         "Every number here is produced by `python -m event_lab.run` from the committed code.", "",
         f"**Stage reached:** {stage}", ""]
    if counts:
        L += ["## Data collected", ""] + [f"- {k}: {v}" for k, v in counts.items()] + [""]
    if g0:
        L += ["## Gate 0: data feasibility", "", f"**Result: {'PASS' if g0['pass'] else 'FAIL'}**", "",
              "| Measure | Pass level | Median 2018–2025 | 2025 | Pass |", "|---|---|---|---|---|"]
        for k, c in g0["checks"].items():
            L.append(f"| {k} | {c['level']} | {c['median_2018_2025']:.3g} | {c['year_2025']:.3g} | {'yes' if c['pass'] else 'NO'} |")
        L += ["", "| Year | Verified pairs (all) | Usable pairs | Customers | Top-5 share | Sectors ≥10 | Events | Clusters | Priced |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in g0["by_year"]:
            L.append(f"| {r['year']} | {r['verified_pairs_all']} | {r['pairs']} | {r['customers']} | {r['top5_share']:.0%} | "
                     f"{r['sectors']} | {r['events']} | {r['clusters']} | {r['priced']:.0%} |")
        L.append("")
        if not g0["pass"]:
            L += ["**Recommendation: STOP.** The gate failed, so the historical test was not run.", "",
                  "What this does and does not mean: this particular data approach (named customers found by phrase "
                  "search in annual reports, free price data) did not yield enough usable, independent events. It says "
                  "nothing either way about whether event-driven trading with other data could work.", ""]
    for label, res, note in (("Development period (for building only, not evidence)", dev, True),
                             ("Holdout period (the pre-registered test)", hold, False)):
        if not res:
            continue
        p, a, pl = res["primary_A_minus_placebo"], res["arm_A_vs_sector"], res["placebo_vs_sector"]
        L += [f"## {label}", "", f"Period: {res['period'][0]} to {res['period'][1]}. Code `{res['code_hash']}`, commit `{str(res['commit'])[:7]}`.", ""]
        if not p.get("events"):
            L += ["No qualifying events.", ""]
            continue
        L += ["| Measure, per event, after costs | Mean | 90% interval | Events | Clusters |", "|---|---|---|---|---|",
              f"| **Arm A minus placebo (primary)** | {pct(p['mean'])} | {pct(p['low90'])} to {pct(p['high90'])} | {p['events']} | {p['clusters']} |",
              f"| Arm A against its sector | {pct(a['mean'])} | {pct(a['low90'])} to {pct(a['high90'])} | | |",
              f"| Placebo against its sector | {pct(pl['mean'])} | {pct(pl['low90'])} to {pct(pl['high90'])} | | |", "",
              f"- Share of events where A beat the placebo: {p['share_positive']:.0%}. Median difference: {pct(p['median'])}.",
              f"- Before costs, arm A averaged {pct(res.get('mean_gross_A'))} per trade; costs averaged {pct(res.get('mean_cost_A'))} per trade.",
              f"- Distinct customers: {res.get('distinct_customers')}. Trades: {res.get('trades')}."]
        for key, name in (("long_events_A_minus_placebo", "Long events"), ("short_events_A_minus_placebo", "Short events")):
            s = res.get(key) or {}
            if s.get("events"):
                L.append(f"- {name}: {pct(s['mean'])} ({pct(s['low90'])} to {pct(s['high90'])}), {s['events']} events.")
        if p.get("top10_share_of_total") is not None:
            L.append(f"- The ten best events account for {p['top10_share_of_total']:.0%} of the total difference.")
        L += ["", "By year (mean difference): " + ", ".join(f"{y}: {pct(v)}" for y, v in (res.get("by_year_mean_diff") or {}).items()), ""]
        if not note:
            L += [f"### Decision: {res['decision']}", "",
                  f"Rule fixed in advance: GO if the lower bound is above zero and the mean is at least {MIN_EDGE:.2%}; "
                  f"STOP if the upper bound is below {MIN_EDGE:.2%}; otherwise INCONCLUSIVE (no AI spend by default). "
                  "GO also requires arm A itself to be positive against its sector after costs.", ""]
            d = res.get("diagnostics_not_used_for_decision") or {}
            if d:
                L += ["Diagnostics, not used for the decision:", "", "| Variant | Mean | 90% interval | Events |", "|---|---|---|---|"]
                for k, s in d.items():
                    if s.get("events"):
                        L.append(f"| {k} | {pct(s['mean'])} | {pct(s['low90'])} to {pct(s['high90'])} | {s['events']} |")
                L.append("")
    L += ["## Limitations", "",
          "- Links come from a phrase search over annual reports for about 140 large customers chosen today. Disclosures in tables, unusual wording or anonymous form are missed.",
          "- Prices are from an unofficial free source. Companies that were delisted are mostly missing, which biases history. The 'priced' row above measures how much was lost.",
          "- SEC acceptance times are read as New York time and pushed to the next trading day after 15:45, the conservative reading.",
          "- Size is measured by traded value, and short-sale limits (minimum price and liquidity, a borrowing fee) are assumptions, not broker quotes.",
          "- The cost of trading the sector ETF hedge is ignored.",
          "- A pass on history shows the effect was present. It is not proof of a tradable edge.", ""]
    open(os.path.join(OUT, "REPORT.md"), "w").write("\n".join(L))


def main():
    os.makedirs(WORK, exist_ok=True)
    status = load("STATUS.json") or {}
    if status.get("final"):
        print("finished earlier:", status.get("stage"))
        return
    if os.path.exists(os.path.join(OUT, "error.txt")):
        os.remove(os.path.join(OUT, "error.txt"))
    from .sec import Sec
    sec = Sec()
    deadline = time.time() + int(os.environ.get("EVENT_LAB_MINUTES", "300")) * 60
    stage = "discovering reports"
    done = links.discover(sec, deadline) and (stage := "verifying links") and links.verify(sec, deadline)
    link_rows = links._read(links.LINKS)
    counts = {"candidate reports found": len({(h["adsh"], h["file"]) for h in links._read(links.HITS)}),
              "reports read": len(open(links.DONE).read().split()) if os.path.exists(links.DONE) else 0,
              "verified disclosures": len(link_rows), "SEC requests this run": sec.calls}
    if not done:
        save("STATUS.json", {"stage": stage, "final": False, **counts, "code_hash": code_hash()})
        return
    filers, done = filers_stage(sec, deadline, link_rows)
    counts["SEC requests this run"] = sec.calls
    if not done:
        save("STATUS.json", {"stage": "reading company records", "final": False, **counts, "code_hash": code_hash()})
        return
    lk, sector_of, filings = prepare(filers, link_rows)
    random.seed(7)
    sample = random.sample(link_rows, min(40, len(link_rows)))
    open(os.path.join(OUT, "links_sample.md"), "w").write(
        "# 40 randomly chosen verified disclosures, for manual checking\n\n" +
        "\n".join(f"- **{r['customer']}** ← {r['supplier_name']} ({r['file_date']}, {r['pct']}%): {r['evidence']}" for r in sample))
    tickers = set(ETFS) | {t for t, _ in CUSTOMERS} | {s for s in lk["supplier"] if s}
    adj, raw, dv, days = load_prices(tickers)
    counts.update({"8-K filings by customers": sum(len(v) for v in filings.values()),
                   "tickers requested / with prices": f"{len(tickers)} / {adj.shape[1]}",
                   "prices through": str(days[-1].date())})
    universe = {}
    for tk in sorted({s for s in lk["supplier"] if s and s in adj.columns}):
        universe.setdefault(sector_of.get(tk, "SPY"), []).append(tk)
    events = core.customer_events(filings, adj, days, sector_of)
    cand = core.candidates(events, lk, adj, raw, dv, sector_of, universe)
    counts["qualifying customer events (3% move)"] = len(events)
    g0 = gate0(lk, cand, adj)
    save("gate0.json", g0)
    if not g0["pass"]:
        report("Gate 0 failed. Stopped.", g0, counts=counts)
        save("STATUS.json", {"stage": "gate 0 failed", "final": True, "recommendation": "STOP", **counts, "code_hash": code_hash()})
        return
    args = (lk, sector_of, filings, adj, raw, dv, days, universe)
    dev = load("dev.json")
    if not dev or dev.get("code_hash") != code_hash():
        dev = run_period("dev", DEV_START, HOLDOUT_START, *args, diagnostics=False)
    hold = load("holdout.json")
    frozen = open(FROZEN).read().strip() if os.path.exists(FROZEN) else ""
    if not hold and frozen == code_hash():
        last = str(days[-1 - HOLD_DAYS - 1].date())
        hold = run_period("holdout", HOLDOUT_START, last, *args, diagnostics=True)
    stage = "holdout evaluated" if hold else "development run done; waiting for the code freeze before the holdout"
    report(stage, g0, dev, hold, counts)
    save("STATUS.json", {"stage": stage, "final": bool(hold), "recommendation": hold["decision"] if hold else None,
                         **counts, "code_hash": code_hash()})


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:   # leave a trace in the repository, without the contact address
        if isinstance(exc, SystemExit) and not exc.code:
            raise
        text = traceback.format_exc().replace(os.environ.get("SEC_CONTACT", "\0") or "\0", "[contact]")
        os.makedirs(OUT, exist_ok=True)
        open(os.path.join(OUT, "error.txt"), "w").write(time.strftime("%Y-%m-%d %H:%M UTC\n", time.gmtime()) + text[-4000:])
        print(text[-2000:])
        sys.exit(0)
