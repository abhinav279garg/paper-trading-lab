# Paper trading lab

**Simulated money only.** Ten rule-based strategies, each starting with an imaginary €10. No broker is connected and no real order is ever placed. This is an experiment, not investment advice.

_Last updated: 2026-11-22 07:21 UTC. Updated automatically by GitHub Actions._

## Live paper portfolio (record started 2026-11-13 03:54 UTC)

**Strategies: €100.00 → €95.24 (-4.8%)**  
**Just holding each benchmark: €100.00 → €89.83 (-10.2%)**

| # | Strategy | €10 is now | Hold instead | Holding now | Waiting order | Fills |
|---|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | €8.76 (-12.4%) | €8.42 BTC | BTC +100% |  | 1 |
| 2 | Ether 20-day breakout | €10.00 (+0.0%) | €8.40 ETH | cash |  | 0 |
| 3 | Bitcoin intraday mean reversion (hourly) | €9.74 (-2.6%) | €8.50 BTC | cash |  | 13 |
| 4 | S&P 500 ETF buy and hold (benchmark) | €9.20 (-8.0%) | €9.22 SPY | SPY +100% |  | 1 |
| 5 | ETF rotation, top 2 of 5, monthly | €9.24 (-7.6%) | €9.22 SPY | EFA +50%, SPY +50% |  | 1 |
| 6 | Stock momentum, top 3 of 12, monthly | €9.50 (-5.0%) | €9.22 SPY | AAPL +34%, JNJ +33%, MSFT +33% |  | 1 |
| 7 | Short-term mean reversion on S&P 500 ETF | €9.63 (-3.7%) | €9.22 SPY | SPY +100% |  | 1 |
| 8 | Futures trend, S&P / gold / oil, long-short | €10.49 (+4.9%) | €9.22 SPY | BZ -33%, ES -32%, GC -33% |  | 4 |
| 9 | Covered call on S&P 500 ETF (model-priced) | €9.27 (-7.3%) | €9.22 SPY | shares + short call, strike 696.33, 15 trading days left |  | 1 |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | €9.40 (-6.0%) | €9.22 SPY | cash + short put, strike 669.02, 15 trading days left |  | 1 |

Risk-adjusted comparison (Sharpe, worst drop) appears once 30 daily values are recorded (6 so far).

Each strategy started in cash. "Hold instead" is €10 put into that strategy's benchmark at the same moment. Judge a strategy by its number of fills and its result against that benchmark, not by elapsed time alone: a monthly rule produces about 12 decisions a year.

### Latest fills

