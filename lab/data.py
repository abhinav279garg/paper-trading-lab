"""Price download with an on-disk cache. If a download fails, the cached prices are used and the
report says how old they are."""
from __future__ import annotations

import os
import time

import pandas as pd

from .config import ALREADY_EUR, DOWNLOAD_START, NOT_A_PRICE, SYMBOLS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DAILY, HOURLY = os.path.join(DATA_DIR, "daily.csv"), os.path.join(DATA_DIR, "btc_hourly.csv")


def _read(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
    return df


def _download(symbols, **kw):
    import yfinance as yf
    last = None
    for attempt in range(3):
        try:
            raw = yf.download(symbols, auto_adjust=True, progress=False, threads=False, **kw)
            close = raw["Close"] if "Close" in raw else pd.DataFrame()
            if isinstance(close, pd.Series):
                close = close.to_frame(symbols if isinstance(symbols, str) else symbols[0])
            close = close.dropna(how="all")
            if len(close):
                close.index = pd.to_datetime(close.index, utc=True).tz_localize(None)
                return close
        except Exception as exc:  # network or provider error: fall back to the cache
            last = exc
        time.sleep(5 * (attempt + 1))
    print("download failed:", symbols if isinstance(symbols, str) else len(symbols), last)
    return pd.DataFrame()


def refresh():
    """Download fresh prices and merge them into the cache. Returns a list of notes."""
    os.makedirs(DATA_DIR, exist_ok=True)
    notes = []
    fresh = _download(list(SYMBOLS.values()), start=DOWNLOAD_START)
    if len(fresh):
        fresh = fresh.rename(columns={v: k for k, v in SYMBOLS.items()})
        fresh.index = fresh.index.normalize()
        fresh = fresh.groupby(level=0).last()
        merged = fresh.combine_first(_read(DAILY)).sort_index()
        merged.to_csv(DAILY, float_format="%.6g")
        missing = [k for k in SYMBOLS if k not in fresh.columns or fresh[k].dropna().empty]
        if missing:
            notes.append("No fresh daily prices for: " + ", ".join(missing))
    else:
        notes.append("Daily price download failed; using cached prices.")
    return notes + refresh_hourly()


def refresh_hourly():
    os.makedirs(DATA_DIR, exist_ok=True)
    hourly = _download("BTC-EUR", period="730d", interval="1h")
    if len(hourly):
        hourly.columns = ["BTC"]
        merged = hourly.combine_first(_read(HOURLY)).sort_index()
        merged.to_csv(HOURLY, float_format="%.8g")
        return []
    return ["Hourly Bitcoin download failed; using cached prices."]


def load():
    """Returns (daily prices in EUR, hourly BTC in EUR)."""
    raw = _read(DAILY)
    if raw.empty:
        raise SystemExit("No price data available (download failed and cache is empty).")
    fx = raw["EURUSD"].ffill()
    d = pd.DataFrame(index=raw.index)
    for col in raw.columns:
        if col in NOT_A_PRICE:
            d[col] = raw[col]
        elif col in ALREADY_EUR:
            d[col] = raw[col]
        else:
            d[col] = raw[col] / fx
    price_cols = [c for c in d.columns if c != "EURUSD"]
    d[price_cols] = d[price_cols].where(d[price_cols] > 0)
    # Never act on an unfinished bar: crypto days close at 00:00 UTC, US markets by about 21:30 UTC.
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    today = now.normalize()
    if today in d.index:
        unfinished = [c for c in d.columns if c in ALREADY_EUR or now.hour * 60 + now.minute < 21 * 60 + 30]
        d.loc[today, unfinished] = float("nan")
    hourly = _read(HOURLY)
    hourly = hourly[hourly.index <= now.floor("h") - pd.Timedelta(hours=1)]
    return d, (hourly["BTC"] if "BTC" in hourly else pd.Series(dtype=float))
