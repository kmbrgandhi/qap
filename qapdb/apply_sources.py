"""Apply data/sources.csv to the database.

Where a document came from cannot be read out of the document. Ingest can
identify a state and usually a cycle from the text, but the agency page it was
downloaded from exists only in whoever downloaded it. That belongs in a
committed file, not in the database, because the database is a build artefact:
delete data/qap.db, rebuild, and anything recorded only there is gone.

data/sources.csv is that file. It is keyed by sha256, so renaming a PDF does
not break the link, and it carries three kinds of thing:

  * source_url and landing_page - where to re-fetch the document
  * retrieved_at                - when it was fetched
  * agency, cycle_start/end     - corrections a human verified against the
                                  agency's own site, for documents whose text
                                  does not state them

A cycle set here is recorded with cycle_source = 'manual', so it is never
confused with one the document itself stated. Blank columns change nothing.

Usage:
    python -m qapdb.apply_sources [--db data/qap.db] [--commit]
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

SOURCES = Path(__file__).resolve().parent.parent / "data" / "sources.csv"


def apply(db_path: Path, csv_path: Path, commit: bool) -> int:
    if not csv_path.exists():
        print(f"{csv_path} not found", file=sys.stderr)
        return 1
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = list(csv.DictReader(csv_path.open()))
    changes: list[str] = []
    unmatched: list[str] = []

    for r in rows:
        sha = (r.get("sha256") or "").strip()
        doc = conn.execute(
            "SELECT id, state, filename, agency, source_url, cycle_start, cycle_end"
            " FROM qaps WHERE sha256 = ?", (sha,)).fetchone()
        if not doc:
            unmatched.append(r.get("filename", sha[:12]))
            continue

        sets: dict[str, object] = {}
        if r.get("source_url") and r["source_url"] != doc["source_url"]:
            sets["source_url"] = r["source_url"]
        if r.get("retrieved_at"):
            sets["retrieved_at"] = r["retrieved_at"]
        if r.get("agency") and r["agency"] != doc["agency"]:
            sets["agency"] = r["agency"]
        if r.get("cycle_start"):
            cs, ce = int(r["cycle_start"]), int(r["cycle_end"] or r["cycle_start"])
            if (cs, ce) != (doc["cycle_start"], doc["cycle_end"]):
                sets.update(cycle_start=cs, cycle_end=ce, cycle_source="manual")
        # The note explains provenance and belongs with the document, appended
        # rather than replacing whatever ingest flagged.
        if r.get("note"):
            existing = conn.execute("SELECT notes FROM qaps WHERE id = ?",
                                    (doc["id"],)).fetchone()[0] or ""
            if r["note"] not in existing:
                sets["notes"] = (existing + "\n" if existing else "") + r["note"]

        if not sets:
            continue
        changes.append(f"  {doc['state'] or '??'} {doc['filename'][:48]}: "
                       + ", ".join(k for k in sets if k != "notes"))
        if commit:
            cols = ", ".join(f"{k} = ?" for k in sets)
            conn.execute(f"UPDATE qaps SET {cols} WHERE id = ?",
                         (*sets.values(), doc["id"]))

    print(f"{len(rows)} rows in {csv_path.name}; {len(changes)} documents to update")
    for c in changes:
        print(c)
    if unmatched:
        print(f"\n{len(unmatched)} rows match no document in the database "
              f"(is the PDF in the drop folder, and ingested?):")
        for u in unmatched:
            print(f"  {u}")

    missing = conn.execute(
        "SELECT state, filename FROM qaps WHERE source_url IS NULL OR source_url = ''"
    ).fetchall()
    if commit:
        conn.commit()
        missing = conn.execute(
            "SELECT state, filename FROM qaps WHERE source_url IS NULL OR source_url = ''"
        ).fetchall()
    if missing:
        print(f"\n{len(missing)} documents still have no source URL:")
        for m in missing:
            print(f"  {m['state'] or '??'}  {m['filename']}")
    else:
        print("\nevery document has a source URL")

    if not commit:
        print("\ndry run - nothing written. Re-run with --commit.")
    conn.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=Path("data/qap.db"))
    ap.add_argument("--csv", type=Path, default=SOURCES)
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    return apply(args.db, args.csv, args.commit)


if __name__ == "__main__":
    raise SystemExit(main())
