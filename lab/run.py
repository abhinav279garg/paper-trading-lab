"""Scheduled job. Daily mode: refresh prices, run the forward paper engine for all ten strategies,
re-run the backtests, write README and charts. Hourly mode: only the intraday strategy."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker  # noqa: F401
import pandas as pd

from . import data, live
from .config import BACKTEST_START, COST, SPLIT_DATE, START_CAPITAL
from .engine import stats
from .strategies import STRATEGIES, backtest

ROOT = os.path.dirname(os.path.dirname(__file__))
REPO = "https://github.com/abhinav279garg/paper-trading-lab"
BLUE, GRAY, INK, MUTED, SURFACE = "#2a78d6", "#9a9992", "#0b0b0b", "#52514e", "#fcfcfb"


def pct(x):
    return "n/a" if x is None or x != x else f"{x * 100:+.1f}%"


def eur(x):
    return "n/a" if x is None or x != x else f"€{x:,.2f}"


def build(daily, hourly, only=None):
    specs, benchmarks, errors = {}, {}, {}
    for sid, name, klass, bench, ppy, fn, uses_hourly in STRATEGIES:
        if only and sid not in only:
            continue
        try:
            src = hourly if uses_hourly else daily
            if uses_hourly and len(src) < 100:
                raise ValueError("no hourly prices")
            specs[sid] = fn(src)
            benchmarks[sid] = (hourly if uses_hourly else daily[bench]).dropna()
        except Exception as exc:
            errors[sid] = repr(exc)
    return specs, benchmarks, errors


def evaluate(specs, benchmarks, errors):
    out, bt_start = [], pd.Timestamp(BACKTEST_START)
    for sid, name, klass, bench, ppy, fn, uses_hourly in STRATEGIES:
        row = {"id": sid, "name": name, "class": klass, "benchmark": bench}
        out.append(row)
        if sid not in specs:
            row["error"] = errors.get(sid, "not run")
            continue
        eq, trades, _ = backtest(specs[sid])
        bt = eq.dropna()
        bt = bt[bt.index >= bt_start]
        if len(bt) < 30:
            row["error"] = "not enough price history"
            continue
        scale = START_CAPITAL / bt.iloc[0]
        bt_eq = bt * scale
        b = benchmarks[sid]
        b = b[(b.index >= bt.index[0]) & (b.index <= bt.index[-1])]
        bench_eq = b / b.iloc[0] * START_CAPITAL
        bt_trades = [t for t in trades if t["time"] >= bt.index[0]]
        row.update({"backtest": stats(bt_eq, ppy), "benchmark_stats": stats(bench_eq, ppy),
                    "trades": len(bt_trades), "fees_paid": float(sum(t["fee"] for t in bt_trades) * scale),
                    "bt_eq": bt_eq, "bench_eq": bench_eq, "hourly": uses_hourly})
        split = pd.Timestamp(SPLIT_DATE)
        if bt_eq.index[0] < split < bt_eq.index[-1]:
            row["halves"] = [(float(a.iloc[-1] / a.iloc[0] - 1), float(c.iloc[-1] / c.iloc[0] - 1))
                             for a, c in ((bt_eq[bt_eq.index < split], bench_eq[bench_eq.index < split]),
                                          (bt_eq[bt_eq.index >= split], bench_eq[bench_eq.index >= split]))]
    return out


def portfolio(rows):
    """Equal money in each daily-bar strategy, never rebalanced, against two yardsticks."""
    good = [r for r in rows if "bt_eq" in r and not r["hourly"]]
    if len(good) < 2:
        return None
    idx = good[0]["bt_eq"].index
    for r in good[1:]:
        idx = idx.union(r["bt_eq"].index)
    idx = idx[idx >= max(r["bt_eq"].index[0] for r in good)]

    def total(key):
        return sum(r[key].reindex(idx).ffill() for r in good).dropna()
    spy = next(r for r in good if r["id"] == "spy_hold")["bench_eq"].reindex(idx).ffill().dropna() * len(good)
    rest = sum(r["bt_eq"].reindex(idx).ffill() for r in good if r["id"] != "eth_breakout").dropna()
    return {"n": len(good), "strategies": stats(total("bt_eq"), 365), "own_benchmarks": stats(total("bench_eq"), 365),
            "spy": stats(spy, 365), "without_eth": stats(rest, 365)}


def charts(rows):
    os.makedirs(os.path.join(ROOT, "charts"), exist_ok=True)
    good = [r for r in rows if "bt_eq" in r]
    cols = 2
    n = (len(good) + cols - 1) // cols
    fig, axes = plt.subplots(n, cols, figsize=(9, 2.6 * n), facecolor=SURFACE)
    for ax, r in zip(axes.ravel(), good):
        ax.set_facecolor(SURFACE)
        ax.plot(r["bench_eq"].index, r["bench_eq"].values, color=GRAY, lw=1.2)
        ax.plot(r["bt_eq"].index, r["bt_eq"].values, color=BLUE, lw=1.8)
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


def live_risk(live_dir):
    rows = live.read_csv("equity.csv", live_dir)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["value"], df["benchmark_value"] = df["value"].astype(float), df["benchmark_value"].astype(float)
    n = df["strategy_id"].nunique()
    by_day = df.groupby("bar").agg(value=("value", "sum"), bench=("benchmark_value", "sum"), k=("value", "size"))
    by_day = by_day[by_day["k"] == n]
    by_day.index = pd.to_datetime(by_day.index)
    if len(by_day) < 30:
        return {"days": len(by_day)}
    return {"days": len(by_day), "strategies": stats(by_day["value"], 365), "benchmarks": stats(by_day["bench"], 365)}


def readme(rows, state, notes, live_dir):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    S = state["strategies"]
    L = ["# Paper trading lab", "",
         "**Simulated money only.** Ten rule-based strategies, each starting with an imaginary €10. "
         "No broker is connected and no real order is ever placed. This is an experiment, not investment advice.", "",
         f"_Last updated: {now}. Updated automatically by GitHub Actions._", ""]
    for n in notes:
        L.append(f"> **Data note:** {n}")
    if notes:
        L.append("")
    seen = [r for r in rows if r["id"] in S and "view" in S[r["id"]]]
    total = sum(S[r["id"]]["view"]["value"] for r in seen)
    bench = sum(S[r["id"]]["view"]["benchmark_value"] for r in seen)
    start = START_CAPITAL * len(seen)
    L += [f"## Live paper portfolio (record started {state['started_at'][:16]} UTC)", ""]
    if seen:
        L += [f"**Strategies: {eur(start)} → {eur(total)} ({pct(total / start - 1)})**  ",
              f"**Just holding each benchmark: {eur(start)} → {eur(bench)} ({pct(bench / start - 1)})**", "",
              "| # | Strategy | €10 is now | Hold instead | Holding now | Waiting order | Fills |",
              "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        st = S.get(r["id"], {})
        v = st.get("view")
        if not v:
            L.append(f"| {i} | {r['name']} | n/a | n/a | {r.get('error', 'waiting for data')} | | |")
            continue
        h = v["holding"]
        if isinstance(h, dict):
            h = ", ".join(f"{k} {x * 100:+.0f}%" for k, x in h.items()) or "cash"
        L.append(f"| {i} | {r['name']} | {eur(v['value'])} ({pct(v['value'] / START_CAPITAL - 1)}) | "
                 f"{eur(v['benchmark_value'])} {r['benchmark']} | {h} | "
                 f"{'yes' if st.get('pending') else ''} | {st.get('fills', 0)} |")
    risk = live_risk(live_dir)
    L.append("")
    if risk and "strategies" in risk:
        s, b = risk["strategies"], risk["benchmarks"]
        L += [f"Risk-adjusted, over {risk['days']} recorded days: strategies Sharpe {s['sharpe']:.2f}, worst drop "
              f"{pct(s['max_drawdown'])}; benchmarks Sharpe {b['sharpe']:.2f}, worst drop {pct(b['max_drawdown'])}.", ""]
    else:
        L += [f"Risk-adjusted comparison (Sharpe, worst drop) appears once 30 daily values are recorded "
              f"({(risk or {}).get('days', 0)} so far).", ""]
    L += ["Each strategy started in cash. \"Hold instead\" is €10 put into that strategy's benchmark at the same moment. "
          "Judge a strategy by its number of fills and its result against that benchmark, not by elapsed time alone: "
          "a monthly rule produces about 12 decisions a year.", ""]
    pend = [(sid, st["pending"]) for sid, st in S.items() if st.get("pending")]
    if pend:
        L += ["### Orders waiting to be filled", "",
              "Recorded now, filled at the close of the next finished price bar.", "",
              "| Order | Recorded (UTC) | Instruction |", "|---|---|---|"]
        for sid, o in pend:
            ins = o["instruction"]
            text = ins.get("action") or ", ".join(f"{k} {v * 100:+.0f}%" for k, v in ins.items() if v) or "all cash"
            L.append(f"| {o['order_id']} | {o['recorded_at'][:16]} | {text} |")
        L.append("")
    fills = live.read_csv("fills.csv", live_dir)
    L += ["### Latest fills", ""]
    if fills:
        L += ["| Order | Bar closed (UTC) | Action | Asset | Price | Value | Fee |", "|---|---|---|---|---|---|---|"]
        for f in fills[::-1][:20]:
            L.append(f"| {f['order_id']} | {f['bar_closed_at'][:16]} | {f['side']} | {f['asset']} | "
                     f"{float(f['price']):,.4f} | €{float(f['value']):.2f} | €{float(f['fee']):.4f} |")
    else:
        L.append("None yet. The first orders are recorded above and fill at the next bar close.")
    L += ["", "## How the live record is kept honest", "",
          "- **Orders are written down before they can be filled.** Each run first fills earlier orders at the close "
          "of the first price bar that finished *after* the order was recorded, then records new orders. The order "
          "is committed to git before the price it fills at exists. See `results/live/orders.csv` and `fills.csv`.",
          "- **Nothing live is recomputed from history.** Positions and cash are carried forward in "
          "`results/live/state.json`. If a run is missed, the order simply fills later, as it would for a real bot that was down.",
          f"- **Rule version `{state['rules_hash']}`.** Every order, fill and daily value carries this hash of the rule "
          "code and the git commit that produced it. If the rule code changes at all, the hash changes, the current "
          "record is moved untouched to `results/archive/` and a new record starts from €10. This is enforced by the "
          "code, not by a promise.",
          f"- **This record started from commit [`{state['started_commit'][:7]}`]({REPO}/commit/{state['started_commit']}).**",
          "- **Fills use the bar's closing price** plus the percentage cost below. A real order would not get exactly "
          "that price; the cost figure is the allowance for it.", ""]
    archive = os.path.join(ROOT, "results", "archive")
    if os.path.isdir(archive) and os.listdir(archive):
        L += ["Earlier records, kept unchanged: " + ", ".join(f"`results/archive/{d}`" for d in sorted(os.listdir(archive))) + ".", ""]
    L += ["## Backtest: what these rules would have done in the past", "",
          "This is history, not evidence that the rules will work. Fees are included. \"Hold\" is simply buying the "
          "benchmark and doing nothing over the same period.", "",
          "| # | Strategy | Period | Total | Per year | Worst drop | Sharpe | Hold: total | Hold: worst drop | Hold: Sharpe | Trades | Fees per €10 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        if "backtest" not in r:
            L.append(f"| {i} | {r['name']} | {r.get('error', '')} | | | | | | | | | |")
            continue
        s, b = r["backtest"], r["benchmark_stats"]
        L.append(f"| {i} | {r['name']} | {s['start']} → {s['end']} | {pct(s['total_return'])} | {pct(s['cagr'])} | "
                 f"{pct(s['max_drawdown'])} | {s['sharpe']:.2f} | {pct(b['total_return'])} {r['benchmark']} | "
                 f"{pct(b['max_drawdown'])} | {b['sharpe']:.2f} | {r['trades']} | {eur(r['fees_paid'])} |")
    pf = portfolio(rows)
    if pf:
        L += ["", f"### All {pf['n']} daily strategies together, equal money in each", "",
              "| Portfolio | Per year | Worst drop | Volatility | Sharpe |", "|---|---|---|---|---|"]
        for label, key in (("The strategies", "strategies"), ("The strategies without Ether breakout", "without_eth"),
                           ("Each strategy's own benchmark, held", "own_benchmarks"),
                           ("Everything in the S&P 500 ETF", "spy")):
            s = pf[key]
            L.append(f"| {label} | {pct(s['cagr'])} | {pct(s['max_drawdown'])} | {pct(s['volatility'])[1:]} | {s['sharpe']:.2f} |")
        L += ["", "The combined result leans almost entirely on one strategy. Without Ether breakout the rest did "
              "not beat simply holding the S&P 500 ETF on a risk-adjusted basis."
              if pf["without_eth"]["sharpe"] < pf["spy"]["sharpe"] else
              "The second row shows how much of the combined result depends on the single best strategy."]
    L += ["", "### Consistency check: the same backtest in two halves", "",
          "This is **not** an out-of-sample test: both halves were already known when the rules were written. "
          "It only shows whether a result came from one lucky stretch. The only real out-of-sample evidence is the live record above.", "",
          f"| # | Strategy | Before {SPLIT_DATE[:4]}: strategy | hold | From {SPLIT_DATE[:4]}: strategy | hold | Beat hold in both? |",
          "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        if "halves" not in r:
            L.append(f"| {i} | {r['name']} | n/a | n/a | n/a | n/a | history too short |")
            continue
        (s1, b1), (s2, b2) = r["halves"]
        verdict = "is the benchmark" if r["id"] == "spy_hold" else ("yes" if s1 > b1 and s2 > b2 else "no")
        L.append(f"| {i} | {r['name']} | {pct(s1)} | {pct(b1)} | {pct(s2)} | {pct(b2)} | {verdict} |")
    L += ["", "![Backtest charts](charts/backtest.png)", "",
          "## Read this before believing any number above", "",
          "- **Past results do not predict future results.** A rule that worked in a backtest often stops working.",
          "- **Stock momentum still has some bias.** Its universe is the 12 largest US companies at the end of 2017, "
          "so it does not pick from today's winners. But 12 giants that all survived is a small and favourable sample.",
          "- **Options are model-priced.** There is no free historical options data, so strategies 9 and 10 use a "
          f"pricing formula with the VIX index as volatility, a {COST['option_haircut'] * 100:.0f}% spread haircut and a "
          "rough adjustment for calls. Real covered-call funds have lagged the index over this period.",
          "- **Futures and options cannot be traded at €10.** One futures contract needs thousands of euros of margin "
          "and one option contract covers 100 shares. The simulation allows fractions to show how the rule behaves.",
          "- **Day trading loses to fees.** The hourly Bitcoin rule trades hundreds of times, and each trade pays the fee. "
          "GitHub's scheduler can also run late, which delays its orders.",
          "- **Real fees at this size would be worse.** Costs are a percentage "
          f"({COST['crypto'] * 100:.2f}% crypto, {COST['equity'] * 100:.2f}% stocks/ETFs, "
          f"{COST['futures'] * 100:.2f}% futures per trade). A flat €1 broker fee on a €10 order is 10%.",
          "- **Currency:** US assets are converted to euros with the daily EUR/USD rate.",
          "- **No taxes, no interest on cash.**", "",
          "## How it works", "",
          "- `lab/strategies.py`: the ten rules. `lab/engine.py`: trade arithmetic and backtest. "
          "`lab/live.py`: the forward paper engine. `lab/run.py`: the scheduled job. `tests/`: checks, run before every update.",
          "- A decision made on one bar's closing price is executed on a later bar's closing price.",
          "- Prices come from Yahoo Finance via the `yfinance` library.",
          "- Run the backtest yourself: `pip install -r requirements.txt && python -m lab.run --offline` "
          "(outside GitHub Actions this never touches the live record).", ""]
    open(os.path.join(ROOT, "README.md"), "w").write("\n".join(L))


def commit_id():
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main():
    hourly_mode = "--mode" in sys.argv and sys.argv[sys.argv.index("--mode") + 1] == "hourly"
    official = os.environ.get("GITHUB_ACTIONS") == "true"
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    notes = []
    if "--offline" not in sys.argv:
        notes = data.refresh_hourly() if hourly_mode else data.refresh()
    daily, hourly = data.load()
    live_dir = live.LIVE_DIR
    if not official:  # a local run works on a throwaway copy and never changes the real record
        live_dir = os.path.join(tempfile.mkdtemp(), "live")
        if os.path.isdir(live.LIVE_DIR):
            shutil.copytree(live.LIVE_DIR, live_dir)
    only = {"btc_intraday"} if hourly_mode else None
    specs, benchmarks, errors = build(daily, hourly)
    state, events = live.process({k: v for k, v in specs.items() if not only or k in only}, benchmarks, now,
                                 commit_id(), live_dir=live_dir, snapshot=not hourly_mode)
    if hourly_mode and not events:
        print("hourly check: nothing to do")
        return
    age = (now - daily.index[-1]).days
    if age > 4:
        notes.append(f"Latest daily price is {age} days old.")
    if len(hourly) < 100:
        notes.append("No hourly Bitcoin prices available; the intraday strategy is not running.")
    rows = evaluate(specs, benchmarks, errors)
    charts(rows)
    readme(rows, state, notes, live_dir)
    slim = [{k: v for k, v in r.items() if k not in ("bt_eq", "bench_eq")} for r in rows]
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    json.dump({"updated": datetime.now(timezone.utc).isoformat(), "notes": notes, "backtests": slim,
               "portfolio_backtest": portfolio(rows)},
              open(os.path.join(ROOT, "results", "summary.json"), "w"), indent=1, default=str)
    for r in rows:
        v = state["strategies"].get(r["id"], {}).get("view", {})
        print(r["id"], r.get("error") or pct(r["backtest"]["total_return"]), v.get("value"), v.get("holding"))


if __name__ == "__main__":
    main()
