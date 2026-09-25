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

    # ---- North Dakota ------------------------------------------------------
    ("ND", "7.A"): AFF,         ("ND", "7.B"): LOC,
    ("ND", "7.C"): PRES,        ("ND", "7.D"): POP,
    ("ND", "7.E"): DES,         ("ND", "7.F"): DES,
    ("ND", "7.G"): DES,         ("ND", "7.H"): POP,
    ("ND", "7.I"): POP,         ("ND", "7.J"): POP,
    ("ND", "7.K"): POP,         ("ND", "7.L"): PRES,
    ("ND", "7.M"): COST,
    # The per-requirement deduction is about application completeness.
    ("ND", "5.deduction"): READY,

    # ---- North Carolina ----------------------------------------------------
    ("NC", "IV.A.1.b.i"): LOC,
    ("NC", "IV.A.1.b.ii.grocery"): LOC,      ("NC", "IV.A.1.b.ii.shopping"): LOC,
    ("NC", "IV.A.1.b.ii.pharmacy"): LOC,     ("NC", "IV.A.1.b.ii.otherprimary"): LOC,
    ("NC", "IV.A.1.b.ii.service"): LOC,      ("NC", "IV.A.1.b.ii.healthcare"): LOC,
    ("NC", "IV.A.1.b.ii.publicfacility"): LOC, ("NC", "IV.A.1.b.ii.publicschool"): LOC,
    ("NC", "IV.A.1.b.ii.otherretail"): LOC,
    # Tribal funds buy amenity points, but what is scored is a funding commitment.
    ("NC", "IV.A.1.b.ii.tribal"): (COST, LOC),
    ("NC", "IV.A.1.b.ii.transit"): LOC,
    ("NC", "IV.A.1.b.iii.1"): LOC,           ("NC", "IV.A.1.b.iii.2"): READY,
    ("NC", "IV.A.1.b.iii.3"): LOC,           ("NC", "IV.A.1.b.iii.4"): READY,
    ("NC", "IV.A.1.b.iv"): READY,
    ("NC", "IV.B.2"): AFF,                   ("NC", "IV.C.1"): COST,
    ("NC", "IV.E.1"): AFF,                   ("NC", "IV.F.2"): SPON,
    ("NC", "IV.F.5.a"): POP,                 ("NC", "IV.F.5.b"): (POP, LOC),
    ("NC", "IV.F.6"): SPON,
    ("NC", "IV.G.2.a"): DES,                 ("NC", "IV.G.2.b"): DES,
    ("NC", "IV.G.2.c"): (PRES, DES),

    # ---- Virginia ----------------------------------------------------------
    ("VA", "E.1"): READY,
    ("VA", "E.2.a"): READY,                  ("VA", "E.2.b"): LOC,
    ("VA", "E.2.c"): LOC,                    ("VA", "E.2.d"): POP,
    ("VA", "E.2.e"): COST,                   ("VA", "E.2.f"): (COST, AFF),
    ("VA", "E.2.g"): COST,                   ("VA", "E.2.h"): PRES,
    ("VA", "E.2.i"): LOC,                    ("VA", "E.2.j"): PRES,
    ("VA", "E.2.k"): LOC,                    ("VA", "E.2.l"): LOC,
    ("VA", "E.3.a.1.a"): DES,                ("VA", "E.3.a.1.b.brick"): DES,
    ("VA", "E.3.a.1.b.fibercement"): DES,    ("VA", "E.3.a.1.c"): DES,
    ("VA", "E.3.a.1.d"): DES,                ("VA", "E.3.a.1.e"): DES,
    ("VA", "E.3.a.1.f.fan"): DES,            ("VA", "E.3.a.1.f.humidistat"): DES,
    ("VA", "E.3.a.1.g"): DES,                ("VA", "E.3.a.1.h.hookups"): DES,
    ("VA", "E.3.a.1.h.systems"): DES,        ("VA", "E.3.a.1.i"): DES,
    ("VA", "E.3.a.1.j"): DES,                ("VA", "E.3.a.1.k"): DES,
    ("VA", "E.3.a.1.l"): DES,                ("VA", "E.3.a.1.m"): DES,
    ("VA", "E.3.a.1.n"): DES,
    ("VA", "E.3.a.2.a"): (DES, POP),         ("VA", "E.3.a.2.b"): (DES, POP),
    ("VA", "E.3.a.2.c"): (DES, POP),         ("VA", "E.3.a.2.d"): (DES, POP),
    ("VA", "E.3.a.3.a"): PRES,               ("VA", "E.3.a.3.b"): DES,
    ("VA", "E.3.a.3.c"): LOC,
    ("VA", "E.3.d.1"): DES,                  ("VA", "E.3.d.2"): DES,
    ("VA", "E.3.e"): DES,                    ("VA", "E.3.f"): COST,
    ("VA", "E.3.g"): COST,
    ("VA", "E.4"): POP,
    ("VA", "E.5.a"): SPON,                   ("VA", "E.5.b"): SPON,
    ("VA", "E.5.c.1"): SPON,                 ("VA", "E.5.c.2"): SPON,
    ("VA", "E.5.c.3"): SPON,                 ("VA", "E.5.c.4"): SPON,
    ("VA", "E.5.c.5"): SPON,                 ("VA", "E.5.c.6"): SPON,
    ("VA", "E.6"): COST,
    ("VA", "E.7.a"): AFF,                    ("VA", "E.7.b"): AFF,
    ("VA", "E.7.c"): AFF,                    ("VA", "E.7.d"): SPON,
    ("VA", "E.7.e"): (AFF, PRES),            ("VA", "E.7.f"): SPON,

    # ---- Arkansas ----------------------------------------------------------
    ("AR", "II.A.1"): LOC,              ("AR", "II.A.2"): POP,
    ("AR", "II.A.3"): PRES,             ("AR", "II.A.4"): COST,
    ("AR", "II.A.5"): PRES,             ("AR", "II.A.6"): LOC,
    ("AR", "II.A.7"): AFF,              ("AR", "II.A.8"): LOC,
    ("AR", "II.A.8.adjacent"): LOC,     ("AR", "II.A.8.nearby"): LOC,
    ("AR", "II.A.9"): COST,             ("AR", "II.A.10"): AFF,
    ("AR", "II.A.11"): (AFF, PRES),     ("AR", "II.A.12"): LOC,
    ("AR", "II.A.13"): DES,             ("AR", "II.A.14"): SPON,
    ("AR", "II.A.15"): SPON,

    # ---- Hawaii ------------------------------------------------------------
    ("HI", "III.D.1"): COST,            ("HI", "III.D.2"): LOC,
    ("HI", "III.D.3"): COST,            ("HI", "III.D.4"): READY,
    ("HI", "III.D.5"): POP,             ("HI", "III.D.6"): (AFF, POP),
    ("HI", "III.D.7"): COST,            ("HI", "III.D.8"): COST,
    ("HI", "III.D.9"): DES,             ("HI", "III.D.10"): LOC,
    ("HI", "III.D.11"): SPON,           ("HI", "III.D.12"): AFF,
    ("HI", "III.D.13"): POP,            ("HI", "III.D.14"): POP,
    ("HI", "III.D.15"): AFF,            ("HI", "III.D.16"): SPON,
    ("HI", "III.D.17"): POP,            ("HI", "III.D.18"): LOC,
    ("HI", "III.D.19"): PRES,           ("HI", "III.D.20"): LOC,
    ("HI", "III.D.21"): COST,           ("HI", "III.D.22"): AFF,
    ("HI", "III.D.23"): PRES,

    # ---- Missouri ----------------------------------------------------------
    # The Phase II award is a flat 45 for meeting any of nine priority groups,
    # which span several categories; it is filed under readiness as the gate
    # that lets an application proceed rather than under any one subject.
    ("MO", "IV.B"): READY,
    ("MO", "IV.C.1.income"): AFF,       ("MO", "IV.C.1.mixedincome"): AFF,
    ("MO", "IV.C.1.homeownership"): POP, ("MO", "IV.C.1.serviceenriched"): POP,
    ("MO", "IV.C.1.supportive"): POP,   ("MO", "IV.C.1.extended"): AFF,
    ("MO", "IV.C.1.previousphase"): SPON,
    ("MO", "IV.C.2.costburden"): LOC,   ("MO", "IV.C.2.opportunity"): LOC,
    ("MO", "IV.C.2.rural"): LOC,        ("MO", "IV.C.2.preservation"): PRES,
    ("MO", "IV.C.3.favorable"): COST,   ("MO", "IV.C.3.localsupport"): COST,
    ("MO", "IV.C.3.cdbgdr"): COST,      ("MO", "IV.C.3.pbra"): (AFF, COST),
    ("MO", "IV.C.3.creditefficiency"): COST,
    ("MO", "IV.C.4.priorperformance"): SPON,

    # ---- Wisconsin ---------------------------------------------------------
    ("WI", "C.1.a"): LOC,       ("WI", "C.1.b"): LOC,
    ("WI", "C.1.c"): LOC,       ("WI", "C.1.d"): LOC,
    ("WI", "C.1.e"): LOC,       ("WI", "C.2.a"): LOC,
    ("WI", "C.2.b"): LOC,       ("WI", "C.3"): (PRES, LOC),
    ("WI", "C.4.a"): LOC,       ("WI", "C.4.b"): LOC,
    ("WI", "C.5"): POP,         ("WI", "C.6"): AFF,
    ("WI", "C.7"): POP,         ("WI", "C.8"): POP,
    ("WI", "C.9"): DES,         ("WI", "C.10"): DES,
    ("WI", "C.11"): POP,        ("WI", "C.12"): COST,
    ("WI", "C.13.a"): DES,      ("WI", "C.13.b"): DES,
    ("WI", "C.14"): COST,       ("WI", "C.15"): SPON,
    ("WI", "C.16"): READY,

    # ---- Alabama -----------------------------------------------------------
    ("AL", "A.1.i.a"): DES,                 ("AL", "A.1.i.newconstruction"): DES,
    ("AL", "A.1.i.rehabilitation"): (PRES, DES), ("AL", "A.1.ii"): DES,
    ("AL", "A.1.iii.a"): COST,              ("AL", "A.1.iii.b"): (COST, PRES),
    ("AL", "A.1.iii.c"): (AFF, COST),       ("AL", "A.1.iii.d"): AFF,
    ("AL", "A.1.iv.a"): POP,                ("AL", "A.1.iv.b"): POP,
    ("AL", "A.1.iv.c"): POP,                ("AL", "A.1.iv.d"): POP,
    ("AL", "A.1.iv.e"): DES,
    ("AL", "A.1.v.a"): PRES,                ("AL", "A.1.v.b"): PRES,
    ("AL", "A.1.v.c"): PRES,                ("AL", "A.1.v.d"): PRES,
    ("AL", "A.1.vi.a"): LOC,
    ("AL", "A.1.vi.b.1.adjacent"): LOC,     ("AL", "A.1.vi.b.1.nearby"): LOC,
    ("AL", "A.1.vi.b.2"): LOC,
    ("AL", "A.2.i"): SPON,                  ("AL", "A.2.ii"): SPON,
    ("AL", "A.2.iii"): SPON,
    ("AL", "B.1.i"): SPON,                  ("AL", "B.2"): SPON,

    # ---- New York ----------------------------------------------------------
    ("NY", "2040.3.f.1"): LOC,      ("NY", "2040.3.f.2"): COST,
    ("NY", "2040.3.f.3"): SPON,     ("NY", "2040.3.f.4"): DES,
    ("NY", "2040.3.f.5"): DES,      ("NY", "2040.3.f.6"): AFF,
    ("NY", "2040.3.f.7"): POP,      ("NY", "2040.3.f.8"): READY,
    ("NY", "2040.3.f.9"): POP,      ("NY", "2040.3.f.10"): SPON,
    ("NY", "2040.3.f.11"): AFF,     ("NY", "2040.3.f.12"): PRES,
    ("NY", "2040.3.f.13"): COST,    ("NY", "2040.3.f.14"): LOC,
    ("NY", "2040.3.f.15"): LOC,     ("NY", "2040.3.f.16"): LOC,
    ("NY", "2040.3.f.17"): SPON,

    # ---- South Dakota ------------------------------------------------------
    ("SD", "V.A.1"): AFF,       ("SD", "V.A.2"): AFF,
    ("SD", "V.A.3"): (PRES, POP), ("SD", "V.A.4"): LOC,
    ("SD", "V.A.5"): COST,      ("SD", "V.A.6.a"): SPON,
    ("SD", "V.A.6.b"): SPON,    ("SD", "V.A.6.d"): SPON,
    ("SD", "V.A.7"): POP,       ("SD", "V.A.8"): COST,
    ("SD", "V.A.9.a"): LOC,     ("SD", "V.A.9.b"): LOC,
    ("SD", "V.A.10"): POP,      ("SD", "V.A.11"): POP,
    ("SD", "V.B.1"): READY,     ("SD", "V.B.2"): READY,
    ("SD", "V.B.3"): READY,     ("SD", "V.B.4"): READY,
    ("SD", "V.B.5"): READY,     ("SD", "V.B.6"): READY,
    # Project Characteristics defers entirely to Exhibit 4, which is not in the
    # corpus; filed under design as the closest fit, flagged in its note.
    ("SD", "V.C"): DES,         ("SD", "V.D"): POP,
    ("SD", "V.E"): LOC,

    # ---- Ohio --------------------------------------------------------------
    # Three index-driven criteria, the shortest scoring system in the corpus.
    ("OH", "H.1"): LOC,     ("OH", "H.2"): LOC,     ("OH", "H.3"): COST,

    # ---- Pennsylvania ------------------------------------------------------
    ("PA", "A.1"): LOC,     ("PA", "A.2"): LOC,     ("PA", "A.3"): LOC,
    ("PA", "B.1"): AFF,     ("PA", "B.2"): POP,     ("PA", "B.3"): DES,
    ("PA", "B.4"): POP,     ("PA", "B.5"): DES,     ("PA", "B.6"): POP,
    ("PA", "C.1"): LOC,     ("PA", "C.2"): DES,     ("PA", "C.3"): DES,
    ("PA", "C.4"): COST,
    ("PA", "D.1"): SPON,    ("PA", "D.2"): SPON,    ("PA", "D.3"): READY,
    ("PA", "D.4"): COST,    ("PA", "D.5"): SPON,
    ("PA", "E"): COST,      ("PA", "F"): READY,

    # ---- Delaware ----------------------------------------------------------
    ("DE", "1.1"): AFF,     ("DE", "1.2"): PRES,    ("DE", "1.3"): DES,
    ("DE", "1.4"): POP,     ("DE", "1.5"): DES,
    ("DE", "2.1"): LOC,     ("DE", "2.2"): LOC,     ("DE", "2.3"): LOC,
    ("DE", "2.4"): DES,
    ("DE", "3.1"): AFF,     ("DE", "3.2"): POP,     ("DE", "3.3"): POP,
    ("DE", "3.4"): AFF,
    ("DE", "4.1"): COST,    ("DE", "4.2"): COST,    ("DE", "4.3"): AFF,
    ("DE", "4.4"): PRES,
    ("DE", "5.1"): SPON,    ("DE", "5.2"): SPON,    ("DE", "5.3"): SPON,
    ("DE", "5.4"): READY,
    ("DE", "BONUS"): COST,

    # ---- Michigan ----------------------------------------------------------
    # Parallel urban (A) and rural (B) tracks share categories name for name.
    ("MI", "A.1"): LOC,     ("MI", "A.2"): LOC,     ("MI", "A.3"): LOC,
    ("MI", "A.4"): LOC,     ("MI", "A.5"): LOC,     ("MI", "A.6"): LOC,
    ("MI", "A.7"): LOC,
    ("MI", "B.1"): LOC,     ("MI", "B.2"): LOC,     ("MI", "B.3"): LOC,
    ("MI", "B.4"): LOC,     ("MI", "B.5"): LOC,     ("MI", "B.6"): LOC,
    ("MI", "B.7"): LOC,
    ("MI", "C.1"): POP,     ("MI", "C.2"): AFF,     ("MI", "C.3"): PRES,
    ("MI", "C.4"): AFF,     ("MI", "C.5"): AFF,     ("MI", "C.6"): POP,
    ("MI", "C.7"): DES,     ("MI", "C.8"): READY,   ("MI", "C.9"): READY,
    ("MI", "C.10"): POP,    ("MI", "C.11"): DES,    ("MI", "C.12"): COST,
    ("MI", "C.13"): PRES,   ("MI", "C.14"): AFF,
    ("MI", "D.1"): SPON,    ("MI", "D.2"): SPON,    ("MI", "D.3"): SPON,
    ("MI", "D.4"): SPON,    ("MI", "D.5"): SPON,    ("MI", "D.6"): SPON,
    ("MI", "E.1"): POP,     ("MI", "E.2"): POP,     ("MI", "E.3"): POP,
    ("MI", "E.4"): LOC,     ("MI", "E.5"): SPON,    ("MI", "E.6"): POP,
    ("MI", "E.7"): POP,     ("MI", "E.8"): POP,     ("MI", "E.9"): POP,
    ("MI", "E.10"): POP,
    ("MI", "F.1"): COST,

    # ---- Nevada ------------------------------------------------------------
    # 7.2 project type priorities are populations; 7.2.9 is Tribal housing,
    # scored on credits per bedroom, so cost is secondary.
    ("NV", "7.2.1"): POP,   ("NV", "7.2.2"): POP,   ("NV", "7.2.3"): POP,
    ("NV", "7.2.4"): POP,   ("NV", "7.2.5"): (AFF, POP),
    ("NV", "7.2.6"): LOC,   ("NV", "7.2.7"): POP,
    ("NV", "7.2.8"): (COST, DES),
    ("NV", "7.2.9"): (POP, COST),
    ("NV", "7.3.1"): LOC,   ("NV", "7.3.2"): READY, ("NV", "7.3.3"): DES,
    ("NV", "7.3.4"): SPON,  ("NV", "7.3.5"): AFF,   ("NV", "7.3.6"): DES,
    ("NV", "7.3.7"): PRES,  ("NV", "7.3.8"): (LOC, DES, COST),
    ("NV", "7.3.9.A"): COST, ("NV", "7.3.9.B"): COST,
    ("NV", "7.3.9.C"): PRES, ("NV", "7.3.9.D"): PRES, ("NV", "7.3.9.E"): PRES,
    ("NV", "7.3.9.F"): AFF,  ("NV", "7.3.9.G"): AFF,  ("NV", "7.3.9.H"): READY,
    ("NV", "7.4.1"): AFF,   ("NV", "7.4.2"): AFF,   ("NV", "7.4.3"): POP,
    ("NV", "7.4.4"): COST,  ("NV", "7.4.5"): COST,
    ("NV", "7.4.6.A"): COST, ("NV", "7.4.6.B"): COST,
    ("NV", "7.6"): SPON,    ("NV", "16.reduction"): SPON, ("NV", "16.waiver"): READY,
    ("NV", "8.2.ami"): AFF, ("NV", "8.2.site"): LOC,  ("NV", "8.2.land"): COST,
    ("NV", "8.2.leverage"): COST, ("NV", "8.2.owner"): SPON,
    ("NV", "8.2.ded.compliance"): SPON, ("NV", "8.2.ded.pricing"): COST,
    ("NV", "8.2.ded.finance"): READY,   ("NV", "8.2.ded.cost"): COST,

    # ---- Iowa --------------------------------------------------------------
    # 6.1.F pays for limiting the credit to a 6% rate, so cost is secondary.
    ("IA", "6.1.A"): AFF,   ("IA", "6.1.B"): AFF,   ("IA", "6.1.C"): POP,
    ("IA", "6.1.D.1"): AFF, ("IA", "6.1.D.2"): AFF, ("IA", "6.1.E"): AFF,
    ("IA", "6.1.F"): (AFF, COST),
    ("IA", "6.2.A"): LOC,   ("IA", "6.2.B"): LOC,   ("IA", "6.2.C"): LOC,
    ("IA", "6.2.D"): LOC,   ("IA", "6.2.E"): LOC,   ("IA", "6.2.F"): LOC,
    ("IA", "6.2.G"): LOC,   ("IA", "6.2.H"): (LOC, READY),
    ("IA", "6.3.A"): DES,   ("IA", "6.3.B"): DES,   ("IA", "6.3.C"): DES,
    ("IA", "6.3.D"): DES,   ("IA", "6.3.E"): DES,   ("IA", "6.3.F"): AFF,
    ("IA", "6.3.G"): DES,   ("IA", "6.3.H"): DES,   ("IA", "6.3.I"): (DES, PRES),
    ("IA", "6.3.J"): (DES, PRES), ("IA", "6.3.K"): (DES, POP),
    ("IA", "6.3.L"): DES,   ("IA", "6.3.M"): DES,   ("IA", "6.3.N"): DES,
    ("IA", "6.4.A"): SPON,  ("IA", "6.4.B.1"): SPON, ("IA", "6.4.B.2"): SPON,
    ("IA", "6.4.C"): (SPON, READY),
    ("IA", "6.5.A"): READY, ("IA", "6.5.B"): PRES,
    ("IA", "7.10.B"): READY,

    # ---- Alaska ------------------------------------------------------------
    # Section 4 Market Conditions scores local demand; filed under location.
    ("AK", "1.a"): LOC,     ("AK", "1.b"): LOC,
    ("AK", "2.a"): DES,     ("AK", "2.b"): POP,     ("AK", "2.c"): DES,
    ("AK", "2.d"): PRES,    ("AK", "2.e"): DES,     ("AK", "2.f"): POP,
    ("AK", "2.g"): AFF,
    ("AK", "3.a"): AFF,     ("AK", "3.b"): AFF,     ("AK", "3.c"): POP,
    ("AK", "3.d"): (AFF, LOC), ("AK", "3.e"): AFF,  ("AK", "3.f"): POP,
    ("AK", "3.g"): POP,     ("AK", "3.h"): POP,     ("AK", "3.i"): POP,
    ("AK", "4.a"): LOC,     ("AK", "4.b"): LOC,     ("AK", "4.c"): LOC,
    ("AK", "5.a"): READY,   ("AK", "5.a.v"): READY, ("AK", "5.b"): COST,
    ("AK", "5.b.iii"): READY, ("AK", "5.c"): READY,
    ("AK", "6.a"): COST,    ("AK", "6.b"): COST,
    ("AK", "7.a"): SPON,    ("AK", "7.b"): SPON,
    ("AK", "8"): POP,

    # ---- Arizona -----------------------------------------------------------
    # Rehab (V.B) and new construction (V.C) are separate tracks; the shared
    # CRP/QCT and developer experience criteria are labelled alike in both.
    ("AZ", "V.B.1"): PRES,  ("AZ", "V.B.2"): PRES,  ("AZ", "V.B.3"): AFF,
    ("AZ", "V.B.4"): LOC,   ("AZ", "V.B.5"): SPON,
    ("AZ", "V.C.1"): SPON,  ("AZ", "V.C.2"): POP,   ("AZ", "V.C.3"): LOC,
    ("AZ", "V.C.4"): LOC,   ("AZ", "V.C.5"): COST,  ("AZ", "V.C.6"): POP,
    ("AZ", "V.C.7"): DES,   ("AZ", "V.C.8"): AFF,   ("AZ", "V.C.9"): SPON,

    # ---- New Jersey --------------------------------------------------------
    # Core categories shared by all three cycles, then each cycle's add-ons.
    # 33.15(a)21 is recorded on both the family and senior tracks.
    ("NJ", "33.15(a)1"): AFF,      ("NJ", "33.15(a)2"): POP,
    ("NJ", "33.15(a)4"): COST,     ("NJ", "33.15(a)6"): SPON,
    ("NJ", "33.15(a)7"): LOC,      ("NJ", "33.15(a)8"): DES,
    ("NJ", "33.15(a)9"): DES,      ("NJ", "33.15(a)10"): DES,
    ("NJ", "33.15(a)11i"): LOC,    ("NJ", "33.15(a)11ii"): LOC,
    ("NJ", "33.15(a)12"): READY,   ("NJ", "33.15(a)13"): DES,
    ("NJ", "33.15(a)14i"): (PRES, LOC), ("NJ", "33.15(a)14iv-v"): LOC,
    ("NJ", "33.15(a)15"): SPON,    ("NJ", "33.15(a)16"): SPON,
    ("NJ", "33.15(a)17"): SPON,    ("NJ", "33.15(a)18"): SPON,
    ("NJ", "33.15(a)19"): SPON,    ("NJ", "33.15(a)20"): SPON,
    ("NJ", "33.15(a)22"): AFF,     ("NJ", "33.15(a)23"): READY,
    ("NJ", "33.15(a)24"): SPON,    ("NJ", "33.15(a)25"): (AFF, COST),
    ("NJ", "33.15(a)3"): POP,      ("NJ", "33.15(a)5"): POP,
    ("NJ", "33.15(a)14ii"): LOC,   ("NJ", "33.15(a)14iii"): LOC,
    ("NJ", "33.15(a)21.family"): POP, ("NJ", "33.15(a)21.senior"): POP,
    ("NJ", "33.16(b)1"): LOC,      ("NJ", "33.16(b)2"): POP,
    ("NJ", "33.17(a)1"): POP,      ("NJ", "33.17(a)2-3"): LOC,
    ("NJ", "33.17(b)1"): POP,      ("NJ", "33.17(b)2"): POP,
    ("NJ", "33.17(b)3"): POP,      ("NJ", "33.17(b)4"): AFF,
    ("NJ", "33.17(b)5"): SPON,     ("NJ", "33.17(b)6"): POP,
    ("NJ", "33.17(b)7"): DES,

    # ---- Minnesota (self-scoring worksheet) ---------------------------------
    ("MN", "1.A"): POP,     ("MN", "1.B"): POP,     ("MN", "1.C"): POP,
    ("MN", "1.D"): POP,
    ("MN", "2.A"): PRES,    ("MN", "2.B"): AFF,     ("MN", "2.C"): AFF,
    ("MN", "2.D"): AFF,
    ("MN", "3.A"): LOC,     ("MN", "3.B"): LOC,     ("MN", "3.C"): LOC,
    ("MN", "4.A"): LOC,     ("MN", "4.B"): (POP, LOC), ("MN", "4.C"): LOC,
    ("MN", "4.D"): LOC,     ("MN", "4.E"): LOC,     ("MN", "4.F"): SPON,
    ("MN", "4.G"): LOC,
    ("MN", "5.A"): (COST, READY), ("MN", "5.B"): COST, ("MN", "5.C"): COST,
    ("MN", "6.A"): (DES, COST), ("MN", "6.B"): DES, ("MN", "6.C"): DES,
    ("MN", "7"): SPON,

    # ---- Oklahoma ----------------------------------------------------------
    ("OK", "SC.1"): AFF,    ("OK", "SC.2"): AFF,    ("OK", "SC.3"): LOC,
    ("OK", "SC.4"): POP,    ("OK", "SC.5"): POP,    ("OK", "SC.6"): PRES,
    ("OK", "SC.7"): DES,    ("OK", "SC.8"): PRES,   ("OK", "SC.9"): DES,
    ("OK", "SC.10"): COST,  ("OK", "SC.11"): SPON,
    ("OK", "OAHTC.efficiency"): COST,

    # ---- Wyoming -----------------------------------------------------------
    # Housing Needs scores market demand at the site, filed under location.
    ("WY", "1.a"): LOC,     ("WY", "1.b"): LOC,     ("WY", "1.c"): LOC,
    ("WY", "1.d"): LOC,     ("WY", "1.e"): LOC,
    ("WY", "2.a"): DES,
    ("WY", "3.a"): LOC,     ("WY", "3.a.dynamic"): LOC, ("WY", "3.b"): LOC,
    ("WY", "3.c"): LOC,     ("WY", "3.d"): (READY, LOC), ("WY", "3.d.neg"): (READY, LOC),
    ("WY", "3.e"): LOC,
    ("WY", "4.a"): DES,     ("WY", "4.b"): READY,   ("WY", "4.c"): READY,
    ("WY", "4.d"): AFF,
    ("WY", "5.a"): SPON,    ("WY", "5.b"): SPON,
    ("WY", "6.a"): COST,    ("WY", "6.b"): COST,    ("WY", "6.c"): COST,
    ("WY", "6.d"): COST,

    # ---- Colorado ----------------------------------------------------------
    ("CO", "5.A.1"): AFF,   ("CO", "5.A.1.county"): (AFF, LOC),
    ("CO", "5.A.1.d"): AFF, ("CO", "5.A.2"): AFF,   ("CO", "5.A.3"): LOC,
    ("CO", "5.B.1"): LOC,   ("CO", "5.B.2.a"): LOC, ("CO", "5.B.2.b"): LOC,
    ("CO", "5.B.3.a"): AFF, ("CO", "5.B.3.b"): LOC, ("CO", "5.B.3.c"): PRES,
    ("CO", "5.B.3.d"): PRES, ("CO", "5.B.3.e"): DES, ("CO", "5.B.3.f"): (COST, DES),
    ("CO", "5.B.3.g"): DES, ("CO", "5.B.3.h"): POP,
    ("CO", "5.B.4"): SPON,  ("CO", "5.B.5"): POP,   ("CO", "5.B.6"): POP,

    # ---- Indiana -----------------------------------------------------------
    # Core track plus nine_pct (6.1(A), 6.1(B), 6.3(B)) and bond (6.6(A)).
    ("IN", "6.1(A)"): AFF,  ("IN", "6.1(B)"): AFF,  ("IN", "6.1(C)"): AFF,
    ("IN", "6.2(A)"): DES,  ("IN", "6.2(B)"): DES,  ("IN", "6.2(C)"): DES,
    ("IN", "6.2(D)"): PRES, ("IN", "6.2(E)"): PRES, ("IN", "6.2(E).bonus"): PRES,
    ("IN", "6.2(F)"): LOC,  ("IN", "6.2(G)"): PRES, ("IN", "6.2(H)"): PRES,
    ("IN", "6.2(I)"): DES,  ("IN", "6.2(J)"): AFF,  ("IN", "6.2(K)"): DES,
    ("IN", "6.2(L)"): DES,
    ("IN", "6.3(A)"): LOC,  ("IN", "6.3(A).undesirable"): LOC,
    ("IN", "6.3(B)"): LOC,  ("IN", "6.3(C)"): LOC,  ("IN", "6.3(D)"): LOC,
    ("IN", "6.3(D).recap"): LOC, ("IN", "6.3(E)"): LOC, ("IN", "6.3(F)"): LOC,
    ("IN", "6.3(G)"): LOC,  ("IN", "6.3(H)"): LOC,  ("IN", "6.3(I)"): LOC,
    ("IN", "6.4(A)"): COST, ("IN", "6.4(B)"): COST, ("IN", "6.4(C)"): AFF,
    ("IN", "6.4(D)"): COST,
    ("IN", "6.5(A)"): SPON, ("IN", "6.5(B)"): DES,  ("IN", "6.5(C)"): POP,
    ("IN", "6.5(D)"): POP,  ("IN", "6.5(E)"): POP,  ("IN", "6.5(F)"): POP,
    ("IN", "6.5(G)"): POP,  ("IN", "6.5(H)"): POP,  ("IN", "6.5(I)"): READY,
    ("IN", "6.5(J)"): SPON, ("IN", "6.6(A)"): SPON,
    ("IL", "IX.C.i.a"): SPON, ("IL", "IX.C.i.b"): SPON, ("IL", "IX.C.i.c"): SPON,
    ("IL", "IX.C.i.d"): SPON, ("IL", "IX.C.ii.a"): COST, ("IL", "IX.C.ii.b"): AFF,
    ("IL", "IX.C.ii.c"): COST, ("IL", "IX.C.iii.a"): LOC, ("IL", "IX.C.iii.b"): LOC,
    ("IL", "IX.C.iii.c"): LOC, ("IL", "IX.C.iv.a"): DES, ("IL", "IX.C.iv.b"): DES,
    ("IL", "IX.C.iv.c"): DES, ("IL", "IX.C.v.a"): POP, ("IL", "IX.C.vi.a"): DES,
    ("IL", "IX.D.a"): PRES, ("IL", "IX.D.b"): PRES, ("IL", "IX.D.c"): COST,
    ("IL", "IX.D.d"): COST, ("IL", "IX.D.e"): COST, ("IL", "IX.E.a"): POP,
    ("IL", "IX.E.b"): POP, ("IL", "IX.E.c"): POP, ("IL", "IX.E.d"): POP,
    ("IL", "IX.E.e"): POP, ("IL", "IX.E.f"): SPON, ("IL", "IX.F.a"): LOC,
    ("IL", "IX.F.b"): LOC, ("IL", "IX.F.c"): LOC, ("IL", "IX.F.d"): LOC,
    ("IL", "IX.F.e"): LOC, ("IL", "IX.F.f"): LOC,
    ("NM", "V.A"): SPON, ("NM", "V.B"): LOC, ("NM", "V.C"): PRES, ("NM", "V.D"): PRES,
    ("NM", "V.E"): AFF, ("NM", "V.F"): AFF, ("NM", "V.G"): AFF, ("NM", "V.H"): POP,
    ("NM", "V.I"): POP, ("NM", "V.J"): POP, ("NM", "V.K"): COST, ("NM", "V.L"): POP,
    ("NM", "V.M"): LOC, ("NM", "V.N"): AFF, ("NM", "V.O"): PRES, ("NM", "V.P"): COST,
    ("NM", "V.Q"): DES, ("NM", "V.R"): PRES, ("NM", "V.S"): LOC, ("NM", "V.T"): AFF,
    ("KS", "VII.A.1"): SPON, ("KS", "VII.A.2"): SPON, ("KS", "VII.A.3.dev"): SPON,
    ("KS", "VII.A.3.comp"): SPON, ("KS", "VII.B"): LOC, ("KS", "VII.C"): LOC,
    ("KS", "VII.D"): LOC, ("KS", "VII.E"): LOC, ("KS", "VII.F.1"): LOC,
    ("KS", "VII.F.2"): LOC, ("KS", "VII.G.1"): COST, ("KS", "VII.G.2"): COST,
    ("KS", "VII.H"): LOC, ("KS", "VII.I"): LOC, ("KS", "VII.J.1"): POP,
    ("KS", "VII.J.2"): POP, ("KS", "VII.K.1"): AFF, ("KS", "VII.K.2"): AFF,
    ("KS", "VII.K.3"): AFF, ("KS", "VII.K.4"): AFF, ("KS", "VII.K.5"): AFF,
    ("ID", "6.4.1"): LOC, ("ID", "6.4.2"): DES, ("ID", "6.4.3"): POP, ("ID", "6.4.4"): AFF,
    ("ID", "6.4.5"): POP, ("ID", "6.4.6"): POP, ("ID", "6.4.7"): POP, ("ID", "6.4.8"): COST,
    ("ID", "6.4.9"): SPON, ("ID", "6.4.10"): LOC, ("ID", "6.4.11"): PRES, ("ID", "6.4.12"): AFF,
    ("ID", "6.4.13"): LOC, ("ID", "6.4.14"): COST, ("ID", "6.4.15"): PRES, ("ID", "6.4.16"): LOC,
    ("ID", "6.4.17"): POP, ("ID", "6.4.18"): POP, ("ID", "6.4.19"): COST, ("ID", "6.4.20"): SPON,
    ("ID", "6.5.1"): AFF, ("ID", "6.5.2"): AFF, ("ID", "6.5.3"): AFF, ("ID", "6.5.4"): AFF,
    ("ID", "6.5.5"): LOC, ("ID", "6.6.1"): SPON, ("ID", "6.6.2"): SPON, ("ID", "6.6.3"): SPON,
    ("ID", "6.6.4"): SPON, ("ID", "6.6.5"): READY, ("ID", "6.6.6"): SPON,
    ("MS", "SC.1"): LOC, ("MS", "SC.2"): LOC, ("MS", "SC.3"): LOC, ("MS", "SC.4"): LOC,
    ("MS", "SC.5"): DES, ("MS", "SC.6"): DES, ("MS", "SC.7"): DES, ("MS", "SC.8.A"): DES,
    ("MS", "SC.8.B"): PRES, ("MS", "SC.9"): AFF, ("MS", "SC.10.a"): POP, ("MS", "SC.10.b"): POP,
    ("MS", "SC.10.c"): POP, ("MS", "SC.11"): SPON, ("MS", "SC.12"): SPON, ("MS", "SC.12.neg"): SPON,
    ("MS", "PA.1"): LOC, ("MS", "PA.2"): COST, ("MS", "PA.3"): READY, ("MS", "PA.4"): READY,
    ("GA", "III"): AFF, ("GA", "IV"): COST, ("GA", "V"): SPON, ("GA", "VI"): POP,
    ("GA", "VII"): READY, ("GA", "VIII"): AFF, ("GA", "IX"): POP, ("GA", "XXII"): POP,
    ("GA", "XXIII"): LOC, ("GA", "X.A"): LOC, ("GA", "X.B"): LOC, ("GA", "XI"): LOC,
    ("GA", "XII"): LOC, ("GA", "XIII"): LOC, ("GA", "XIV"): LOC, ("GA", "XV"): LOC,
    ("GA", "XVI"): LOC, ("GA", "XVII"): LOC, ("GA", "XVIII"): LOC, ("GA", "XIX"): LOC,
    ("GA", "XX"): AFF, ("GA", "XXI"): PRES, ("GA", "XXIV.A"): PRES, ("GA", "XXIV.B"): PRES,
    ("GA", "XXIV.C"): PRES, ("GA", "XXIV.D"): PRES, ("GA", "XXIV.E"): LOC, ("GA", "XXIV.F.1"): PRES,
    ("GA", "XXIV.F.2"): PRES, ("GA", "XXIV.F.3"): PRES, ("GA", "XXIV.F.4"): PRES,
    ("TN", "17.A.1"): LOC, ("TN", "17.A.2"): AFF, ("TN", "17.A.3"): DES, ("TN", "17.A.4"): SPON,
    ("TN", "17.A.5"): READY, ("TN", "17.A.6"): READY, ("TN", "17.A.7"): READY, ("TN", "17.A.8"): READY,
    ("TN", "17.A.9"): POP, ("TN", "17.A.10"): POP, ("TN", "17.A.11"): AFF, ("TN", "17.A.12"): DES,
    ("TN", "17.A.13"): LOC, ("TN", "17.A.14"): AFF, ("TN", "17.A.15"): AFF, ("TN", "17.B.1"): LOC,
    ("TN", "17.B.2"): PRES, ("TN", "17.B.3"): DES, ("TN", "17.B.4"): SPON, ("TN", "17.B.5"): POP,
    ("TN", "17.B.6"): POP, ("TN", "17.B.7"): POP, ("TN", "17.B.8"): AFF, ("TN", "17.B.9"): DES,
    ("TN", "17.B.10"): LOC, ("TN", "17.B.11"): AFF, ("TN", "17.B.12"): AFF,
    ("WV", "PC.1"): DES, ("WV", "PC.3.a"): COST, ("WV", "PC.3.d"): COST, ("WV", "PC.5"): AFF,
    ("WV", "AP.1"): READY, ("WV", "AP.2"): READY, ("WV", "AP.3"): SPON, ("WV", "AP.4"): SPON,
    ("WV", "AP.5"): SPON, ("WV", "AP.6"): SPON, ("WV", "AP.7"): READY, ("WV", "LH.1"): LOC,
    ("WV", "LH.2"): LOC, ("WV", "LH.3"): LOC, ("WV", "LH.4"): LOC, ("WV", "LH.5.a"): LOC,
    ("WV", "LH.5.b"): LOC, ("WV", "LH.6.a"): LOC, ("WV", "LH.6.b"): LOC, ("WV", "LH.6.c"): LOC,
    ("WV", "LH.6.d"): LOC, ("WV", "LH.6.e"): LOC, ("WV", "LH.6.f"): LOC, ("WV", "LH.6.g.1"): LOC,
    ("WV", "LH.6.g.2"): LOC, ("WV", "LH.6.h"): LOC, ("WV", "SC.1"): POP, ("WV", "TP.1"): POP,
    ("WV", "PW.1"): POP, ("WV", "TO.1"): AFF, ("WV", "HN.1"): PRES, ("WV", "LI.1"): AFF,
    ("WV", "LP.1"): AFF, ("WV", "QC.1"): LOC, ("WV", "EQ.1"): DES, ("WV", "EQ.2"): DES,
    ("WV", "EQ.3"): DES, ("WV", "EQ.4"): DES, ("WV", "EQ.5"): DES, ("WV", "EQ.6"): DES,
    ("WV", "EQ.7"): DES, ("WV", "EQ.8"): DES, ("WV", "EQ.9"): DES, ("WV", "EQ.11"): DES,
    ("WV", "EQ.12"): DES, ("WV", "EQ.13"): DES, ("WV", "EQ.14"): DES, ("WV", "EQ.10"): DES,
    ("WV", "PC.1.E"): DES, ("WV", "PC.2.E"): PRES, ("WV", "PC.3.a.E"): COST, ("WV", "PC.3.b.E"): PRES,
    ("WV", "PC.3.c.E"): PRES, ("WV", "PC.3.d.E"): COST, ("WV", "PC.4.E"): LOC, ("WV", "PC.5.E"): AFF,
    ("WV", "AP.1.E"): READY, ("WV", "AP.2.E"): READY, ("WV", "AP.3.E"): SPON, ("WV", "AP.4.E"): SPON,
    ("WV", "AP.5.E"): SPON, ("WV", "AP.6.E"): SPON, ("WV", "AP.7.E"): READY, ("WV", "LH.1.E"): LOC,
    ("WV", "LH.2.E"): LOC, ("WV", "LH.3.E"): LOC, ("WV", "LH.4.E"): LOC, ("WV", "LH.5.a.E"): LOC,
    ("WV", "LH.5.b.E"): LOC, ("WV", "LH.6.a.E"): LOC, ("WV", "LH.6.b.E"): LOC, ("WV", "LH.6.c.E"): LOC,
    ("WV", "LH.6.d.E"): LOC, ("WV", "LH.6.e.E"): LOC, ("WV", "LH.6.f.E"): LOC, ("WV", "LH.6.g.1.E"): LOC,
    ("WV", "LH.6.g.2.E"): LOC, ("WV", "LH.6.h.E"): LOC, ("WV", "SC.1.E"): POP, ("WV", "TP.1.E"): POP,
    ("WV", "PW.1.E"): POP, ("WV", "TO.1.E"): AFF, ("WV", "HN.1.E"): PRES, ("WV", "LI.1.E"): AFF,
    ("WV", "LP.1.E"): AFF, ("WV", "QC.1.E"): LOC, ("WV", "EQ.1.E"): DES, ("WV", "EQ.2.E"): DES,
    ("WV", "EQ.3.E"): DES, ("WV", "EQ.4.E"): DES, ("WV", "EQ.5.E"): DES, ("WV", "EQ.6.E"): DES,
    ("WV", "EQ.7.E"): DES, ("WV", "EQ.8.E"): DES, ("WV", "EQ.11.E"): DES, ("WV", "EQ.12.E"): DES,
    ("WV", "EQ.13.E"): DES, ("WV", "EQ.14.E"): DES, ("WV", "EQ.10.E"): DES, ("WV", "BONUS.1"): READY,
    ("WV", "NEG.1"): READY, ("WV", "NEG.2"): SPON,
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
