# Paper trading lab

**Simulated money only.** Ten rule-based strategies, each starting with an imaginary €10 on 2026-11-12. No broker is connected and no real order is ever placed. This is an experiment, not investment advice.

_Last updated: 2026-11-13 02:39 UTC. Updated automatically once a day by GitHub Actions._

## Live paper portfolio since 2026-11-12

**€100.00 simulated → €99.62 (-0.4%)**

| # | Strategy | Type | €10 is now | Change | Holding now |
|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | Crypto | €9.76 | -2.4% | BTC +100% |
| 2 | Ether 20-day breakout | Crypto | €10.00 | +0.0% | cash |
| 3 | Bitcoin intraday mean reversion (hourly) | Day trading | €9.73 | -2.7% | BTC +100% |
| 4 | S&P 500 ETF buy and hold (benchmark) | ETF | €10.03 | +0.3% | SPY +100% |
| 5 | ETF rotation, top 2 of 5, monthly | ETF | €10.02 | +0.2% | SPY +50%, EFA +50% |
| 6 | Stock momentum, top 3 of 12, monthly | Stocks | €10.13 | +1.3% | AAPL +35%, MSFT +34%, XOM +31% |
| 7 | Short-term mean reversion on S&P 500 ETF | ETF | €10.00 | +0.0% | cash |
| 8 | Futures trend, S&P / gold / oil, long-short | Futures | €9.94 | -0.6% | ES +33%, GC -33%, BZ +33% |
| 9 | Covered call on S&P 500 ETF (model-priced) | Options | €10.01 | +0.1% | shares + short call, strike 693.90, 19 trading days left |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | Options | €10.00 | +0.0% | cash + short put, strike 666.68, 19 trading days left |

A strategy starts in whatever position its rule already held on the start date. A few days of results say nothing; judge this over months.

### Latest simulated trades

| Time (UTC) | Strategy | Action | Asset | Value | Fee |
|---|---|---|---|---|---|
| 2026-11-12 12:00 | Bitcoin intraday mean reversion (hourly) | BUY | BTC | €9.97 | €0.0299 |
| 2026-11-12 00:00 | Futures trend, S&P / gold / oil, long-short | SELL | ES | €0.04 | €0.0000 |
| 2026-11-12 00:00 | Futures trend, S&P / gold / oil, long-short | SELL | GC | €0.03 | €0.0000 |
| 2026-11-12 00:00 | Futures trend, S&P / gold / oil, long-short | BUY | BZ | €6.78 | €0.0034 |

## Backtest: what these rules would have done in the past

Fees and slippage are included. "Hold" is what simply buying the same asset and doing nothing would have returned over the same period.

| # | Strategy | Period | Total | Per year | Worst drop | Sharpe | Hold: total | Hold: worst drop | Trades | Fees per €10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | 2018-01-01 → 2026-11-12 | +292.6% | +16.7% | -63.3% | 0.56 | +471.9% | -80.4% | 18 | €1.35 |
| 2 | Ether 20-day breakout | 2018-01-01 → 2026-11-12 | +2865.7% | +46.6% | -51.5% | 0.99 | +183.7% | -93.5% | 127 | €62.24 |
| 3 | Bitcoin intraday mean reversion (hourly) | 2024-11-13 → 2026-11-13 | -88.8% | -66.6% | -88.9% | -4.70 | -22.9% | -52.6% | 705 | €9.59 |
| 4 | S&P 500 ETF buy and hold (benchmark) | 2018-01-02 → 2026-11-12 | +248.2% | +15.1% | -33.1% | 0.80 | +248.2% | -33.1% | 0 | €0.00 |
| 5 | ETF rotation, top 2 of 5, monthly | 2018-01-02 → 2026-11-12 | +109.7% | +8.7% | -25.8% | 0.58 | +248.2% | -33.1% | 236 | €0.56 |
| 6 | Stock momentum, top 3 of 12, monthly | 2018-01-02 → 2026-11-12 | +510.3% | +22.7% | -30.5% | 0.95 | +248.2% | -33.1% | 397 | €2.10 |
| 7 | Short-term mean reversion on S&P 500 ETF | 2018-01-02 → 2026-11-12 | +16.4% | +1.7% | -12.2% | 0.31 | +248.2% | -33.1% | 128 | €1.40 |
| 8 | Futures trend, S&P / gold / oil, long-short | 2018-01-02 → 2026-11-12 | -39.0% | -5.4% | -47.2% | -0.23 | +248.2% | -33.1% | 1054 | €1.03 |
| 9 | Covered call on S&P 500 ETF (model-priced) | 2018-01-02 → 2026-11-12 | +203.2% | +13.3% | -28.8% | 0.85 | +248.2% | -33.1% | 214 | €1.03 |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | 2018-01-02 → 2026-11-12 | +116.5% | +9.1% | -24.2% | 0.75 | +248.2% | -33.1% | 214 | €1.11 |

