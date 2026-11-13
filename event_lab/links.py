"""Step 0a: find annual reports that name a customer, and keep a link only when the customer's name
appears word for word next to a revenue-concentration figure."""
from __future__ import annotations

import csv
import html
import os
import re
import time

from .config import CUSTOMERS, HISTORY_START, PHRASES

WORK = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results", "event_lab", "work")
HITS, LINKS, DONE = (os.path.join(WORK, n) for n in ("hits.csv", "links.csv", "docs_done.txt"))
QUERIES_DONE = os.path.join(WORK, "queries_done.txt")
HIT_FIELDS = ["customer", "alias", "cik", "adsh", "file", "file_date", "sic", "name"]
LINK_FIELDS = ["customer", "alias", "supplier_cik", "adsh", "file", "file_date", "sic", "supplier_name",
               "pct", "evidence"]
VERB = r"(?i:accounted\s+for|represented|comprised|constituted)"
QUAL = r"(?i:approximately\s+|about\s+|nearly\s+|more\s+than\s+|over\s+|roughly\s+)?"
PCT = r"(\d{1,3}(?:\.\d+)?)\s?%"
REV = r"(?i:net\s+sales|sales|revenues?|net\s+revenues?|accounts\s+receivable)"


def html_to_text(doc: str) -> str:
    doc = re.sub(r"(?is)<ix:header.*?</ix:header>", " ", doc)
    doc = re.sub(r"(?is)<(script|style).*?</\1>", " ", doc)
    doc = re.sub(r"(?i)</(p|div|tr|td|th|li|h\d|table)>|<br\s*/?>", " \n ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    doc = html.unescape(doc).replace("\xa0", " ").replace("’", "'")
    return re.sub(r"[ \t\r\f\v]+", " ", doc)


def find_evidence(text: str, alias: str):
    """Returns (percent, sentence) if the text states that the named customer made up a share of
    sales/revenue, else None. The name must appear exactly (case-sensitive, whole word)."""
    text = re.sub(r"\b(Inc|Corp|Co|Cos|Ltd|LLC|L\.P|U\.S|No)\.", lambda m: m.group(1).replace(".", ""), text)
    a = r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])"
    patterns = [
        a + r"[^.;\n]{0,120}?\b" + VERB + r"\s+" + QUAL + PCT + r"[^.;\n]{0,120}?\b" + REV,
        r"\b" + REV + r"\s+(?:to|from)\s+[^.;\n]{0,40}?" + a + r"[^.;\n]{0,100}?\b(?:" + VERB + r"|were|was|of)\s+"
        + QUAL + PCT,
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            pct = float(m.group(1))
            if 5 <= pct <= 100:
                lo, hi = max(0, m.start() - 80), min(len(text), m.end() + 120)
                return pct, " ".join(text[lo:hi].split())
    return None


def _read(path):
    return list(csv.DictReader(open(path, encoding="utf-8"))) if os.path.exists(path) else []


def _append(path, fields, rows):
    fresh = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if fresh:
            w.writeheader()
        w.writerows(rows)


def discover(sec, deadline):
    """Full-text search for every (customer name, phrase). Resumable. Returns True when finished."""
    os.makedirs(WORK, exist_ok=True)
    done = set(open(QUERIES_DONE).read().split("\n")) if os.path.exists(QUERIES_DONE) else set()
    seen = {(h["customer"], h["adsh"], h["file"]) for h in _read(HITS)}
    today = time.strftime("%Y-%m-%d")
    for ticker, aliases in CUSTOMERS:
        for alias in aliases:
            for phrase in PHRASES:
                q = '"' + phrase.format(a=alias) + '"'
                if q in done:
                    continue
                if time.time() > deadline:
                    return False
                rows, start = [], 0
                while start < 2000:
                    res = sec.get("https://efts.sec.gov/LATEST/search-index",
                                  params={"q": q, "forms": "10-K", "dateRange": "custom",
                                          "startdt": HISTORY_START, "enddt": today, "from": start})
                    hits = (res or {}).get("hits", {}).get("hits", [])
                    for h in hits:
                        src = h.get("_source", {})
                        adsh, _, fname = h.get("_id", "").partition(":")
                        if src.get("file_type") != "10-K" or not fname or not src.get("ciks"):
                            continue
                        key = (ticker, adsh, fname)
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append({"customer": ticker, "alias": alias, "cik": src["ciks"][0], "adsh": adsh,
                                     "file": fname, "file_date": src.get("file_date", ""),
                                     "sic": (src.get("sics") or [""])[0],
                                     "name": (src.get("display_names") or [""])[0][:80]})
                    if len(hits) < 100:
                        break
                    start += 100
                _append(HITS, HIT_FIELDS, rows)
                with open(QUERIES_DONE, "a") as f:
                    f.write(q + "\n")
                done.add(q)
    return True


def verify(sec, deadline):
    """Download each candidate report once and test every customer name found for it. Resumable."""
    hits = _read(HITS)
    done = set(open(DONE).read().split("\n")) if os.path.exists(DONE) else set()
    by_doc = {}
    for h in hits:
        by_doc.setdefault((h["cik"], h["adsh"], h["file"]), []).append(h)
    aliases = {t: al for t, al in CUSTOMERS}
    n = 0
    for (cik, adsh, fname), group in sorted(by_doc.items(), key=lambda kv: kv[1][0]["file_date"], reverse=True):
        doc_id = adsh + ":" + fname
        if doc_id in done:
            continue
        if time.time() > deadline:
            return False
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-', '')}/{fname}"
        try:
            raw = sec.get(url, as_json=False)
        except RuntimeError as exc:
            print("skip", exc)
            raw = None
        rows = []
        if raw:
            text = html_to_text(raw)
            for ticker in sorted({h["customer"] for h in group}):
                best = None
                for alias in aliases[ticker]:
                    found = find_evidence(text, alias)
                    if found and (best is None or found[0] > best[1]):
                        best = (alias, found[0], found[1])
                if best:
                    h = group[0]
                    rows.append({"customer": ticker, "alias": best[0], "supplier_cik": cik, "adsh": adsh,
                                 "file": fname, "file_date": h["file_date"], "sic": h["sic"],
                                 "supplier_name": h["name"], "pct": best[1], "evidence": best[2][:500]})
        _append(LINKS, LINK_FIELDS, rows)
        with open(DONE, "a") as f:
            f.write(doc_id + "\n")
        n += 1
        if n % 200 == 0:
            print("verified documents:", n)
    return True
