"""Ingest QAP PDFs into the database.

Identifies state, cycle years, and document status from the PDF's own text,
hashes the file for reproducibility, and flags documents with no usable text
layer (which need OCR before anything can extract from them).

Identification is heuristic and always records a confidence signal. Anything
it is not sure about is left NULL with a note rather than guessed at, so the
inventory never contains a plausible-looking value nobody verified.

Usage:
    python -m qapdb.ingest <pdf-dir> [--db data/qap.db] [--commit]

Without --commit it prints what it would insert and changes nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, asdict, field
from datetime import date
from pathlib import Path

import pymupdf

# Pages scanned when identifying a document. Front matter carries the state,
# agency, cycle, and draft/final status in essentially every QAP.
ID_PAGES = 6

# Below this many characters per page the text layer is unusable and the
# document needs OCR. A real QAP page runs to a few thousand characters;
# a scanned page yields ~0.
MIN_CHARS_PER_PAGE = 50

# Minimum share of extracted characters that must be ASCII letters. A PDF can
# carry a text layer that extracts thousands of characters of pure garbage:
# Vermont's June 2026 draft uses an embedded Type3 font with no Unicode
# mapping, so it yields 51,819 characters of raw glyph indices at a 3% letter
# ratio. Real English prose runs 70-80%. Character count alone cannot tell the
# two apart, and a garbled document that passes ingest produces extractions
# that are silently wrong rather than obviously missing.
MIN_LETTER_RATIO = 0.45

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia",
}

# Agency names are a stronger signal than the state name, which shows up
# incidentally ("...similar to New York's approach..."). Checked first.
# Token -> (state or None, agency name). Matched longest token first, so a
# full agency name always beats a bare abbreviation.
#
# Abbreviations are not unique across states and must not carry a state on
# their own: CHFA is both the Connecticut Housing Finance Authority and the
# Colorado Housing and Finance Authority, and it silently filed Colorado's
# 2025-2026 QAP under CT. An abbreviation that two agencies share maps to
# state None, which falls through to counting state names in the text.
AGENCIES = {
    "CONNECTICUT HOUSING FINANCE AUTHORITY": ("CT", "Connecticut Housing Finance Authority"),
    "COLORADO HOUSING AND FINANCE AUTHORITY": ("CO", "Colorado Housing and Finance Authority"),
    "CHFA": (None, None),                    # ambiguous: CT and CO
    "MASSHOUSING": ("MA", "MassHousing"),
    "EOHLC": ("MA", "Executive Office of Housing and Livable Communities"),
    "DHCD": (None, "Dept. of Housing and Community Development"),
    "MAINEHOUSING": ("ME", "MaineHousing"),
    "VHFA": ("VT", "Vermont Housing Finance Agency"),
    "RIHOUSING": ("RI", "RIHousing"),
    "RI HOUSING": ("RI", "RIHousing"),
    "NEW HAMPSHIRE HOUSING": ("NH", "New Hampshire Housing Finance Authority"),
    "NJHMFA": ("NJ", "New Jersey Housing and Mortgage Finance Agency"),
    "HCR": ("NY", "NYS Homes and Community Renewal"),
    # Added with the 2026 multi-state expansion.
    "TEXAS DEPARTMENT OF HOUSING AND COMMUNITY AFFAIRS": ("TX", "Texas Dept. of Housing and Community Affairs"),
    "TDHCA": ("TX", "Texas Dept. of Housing and Community Affairs"),
    "CALIFORNIA TAX CREDIT ALLOCATION COMMITTEE": ("CA", "California Tax Credit Allocation Committee"),
    "TCAC": ("CA", "California Tax Credit Allocation Committee"),
    "WASHINGTON STATE HOUSING FINANCE COMMISSION": ("WA", "Washington State Housing Finance Commission"),
    "WSHFC": ("WA", "Washington State Housing Finance Commission"),
    "OHIO HOUSING FINANCE AGENCY": ("OH", "Ohio Housing Finance Agency"),
    "OHFA": (None, None),                    # ambiguous: OH and OK
    "NORTH CAROLINA HOUSING FINANCE AGENCY": ("NC", "North Carolina Housing Finance Agency"),
    "NCHFA": ("NC", "North Carolina Housing Finance Agency"),
    "GEORGIA HOUSING AND FINANCE AUTHORITY": ("GA", "Georgia Housing and Finance Authority"),
    "GHFA": ("GA", "Georgia Housing and Finance Authority"),
    "FLORIDA HOUSING FINANCE CORPORATION": ("FL", "Florida Housing Finance Corporation"),
    "VIRGINIA HOUSING DEVELOPMENT AUTHORITY": ("VA", "Virginia Housing"),
    "VIRGINIA HOUSING": ("VA", "Virginia Housing"),
    "DELAWARE STATE HOUSING AUTHORITY": ("DE", "Delaware State Housing Authority"),
    "DSHA": ("DE", "Delaware State Housing Authority"),
    "PENNSYLVANIA HOUSING FINANCE AGENCY": ("PA", "Pennsylvania Housing Finance Agency"),
    "PHFA": ("PA", "Pennsylvania Housing Finance Agency"),
    "ILLINOIS HOUSING DEVELOPMENT AUTHORITY": ("IL", "Illinois Housing Development Authority"),
    "IHDA": ("IL", "Illinois Housing Development Authority"),
    "WISCONSIN HOUSING AND ECONOMIC DEVELOPMENT AUTHORITY": ("WI", "WHEDA"),
    "WHEDA": ("WI", "WHEDA"),
    "MINNESOTA HOUSING": ("MN", "Minnesota Housing Finance Agency"),
    "MICHIGAN STATE HOUSING DEVELOPMENT AUTHORITY": ("MI", "Michigan State Housing Development Authority"),
    "MSHDA": ("MI", "Michigan State Housing Development Authority"),
    "MISSOURI HOUSING DEVELOPMENT COMMISSION": ("MO", "Missouri Housing Development Commission"),
    "MHDC": ("MO", "Missouri Housing Development Commission"),
}

DRAFT_RE = re.compile(r"\bdraft\b", re.I)

# Full cycle: "2025-2026", "2025 / 2026". Two-digit tail: "2024-25".
CYCLE_FULL_RE = re.compile(r"(20\d{2})\s*[-‐-―_/]\s*(20\d{2})")
CYCLE_SHORT_RE = re.compile(r"(20\d{2})\s*[-‐-―_/]\s*(\d{2})(?!\d)")

# A lone year counts as the cycle only when it sits next to the phrase naming
# the document. "2026 Qualified Allocation Plan" is the cycle; a 2026 in a
# table of contents is not.
CYCLE_NEAR_TITLE_RE = re.compile(
    r"(?:(20\d{2})\s*(?:qualified allocation plan|qap)"
    r"|(?:qualified allocation plan|qap)\s*(?:for\s+)?(20\d{2}))",
    re.I,
)
EFFECTIVE_RE = re.compile(
    r"effective(?:\s+date)?[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+20\d{2})", re.I
)

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}


@dataclass
class Ident:
    """What we could determine about a PDF, plus why."""
    state: str | None = None
    state_name: str | None = None
    agency: str | None = None
    cycle_start: int | None = None
    cycle_end: int | None = None
    cycle_source: str = "none"
    doc_status: str = "unknown"
    effective_date: str | None = None
    title: str | None = None
    n_pages: int = 0
    text_chars: int = 0
    source_quality: str = "native"
    pdf_metadata: str | None = None
    warnings: list[str] = field(default_factory=list)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_effective(text: str) -> str | None:
    m = EFFECTIVE_RE.search(text)
    if not m:
        return None
    parts = m.group(1).replace(",", "").split()
    if len(parts) != 3:
        return None
    month = MONTHS.get(parts[0].lower())
    if not month:
        return None
    try:
        return date(int(parts[2]), month, int(parts[1])).isoformat()
    except ValueError:
        return None


def _find_cycle(text: str, *, near_title_only: bool) -> tuple[int, int] | None:
    """Pull a cycle out of a string, or None.

    Deliberately conservative. Returns None rather than guessing from stray
    years, because a wrong cycle silently mislabels every criterion under it.
    """
    if m := CYCLE_FULL_RE.search(text):
        a, b = int(m.group(1)), int(m.group(2))
        if 2000 <= a <= 2040 and a <= b <= a + 6:
            return a, b
    if m := CYCLE_SHORT_RE.search(text):
        a = int(m.group(1))
        b = (a // 100) * 100 + int(m.group(2))   # "2024-25" -> 2024, 2025
        if 2000 <= a <= 2040 and a <= b <= a + 6:
            return a, b
    if near_title_only:
        if m := CYCLE_NEAR_TITLE_RE.search(text):
            y = int(m.group(1) or m.group(2))
            if 2000 <= y <= 2040:
                return y, y
    return None


def _resolve_cycle(ident: Ident, filename: str, title_text: str) -> None:
    """Reconcile the filename's cycle against the document's own.

    The document wins on conflict, but the conflict is always flagged - it
    usually means the file was renamed or is not the document it claims.
    """
    from_name = _find_cycle(filename, near_title_only=False)
    from_doc = _find_cycle(title_text, near_title_only=True)

    if from_name and from_doc:
        if from_name == from_doc:
            ident.cycle_start, ident.cycle_end = from_doc
            ident.cycle_source = "both_agree"
        else:
            ident.cycle_start, ident.cycle_end = from_doc
            ident.cycle_source = "CONFLICT"
            ident.warnings.append(
                f"cycle conflict: filename says {from_name[0]}-{from_name[1]}, "
                f"document says {from_doc[0]}-{from_doc[1]}; using the document"
            )
    elif from_doc:
        ident.cycle_start, ident.cycle_end = from_doc
        ident.cycle_source = "document"
    elif from_name:
        ident.cycle_start, ident.cycle_end = from_name
        ident.cycle_source = "filename"
        ident.warnings.append(
            "cycle taken from the FILENAME - the document's front matter does "
            "not state it; confirm against the source page"
        )
    else:
        ident.cycle_source = "none"
        ident.warnings.append("cycle not found in filename or document; set manually")


def identify(path: Path) -> Ident:
    """Read a PDF's front matter and work out what document it is."""
    ident = Ident()
    doc = pymupdf.open(path)
    ident.n_pages = doc.page_count

    ident.text_chars = sum(len(doc[i].get_text()) for i in range(doc.page_count))
    per_page = ident.text_chars / max(doc.page_count, 1)
    if per_page < MIN_CHARS_PER_PAGE:
        ident.source_quality = "no_text_layer"
        ident.warnings.append(
            f"no usable text layer ({ident.text_chars} chars / "
            f"{doc.page_count} pages) - needs OCR before extraction"
        )

    # Measure the whole document, not the front matter. A title page and a
    # dotted table of contents are mostly digits, dots and whitespace: over the
    # first 8 pages Michigan's 2026-2027 QAP reads 22% letters and Minnesota's
    # 30%, against 72% and 74% across the full document. Both were flagged as
    # garbled and neither is. Genuine garbling does not hide: Vermont's Type3
    # draft measures 3% whichever way you slice it.
    probe = " ".join(doc[i].get_text() for i in range(doc.page_count))
    letters = sum(c.isascii() and c.isalpha() for c in probe)
    ratio = letters / max(len(probe.strip()), 1)
    if ident.source_quality == "native" and len(probe.strip()) > 200 \
            and ratio < MIN_LETTER_RATIO:
        ident.source_quality = "garbled_text"
        ident.warnings.append(
            f"text layer extracts but is not readable text "
            f"({ratio:.0%} letters, expected >{MIN_LETTER_RATIO:.0%}) - "
            f"likely a font with no Unicode mapping; needs --force-ocr"
        )

    head = " ".join(doc[i].get_text() for i in range(min(ID_PAGES, doc.page_count)))

    # Embedded metadata is authored by the issuing agency and often survives
    # when the text layer does not - it is how a scanned QAP gets identified.
    meta = doc.metadata or {}
    meta_text = " ".join(
        str(meta.get(k) or "") for k in ("title", "author", "subject", "keywords")
    ).strip()
    if meta_text:
        ident.pdf_metadata = meta_text
        head = f"{meta_text} {head}"
        # Only worth flagging when metadata is actually load-bearing, i.e.
        # there is no text layer to identify from. Otherwise it just reports
        # incidental fields like the author's name.
        if ident.source_quality == "no_text_layer":
            ident.warnings.append(f"identified from PDF metadata: {meta_text[:120]}")

    head = re.sub(r"\s+", " ", head)
    doc.close()

    if not head.strip():
        ident.warnings.append("no front-matter text or metadata; identify manually")
        return ident

    ident.title = head[:200].strip() or None
    upper = head.upper()

    # Agency first - a stronger signal than an incidental state mention.
    # Longest token first: "COLORADO HOUSING AND FINANCE AUTHORITY" must win
    # over the "CHFA" that also appears in the same document.
    for token in sorted(AGENCIES, key=len, reverse=True):
        if token in upper:
            st, name = AGENCIES[token]
            if name:
                ident.agency = name
            if st:
                ident.state = st
                break
            # An ambiguous abbreviation identifies nothing on its own; keep
            # looking for a token that does.

    if not ident.state:
        hits = {code: upper.count(nm.upper())
                for code, nm in STATES.items() if nm.upper() in upper}
        if hits:
            ranked = sorted(hits.items(), key=lambda kv: -kv[1])
            ident.state = ranked[0][0]
            if len(ranked) > 1 and ranked[1][1] >= ranked[0][1]:
                ident.warnings.append(
                    "ambiguous state: " + ", ".join(f"{k}({v})" for k, v in ranked[:3])
                )
    if ident.state:
        ident.state_name = STATES[ident.state]
    else:
        ident.warnings.append("state not identified; set manually")

    # Cycle comes from the filename and/or the title block only - never from
    # stray years deeper in the document.
    _resolve_cycle(ident, path.name, head[:2500])

    # Draft detection looks only at the first page - later pages say
    # "draft" about unrelated things (draft regulatory agreements, etc.).
    first_page = head[:1500]
    ident.doc_status = "draft" if DRAFT_RE.search(first_page) else "final"
    if ident.doc_status == "draft":
        ident.warnings.append("appears to be a DRAFT, not an adopted QAP")

    ident.effective_date = _parse_effective(head)
    return ident


