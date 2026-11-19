# Paper trading lab

**Simulated money only.** Ten rule-based strategies, each starting with an imaginary €10. No broker is connected and no real order is ever placed. This is an experiment, not investment advice.

_Last updated: 2026-11-19 07:50 UTC. Updated automatically by GitHub Actions._

## Live paper portfolio (record started 2026-11-13 03:54 UTC)

**Strategies: €100.00 → €97.81 (-2.2%)**  
**Just holding each benchmark: €100.00 → €94.98 (-5.0%)**

| # | Strategy | €10 is now | Hold instead | Holding now | Waiting order | Fills |
|---|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | €9.18 (-8.2%) | €8.83 BTC | BTC +100% |  | 1 |
| 2 | Ether 20-day breakout | €10.00 (+0.0%) | €8.86 ETH | cash |  | 0 |
| 3 | Bitcoin intraday mean reversion (hourly) | €9.69 (-3.1%) | €9.15 BTC | BTC +100% | yes | 7 |
| 4 | S&P 500 ETF buy and hold (benchmark) | €9.72 (-2.8%) | €9.73 SPY | SPY +100% |  | 1 |
| 5 | ETF rotation, top 2 of 5, monthly | €9.69 (-3.1%) | €9.73 SPY | EFA +50%, SPY +50% |  | 1 |
| 6 | Stock momentum, top 3 of 12, monthly | €9.75 (-2.5%) | €9.73 SPY | AAPL +34%, JNJ +33%, MSFT +33% |  | 1 |
| 7 | Short-term mean reversion on S&P 500 ETF | €10.00 (+0.0%) | €9.73 SPY | cash | yes | 0 |
| 8 | Futures trend, S&P / gold / oil, long-short | €10.19 (+1.9%) | €9.73 SPY | BZ +34%, ES -33%, GC -33% | yes | 3 |
| 9 | Covered call on S&P 500 ETF (model-priced) | €9.76 (-2.4%) | €9.73 SPY | shares + short call, strike 696.33, 17 trading days left |  | 1 |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | €9.83 (-1.7%) | €9.73 SPY | cash + short put, strike 669.02, 17 trading days left |  | 1 |

Risk-adjusted comparison (Sharpe, worst drop) appears once 30 daily values are recorded (4 so far).

Each strategy started in cash. "Hold instead" is €10 put into that strategy's benchmark at the same moment. Judge a strategy by its number of fills and its result against that benchmark, not by elapsed time alone: a monthly rule produces about 12 decisions a year.

### Orders waiting to be filled

Recorded now, filled at the close of the next finished price bar.

| Order | Recorded (UTC) | Instruction |
|---|---|---|
| btc_intraday-00010 | 2026-11-19 07:49 | all cash |
| futures_trend-00004 | 2026-11-19 03:33 | BZ -33%, ES -33%, GC -33% |
| spy_rsi2-00002 | 2026-11-19 03:33 | SPY +100% |

### Latest fills

| Order | Bar closed (UTC) | Action | Asset | Price | Value | Fee |
|---|---|---|---|---|---|---|
| futures_trend-00003 | 2026-11-18 21:30 | BUY | BZ | 80.9068 | €6.53 | €0.0033 |
| futures_trend-00003 | 2026-11-18 21:30 | SELL | GC | 3,374.0869 | €0.14 | €0.0001 |
| futures_trend-00003 | 2026-11-18 21:30 | SELL | ES | 6,700.9160 | €6.66 | €0.0033 |
| btc_intraday-00009 | 2026-11-18 21:00 | BUY | BTC | 56,989.6290 | €9.51 | €0.0285 |
| futures_trend-00002 | 2026-11-17 21:30 | SELL | BZ | 84.3956 | €6.53 | €0.0033 |
| futures_trend-00002 | 2026-11-17 21:30 | SELL | GC | 3,448.8371 | €0.03 | €0.0000 |
| futures_trend-00002 | 2026-11-17 21:30 | BUY | ES | 6,709.7343 | €0.03 | €0.0000 |
| btc_intraday-00008 | 2026-11-18 03:00 | SELL | BTC | 58,480.8400 | €9.56 | €0.0287 |
| btc_intraday-00007 | 2026-11-17 21:00 | BUY | BTC | 58,080.0780 | €9.50 | €0.0285 |
| btc_intraday-00005 | 2026-11-15 07:00 | SELL | BTC | 58,600.0120 | €9.55 | €0.0287 |
| btc_intraday-00003 | 2026-11-14 07:00 | BUY | BTC | 61,119.0200 | €9.97 | €0.0299 |
| stock_momentum-00001 | 2026-11-13 21:30 | BUY | JNJ | 258.5926 | €3.33 | €0.0033 |
| stock_momentum-00001 | 2026-11-13 21:30 | BUY | MSFT | 474.0910 | €3.33 | €0.0033 |
| stock_momentum-00001 | 2026-11-13 21:30 | BUY | AAPL | 322.4105 | €3.33 | €0.0033 |
| cash_secured_put-00001 | 2026-11-13 21:30 | SELL | SPY put 669.02 | 8.7113 | €0.13 | €0.0069 |
| covered_call-00001 | 2026-11-13 21:30 | SELL | SPY call 696.33 | 6.9548 | €0.10 | €0.0054 |
| futures_trend-00001 | 2026-11-13 21:30 | BUY | BZ | 86.9487 | €3.33 | €0.0017 |
| futures_trend-00001 | 2026-11-13 21:30 | SELL | GC | 3,518.1264 | €3.33 | €0.0017 |
| futures_trend-00001 | 2026-11-13 21:30 | BUY | ES | 6,842.4101 | €3.33 | €0.0017 |
| etf_rotation-00001 | 2026-11-13 21:30 | BUY | EFA | 94.2698 | €5.00 | €0.0050 |