| Order | Bar closed (UTC) | Action | Asset | Price | Value | Fee |
|---|---|---|---|---|---|---|
| btc_intraday-00015 | 2026-11-21 18:00 | SELL | BTC | 54,803.2190 | €9.77 | €0.0293 |
| btc_intraday-00014 | 2026-11-21 08:00 | SELL | BTC | 52,923.6290 | €0.00 | €0.0000 |
| btc_intraday-00013 | 2026-11-20 21:00 | BUY | BTC | 53,268.6720 | €9.50 | €0.0285 |
| btc_intraday-00012 | 2026-11-20 12:00 | SELL | BTC | 56,358.2110 | €9.56 | €0.0287 |
| futures_trend-00004 | 2026-11-19 21:30 | SELL | BZ | 81.8356 | €6.86 | €0.0034 |
| futures_trend-00004 | 2026-11-19 21:30 | SELL | GC | 3,212.0853 | €0.26 | €0.0001 |
| futures_trend-00004 | 2026-11-19 21:30 | SELL | ES | 6,526.8410 | €0.18 | €0.0001 |
| spy_rsi2-00002 | 2026-11-19 21:30 | BUY | SPY | 652.4517 | €9.99 | €0.0100 |
| btc_intraday-00011 | 2026-11-20 03:00 | BUY | BTC | 56,708.0000 | €9.62 | €0.0288 |
| btc_intraday-00010 | 2026-11-19 08:00 | SELL | BTC | 57,993.3910 | €9.67 | €0.0290 |
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
| 1 | Bitcoin trend following (50/200-day) | 2018-01-01 → 2026-11-21 | +230.8% | +14.4% | -63.3% | 0.52 | +381.8% BTC | -80.4% | 0.60 | 18 | €1.35 |
| 2 | Ether 20-day breakout | 2018-01-01 → 2026-11-21 | +2865.7% | +46.4% | -51.5% | 0.99 | +138.4% ETH | -93.5% | 0.54 | 127 | €62.24 |
| 3 | Bitcoin intraday mean reversion (hourly) | 2024-11-13 → 2026-11-22 | -88.9% | -66.2% | -89.8% | -4.49 | -35.1% BTC | -52.8% | -0.26 | 724 | €9.65 |
| 4 | S&P 500 ETF buy and hold (benchmark) | 2018-01-02 → 2026-11-20 | +220.9% | +14.0% | -33.1% | 0.75 | +220.9% SPY | -33.1% | 0.75 | 0 | €0.00 |
| 5 | ETF rotation, top 2 of 5, monthly | 2018-01-02 → 2026-11-20 | +56.6% | +5.2% | -34.0% | 0.36 | +220.9% SPY | -33.1% | 0.75 | 228 | €0.49 |
| 6 | Stock momentum, top 3 of 12, monthly | 2018-01-02 → 2026-11-20 | +466.0% | +21.6% | -29.9% | 0.91 | +220.9% SPY | -33.1% | 0.75 | 398 | €2.05 |
| 7 | Short-term mean reversion on S&P 500 ETF | 2018-01-02 → 2026-11-20 | +12.1% | +1.3% | -12.2% | 0.23 | +220.9% SPY | -33.1% | 0.75 | 129 | €1.41 |
| 8 | Futures trend, S&P / gold / oil, long-short | 2018-01-02 → 2026-11-20 | -36.8% | -5.0% | -47.2% | -0.20 | +220.9% SPY | -33.1% | 0.75 | 1060 | €1.03 |
| 9 | Covered call on S&P 500 ETF (model-priced) | 2018-01-02 → 2026-11-20 | +181.8% | +12.4% | -28.8% | 0.79 | +220.9% SPY | -33.1% | 0.75 | 214 | €1.03 |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | 2018-01-02 → 2026-11-20 | +104.1% | +8.4% | -24.2% | 0.69 | +220.9% SPY | -33.1% | 0.75 | 214 | €1.11 |

### All 9 daily strategies together, equal money in each

| Portfolio | Per year | Worst drop | Volatility | Sharpe |
|---|---|---|---|---|
| The strategies | +20.9% | -34.4% | 26.2% | 0.86 |
| The strategies without Ether breakout | +10.9% | -24.6% | 15.9% | 0.73 |
| Each strategy's own benchmark, held | +14.0% | -41.2% | 26.4% | 0.63 |
| Everything in the S&P 500 ETF | +14.0% | -33.1% | 20.1% | 0.75 |

The combined result leans almost entirely on one strategy. Without Ether breakout the rest did not beat simply holding the S&P 500 ETF on a risk-adjusted basis.

### Consistency check: the same backtest in two halves

This is **not** an out-of-sample test: both halves were already known when the rules were written. It only shows whether a result came from one lucky stretch. The only real out-of-sample evidence is the live record above.

| # | Strategy | Before 2022: strategy | hold | From 2022: strategy | hold | Beat hold in both? |
|---|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | +153.8% | +258.0% | +26.6% | +30.7% | no |
| 2 | Ether 20-day breakout | +1957.9% | +403.2% | +44.1% | -53.7% | yes |
| 3 | Bitcoin intraday mean reversion (hourly) | n/a | n/a | n/a | n/a | history too short |
| 4 | S&P 500 ETF buy and hold (benchmark) | +100.9% | +100.9% | +59.5% | +59.5% | is the benchmark |
| 5 | ETF rotation, top 2 of 5, monthly | +14.0% | +100.9% | +39.0% | +59.5% | no |
| 6 | Stock momentum, top 3 of 12, monthly | +156.4% | +100.9% | +120.1% | +59.5% | yes |
| 7 | Short-term mean reversion on S&P 500 ETF | +10.9% | +100.9% | +1.1% | +59.5% | no |
| 8 | Futures trend, S&P / gold / oil, long-short | -19.7% | +100.9% | -21.1% | +59.5% | no |
| 9 | Covered call on S&P 500 ETF (model-priced) | +81.6% | +100.9% | +55.1% | +59.5% | no |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | +47.9% | +100.9% | +38.0% | +59.5% | no |

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
