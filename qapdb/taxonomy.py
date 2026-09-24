"""Apply the shared cross-state category codebook.

The QAPs' own category names cannot be compared: Massachusetts files every
criterion under one of two structural headings ("Fundamental" / "Special"),
Vermont uses fifteen headings that are mostly one criterion each. Forty-four
native categories across five states collapse to eight shared ones here.

Assignment is explicit per criterion, keyed by (state, section_label), rather
than inferred from keywords. Keyword matching on headings looks tidy and
quietly miscodes the awkward cases - and the awkward cases are the ones that
matter, because they are where states differ.

Multi-label is supported: exactly one category is primary and drives every
total and chart, secondary labels only widen search. That is what lets a
criterion rewarding historic rehabilitation *or* a green certification be
findable under both without being counted twice.

Usage:
    python -m qapdb.taxonomy [--db data/qap.db] [--commit]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

CODEBOOK_VERSION = "v1-2026-pilot"

# Threshold requirements are mapped to the same category vocabulary by hand,
# in a data file rather than in code because the list grows with every state
# added. Keys are 'STATE|section_label'. Missing file is not fatal: thresholds
# simply go unlabelled and are reported.
_THRESHOLD_MAP = Path(__file__).resolve().parent.parent / "data" / "threshold_categories.json"
THRESHOLD_ASSIGN: dict[str, str] = (
    json.loads(_THRESHOLD_MAP.read_text()) if _THRESHOLD_MAP.exists() else {})

# name -> (definition, what belongs, what explicitly does not)
CATEGORIES: dict[str, tuple[str, str, str]] = {
    "Affordability & income targeting": (
        "Depth and duration of income and rent restriction.",
        "Units at or below a stated AMI band; average-income elections; mixed-income "
        "and market-rate components; rental subsidy that deepens affordability; "
        "extended affordability periods.",
        "Not funding sources that merely improve feasibility (Cost efficiency & "
        "leverage), and not the population a project serves (Populations & "
        "supportive services).",
    ),
    "Populations & supportive services": (
        "Who the housing is for, and the services attached to it.",
        "Homelessness, veterans, disability, elderly, families and bedroom mix, "
        "special needs set-asides, resident service coordination, 811 PRA units, "
        "public housing waiting lists.",
        "Not the income level served, which is Affordability & income targeting.",
    ),
    "Location, transit & community": (
        "Where the project sits and how that location is judged.",
        "Qualified census tracts, opportunity indices, community revitalization "
        "plans, measured housing need, rural or urban designations, local support, "
        "transit proximity, walkability, smart-growth and infrastructure access.",
        "Not the physical design of the building itself.",
    ),
    "Design, accessibility & sustainability": (
        "The physical quality of what gets built.",
        "Accessibility and universal design beyond code minimums, energy and green "
        "building certification, renewable energy, resident amenities, design "
        "standards and climate resilience.",
        "Not adaptive reuse of an existing structure, which is Preservation & "
        "historic reuse.",
    ),
    "Cost efficiency & leverage": (
        "Getting more housing per public dollar.",
        "Cost containment and per-unit cost tests, credit efficiency, outside and "
        "non-credit funding sources, land donation, tax relief and PILOTs, "
        "permanent debt, cost-overrun penalties.",
        "Not a sponsor's financial capacity, which is Sponsor capacity & "
        "performance.",
    ),
    "Sponsor capacity & performance": (
        "Who is doing the development, and their track record.",
        "Developer and management experience, prior compliance and performance "
        "penalties, non-profit or public housing authority status, MBE/WBE "
        "participation, development team composition.",
        "Not project-level readiness, which is Readiness & feasibility.",
    ),
    "Readiness & feasibility": (
        "Whether this project can actually proceed, and soon.",
        "Permits and land use approvals secured, site control, environmental and "
        "historic review progress, financial feasibility, marketability, phasing "
        "and twinned deals, site conditions impeding construction.",
        "Not the sponsor's general capacity, which is Sponsor capacity & "
        "performance.",
    ),
    "Preservation & historic reuse": (
        "Keeping or reusing housing and buildings that already exist.",
        "Rehabilitation of existing rental housing, at-risk federally assisted "
        "preservation, re-syndication, adaptive reuse, brownfield redevelopment, "
        "historic rehabilitation credits.",
        "Not new construction with green or accessible design, which is Design, "
        "accessibility & sustainability.",
    ),
}

AFF, POP, LOC = ("Affordability & income targeting", "Populations & supportive services",
                 "Location, transit & community")
DES, COST, SPON = ("Design, accessibility & sustainability", "Cost efficiency & leverage",
                   "Sponsor capacity & performance")
READY, PRES = "Readiness & feasibility", "Preservation & historic reuse"

# (state, section_label) -> primary, or (primary, *secondary)
ASSIGN: dict[tuple[str, str], object] = {
    # ---- Connecticut -------------------------------------------------------
    ("CT", "III.H.1.a"): POP,   ("CT", "III.H.1.b"): AFF,
    ("CT", "III.H.1.c"): AFF,   ("CT", "III.H.1.d"): AFF,
    ("CT", "III.H.1.e"): READY, ("CT", "III.H.1.f"): POP,
    ("CT", "III.H.2.a"): COST,  ("CT", "III.H.2.b"): COST,
    ("CT", "III.H.2.c"): COST,  ("CT", "III.H.2.d"): COST,
    ("CT", "III.H.2.e"): DES,   ("CT", "III.H.2.f"): COST,
    ("CT", "III.H.3.a"): LOC,   ("CT", "III.H.3.b"): LOC,
    ("CT", "III.H.3.c"): (PRES, DES),
    ("CT", "III.H.3.d"): LOC,   ("CT", "III.H.3.e"): LOC,
    ("CT", "III.H.4.a"): LOC,   ("CT", "III.H.4.b"): LOC,
    ("CT", "III.H.5.a"): SPON,  ("CT", "III.H.5.b"): SPON,
    ("CT", "III.H.5.c"): SPON,

    # ---- Massachusetts -----------------------------------------------------
    ("MA", "XI-A.A-1"): READY,  ("MA", "XI-A.A-2"): DES,
    ("MA", "XI-A.A-3"): SPON,   ("MA", "XI-A.A-4"): READY,
    ("MA", "XI-A.A-5"): READY,
    ("MA", "XI-B.B-1"): LOC,    ("MA", "XI-B.B-2"): LOC,
    ("MA", "XI-B.B-3"): SPON,   ("MA", "XI-B.B-4"): SPON,
    ("MA", "XI-B.B-5"): POP,    ("MA", "XI-B.B-6"): LOC,
    ("MA", "XI-B.B-7"): LOC,    ("MA", "XI-B.B-8"): AFF,
    ("MA", "XI-B.B-9"): DES,    ("MA", "XI-B.B-10"): DES,
    ("MA", "XI-B.B-11"): LOC,

    # ---- Maine -------------------------------------------------------------
    ("ME", "6.A"): PRES,        ("ME", "6.B"): PRES,
    ("ME", "6.C"): POP,         ("ME", "6.D"): POP,
    ("ME", "6.E"): DES,         ("ME", "6.F"): (COST, AFF),
    ("ME", "6.G"): COST,        ("ME", "6.H"): COST,
    ("ME", "6.I"): LOC,         ("ME", "6.J"): (LOC, PRES),
    ("ME", "6.K"): LOC,         ("ME", "6.L"): READY,
    ("ME", "6.M"): SPON,        ("ME", "6.N"): SPON,
    ("ME", "6.O"): SPON,        ("ME", "6.P"): SPON,

    # ---- New Hampshire -----------------------------------------------------
    ("NH", "109.07.A.1"): POP,
    ("NH", "109.07.A.2.a"): AFF, ("NH", "109.07.A.2.b"): AFF,
    ("NH", "109.07.A.2.c"): AFF, ("NH", "109.07.A.2.d"): AFF,
    ("NH", "109.07.A.3.a"): POP, ("NH", "109.07.A.3.b"): POP,
    ("NH", "109.07.A.4"): POP,   ("NH", "109.07.A.5"): (POP, PRES),
    ("NH", "109.07.A.6.a"): POP,
    ("NH", "109.07.A.7.a"): LOC, ("NH", "109.07.A.7.b"): LOC,
    ("NH", "109.07.A.8.a"): (AFF, POP),
    ("NH", "109.07.A.8.b"): COST,
    ("NH", "109.07.A.9.a"): READY, ("NH", "109.07.A.9.b"): READY,
    ("NH", "109.07.A.9.c"): READY,
    ("NH", "109.07.A.10.a"): LOC, ("NH", "109.07.A.10.b"): LOC,
    ("NH", "109.07.A.10.c"): PRES, ("NH", "109.07.A.10.d"): PRES,
    ("NH", "109.07.A.10.e"): LOC,
    ("NH", "109.07.A.11"): COST,
    ("NH", "109.07.A.12"): SPON, ("NH", "109.07.A.13"): SPON,
    ("NH", "109.07.A.14.a"): SPON, ("NH", "109.07.A.14.b"): SPON,
    ("NH", "109.07.A.14.c"): SPON,
    ("NH", "109.07.A.15.a"): DES, ("NH", "109.07.A.15.b"): DES,
    ("NH", "109.07.A.16.a"): DES, ("NH", "109.07.A.16.b"): DES,
    ("NH", "109.07.A.17"): DES,
    ("NH", "109.07.A.18.a"): DES, ("NH", "109.07.A.18.b"): (DES, PRES),
    ("NH", "109.07.A.18.c"): DES,
    ("NH", "109.07.A.19"): AFF,

    # ---- Vermont -----------------------------------------------------------
    ("VT", "4.01.a"): LOC,      ("VT", "4.01.b"): LOC,
    ("VT", "4.02"): LOC,        ("VT", "4.03"): POP,
    ("VT", "4.04"): AFF,        ("VT", "4.05"): POP,
    ("VT", "4.06"): (AFF, POP), ("VT", "4.07"): COST,
    ("VT", "4.08"): COST,       ("VT", "4.09"): COST,
    ("VT", "4.10"): COST,       ("VT", "4.11"): READY,
    ("VT", "4.12"): PRES,       ("VT", "4.13"): (PRES, DES),
    ("VT", "4.14"): POP,        ("VT", "4.15"): READY,

    # ---- Rhode Island ------------------------------------------------------
    # Section labels are ours: the QAP letters its items A, B, C within each
    # unnumbered scoring section, so the section abbreviation keeps them unique.
    ("RI", "III.B.Fin.A"): COST,        ("RI", "III.B.Fin.B"): COST,
    ("RI", "III.B.Fin.C"): (COST, AFF), ("RI", "III.B.Fin.D"): COST,
    ("RI", "III.B.Inc.A"): POP,         ("RI", "III.B.Inc.B"): (POP, AFF),
    ("RI", "III.B.Inc.C"): DES,         ("RI", "III.B.Inc.D"): AFF,
    ("RI", "III.B.Inc.E"): POP,
    ("RI", "III.B.Work.A"): SPON,       ("RI", "III.B.Work.B"): SPON,
    ("RI", "III.B.Work.C"): SPON,       ("RI", "III.B.Work.D"): READY,
    ("RI", "III.B.Comm.A"): LOC,        ("RI", "III.B.Comm.1"): LOC,
    ("RI", "III.B.Comm.2"): LOC,
    ("RI", "III.B.Sust.A"): DES,        ("RI", "III.B.Sust.B"): DES,
    ("RI", "III.B.Sust.C"): DES,        ("RI", "III.B.Sust.D"): DES,
    # Greenfield avoidance is a siting judgement about which land gets built
    # on, so it leads on location, with design second.
    ("RI", "III.B.Sust.E"): (LOC, DES),
    # All four deductions are assessed on the developer's performance under a
    # previous allocation, which is sponsor capacity rather than cost.
    ("RI", "III.B.Neg.1"): SPON,        ("RI", "III.B.Neg.2"): SPON,
    ("RI", "III.B.Neg.3"): SPON,        ("RI", "III.B.Neg.4"): SPON,
}


def apply(db_path: Path, commit: bool) -> int:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    rows = [dict(r) for r in conn.execute(
        """SELECT c.id, q.state, c.section_label, c.heading, c.kind, c.points_max
           FROM criteria c JOIN qaps q ON q.id = c.qap_id
           WHERE c.kind = 'competitive' ORDER BY q.state, c.ord""")]

    unmapped = [r for r in rows if (r["state"], r["section_label"]) not in ASSIGN]
    print(f"{len(rows)} competitive criteria, {len(rows)-len(unmapped)} mapped, "
          f"{len(unmapped)} unmapped")
    for r in unmapped:
        print(f"  ! UNMAPPED  {r['state']} {r['section_label']}  {r['heading'][:56]}")
    if unmapped:
        print("\nEvery competitive criterion must be assigned deliberately; an "
              "unmapped one would silently vanish from category totals.", file=sys.stderr)
        return 1

    if not commit:
        by_cat: dict[str, list] = {}
        for r in rows:
            a = ASSIGN[(r["state"], r["section_label"])]
            by_cat.setdefault(a[0] if isinstance(a, tuple) else a, []).append(r)
        print("\nprimary assignment:")
        for name in CATEGORIES:
            got = by_cat.get(name, [])
            pts = sum(x["points_max"] or 0 for x in got)
            print(f"  {name:<40} {len(got):>3} criteria  {pts:>6.0f} pts")
        sec = sum(1 for r in rows if isinstance(ASSIGN[(r['state'], r['section_label'])], tuple))
        print(f"\n{sec} criteria also carry a secondary label (search only, never counted).")
        print("\ndry run - nothing written. Re-run with --commit.")
        return 0

    conn.execute("DELETE FROM criterion_categories")
    conn.execute("DELETE FROM categories WHERE codebook_version = ?", (CODEBOOK_VERSION,))
    ids = {}
    for name, (definition, incl, excl) in CATEGORIES.items():
        cur = conn.execute(
            """INSERT INTO categories (name, definition, inclusion_rules,
                                       exclusion_rules, codebook_version)
               VALUES (?,?,?,?,?)""",
            (name, definition, incl, excl, CODEBOOK_VERSION))
        ids[name] = cur.lastrowid

    n_prim = n_sec = 0
    for r in rows:
        a = ASSIGN[(r["state"], r["section_label"])]
        names = list(a) if isinstance(a, tuple) else [a]
        for i, nm in enumerate(names):
            conn.execute(
                """INSERT INTO criterion_categories
                   (criterion_id, category_id, is_primary, assigned_by)
                   VALUES (?,?,?,?)""",
                (r["id"], ids[nm], 1 if i == 0 else 0, "codebook:" + CODEBOOK_VERSION))
            n_prim += i == 0
            n_sec += i > 0

    # Threshold requirements carry the same category vocabulary, mapped by
    # hand in data/threshold_categories.json keyed 'STATE|section_label'.
    # They are applied here rather than in a separate command because the
    # DELETE above clears the whole table: a separate step would be silently
    # undone by the next taxonomy run, which is what emptied them before.
    n_thresh, unmapped = 0, []
    for r in conn.execute(
            """SELECT c.id, q.state, c.section_label, c.heading
               FROM criteria c JOIN qaps q ON q.id = c.qap_id
               WHERE c.kind = 'threshold'"""):
        cid, state, label, heading = r
        name = THRESHOLD_ASSIGN.get(f"{state}|{label}")
        if name is None:
            unmapped.append(f"{state}|{label} {heading or ''}".strip())
            continue
        conn.execute(
            """INSERT INTO criterion_categories
               (criterion_id, category_id, is_primary, assigned_by)
               VALUES (?,?,1,?)""",
            (cid, ids[name], "threshold-codebook:" + CODEBOOK_VERSION))
        n_thresh += 1

    conn.commit()
    print(f"\nwrote {len(ids)} categories, {n_prim} primary and {n_sec} secondary labels")
    print(f"threshold requirements labelled: {n_thresh}")
    if unmapped:
        print(f"UNMAPPED thresholds ({len(unmapped)}) -- add to "
              f"data/threshold_categories.json:")
        for u in unmapped:
            print("   ", u)
    conn.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=Path("data/qap.db"))
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    return apply(a.db, a.commit)


if __name__ == "__main__":
    raise SystemExit(main())