## How the live record is kept honest

- **Orders are written down before they can be filled.** Each run first fills earlier orders at the close of the first price bar that finished *after* the order was recorded, then records new orders. The order is committed to git before the price it fills at exists. See `results/live/orders.csv` and `fills.csv`.
- **Nothing live is recomputed from history.** Positions and cash are carried forward in `results/live/state.json`. If a run is missed, the order simply fills later, as it would for a real bot that was down.
- **Rule version `a1ef7b38b459`.** Every order, fill and daily value carries this hash of the rule code and the git commit that produced it. If the rule code changes at all, the hash changes, the current record is moved untouched to `results/archive/` and a new record starts from €10. This is enforced by the code, not by a promise.
- **This record started from commit [`da814c3`](https://github.com/abhinav279garg/paper-trading-lab/commit/da814c3bc112db9c2695dbc6b29c245439dd2e6c).**
- **Fills use the bar's closing price** plus the percentage cost below. A real order would not get exactly that price; the cost figure is the allowance for it.

Earlier records, kept unchanged: `results/archive/2026-11-12_v1-recomputed`.

## Backtest: what these rules would have done in the past

This is history, not evidence that the rules will work. Fees are included. "Hold" is simply buying the benchmark and doing nothing over the same period.

| # | Strategy | Period | Total | Per year | Worst drop | Sharpe | Hold: total | Hold: worst drop | Hold: Sharpe | Trades | Fees per €10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | 2018-01-01 → 2026-11-18 | +246.6% | +15.0% | -63.3% | 0.53 | +404.8% BTC | -80.4% | 0.61 | 18 | €1.35 |
| 2 | Ether 20-day breakout | 2018-01-01 → 2026-11-18 | +2865.7% | +46.5% | -51.5% | 0.99 | +151.4% ETH | -93.5% | 0.54 | 127 | €62.24 |
| 3 | Bitcoin intraday mean reversion (hourly) | 2024-11-13 → 2026-11-19 | -89.0% | -66.5% | -89.7% | -4.61 | -30.1% BTC | -52.6% | -0.18 | 718 | €9.63 |
| 4 | S&P 500 ETF buy and hold (benchmark) | 2018-01-02 → 2026-11-18 | +239.0% | +14.7% | -33.1% | 0.79 | +239.0% SPY | -33.1% | 0.79 | 0 | €0.00 |
| 5 | ETF rotation, top 2 of 5, monthly | 2018-01-02 → 2026-11-18 | +64.2% | +5.7% | -34.0% | 0.39 | +239.0% SPY | -33.1% | 0.79 | 228 | €0.49 |
| 6 | Stock momentum, top 3 of 12, monthly | 2018-01-02 → 2026-11-18 | +480.4% | +21.9% | -29.9% | 0.92 | +239.0% SPY | -33.1% | 0.79 | 398 | €2.05 |
| 7 | Short-term mean reversion on S&P 500 ETF | 2018-01-02 → 2026-11-18 | +16.4% | +1.7% | -12.2% | 0.31 | +239.0% SPY | -33.1% | 0.79 | 128 | €1.40 |
| 8 | Futures trend, S&P / gold / oil, long-short | 2018-01-02 → 2026-11-18 | -39.6% | -5.5% | -47.2% | -0.23 | +239.0% SPY | -33.1% | 0.79 | 1057 | €1.03 |
| 9 | Covered call on S&P 500 ETF (model-priced) | 2018-01-02 → 2026-11-18 | +196.6% | +13.0% | -28.8% | 0.83 | +239.0% SPY | -33.1% | 0.79 | 214 | €1.03 |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | 2018-01-02 → 2026-11-18 | +113.3% | +8.9% | -24.2% | 0.73 | +239.0% SPY | -33.1% | 0.79 | 214 | €1.11 |

### All 9 daily strategies together, equal money in each

| Portfolio | Per year | Worst drop | Volatility | Sharpe |
|---|---|---|---|---|
| The strategies | +21.2% | -34.4% | 26.2% | 0.86 |
| The strategies without Ether breakout | +11.4% | -24.6% | 15.9% | 0.76 |
| Each strategy's own benchmark, held | +14.7% | -41.2% | 26.3% | 0.65 |
| Everything in the S&P 500 ETF | +14.7% | -33.1% | 20.1% | 0.79 |

The combined result leans almost entirely on one strategy. Without Ether breakout the rest did not beat simply holding the S&P 500 ETF on a risk-adjusted basis.

### Consistency check: the same backtest in two halves

This is **not** an out-of-sample test: both halves were already known when the rules were written. It only shows whether a result came from one lucky stretch. The only real out-of-sample evidence is the live record above.

| # | Strategy | Before 2022: strategy | hold | From 2022: strategy | hold | Beat hold in both? |
|---|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | +153.8% | +258.0% | +32.6% | +36.9% | no |
| 2 | Ether 20-day breakout | +1957.9% | +403.2% | +44.1% | -51.2% | yes |
| 3 | Bitcoin intraday mean reversion (hourly) | n/a | n/a | n/a | n/a | history too short |
| 4 | S&P 500 ETF buy and hold (benchmark) | +100.9% | +100.9% | +68.5% | +68.5% | is the benchmark |
| 5 | ETF rotation, top 2 of 5, monthly | +14.0% | +100.9% | +45.7% | +68.5% | no |
| 6 | Stock momentum, top 3 of 12, monthly | +156.4% | +100.9% | +125.6% | +68.5% | yes |
| 7 | Short-term mean reversion on S&P 500 ETF | +10.9% | +100.9% | +5.0% | +68.5% | no |
| 8 | Futures trend, S&P / gold / oil, long-short | -19.7% | +100.9% | -24.6% | +68.5% | no |
| 9 | Covered call on S&P 500 ETF (model-priced) | +81.6% | +100.9% | +63.3% | +68.5% | no |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | +47.9% | +100.9% | +44.2% | +68.5% | no |

![Backtest charts](charts/backtest.png)

## Read this before believing any number above

- **Past results do not predict future results.** A rule that worked in a backtest often stops working.
- **Stock momentum still has some bias.** Its universe is the 12 largest US companies at the end of 2017, so it does not pick from today's winners. But 12 giants that all survived is a small and favourable sample.
- **Options are model-priced.** There is no free historical options data, so strategies 9 and 10 use a pricing formula with the VIX index as volatility, a 5% spread haircut and a rough adjustment for calls. Real covered-call funds have lagged the index over this period.
- **Futures and options cannot be traded at €10.** One futures contract needs thousands of euros of margin and one option contract covers 100 shares. The simulation allows fractions to show how the rule behaves.
- **Day trading loses to fees.** The hourly Bitcoin rule trades hundreds of times, and each trade pays the fee. GitHub's scheduler can also run late, which delays its orders.
- **Real fees at this size would be worse.** Costs are a percentage (0.30% crypto, 0.10% stocks/ETFs, 0.05% futures per trade). A flat €1 broker fee on a €10 order is 10%.
- **Currency:** US assets are converted to euros with the daily EUR/USD rate.
- **No taxes, no interest on cash.**

## How it works

- `lab/strategies.py`: the ten rules. `lab/engine.py`: trade arithmetic and backtest. `lab/live.py`: the forward paper engine. `lab/run.py`: the scheduled job. `tests/`: checks, run before every update.
- A decision made on one bar's closing price is executed on a later bar's closing price.
- Prices come from Yahoo Finance via the `yfinance` library.
- Run the backtest yourself: `pip install -r requirements.txt && python -m lab.run --offline` (outside GitHub Actions this never touches the live record).
