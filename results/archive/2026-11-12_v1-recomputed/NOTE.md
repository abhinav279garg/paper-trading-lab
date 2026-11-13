First live record, 12 to 13 November 2026. Kept unchanged.

In this version trades were recomputed from price history on each run and then written down,
so an entry could be recorded hours after the bar it traded on. It was replaced by the forward
engine in `lab/live.py`, which records every order before the price it fills at exists.
