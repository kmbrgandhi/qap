"""Load an extraction JSON into the database, verifying every citation.

The JSON format is shared by the hand pilot and the future API pipeline, so
switching extraction sources does not change anything downstream.

Every criterion carries a `quote` and a `page_start`. Before inserting, the
quote is searched for on that page in the actual PDF. A quote that cannot be
found there is loaded with citation_verified = 0 and reported, because a
citation nobody can re-find is the failure mode this whole project exists to
avoid. Nothing is silently dropped or silently trusted.

Usage:
    python -m qapdb.load_extraction data/extractions/CT_2026.json [--commit]
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import pymupdf


def _normalise(s: str) -> str:
    """Collapse the whitespace and punctuation variance PDFs introduce."""
    s = unicodedata.normalize("NFKC", s)
    s = (s.replace("‘", "'").replace("’", "'")
          .replace("“", '"').replace("”", '"')
          .replace("–", "-").replace("—", "-")
          .replace("≥", ">=").replace("≤", "<="))
    return re.sub(r"\s+", " ", s).strip().lower()


def verify_quote(page: pymupdf.Page, quote: str) -> bool:
    """Is this quote actually on this page?

    Tries PyMuPDF's own search first (which also yields the rectangles the
    review UI highlights with), then falls back to a whitespace-normalised
    substring match, which catches quotes broken across line wraps.
    """
    if not quote:
        return False
    if page.search_for(quote, quads=False):
        return True
    return _normalise(quote) in _normalise(page.get_text())


def load(spec_path: Path, db_path: Path, commit: bool) -> int:
    spec = json.loads(spec_path.read_text())
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    match = spec["match"]
    row = conn.execute(
        "SELECT id, local_path, state FROM qaps WHERE filename = ?",
        (match["filename"],),
    ).fetchone()
    if not row:
        print(f"no qap row for {match['filename']}; run ingest first", file=sys.stderr)
        return 1
    qap_id, local_path, state = row

    doc = pymupdf.open(local_path)
    criteria = spec["criteria"]

    # Verify every citation before writing anything.
    failures = []
    for c in criteria:
        pg = c.get("page_start")
        ok = False
        if pg and 1 <= pg <= doc.page_count:
            ok = verify_quote(doc[pg - 1], c.get("quote", ""))
            # A quote can legitimately straddle a page break.
            if not ok and c.get("page_end") and c["page_end"] != pg:
                ok = verify_quote(doc[c["page_end"] - 1], c.get("quote", ""))
        c["_verified"] = 1 if ok else 0
        if not ok:
            failures.append(c)
    doc.close()

    n_ver = sum(c["_verified"] for c in criteria)
    print(f"{state}  {len(criteria)} criteria   citations verified: "
          f"{n_ver}/{len(criteria)}")
    for c in failures:
        print(f"  ! UNVERIFIED p{c.get('page_start')}  {c.get('heading','')[:60]}")
        print(f"      quote: {c.get('quote','')[:80]!r}")

    # Points arithmetic, per track, before it reaches the database.
    tracks: dict[str | None, tuple[float, float]] = {}
    for c in criteria:
        if c.get("kind", "competitive") != "competitive" or c.get("points_max") is None:
            continue
        # Deductions are not part of what a project can earn, and the totals
        # views exclude them (is_negative = 0). Counting them here would report
        # a mismatch against a stated total that never included them: Rhode
        # Island states 147 points and lists 20 negative points separately.
        if c.get("is_negative"):
            continue
        real, naive = tracks.get(c.get("track"), (0.0, 0.0))
        tiers = c.get("tiers") or []
        tracks[c.get("track")] = (
            real + c["points_max"],
            naive + (sum(t["points"] for t in tiers) if tiers else c["points_max"]),
        )
    stated = (spec.get("qap_updates") or {}).get("stated_total")
    for track, (real, naive) in tracks.items():
        flag = ""
        if stated is not None:
            flag = "  OK" if abs(real - stated) < 0.01 else f"  MISMATCH (stated {stated})"
        print(f"  track={track or '-'}: computed={real:g}  flat-sum={naive:g}"
              f"  double-counted={naive - real:g}{flag}")

    if not commit:
        print("\ndry run - nothing written. Re-run with --commit.")
        return 0

    # Reload is idempotent: drop this extractor's prior rows for this QAP.
    version = spec.get("extractor_version", "unknown")
    # Every delete here MUST be scoped by extractor_version as well as qap_id.
    # A state has one qap_id but several extraction files against it -- the
    # competitive pass and the threshold pass read the same PDF -- so a delete
    # scoped to qap_id alone lets whichever file loads last silently wipe the
    # rows the earlier one wrote. That is what emptied exclusivity_groups and
    # track_totals: the *_thresholds.json files carry neither, and they load
    # after their competitive counterparts.
    conn.execute("DELETE FROM criteria WHERE qap_id = ? AND extractor_version = ?",
                 (qap_id, version))
    conn.execute("DELETE FROM exclusivity_groups"
                 " WHERE qap_id = ? AND IFNULL(extractor_version, '') = ?",
                 (qap_id, version))

    if upd := spec.get("qap_updates"):
        cols = ", ".join(f"{k} = ?" for k in upd)
        conn.execute(f"UPDATE qaps SET {cols} WHERE id = ?",
                     (*upd.values(), qap_id))

    conn.execute("DELETE FROM track_totals"
                 " WHERE qap_id = ? AND IFNULL(extractor_version, '') = ?",
                 (qap_id, version))
    for tt in spec.get("track_totals", []):
        conn.execute(
            "INSERT INTO track_totals"
            " (qap_id, track, stated_total, page, note, extractor_version)"
            " VALUES (?,?,?,?,?,?)",
            (qap_id, tt.get("track"), tt.get("stated_total"),
             tt.get("page"), tt.get("note"), version))

    group_ids: dict[str, int] = {}
    for g in spec.get("groups", []):
        cur = conn.execute(
            """INSERT INTO exclusivity_groups
               (qap_id, label, rule, group_cap, source_quote, page_start, note,
                extractor_version)
               VALUES (?,?,?,?,?,?,?,?)""",
            (qap_id, g.get("label"), g.get("rule", "max_one"), g.get("group_cap"),
             g.get("source_quote"), g.get("page_start"), g.get("note"), version))
        group_ids[g["key"]] = cur.lastrowid

    for c in criteria:
        cur = conn.execute(
            """INSERT INTO criteria
               (qap_id, ord, section_label, heading, verbatim_text, quote,
                page_start, page_end, citation_verified, points_max, points_type,
                scoring_unit, kind, rank_order, track, native_category, is_negative,
                note, exclusivity_group_id, extractor_version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (qap_id, c.get("ord"), c.get("section_label"), c.get("heading"),
             c.get("verbatim_text"), c.get("quote"), c.get("page_start"),
             c.get("page_end"), c["_verified"], c.get("points_max"),
             c.get("points_type", "fixed"), c.get("scoring_unit", "points"),
             c.get("kind", "competitive"),
             c.get("rank_order"), c.get("track"), c.get("native_category"),
             1 if c.get("is_negative") else 0, c.get("note"),
             group_ids.get(c.get("group")), version))
        cid = cur.lastrowid
        for i, t in enumerate(c.get("tiers") or [], start=1):
            conn.execute(
                """INSERT INTO point_tiers
                   (criterion_id, ord, tier_label, points, condition_text)
                   VALUES (?,?,?,?,?)""",
                (cid, i, t.get("tier_label"), t.get("points"), t.get("condition_text")))

    conn.commit()
    print(f"\nloaded {len(criteria)} criteria for {state} (qap_id={qap_id})")
    conn.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--db", type=Path, default=Path("data/qap.db"))
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    return load(args.spec, args.db, args.commit)


if __name__ == "__main__":
    raise SystemExit(main())
