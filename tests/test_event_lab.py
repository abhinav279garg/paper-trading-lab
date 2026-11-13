import numpy as np
import pandas as pd

from event_lab import core
from event_lab.config import HOLD_DAYS, sector_etf
from event_lab.links import find_evidence, html_to_text

DAYS = pd.bdate_range("2022-01-03", periods=400)


def _market(seed=1, names=("CUST", "SUP1", "SUP2", "DEC1", "DEC2", "DEC3", "SPY", "XLK", "XLY")):
    rng = np.random.default_rng(seed)
    adj = pd.DataFrame({n: 50 * np.exp(np.cumsum(rng.normal(0, 0.01, len(DAYS)))) for n in names}, index=DAYS)
    dv = pd.DataFrame(2e7, index=DAYS, columns=names)
    return adj, adj.copy(), dv


def _links():
    return pd.DataFrame([
        {"customer": "CUST", "supplier_cik": "1", "supplier": "SUP1", "sic": "3674", "pct": 30.0,
         "valid_from": pd.Timestamp("2022-03-01"), "valid_to": pd.Timestamp("2023-03-01"), "adsh": "a"},
        {"customer": "CUST", "supplier_cik": "2", "supplier": "SUP2", "sic": "3674", "pct": 12.0,
         "valid_from": pd.Timestamp("2022-09-01"), "valid_to": pd.Timestamp("2023-09-01"), "adsh": "b"}])


SECTOR = {"CUST": "XLY", "SUP1": "XLK", "SUP2": "XLK", "DEC1": "XLK", "DEC2": "XLK", "DEC3": "XLK",
          "SPY": "SPY", "XLK": "XLK", "XLY": "XLY"}
UNIVERSE = {"XLK": ["DEC1", "DEC2", "DEC3", "SUP1", "SUP2"]}


def test_timeline_never_enters_on_the_day_that_measures_the_trigger():
    d = DAYS[100]
    for stamp in (d + pd.Timedelta(hours=9), d + pd.Timedelta(hours=15, minutes=45)):
        prev, t1, t2, exit_ = core.timeline(stamp, DAYS)
        assert (prev, t1, t2, exit_) == (DAYS[99], DAYS[100], DAYS[101], DAYS[101 + HOLD_DAYS])
    prev, t1, t2, _ = core.timeline(d + pd.Timedelta(hours=15, minutes=46), DAYS)   # after the cutoff
    assert (prev, t1, t2) == (DAYS[100], DAYS[101], DAYS[102])
    saturday = pd.Timestamp("2022-06-04 10:00")
    prev, t1, t2, _ = core.timeline(saturday, DAYS)
    assert prev == pd.Timestamp("2022-06-03") and t1 == pd.Timestamp("2022-06-06") and t2 > t1
    assert core.timeline(DAYS[-3] + pd.Timedelta(hours=10), DAYS) is None      # window runs past the data


def test_links_start_after_filing_and_end_at_next_annual_report():
    rows = [{"customer": "WMT", "supplier_cik": "0000000009", "file_date": "2022-03-10", "pct": "20", "adsh": "x"}]
    filers = {"0000000009": {"ticker": "ABC.B", "sic": "2000", "tenk": ["2022-03-10", "2023-03-15"]},
              "ticker:WMT": {"cik": "0000104169"}}
    lk = core.build_links(rows, filers)
    assert lk.loc[0, "valid_from"] == pd.Timestamp("2022-03-11")
    assert lk.loc[0, "valid_to"] == pd.Timestamp("2023-03-16") and lk.loc[0, "supplier"] == "ABC-B"
    filers["ticker:WMT"]["cik"] = "0000000009"          # a company is never its own supplier
    assert core.build_links(rows, filers).empty


def test_a_link_disclosed_later_is_not_used_earlier_and_decoys_are_unlinked():
    adj, raw, dv = _market()
    early = type("E", (), {"customer": "CUST", "t1": pd.Timestamp("2022-06-01"), "t2": pd.Timestamp("2022-06-02"),
                           "trigger": 0.05})()
    direction, pairs = core.select(early, _links(), adj, raw, dv, SECTOR, UNIVERSE)
    assert direction == 1 and [p[0] for p in pairs] == ["SUP1"]           # SUP2's link is not known yet
    late = type("E", (), {"customer": "CUST", "t1": pd.Timestamp("2022-10-03"), "t2": pd.Timestamp("2022-10-04"),
                          "trigger": -0.05})()
    direction, pairs = core.select(late, _links(), adj, raw, dv, SECTOR, UNIVERSE)
    assert direction == -1 and [p[0] for p in pairs] == ["SUP1", "SUP2"]
    assert all(p[1].startswith("DEC") for p in pairs) and len({p[1] for p in pairs}) == 2


