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
from .config import BACKTEST_START, COST, LIVE_START, START_CAPITAL
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
        before = eq[eq.index < live_start]
        after = eq[eq.index >= live_start]
        if len(before) and len(after):
            scale = START_CAPITAL / before.iloc[-1]
            live_eq = pd.concat([before.iloc[-1:], after]) * scale
            row["live_eq"] = live_eq
            row["live_value"] = float(live_eq.iloc[-1])
            row["live_trades"] = [dict(t, strategy=name, units=t["units"] * scale,
                                       value=t["value"] * scale, fee=t["fee"] * scale)
                                  for t in trades if t["time"] >= live_start]
            row["last_bar"] = str(eq.index[-1])
        out.append(row)
    return out


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
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"€{v:g}"))
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.grid(True, which="major", color="#e6e5e0", lw=0.6)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.legend(fontsize=7, frameon=False, loc="upper left", labelcolor=MUTED)
    for ax in axes.ravel()[len(good):]:
        ax.axis("off")
    fig.suptitle("Backtest: growth of €10 (log scale), after fees, vs. simply holding the asset",
                 fontsize=11, color=INK, x=0.01, ha="left")
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
    L += ["", "![Backtest charts](charts/backtest.png)", "",
          "## Read this before believing any number above", "",
          "- **Past results do not predict future results.** A rule that worked in a backtest often stops working.",
          "- **Stock momentum is flattered by hindsight.** Its 12 stocks were picked today from companies that "
          "are already large, so the backtest only ever chooses among known winners.",
          "- **Options are model-priced.** There is no free historical options data, so strategies 9 and 10 "
          "use a pricing formula with the VIX index as volatility and a "
          f"{COST['option_haircut'] * 100:.0f}% spread haircut. Real results would differ.",
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
