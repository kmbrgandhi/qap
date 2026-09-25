"""Build a LOCAL proposal database beside the real one.

This writes `data/qap_proposed.db` — a copy of the live database with three
additions we have not committed to, so a meeting can look at them working
against the real 47 states instead of at a diagram. Nothing here touches
`data/qap.db`, and nothing here is part of the pipeline.

    python -m qapdb.propose            # writes data/qap_proposed.db

The three, and the problem each answers:

1. CONCEPT TAGS (`concepts`, `criterion_concepts`)
   The eight categories are deliberately coarse — every criterion gets exactly
   one, and they were built to make totals addable. They cannot answer "which
   states score broadband?", because broadband sits inside
   "Design, accessibility & sustainability" along with forty other things. The
   public site answers that question with a text search over headings and
   notes, which is fragile: states rarely use the same words, so searching
   "transit" misses "public transportation" and "fixed route stop".
   A concept is a many-to-many tag, finer than a category and independent of
   wording. Seeded here with worked examples so the shape is visible.

2. COMPARABLE SHARES (`v_criterion_share`)
   Scales are not comparable: Ohio's whole scale is 100 points, South Dakota's
   is 780, Utah's largest single criterion is 5,000 weighted. Any cross-state
   claim about "how much a state weights X" has to normalise first, and right
   now every consumer of this data would have to do that arithmetic itself and
   could do it differently. The view does it once, as a share of the
   criterion's own track total.

3. A REVIEW QUEUE (`review_queue`)
   The `reviews` table has existed since the first schema and holds zero rows.
   Looking at it properly: its status check allows accepted, edited, rejected,
   skipped and adjudicated -- all of them DECISIONS. There is no `pending`,
   because a row only exists once someone has reviewed something. So the
   database records review outcomes and has nowhere to record what is waiting
   to be reviewed, or why, or who owns it. The queue is currently implicit:
   "everything not in `reviews`".
   That is fine at 33 items and unworkable at 1,935. `review_queue` makes it
   explicit, seeded with the criteria whose own extraction notes ask for a
   second reader, each carrying the reason. Decide at the meeting whether the
   queue belongs in the database at all or in whatever tracker the team
   already uses -- but it should not stay implicit.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "data" / "qap.db"
OUT = ROOT / "data" / "qap_proposed.db"

# Seed concepts. Each is (name, definition, [regex matched against heading,
# quote and note]). The patterns are a demonstration of the shape, not a
# finished vocabulary -- the point of the meeting is to agree the vocabulary.
CONCEPTS = [
    ("Broadband and connectivity", "In-unit internet, wiring, or digital access commitments.",
     r"broadband|internet|wi-?fi|digital (access|literacy|equity)"),
    ("Historic rehabilitation", "Use of historic tax credits or a listed/contributing structure.",
     r"historic"),
    ("Transit proximity", "Distance or access to fixed-route public transport.",
     r"transit|bus stop|public transportation|rail station|walkab"),
    ("Veterans", "Units, preferences or services targeted at veterans.",
     r"veteran"),
    ("Homelessness", "Units or services for people experiencing homelessness.",
     r"homeless|chronically homeless|continuum of care"),
    ("Energy and green certification", "Certified green building or measured energy performance.",
     r"energy|green (building|communit)|leed|passive house|hers|enterprise green"),
    ("Accessibility beyond code", "Accessible or visitable units above the legal minimum.",
     r"accessib|visitab|type a (unit|dwelling)|universal design|504"),
    ("Local government support", "Resolutions, letters, or contributions from the locality.",
     r"local (support|government|match)|municipal|resolution|letter of support"),
    ("Tenant ownership", "A path to residents owning their units.",
     r"tenant ownership|homeownership|right of first refusal|lease.?purchase"),
    ("Developer experience", "Track record of the developer, sponsor or general partner.",
     r"experience|track record|previous participation|capacity of (the )?develop"),
    ("Rural targeting", "Criteria that turn on a rural designation.",
     r"\brural\b|balance of state|non-?metro|usda"),
    ("Deep affordability", "Units at or below 30% of area median income.",
     r"\b30%|extremely low|\beli\b|deep(er)? (targeting|affordab)"),
]

SHARE_VIEW = """
CREATE VIEW IF NOT EXISTS v_criterion_share AS
-- Each competitive criterion as a share of its own track's stated total, so
-- states with incomparable scales can be compared. Uses the STATED total
-- where the document gives one, because that is the state's own denominator;
-- falls back to the computed total where it does not. Deductions are excluded:
-- they are not part of what a project can earn.
WITH denom AS (
    SELECT q.id AS qap_id,
           IFNULL(tt.track, '')        AS track_key,
           COALESCE(tt.stated_total, v.computed_total) AS total
    FROM qaps q
    JOIN track_totals tt ON tt.qap_id = q.id
    LEFT JOIN v_qap_computed_total v
           ON v.qap_id = q.id AND IFNULL(v.track, '') = IFNULL(tt.track, '')
)
SELECT c.id            AS criterion_id,
       q.state         AS state,
       c.section_label AS section_label,
       c.heading       AS heading,
       c.track         AS track,
       c.points_max    AS points_max,
       c.scoring_unit  AS scoring_unit,
       d.total         AS track_total,
       ROUND(100.0 * c.points_max / NULLIF(d.total, 0), 2) AS pct_of_track
