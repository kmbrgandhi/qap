"""Check that every criterion's quote really appears on its cited page.

The database promises a verified page citation behind every figure. This is the
mechanical half of that promise: it cannot judge whether a criterion was read
correctly, but it can prove the quoted words sit on the page the citation names.

    python -m qapdb.verify_citations              # summary + failures
    python -m qapdb.verify_citations --json out.json
    python -m qapdb.verify_citations --state RI

A quote that is not on its cited page is reported with the nearest page that
does contain it, because the usual cause is a printed page number being read
instead of a PDF page index.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # older installs expose the same API as fitz
    import fitz

from .paths import resolve_pdf

DB = Path(__file__).resolve().parent.parent / "data" / "qap.db"
SEARCH_RADIUS = 3  # pages either side, when a quote misses its cited page


def norm(s: str) -> str:
    """Whitespace- and punctuation-insensitive form for comparison.

    PDF extraction breaks lines mid-sentence, hyphenates, and uses curly quotes
    where the extraction JSON often has straight ones. None of that is a
    citation error, so it should not be reported as one.
    """
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("‑", "-")
    s = re.sub(r"-\s+", "", s)          # de-hyphenate across line breaks
    s = re.sub(r"[^\w]+", " ", s)       # punctuation is not evidence
    return re.sub(r"\s+", " ", s).strip().lower()


def pdf_dir() -> Path | None:
    """The shared drop folder, if this machine has one.

    Returns None rather than exiting when it does not: a session working from
    the git repo alone still has data/pdfs_bundled/, and resolve_pdf finds
    documents there. Callers report which PDFs they could not open.
    """
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("QAP_PDF_DIR="):
                return Path(line.split("=", 1)[1].strip())
    if os.environ.get("QAP_PDF_DIR"):
        return Path(os.environ["QAP_PDF_DIR"])
    return None


def find_pdf(root: Path | None, filename: str) -> Path | None:
    if root is None or not root.exists():
        return None
    direct = root / filename
    if direct.exists():
        return direct
    return next((p for p in root.rglob(filename)), None)


def check(state_filter: str | None = None) -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    sql = """
        SELECT c.id, c.qap_id, c.section_label, c.heading, c.quote,
               c.page_start, c.page_end, c.kind,
               q.state, q.filename, q.n_pages, q.local_path
        FROM criteria c JOIN qaps q ON q.id = c.qap_id
    """
    args: tuple = ()
    if state_filter:
        sql += " WHERE q.state = ?"
        args = (state_filter,)
    sql += " ORDER BY q.state, c.ord"
    rows = [dict(r) for r in con.execute(sql, args)]

    page_cache: dict[tuple[str, int], str] = {}
    docs: dict[str, fitz.Document] = {}
    results = []

    for r in rows:
        fn = r["filename"]
        if fn not in docs:
            path = resolve_pdf(r.get("local_path"), fn) or find_pdf(pdf_dir(), fn)
            docs[fn] = fitz.open(path) if path else None
        doc = docs[fn]
        out = {k: r[k] for k in ("id", "state", "section_label", "heading",
                                 "kind", "page_start", "page_end")}
        if doc is None:
            results.append({**out, "status": "pdf_missing"})
            continue
        if not r["quote"]:
            results.append({**out, "status": "no_quote"})
            continue

        want = norm(r["quote"])

        def page_text(p: int) -> str:
            key = (fn, p)
            if key not in page_cache:
                if 1 <= p <= doc.page_count:
                    page_cache[key] = norm(doc[p - 1].get_text())
                else:
                    page_cache[key] = ""
            return page_cache[key]

        cited = list(range(r["page_start"], (r["page_end"] or r["page_start"]) + 1))
        if any(want in page_text(p) for p in cited):
            results.append({**out, "status": "ok"})
            continue

        # Not on the cited page. Say where it actually is, if anywhere close.
        lo = max(1, r["page_start"] - SEARCH_RADIUS)
        hi = min(doc.page_count, (r["page_end"] or r["page_start"]) + SEARCH_RADIUS)
        found = [p for p in range(lo, hi + 1) if want in page_text(p)]
        if found:
            results.append({**out, "status": "wrong_page", "found_on": found,
                            "offset": found[0] - r["page_start"]})
        else:
            # Maybe only part of the quote survived extraction. Check the opening
            # words, which is enough to locate the passage for a human reviewer.
            head = " ".join(want.split()[:8])
            near = [p for p in range(lo, hi + 1) if head and head in page_text(p)]
            results.append({**out, "status": "not_found",
                            "partial_on": near, "quote": r["quote"][:120]})

    for d in docs.values():
        if d is not None:
            d.close()
    return results


def check_text_hashes(state_filter: str | None = None) -> list[dict]:
    """Has any document's extracted text moved since it was ingested?

    A quote can still be found after a document is re-OCR'd or quietly
    replaced at a rolling URL, while the surrounding text — and therefore what
    the criterion actually says — has changed. Comparing the stored hash of
    the extracted text catches that, and it is why this is cheaper than
    freezing the text to a separate file: the reviewer keeps reading the same
    PDF the citation points at, and drift is still loud.
    """
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    sql = ("SELECT id, state, filename, local_path, text_sha256 FROM qaps"
           " WHERE text_sha256 IS NOT NULL AND id IN (SELECT DISTINCT qap_id FROM criteria)")
    args: tuple = ()
    if state_filter:
        sql += " AND state = ?"
        args = (state_filter,)

    drifted = []
    for r in con.execute(sql, args):
        path = resolve_pdf(r["local_path"], r["filename"]) or find_pdf(
            pdf_dir(), r["filename"])
        if path is None or not path.exists():
            continue
        doc = fitz.open(path)
        text = "".join(p.get_text() for p in doc)
        doc.close()
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != r["text_sha256"]:
            drifted.append({"state": r["state"], "filename": r["filename"]})
    return drifted


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state")
    ap.add_argument("--json", dest="json_path")
    args = ap.parse_args()

    drifted = check_text_hashes(args.state)
    if drifted:
        print(f"!! {len(drifted)} document(s) whose extracted text has CHANGED "
              f"since ingest. Citations below were written against the old text:")
        for d in drifted:
            print(f"   {d['state']}  {d['filename']}")
        print()

    results = check(args.state)
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    print(f"checked {len(results)} criteria")
    for status, n in sorted(by_status.items(), key=lambda kv: -kv[1]):
        print(f"  {status:<12} {n}")

    per_state: dict[str, list[int]] = {}
    for r in results:
        s = per_state.setdefault(r["state"] or "?", [0, 0])
        s[1] += 1
        if r["status"] == "ok":
            s[0] += 1
    print("\nby state (verified / total):")
    for st, (ok, tot) in sorted(per_state.items()):
        print(f"  {st:<4} {ok:>3} / {tot:<3} {'' if ok == tot else '  <-- needs attention'}")

    bad = [r for r in results if r["status"] != "ok"]
    if bad:
        print(f"\n{len(bad)} to look at:")
        for r in bad:
            where = ""
            if r["status"] == "wrong_page":
                where = f" -> actually on p{r['found_on']} (offset {r['offset']:+d})"
            elif r.get("partial_on"):
                where = f" -> opening words on p{r['partial_on']}"
            print(f"  [{r['status']}] {r['state']} {r['section_label'] or ''} "
                  f"{(r['heading'] or '')[:52]} (cited p{r['page_start']}){where}")

    if args.json_path:
        Path(args.json_path).write_text(json.dumps(results, indent=1))
        print(f"\nwrote {args.json_path}")


if __name__ == "__main__":
    main()