def test_short_rules_block_cheap_or_illiquid_shares_and_charge_borrow():
    adj, raw, dv = _market()
    raw["SUP1"] = 3.0                                    # under the minimum price for a short
    ev = type("E", (), {"customer": "CUST", "t1": pd.Timestamp("2022-10-03"), "t2": pd.Timestamp("2022-10-04"),
                        "exit": pd.Timestamp("2022-10-11"), "trigger": -0.05})()
    _, pairs = core.select(ev, _links(), adj, raw, dv, SECTOR, UNIVERSE)
    assert [p[0] for p in pairs] == ["SUP2"]
    ev.trigger = 0.05                                    # the same share may still be bought
    _, pairs = core.select(ev, _links(), adj, raw, dv, SECTOR, UNIVERSE)
    assert "SUP1" in [p[0] for p in pairs]
    g_long, n_long = core.trade_return("SUP2", ev, 1, 2e7, adj, SECTOR)
    g_short, n_short = core.trade_return("SUP2", ev, -1, 2e7, adj, SECTOR)
    assert abs(g_long + g_short) < 1e-12
    assert (g_short - n_short) > (g_long - n_long) > 0   # both pay trading costs, the short also pays borrow


def test_events_need_a_3_percent_move_and_outcomes_cannot_change_selection():
    adj, raw, dv = _market()
    i = 200
    adj.loc[DAYS[i]:, "CUST"] *= 1.08                    # an 8% jump on day i
    filings = {"CUST": [DAYS[i] + pd.Timedelta(hours=8), DAYS[50] + pd.Timedelta(hours=8)]}
    ev = core.customer_events(filings, adj, DAYS, SECTOR)
    assert len(ev) == 1 and ev.loc[0, "t1"] == DAYS[i] and ev.loc[0, "t2"] == DAYS[i + 1]
    pe1, tr1 = core.evaluate(ev, _links(), adj, raw, dv, SECTOR, UNIVERSE)
    adj2 = adj.copy()
    adj2.loc[DAYS[i + 2]:, ["SUP1", "SUP2", "DEC1", "DEC2", "DEC3"]] *= 3   # change everything after entry
    pe2, tr2 = core.evaluate(ev, _links(), adj2, raw, dv, SECTOR, UNIVERSE)
    assert list(tr1["supplier"]) == list(tr2["supplier"]) and list(tr1["decoy"]) == list(tr2["decoy"])
    assert core.evaluate(ev, _links(), adj, raw, dv, SECTOR, UNIVERSE, end="2022-06-01")[0].empty   # holdout stays sealed


def test_summary_counts_clusters_and_decision_rule():
    t1 = pd.to_datetime(["2023-01-02", "2023-01-03", "2023-02-06", "2023-03-06"])
    df = pd.DataFrame({"t1": t1, "sector": ["XLK", "XLK", "XLK", "XLY"], "diff": [0.01, 0.02, -0.01, 0.03]})
    s = core.summarize(df)
    assert s["events"] == 4 and s["clusters"] == 3 and s["low90"] <= s["mean"] <= s["high90"]
    assert core.decide({"events": 9, "mean": 0.004, "low90": 0.001, "high90": 0.007}, 0.0025) == "GO"
    assert core.decide({"events": 9, "mean": 0.0005, "low90": -0.002, "high90": 0.002}, 0.0025) == "STOP"
    assert core.decide({"events": 9, "mean": 0.004, "low90": -0.001, "high90": 0.009}, 0.0025) == "INCONCLUSIVE"
    good = {"events": 9, "mean": 0.004, "low90": 0.001, "high90": 0.007}
    assert core.decide(good, 0.0025, arm_a_mean=-0.001) == "INCONCLUSIVE"     # beats placebo but loses money
    assert core.decide(good, 0.0025, arm_a_mean=0.002) == "GO"


def test_evidence_must_name_the_customer_next_to_a_revenue_share():
    text = html_to_text("<p>Sales to Walmart Inc. accounted for approximately 21% of our net sales.</p>"
                        "<p>Apple accounted for 20% of the smartphone market.</p><p>walmart is large.</p>")
    assert find_evidence(text, "Walmart")[0] == 21.0
    assert find_evidence(text, "Apple") is None and find_evidence(text, "Wal") is None
    assert sector_etf("3674") == "XLK" and sector_etf(None) == "SPY"