# Cloud-sync services and Office leave artefacts beside the real files. A
# "conflicted copy" is especially dangerous: it is a real, readable PDF that
# would ingest silently as if it were a distinct document.
SKIP_PATTERNS = (
    "~$",                    # Office lock files
    ".~",
)
SKIP_SUBSTRINGS = (
    "conflicted copy",       # Dropbox
    "(case conflict)",       # Dropbox
    " - copy",               # Windows / Drive
    "(1)",                   # Drive duplicate suffix
)


def discover(root: Path) -> list[Path]:
    """Every PDF under root, recursively, minus sync and lock artefacts.

    Recursive because a shared drop folder will grow subfolders - the Vermont
    2026 QAP already arrived inside one, and a flat glob silently skipped it.
    """
    out = []
    for p in sorted(root.rglob("*.pdf")):
        name = p.name.lower()
        if any(p.name.startswith(s) for s in SKIP_PATTERNS):
            continue
        if any(s in name for s in SKIP_SUBSTRINGS):
            print(f"  ~ skipping sync artefact: {p.relative_to(root)}")
            continue
        if any(part.startswith(".") for part in p.relative_to(root).parts):
            continue         # .Trash, .dropbox.cache, etc.
        out.append(p)
    return out


def ingest(pdf_dir: Path, db_path: Path, commit: bool) -> int:
    pdfs = sorted(discover(pdf_dir))
    if not pdfs:
        print(f"no PDFs in {pdf_dir}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    rows, skipped = [], 0
    for path in pdfs:
        digest = sha256_of(path)
        existing = conn.execute(
            "SELECT id, state FROM qaps WHERE sha256 = ?", (digest,)
        ).fetchone()
        if existing:
            print(f"  = {path.name}: already ingested as qap id={existing[0]}")
            skipped += 1
            continue

        ident = identify(path)
        rows.append((path, digest, ident))

        cycle = (f"{ident.cycle_start}-{ident.cycle_end}"
                 if ident.cycle_start != ident.cycle_end else str(ident.cycle_start))
        try:
            shown = path.relative_to(pdf_dir)
        except ValueError:
            shown = path.name
        print(f"  + {shown}")
        print(f"      {ident.state or '??'}  cycle={cycle} ({ident.cycle_source})  "
              f"status={ident.doc_status}  eff={ident.effective_date or '-'}  "
              f"pages={ident.n_pages}  quality={ident.source_quality}")
        for w in ident.warnings:
            print(f"      ! {w}")

    if not commit:
        print(f"\ndry run - {len(rows)} would be inserted, {skipped} already present."
              "\nRe-run with --commit to write.")
        conn.close()
        return 0

    today = date.today().isoformat()
    for path, digest, ident in rows:
        conn.execute(
            """INSERT INTO qaps
               (state, state_name, agency, doc_role, doc_status,
                cycle_start, cycle_end, cycle_source, effective_date, title,
                retrieved_at, sha256, filename, local_path,
                n_pages, text_chars, source_quality, notes)
               VALUES (?,?,?,'primary',?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ident.state, ident.state_name, ident.agency, ident.doc_status,
             ident.cycle_start, ident.cycle_end, ident.cycle_source,
             ident.effective_date, ident.title,
             today, digest, path.name, str(path.resolve()),
             ident.n_pages, ident.text_chars, ident.source_quality,
             json.dumps(ident.warnings) if ident.warnings else None),
        )

    # Most-recent flag per state, by cycle_end then cycle_start. Drafts are
    # never marked most-recent: an unadopted document does not supersede a
    # signed one.
    conn.execute("UPDATE qaps SET is_most_recent = 0")
    conn.execute(
        """UPDATE qaps SET is_most_recent = 1
           WHERE id IN (
             SELECT id FROM (
               SELECT id, ROW_NUMBER() OVER (
                 PARTITION BY state
                 ORDER BY COALESCE(cycle_end, cycle_start) DESC,
                          COALESCE(cycle_start, 0) DESC, id DESC) AS rn
               FROM qaps
               WHERE state IS NOT NULL AND doc_status <> 'draft'
             ) WHERE rn = 1)"""
    )
    conn.commit()

    print(f"\ninserted {len(rows)}, skipped {skipped}")
    print("\nmost recent per state (drafts excluded):")
    for r in conn.execute(
        """SELECT state, cycle_start, cycle_end, doc_status, filename
           FROM qaps WHERE is_most_recent = 1 ORDER BY state"""
    ):
        cyc = f"{r[1]}-{r[2]}" if r[1] != r[2] else str(r[1])
        print(f"  {r[0]}  {cyc:<10} {r[3]:<7} {r[4]}")
    conn.close()
    return 0


def _load_env() -> None:
    """Read QAP_PDF_DIR from a local .env if present (never committed)."""
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def main() -> int:
    _load_env()
    ap = argparse.ArgumentParser(description=__doc__)
    # The shared drop folder lives at a different absolute path on each
    # collaborator's machine, so it is configured per-machine rather than
    # committed. QAP_PDF_DIR in .env, or pass the path explicitly.
    default_dir = os.environ.get("QAP_PDF_DIR")
    ap.add_argument("pdf_dir", type=Path, nargs="?" if default_dir else None,
                    default=Path(default_dir) if default_dir else None,
                    help="folder of QAP PDFs (default: $QAP_PDF_DIR)")
    ap.add_argument("--db", type=Path, default=Path("data/qap.db"))
    ap.add_argument("--commit", action="store_true",
                    help="write to the database (default is a dry run)")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"database {args.db} not found; run:\n"
              f"  sqlite3 {args.db} < schema.sql", file=sys.stderr)
        return 1
    return ingest(args.pdf_dir, args.db, args.commit)


if __name__ == "__main__":
    raise SystemExit(main())
