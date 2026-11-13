# Event intelligence experiment: specification

Version 1.0, 13 November 2026. Status: **specification only. Nothing in this document is built yet.**

Paper only. No broker connection, no real orders, no AI spend until Gates 0 and 1 pass.
The ten existing strategies in `lab/`, their rules and their records are not touched by this work.

## 1. The question

When a listed company (the *customer*) files news and its share price reacts, do the share prices of its
disclosed suppliers follow with a delay that is large enough to trade after costs? And if so, does an AI
that reads the filing add anything over a simple rule?

This is a test of a published effect (Cohen and Frazzini, 2008, customer–supplier return predictability).
That paper shows the effect existed in older data. It does not show that the specific rule below works
today. The purpose of Gates 0 and 1 is to find out cheaply, and to stop if it does not.

## 2. Timeline of one event (no step may use information from a later step)

| Mark | What happens | Rule |
|---|---|---|
| T0 | A customer's 8-K becomes available | Forward: the time our system first retrieved it. History: SEC acceptance time, pushed to the next trading day if accepted after 15:45 New York time or on a non-trading day |
| T1 | First regular market close after T0 | The trigger is measured here: customer return from the last close before T0 to the T1 close, minus its sector ETF over the same span |
| Commit | Signal recorded | Only after T1's close is final. Forward: written and committed to git before T2 |
| T2 | Entry | The close of the next trading day after T1. Never the T1 close |
| T2+5 | Exit | The close five trading days after T2 |

An event **qualifies** when the absolute trigger return at T1 is at least 3.0%.
The direction of the trade is the sign of the trigger return.

Consequence, stated openly: entering one full day after the reaction is conservative and will miss part of any effect.

## 3. Relationship graph (point in time)

- Source: annual reports (10-K) of supplier companies that name a customer in a revenue-concentration disclosure.
- Step 0 first tries the SEC's structured (XBRL) customer-concentration tags, then falls back to text. Whether the structured data names customers at useful scale is unknown and is part of the test.
- A link is **verified** only if the customer's name appears word for word in the cited sentence and resolves to exactly one listed company. The sentence, filing ID and acceptance time are stored with the link.
- A link is valid from the first trading day after the disclosing filing's acceptance until the supplier's next annual report. If that report repeats the link, it continues. If not, it ends.
- A link disclosed in a later filing is never applied to an earlier date.
- Many companies report a large customer without naming it. Those are counted and reported, not guessed.

## 4. The four arms

Every arm sees the same events, uses the same T0–T2+5 timeline, the same money per event split equally
across its chosen names, at most 5 names per event, and the same cost model.

| Arm | Candidate pool | Who chooses | Built in |
|---|---|---|---|
| Placebo | Decoys only | Rule: all decoys, same direction as the trigger | Step 1 |
| A | Verified suppliers only | Rule: all verified suppliers, same direction as the trigger | Step 1 |
| B | Verified suppliers and decoys, shuffled, unlabelled | AI reading the filing | After Gate 1 |
| C | The same pool, with link labels and evidence sentences | AI reading the filing | After Gate 1 |

- A **decoy** is a company in the same sector and size decile as a verified supplier with no known link to that customer in any filing seen up to that date. One decoy per supplier.
- B and C choose from an identical pool, so a difference between them comes from the graph information, not from a different set of allowed companies.
- B also yields a diagnostic: how often an unaided AI picks true suppliers over decoys.
- AI arms may abstain. Abstentions are recorded.

Comparisons:
- **A minus Placebo**: does the link effect exist at all? Tested on history in Step 1 (no AI involved, so no model-memory problem), then forward.
- **C minus A**: the primary forward metric. What AI adds on top of the rule.
- B and C are never backtested. A model already knows how past prices moved.

## 5. Measurement

- Return per trade: supplier return from T2 close to T2+5 close, minus its sector ETF over the same span, minus costs.
- Sector mapping: a fixed table from industry code to sector ETF, committed before any result exists.
- Costs per side, by supplier size: 0.10% (large), 0.25% (mid), 0.50% (small). Charged on entry and exit.
- **One observation is one customer event**: the average across that event's trades. Thirty suppliers reacting to one customer's results count once.
- Events from customers in the same sector in the same calendar week are treated as one cluster when computing uncertainty.