### The same backtest, split in two halves

If a rule only worked in one half, its overall number is weak evidence.

| # | Strategy | Before 2022: strategy | hold | From 2022: strategy | hold | Beat hold in both halves? |
|---|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | +153.8% | +258.0% | +50.2% | +55.1% | no |
| 2 | Ether 20-day breakout | +1957.9% | +403.2% | +44.1% | -44.9% | yes |
| 3 | Bitcoin intraday mean reversion (hourly) | n/a | n/a | n/a | n/a | history too short |
| 4 | S&P 500 ETF buy and hold (benchmark) | +100.9% | +100.9% | +73.1% | +73.1% | is the benchmark |
| 5 | ETF rotation, top 2 of 5, monthly | +46.2% | +100.9% | +45.4% | +73.1% | no |
| 6 | Stock momentum, top 3 of 12, monthly | +169.8% | +100.9% | +125.5% | +73.1% | yes |
| 7 | Short-term mean reversion on S&P 500 ETF | +10.9% | +100.9% | +5.0% | +73.1% | no |
| 8 | Futures trend, S&P / gold / oil, long-short | -19.7% | +100.9% | -23.8% | +73.1% | no |
| 9 | Covered call on S&P 500 ETF (model-priced) | +81.6% | +100.9% | +66.9% | +73.1% | no |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | +47.9% | +100.9% | +46.4% | +73.1% | no |

![Backtest charts](charts/backtest.png)

## How the live record is kept honest

- **Rules frozen on 2026-11-12.** No parameter was tuned to fit the backtest (they are standard textbook values), and none will be changed. If a rule is ever changed, its live record restarts.
- **Append-only ledger.** Every simulated trade is written to `results/ledger.csv` and every daily value to `results/equity_log.csv` on the day it happens, and those rows are never rewritten. The git history of this repository timestamps each entry, so the record cannot be adjusted afterwards.
- **Judge it at 3 to 6 months**, against simply holding the S&P 500 ETF (strategy 4), not before.

## Read this before believing any number above

- **Past results do not predict future results.** A rule that worked in a backtest often stops working.
- **Stock momentum still has some bias.** Its universe is the 12 largest US companies at the end of 2017, so it no longer picks from today's winners. But 12 giants that all survived is a small and favourable sample.
- **Options are model-priced.** There is no free historical options data, so strategies 9 and 10 use a pricing formula with the VIX index as volatility and a 5% spread haircut, plus a rough adjustment for calls. The covered-call result in particular depends on that assumption; real covered-call funds have lagged the index over this period. Do not read it as beating buy and hold.
- **Day trading loses to fees.** The hourly Bitcoin rule trades hundreds of times, and each trade pays the fee.
- **Futures at €10 are not possible in reality.** One contract needs thousands of euros of margin. The simulation allows fractions to show how the rule behaves. Prices are front-month series with roll gaps.
- **Real fees at this size would be worse.** Costs are modelled as a percentage (0.30% crypto, 0.10% stocks/ETFs, 0.05% futures per trade). A flat €1 broker fee on a €10 order is 10%.
- **Currency:** US assets are converted to euros with the daily EUR/USD rate, so results include currency moves.
- **No taxes, no interest on cash.**

## How it works

- `lab/strategies.py` holds the ten rules, `lab/engine.py` the simulator, `lab/run.py` the daily job.
- A decision made on one bar's closing price is executed on the next bar's closing price.
- Prices come from Yahoo Finance via the `yfinance` library and are cached in `data/`.
- Run it yourself: `pip install -r requirements.txt && python -m lab.run`