FROM criteria c
JOIN qaps q  ON q.id = c.qap_id
LEFT JOIN denom d ON d.qap_id = c.qap_id AND d.track_key = IFNULL(c.track, '')
WHERE c.kind = 'competitive'
  AND c.is_negative = 0
  AND c.points_max IS NOT NULL;
"""

FLAG = re.compile(
    r"(reviewer should|should confirm|a reviewer|confirm against|CONTRADICTION"
    r"|not verified|unclear|worth checking|ambiguous|cannot confirm)", re.I)


def build(live: Path, out: Path) -> int:
    if not live.exists():
        raise SystemExit(f"{live} not found; build the real database first")
    shutil.copy(live, out)
    con = sqlite3.connect(out)
    con.execute("PRAGMA foreign_keys = ON")

    # ---- 1. concept tags --------------------------------------------------
    con.executescript("""
        CREATE TABLE IF NOT EXISTS concepts (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            definition  TEXT,
            -- How this concept was proposed. A regex is a starting point for a
            -- human, never an assignment: patterns over-match (Utah's
            -- "Applicant Characteristics" contains "experience") and
            -- under-match (a state that says "fixed route stop" and never
            -- "transit"). Kept so a reviewer can see why a row was suggested.
            seed_pattern TEXT
        );
        CREATE TABLE IF NOT EXISTS criterion_concepts (
            criterion_id INTEGER NOT NULL REFERENCES criteria(id) ON DELETE CASCADE,
            concept_id   INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
            -- 'suggested' until a human says otherwise. Nothing downstream
            -- should treat a suggestion as a finding.
            status       TEXT NOT NULL DEFAULT 'suggested'
                         CHECK (status IN ('suggested','confirmed','rejected')),
            PRIMARY KEY (criterion_id, concept_id)
        );
    """)
    for name, definition, pattern in CONCEPTS:
        con.execute("INSERT OR IGNORE INTO concepts (name, definition, seed_pattern)"
                    " VALUES (?,?,?)", (name, definition, pattern))

    rows = con.execute("SELECT id, heading, quote, note FROM criteria").fetchall()
    ids = {n: i for i, n in con.execute("SELECT id, name FROM concepts")}
    tagged = 0
    for name, _definition, pattern in CONCEPTS:
        rx = re.compile(pattern, re.I)
        for cid, heading, quote, note in rows:
            hay = " ".join(x or "" for x in (heading, quote, note))
            if rx.search(hay):
                con.execute("INSERT OR IGNORE INTO criterion_concepts"
                            " (criterion_id, concept_id) VALUES (?,?)", (cid, ids[name]))
                tagged += 1

    # ---- 2. comparable shares --------------------------------------------
    con.executescript(SHARE_VIEW)

    # ---- 3. an explicit review queue --------------------------------------
    con.executescript("""
        CREATE TABLE IF NOT EXISTS review_queue (
            criterion_id INTEGER PRIMARY KEY REFERENCES criteria(id) ON DELETE CASCADE,
            -- Why this is waiting. `reviews` records what was decided; this
            -- records what still needs deciding, which the schema had no
            -- place for.
            reason       TEXT NOT NULL,
            priority     INTEGER NOT NULL DEFAULT 2,   -- 1 high, 2 normal, 3 low
            assigned_to  TEXT,                          -- NULL = nobody has it
            added_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    queued = 0
    for cid, note in con.execute(
            "SELECT id, note FROM criteria WHERE note IS NOT NULL").fetchall():
        m = FLAG.search(note)
        if not m:
            continue
        con.execute("INSERT OR IGNORE INTO review_queue (criterion_id, reason, priority)"
                    " VALUES (?,?,1)",
                    (cid, f"The extraction note asks for a second reader ('{m.group(0)}')."))
        queued += 1

    con.commit()

    n_concepts = con.execute("SELECT count(*) FROM concepts").fetchone()[0]
    n_links = con.execute("SELECT count(*) FROM criterion_concepts").fetchone()[0]
    n_share = con.execute("SELECT count(*) FROM v_criterion_share"
                          " WHERE pct_of_track IS NOT NULL").fetchone()[0]
    con.close()

    print(f"wrote {out}")
    print(f"  concepts          {n_concepts}")
    print(f"  concept links     {n_links} suggested (none confirmed)")
    print(f"  v_criterion_share {n_share} criteria with a comparable share")
    print(f"  reviews queued    {queued}")
    print("\nThis file is a PROPOSAL and is gitignored. The live database is untouched.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", type=Path, default=LIVE)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    return build(a.live, a.out)


if __name__ == "__main__":
    raise SystemExit(main())
