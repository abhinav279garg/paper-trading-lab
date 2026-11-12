"""Daily job: refresh prices, re-run the ten paper strategies, write results, charts and README."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker  # noqa: F401
import pandas as pd

from . import data
import csv

from .config import BACKTEST_START, COST, LIVE_START, RULES_FROZEN, SPLIT_DATE, START_CAPITAL
from .engine import stats
from .strategies import STRATEGIES

ROOT = os.path.dirname(os.path.dirname(__file__))
BLUE, GRAY, INK, MUTED, SURFACE = "#2a78d6", "#9a9992", "#0b0b0b", "#52514e", "#fcfcfb"


def pct(x):
    return "n/a" if x is None or x != x else f"{x * 100:+.1f}%"


def eur(x):
    return f"€{x:,.2f}"


def evaluate(daily, hourly):
    out = []
    live_start, bt_start = pd.Timestamp(LIVE_START), pd.Timestamp(BACKTEST_START)
    for sid, name, klass, bench, ppy, fn, uses_hourly in STRATEGIES:
        try:
            eq, trades, position = fn(hourly) if uses_hourly else fn(daily)
        except Exception as exc:
            out.append({"id": sid, "name": name, "class": klass, "error": repr(exc)})
            continue
        eq = eq.dropna()
        bench_px = (hourly if uses_hourly else daily[bench]).dropna()
        bt = eq[eq.index >= bt_start]
        if len(bt) < 30:
            out.append({"id": sid, "name": name, "class": klass, "error": "not enough price history"})
            continue
        scale_bt = START_CAPITAL / bt.iloc[0]
        bt_eq = bt * scale_bt
        b = bench_px[(bench_px.index >= bt.index[0]) & (bench_px.index <= bt.index[-1])]
        bench_eq = b / b.iloc[0] * START_CAPITAL
        bt_trades = [t for t in trades if t["time"] >= bt.index[0]]
        row = {"id": sid, "name": name, "class": klass, "benchmark": bench,
               "backtest": stats(bt_eq, ppy), "benchmark_stats": stats(bench_eq, ppy),
               "trades": len(bt_trades),
               "fees_paid": float(sum(t["fee"] for t in bt_trades) * scale_bt),
               "position": position, "bt_eq": bt_eq, "bench_eq": bench_eq}
        split = pd.Timestamp(SPLIT_DATE)
        if bt_eq.index[0] < split < bt_eq.index[-1]:
            halves = []
            for a, bb in ((bt_eq[bt_eq.index < split], bench_eq[bench_eq.index < split]),
                          (bt_eq[bt_eq.index >= split], bench_eq[bench_eq.index >= split])):
                halves.append((float(a.iloc[-1] / a.iloc[0] - 1), float(bb.iloc[-1] / bb.iloc[0] - 1)))
            row["halves"] = halves
        before = eq[eq.index < live_start]
        after = eq[eq.index >= live_start]
        if len(before):
            scale = START_CAPITAL / before.iloc[-1]
            live_eq = pd.concat([before.iloc[-1:], after]) * scale
            row["live_eq"] = live_eq
            row["live_value"] = float(live_eq.iloc[-1])
            row["live_trades"] = [dict(t, strategy=name, strategy_id=sid, units=t["units"] * scale,
                                       value=t["value"] * scale, fee=t["fee"] * scale)
                                  for t in trades if t["time"] >= live_start]
            row["last_bar"] = str(eq.index[-1])
        out.append(row)
    return out


def ledger(rows):
    """Append-only record. A trade or daily value is written once, on the run that first sees it,
    and never rewritten. If a later recomputation disagrees with the record, that is reported."""
    folder = os.path.join(ROOT, "results")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    notes = []

    def load_rows(path):
        return list(csv.DictReader(open(path))) if os.path.exists(path) else []

    def append(path, fields, new):
        fresh = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if fresh:
                w.writeheader()
            w.writerows(new)

    tpath = os.path.join(folder, "ledger.csv")
    recorded = load_rows(tpath)
    seen = {(r["strategy_id"], r["time"], r["asset"], r["side"]) for r in recorded}
    current, new = set(), []
    for r in rows:
        for t in r.get("live_trades", []):
            key = (t["strategy_id"], str(t["time"]), t["asset"], t["side"])
            current.add(key)
            if key not in seen:
                new.append({"recorded_at": stamp, "strategy_id": key[0], "time": key[1], "asset": key[2],
                            "side": key[3], "units": f"{t['units']:.8g}", "price": f"{t['price']:.8g}",
                            "value": f"{t['value']:.6f}", "fee": f"{t['fee']:.6f}"})
    append(tpath, ["recorded_at", "strategy_id", "time", "asset", "side", "units", "price", "value", "fee"], new)
    live_ids = {r["id"] for r in rows if "live_trades" in r}
    gone = [k for k in seen if k not in current and k[0] in live_ids]
    if gone:
        notes.append(f"{len(gone)} recorded trade(s) no longer appear when history is recomputed "
                     "(price data was revised). The original record in results/ledger.csv is kept.")

    epath = os.path.join(folder, "equity_log.csv")
    have = {(r["strategy_id"], r["bar"]) for r in load_rows(epath)}
    new = []
    for r in rows:
        if "live_eq" not in r:
            continue
        daily = r["live_eq"].resample("D").last().dropna()
        for bar, value in daily.iloc[:-1].items() if r["id"] == "btc_intraday" else daily.items():
            key = (r["id"], str(bar)[:10])
            if key not in have:
                new.append({"recorded_at": stamp, "strategy_id": key[0], "bar": key[1], "value": f"{value:.4f}"})
    append(epath, ["recorded_at", "strategy_id", "bar", "value"], new)
    return notes


def charts(rows):
    os.makedirs(os.path.join(ROOT, "charts"), exist_ok=True)
    good = [r for r in rows if "bt_eq" in r]
    cols = 2
    n = (len(good) + cols - 1) // cols
    fig, axes = plt.subplots(n, cols, figsize=(9, 2.6 * n), facecolor=SURFACE)
    for ax, r in zip(axes.ravel(), good):
        ax.set_facecolor(SURFACE)
        ax.plot(r["bench_eq"].index, r["bench_eq"].values, color=GRAY, lw=1.2,
                label=f"buy & hold {r['benchmark']}")
        ax.plot(r["bt_eq"].index, r["bt_eq"].values, color=BLUE, lw=1.8, label="strategy")
        ax.set_yscale("log")
        ax.set_title(r["name"], fontsize=9, color=INK, loc="left")
        ax.tick_params(labelsize=7, colors=MUTED, length=0)
        ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(base=10, subs=(1, 2, 5), numticks=12))
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"€{v:g}"))
        ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        ax.grid(True, which="major", color="#e6e5e0", lw=0.6)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.text(0.99, 0.03, f"gray: buy & hold {r['benchmark']}", transform=ax.transAxes, ha="right",
                fontsize=7, color=MUTED)
    for ax in axes.ravel()[len(good):]:
        ax.axis("off")
    fig.suptitle("Backtest: growth of €10 (log scale), after fees.  Blue: strategy.  Gray: simply holding the asset.",
                 fontsize=10, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(os.path.join(ROOT, "charts", "backtest.png"), dpi=130)
    plt.close(fig)


def readme(rows, notes):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    live = [r for r in rows if "live_value" in r]
    L = ["# Paper trading lab", "",
         "**Simulated money only.** Ten rule-based strategies, each starting with an imaginary €10 on "
         f"{LIVE_START}. No broker is connected and no real order is ever placed. "
         "This is an experiment, not investment advice.", "",
         f"_Last updated: {now}. Updated automatically once a day by GitHub Actions._", ""]
    for n in notes:
        L.append(f"> **Data note:** {n}")
    if notes:
        L.append("")
    if live:
        total = sum(r["live_value"] for r in live)
        start = START_CAPITAL * len(live)
        L += [f"## Live paper portfolio since {LIVE_START}", "",
              f"**{eur(start)} simulated → {eur(total)} ({pct(total / start - 1)})**", "",
              "| # | Strategy | Type | €10 is now | Change | Holding now |", "|---|---|---|---|---|---|"]
        for i, r in enumerate(rows, 1):
            if "live_value" not in r:
                L.append(f"| {i} | {r['name']} | {r['class']} | n/a | n/a | {r.get('error', 'waiting for data')} |")
                continue
            pos = r["position"]
            if isinstance(pos, dict):
                pos = ", ".join(f"{k} {v * 100:+.0f}%" for k, v in pos.items()) or "cash"
            L.append(f"| {i} | {r['name']} | {r['class']} | {eur(r['live_value'])} | "
                     f"{pct(r['live_value'] / START_CAPITAL - 1)} | {pos} |")
        L += ["", "A strategy starts in whatever position its rule already held on the start date. "
              "A few days of results say nothing; judge this over months.", ""]
        recent = sorted((t for r in live for t in r["live_trades"]), key=lambda t: t["time"], reverse=True)[:25]
        L += ["### Latest simulated trades", ""]
        if recent:
            L += ["| Time (UTC) | Strategy | Action | Asset | Value | Fee |", "|---|---|---|---|---|---|"]
            for t in recent:
                L.append(f"| {str(t['time'])[:16]} | {t['strategy']} | {t['side']} | {t['asset']} | "
                         f"{eur(t['value'])} | €{t['fee']:.4f} |")
        else:
            L.append("No trades yet since the start date.")
        L.append("")
    L += ["## Backtest: what these rules would have done in the past", "",
          "Fees and slippage are included. \"Hold\" is what simply buying the same asset and doing "
          "nothing would have returned over the same period.", "",
          "| # | Strategy | Period | Total | Per year | Worst drop | Sharpe | Hold: total | Hold: worst drop | Trades | Fees per €10 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        if "backtest" not in r:
            L.append(f"| {i} | {r['name']} | {r.get('error', '')} | | | | | | | | |")
            continue
        s, b = r["backtest"], r["benchmark_stats"]
        L.append(f"| {i} | {r['name']} | {s['start']} → {s['end']} | {pct(s['total_return'])} | {pct(s['cagr'])} | "
                 f"{pct(s['max_drawdown'])} | {s['sharpe']:.2f} | {pct(b['total_return'])} | "
                 f"{pct(b['max_drawdown'])} | {r['trades']} | {eur(r['fees_paid'])} |")
    L += ["", "### The same backtest, split in two halves", "",
          "If a rule only worked in one half, its overall number is weak evidence.", "",
          f"| # | Strategy | Before {SPLIT_DATE[:4]}: strategy | hold | From {SPLIT_DATE[:4]}: strategy | hold | Beat hold in both halves? |",
          "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        if "halves" not in r:
            L.append(f"| {i} | {r['name']} | n/a | n/a | n/a | n/a | history too short |")
            continue
        (s1, b1), (s2, b2) = r["halves"]
        verdict = "is the benchmark" if r["id"] == "spy_hold" else ("yes" if s1 > b1 and s2 > b2 else "no")
        L.append(f"| {i} | {r['name']} | {pct(s1)} | {pct(b1)} | {pct(s2)} | {pct(b2)} | {verdict} |")
    L += ["", "![Backtest charts](charts/backtest.png)", "",
          "## How the live record is kept honest", "",
          f"- **Rules frozen on {RULES_FROZEN}.** No parameter was tuned to fit the backtest (they are standard "
          "textbook values), and none will be changed. If a rule is ever changed, its live record restarts.",
          "- **Append-only ledger.** Every simulated trade is written to `results/ledger.csv` and every daily "
          "value to `results/equity_log.csv` on the day it happens, and those rows are never rewritten. "
          "The git history of this repository timestamps each entry, so the record cannot be adjusted afterwards.",
          "- **Judge it at 3 to 6 months**, against simply holding the S&P 500 ETF (strategy 4), not before.", "",
          "## Read this before believing any number above", "",
          "- **Past results do not predict future results.** A rule that worked in a backtest often stops working.",
          "- **Stock momentum still has some bias.** Its universe is the 12 largest US companies at the end of "
          "2017, so it no longer picks from today's winners. But 12 giants that all survived is a small and "
          "favourable sample.",
          "- **Options are model-priced.** There is no free historical options data, so strategies 9 and 10 "
          "use a pricing formula with the VIX index as volatility and a "
          f"{COST['option_haircut'] * 100:.0f}% spread haircut, plus a rough adjustment for calls. "
          "The covered-call result in particular depends on that assumption; real covered-call funds "
          "have lagged the index over this period. Do not read it as beating buy and hold.",
          "- **Day trading loses to fees.** The hourly Bitcoin rule trades hundreds of times, and each trade pays the fee.",
          "- **Futures at €10 are not possible in reality.** One contract needs thousands of euros of margin. "
          "The simulation allows fractions to show how the rule behaves. Prices are front-month series with roll gaps.",
          "- **Real fees at this size would be worse.** Costs are modelled as a percentage "
          f"({COST['crypto'] * 100:.2f}% crypto, {COST['equity'] * 100:.2f}% stocks/ETFs, "
          f"{COST['futures'] * 100:.2f}% futures per trade). A flat €1 broker fee on a €10 order is 10%.",
          "- **Currency:** US assets are converted to euros with the daily EUR/USD rate, so results include currency moves.",
          "- **No taxes, no interest on cash.**", "",
          "## How it works", "",
          "- `lab/strategies.py` holds the ten rules, `lab/engine.py` the simulator, `lab/run.py` the daily job.",
          "- A decision made on one bar's closing price is executed on the next bar's closing price.",
          "- Prices come from Yahoo Finance via the `yfinance` library and are cached in `data/`.",
          "- Run it yourself: `pip install -r requirements.txt && python -m lab.run`", ""]
    open(os.path.join(ROOT, "README.md"), "w").write("\n".join(L))


def main():
    notes = [] if "--offline" in sys.argv else data.refresh()
    daily, hourly = data.load()
    age = (pd.Timestamp.now(tz="UTC").tz_localize(None) - daily.index[-1]).days
    if age > 4:
        notes.append(f"Latest daily price is {age} days old.")
    if hourly.empty:
        notes.append("No hourly Bitcoin prices available; the intraday strategy is not running.")
        hourly = pd.Series(dtype=float)
    rows = evaluate(daily, hourly)
    notes += ledger(rows)
    charts(rows)
    readme(rows, notes)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    slim = []
    for r in rows:
        s = {k: v for k, v in r.items() if k not in ("bt_eq", "bench_eq", "live_eq", "live_trades")}
        if "live_eq" in r:
            s["live_equity"] = {str(k): round(float(v), 4) for k, v in r["live_eq"].resample("D").last().dropna().items()}
            s["live_trades"] = [dict(t, time=str(t["time"])) for t in r["live_trades"]]
        slim.append(s)
    json.dump({"updated": datetime.now(timezone.utc).isoformat(), "live_start": LIVE_START,
               "notes": notes, "strategies": slim},
              open(os.path.join(ROOT, "results", "summary.json"), "w"), indent=1, default=str)
    for r in rows:
        print(r["id"], r.get("error") or (pct(r["backtest"]["total_return"]), r.get("live_value")))


if __name__ == "__main__":
    main()
