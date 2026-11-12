# Paper trading lab

**Simulated money only.** Ten rule-based strategies, each starting with an imaginary €10 on 2026-11-12. No broker is connected and no real order is ever placed. This is an experiment, not investment advice.

_Last updated: 2026-11-12 12:44 UTC. Updated automatically once a day by GitHub Actions._

## Live paper portfolio since 2026-11-12

**€40.00 simulated → €39.85 (-0.4%)**

| # | Strategy | Type | €10 is now | Change | Holding now |
|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | Crypto | €9.85 | -1.5% | BTC +100% |
| 2 | Ether 20-day breakout | Crypto | €10.00 | +0.0% | cash |
| 3 | Bitcoin intraday mean reversion (hourly) | Day trading | €9.97 | -0.3% | BTC +100% |
| 4 | S&P 500 ETF buy and hold (benchmark) | ETF | n/a | n/a | waiting for data |
| 5 | ETF rotation, top 2 of 5, monthly | ETF | n/a | n/a | waiting for data |
| 6 | Stock momentum, top 3 of 12, monthly | Stocks | n/a | n/a | waiting for data |
| 7 | Short-term mean reversion on S&P 500 ETF | ETF | n/a | n/a | waiting for data |
| 8 | Futures trend, S&P / gold / oil, long-short | Futures | €10.03 | +0.3% | ES +33%, GC -33%, BZ +33% |
| 9 | Covered call on S&P 500 ETF (model-priced) | Options | n/a | n/a | waiting for data |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | Options | n/a | n/a | waiting for data |

A strategy starts in whatever position its rule already held on the start date. A few days of results say nothing; judge this over months.

### Latest simulated trades

| Time (UTC) | Strategy | Action | Asset | Value | Fee |
|---|---|---|---|---|---|
| 2026-11-12 12:00 | Bitcoin intraday mean reversion (hourly) | BUY | BTC | €9.97 | €0.0299 |
| 2026-11-12 00:00 | Futures trend, S&P / gold / oil, long-short | SELL | GC | €0.03 | €0.0000 |
| 2026-11-12 00:00 | Futures trend, S&P / gold / oil, long-short | BUY | BZ | €6.68 | €0.0033 |

## Backtest: what these rules would have done in the past

Fees and slippage are included. "Hold" is what simply buying the same asset and doing nothing would have returned over the same period.

| # | Strategy | Period | Total | Per year | Worst drop | Sharpe | Hold: total | Hold: worst drop | Trades | Fees per €10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Bitcoin trend following (50/200-day) | 2018-01-01 → 2026-11-12 | +296.6% | +16.8% | -63.3% | 0.57 | +477.7% | -80.4% | 18 | €1.35 |
| 2 | Ether 20-day breakout | 2018-01-01 → 2026-11-12 | +2865.7% | +46.6% | -51.5% | 0.99 | +183.3% | -93.5% | 127 | €62.24 |
| 3 | Bitcoin intraday mean reversion (hourly) | 2024-11-13 → 2026-11-12 | -88.5% | -66.2% | -88.7% | -4.65 | -20.9% | -52.6% | 705 | €9.59 |
| 4 | S&P 500 ETF buy and hold (benchmark) | 2018-01-02 → 2026-11-11 | +247.2% | +15.1% | -33.1% | 0.80 | +247.2% | -33.1% | 0 | €0.00 |
| 5 | ETF rotation, top 2 of 5, monthly | 2018-01-02 → 2026-11-11 | +109.4% | +8.7% | -25.8% | 0.58 | +247.2% | -33.1% | 236 | €0.56 |
| 6 | Stock momentum, top 3 of 12, monthly | 2018-01-02 → 2026-11-11 | +1018.5% | +31.3% | -32.6% | 1.13 | +247.2% | -33.1% | 392 | €3.22 |
| 7 | Short-term mean reversion on S&P 500 ETF | 2018-01-02 → 2026-11-11 | +16.4% | +1.7% | -12.2% | 0.31 | +247.2% | -33.1% | 128 | €1.40 |
| 8 | Futures trend, S&P / gold / oil, long-short | 2018-01-02 → 2026-11-12 | -38.4% | -5.3% | -47.2% | -0.22 | +247.2% | -33.1% | 1053 | €1.03 |
| 9 | Covered call on S&P 500 ETF (model-priced) | 2018-01-02 → 2026-11-11 | +313.5% | +17.4% | -28.1% | 1.07 | +247.2% | -33.1% | 214 | €1.59 |
| 10 | Cash-secured put on S&P 500 ETF (model-priced) | 2018-01-02 → 2026-11-11 | +116.4% | +9.1% | -24.2% | 0.75 | +247.2% | -33.1% | 214 | €1.11 |

![Backtest charts](charts/backtest.png)

## Read this before believing any number above

- **Past results do not predict future results.** A rule that worked in a backtest often stops working.
- **Stock momentum is flattered by hindsight.** Its 12 stocks were picked today from companies that are already large, so the backtest only ever chooses among known winners.
- **Options are model-priced.** There is no free historical options data, so strategies 9 and 10 use a pricing formula with the VIX index as volatility and a 5% spread haircut. Real results would differ.
- **Futures at €10 are not possible in reality.** One contract needs thousands of euros of margin. The simulation allows fractions to show how the rule behaves. Prices are front-month series with roll gaps.
- **Real fees at this size would be worse.** Costs are modelled as a percentage (0.30% crypto, 0.10% stocks/ETFs, 0.05% futures per trade). A flat €1 broker fee on a €10 order is 10%.
- **Currency:** US assets are converted to euros with the daily EUR/USD rate, so results include currency moves.
- **No taxes, no interest on cash.**

## How it works

- `lab/strategies.py` holds the ten rules, `lab/engine.py` the simulator, `lab/run.py` the daily job.
- A decision made on one bar's closing price is executed on the next bar's closing price.
- Prices come from Yahoo Finance via the `yfinance` library and are cached in `data/`.
- Run it yourself: `pip install -r requirements.txt && python -m lab.run`
