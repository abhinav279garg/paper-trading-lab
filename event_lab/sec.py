"""Polite SEC client. The contact address comes from the SEC_CONTACT secret and is never written
to disk or printed."""
from __future__ import annotations

import os
import time

import requests


class Sec:
    def __init__(self, pause=0.2):
        contact = os.environ.get("SEC_CONTACT", "").strip()
        if not contact:
            raise SystemExit("SEC_CONTACT is not set")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": f"paper-trading-lab research {contact}",
                               "Accept-Encoding": "gzip, deflate"})
        self.pause, self.last, self.calls = pause, 0.0, 0

    def get(self, url, as_json=True, params=None):
        for attempt in range(6):
            wait = self.pause - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            self.calls += 1
            try:
                r = self.s.get(url, params=params, timeout=60)
            except requests.RequestException as exc:
                err = type(exc).__name__
                time.sleep(3 * (attempt + 1))
                continue
            if r.status_code == 200:
                return r.json() if as_json else r.text
            if r.status_code == 404:
                return None
            err = f"HTTP {r.status_code}"
            time.sleep(min(60, 5 * (attempt + 1) ** 2) if r.status_code in (403, 429) else 3 * (attempt + 1))
        raise RuntimeError(f"{err} for {url}")   # the URL only; request headers are never included
