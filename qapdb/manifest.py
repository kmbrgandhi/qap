"""Write a manifest of the QAP corpus.

The PDFs live in a shared drop folder and are deliberately not in git — they
are large binaries, and two people need to add them without touching the repo.
But a repo that contains neither the documents nor any record of them cannot
reproduce anything. The manifest is that record: one row per document, with the
SHA-256 that makes it identifiable regardless of what anyone renamed the file
to, and the source URL that lets someone else fetch it.

Commit the manifest. Never commit the PDFs.

Usage:
    python -m qapdb.manifest                    # write data/manifest.csv
    python -m qapdb.manifest --check            # verify the drop folder matches
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

FIELDS = [
    "state", "state_name", "agency", "cycle_start", "cycle_end", "cycle_source",
    "doc_status", "effective_date", "governs_round", "is_most_recent",
    "n_pages", "source_quality", "stated_total", "filename", "sha256",
    "source_url", "retrieved_at", "notes",
]


def rows(db: Path) -> list[dict]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    out = [dict(r) for r in conn.execute(
        f"SELECT {', '.join(FIELDS)} FROM qaps ORDER BY state, cycle_start, filename")]
    conn.close()
    return out


def write(db: Path, out: Path) -> int:
    data = rows(db)
    # A database built from data/pdfs_bundled/ holds eleven of the corpus's
    # documents. Overwriting the manifest from it silently dropped the other
    # seventy-odd rows, which are the only record in git that those documents
    # exist. So keep every existing row this database knows nothing about, and
    # refresh only the rows it does know.
    if out.exists():
        known = {r["sha256"] for r in data}
        kept = [r for r in csv.DictReader(out.open()) if r["sha256"] not in known]
        if kept:
            print(f"kept {len(kept)} manifest row(s) for documents not in this database")
        data = sorted(data + kept, key=lambda r: (
            str(r["state"] or ""), str(r["cycle_start"] or ""), r["filename"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(data)
    missing = [r["filename"] for r in data if not r["source_url"]]
    print(f"wrote {out} — {len(data)} documents")
    if missing:
        print(f"\n{len(missing)} document(s) have no source_url recorded. Without it "
              f"nobody else can re-fetch them:")
        for m in missing:
            print(f"  - {m}")
    return 0


def check(db: Path, manifest: Path) -> int:
    """Compare the manifest against what is actually ingested."""
    if not manifest.exists():
        print(f"{manifest} does not exist yet", file=sys.stderr)
        return 1
    have = {r["sha256"]: r for r in rows(db)}
    want = {r["sha256"]: r for r in csv.DictReader(manifest.open())}
    only_db = set(have) - set(want)
    only_mf = set(want) - set(have)
    if not only_db and not only_mf:
        print(f"manifest matches the database — {len(have)} documents")
        return 0
    for h in sorted(only_db):
        print(f"  + in database, not in manifest: {have[h]['filename']}")
    for h in sorted(only_mf):
        print(f"  - in manifest, not ingested:    {want[h]['filename']} "
              f"({want[h]['state']} {want[h]['cycle_start']})")
    print("\nRe-run `python -m qapdb.manifest` after ingesting, or fetch the "
          "missing documents into the shared folder.")
    return 1


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=root / "data" / "qap.db")
    ap.add_argument("--out", type=Path, default=root / "data" / "manifest.csv")
    ap.add_argument("--check", action="store_true",
                    help="compare manifest against the database instead of writing")
    a = ap.parse_args()
    if not a.db.exists():
        print(f"database {a.db} not found", file=sys.stderr)
        return 1
    return check(a.db, a.out) if a.check else write(a.db, a.out)


if __name__ == "__main__":
    raise SystemExit(main())