## 6. Gate 0: data feasibility (Step 0)

Reported for each year 2018–2026, using only links valid at the time:

| Measure | Pass level |
|---|---|
| Verified supplier–customer pairs | at least 150 |
| Distinct customer companies | at least 40 |
| Share of pairs belonging to the 5 largest customers | at most 40% |
| Sectors with at least 10 pairs | at least 4 |
| Independent qualifying events per year | at least 100 |
| Suppliers with usable price history | at least 80% of pairs |

- The last row is the survivorship check. The free price source drops most delisted companies. Every lost pair is counted. Below 80%, the history test is reported as biased and cannot pass Gate 1.
- Also reported: how many concentration disclosures were anonymous, and the expected number of forward events per year.
- Any row failing means **STOP**.

## 7. Gate 1: rules-only historical test (Step 1)

Pre-registration, in this order:
1. The rule is exactly as written in sections 2 to 5. One trigger level (3%), one holding period (5 days), all verified suppliers. No alternatives are tried to find a better one.
2. Development period 2018–2022: used to build and debug the pipeline. Its results are visible and are **not** evidence.
3. Holdout period 2023–2026: not looked at until the code is frozen. The evaluation runs once, in GitHub Actions, and writes its result together with the commit hash of the code that produced it. The commit that freezes the code precedes the commit that contains the result.
4. Diagnostics (1-day and 10-day holding, 2% and 5% triggers) are reported in a separate, labelled table and play no part in the decision.

Decision on the holdout, using the per-event difference A minus Placebo, with a 90% interval clustered as in section 5:

| Result | Decision |
|---|---|
| Lower bound above zero **and** average at least 0.25% per event after costs | **GO**: return with results before any AI spend |
| Upper bound below 0.25% | **STOP** |
| Anything else | **INCONCLUSIVE**: no AI spend by default. This is not proof that no edge exists |

A GO here means the effect was present in recent history. It is not proof of a tradable edge.

## 8. After Gate 1 (only if GO, and only with the owner's approval)

- **Gate 2, forward pilot, about 8 weeks.** All four arms record predictions. The pilot checks that timestamps and commits work and measures how often events occur. It does not judge profitability.
- Variance and clustering are measured from the pilot with the arm differences hidden. The required number of events and one interim check are then fixed and committed.
- **Gate 3, forward evaluation, hard cap 12 months.** Primary metric: C minus A, five-day, sector-adjusted, after costs. Outcomes: GO, STOP for futility, or INCONCLUSIVE (stop spending).
- AI spending halts automatically at €80 in any month.

## 9. Integrity rules

- Three times are stored for every forward filing: SEC acceptance, our first retrieval, prediction commit.
- Prediction files are append-only. The build fails if an existing row changes or disappears.
- Every record carries the code hash, and for AI arms the prompt hash and exact model version. Any change starts a new version and archives the old record unchanged (the mechanism already used in `lab/live.py`).
- AI arms receive the filing text and the candidate pool only. No web access, no tools. Output must match a fixed schema and choose only from the pool. Filing text is treated as untrusted input.
- **Reproducibility:** every number in a decision report must be regenerated by one command from committed code and data. No hand-entered figures.

## 10. Costs and limits, stated plainly

- Steps 0 and 1 use no paid AI service. They are not free: they use GitHub Actions compute and engineering time.
- Price data comes from an unofficial free source with personal-use terms and incomplete coverage of delisted companies. It is adequate for a first screen and not for a final claim.
- Raw price files for this experiment will not be committed to the public repository; only derived results will. (The existing lab currently commits a small price cache. That should be moved out of the repository as a separate change.)
- SEC rules require automated requests to identify themselves with a contact address. Steps 0 and 1 cannot start until the owner authorises one.

## 11. Decision report (end of Step 1)

1. Verified relationships and independent events, by year.
2. Data quality: anonymous disclosures, lost pairs, leakage-test results.
3. Arm A against Placebo and against sector benchmarks, after costs, holdout only.
4. Uncertainty interval and economic size.
5. Expected forward events per year.
6. GO, STOP or INCONCLUSIVE.

## 12. Change log

- 1.0: first version. Incorporates the timing correction (trigger fully observed before the signal is recorded), the expanded feasibility gate, matched candidate pools, and a pre-registered holdout.
