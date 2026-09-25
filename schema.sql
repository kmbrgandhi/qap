-- QAP competitive-criteria database
-- SQLite. Apply with:  sqlite3 data/qap.db < schema.sql

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Documents
-- ---------------------------------------------------------------------------
-- One row per PDF. A state may have several rows: a primary QAP plus exhibits,
-- scoring workbooks, or application manuals that carry scoring by reference,
-- and older cycles once historical QAPs are added.
CREATE TABLE IF NOT EXISTS qaps (
    id              INTEGER PRIMARY KEY,
    -- NULL when the document could not be identified (e.g. an un-OCR'd
    -- scan). Left NULL rather than defaulted, so it surfaces for review.
    state           TEXT,                          -- USPS code, 'MA'
    state_name      TEXT,
    agency          TEXT,                          -- 'CHFA', 'MaineHousing'

    doc_role        TEXT    NOT NULL DEFAULT 'primary',
                    -- primary | exhibit | manual | amendment | workbook
    doc_status      TEXT    NOT NULL DEFAULT 'unknown',
                    -- draft | final | amended | unknown

    -- Cycle the document itself covers, e.g. 2025-2026 -> (2025, 2026).
    -- Often absent from the document's own front matter (Maine's title page
    -- carries no year at all), so cycle_source records where the value came
    -- from and whether the two sources agreed. Never inferred from stray
    -- years elsewhere in the document.
    cycle_start     INTEGER,
    cycle_end       INTEGER,
    cycle_source    TEXT,   -- filename | document | both_agree | CONFLICT | none
    adopted_date    TEXT,                          -- ISO-8601, nullable
    effective_date  TEXT,                          -- ISO-8601, nullable

    -- Which competitive round this document actually governs. Kept separate
    -- from cycle_* because "most recent QAP" and "the QAP governing 2026"
    -- are different documents in some states (NH adopted 2027-2028 in 2026).
    governs_round   INTEGER,
    is_most_recent  INTEGER NOT NULL DEFAULT 0,    -- most recent for this state

    title           TEXT,
    source_url      TEXT,                          -- agency page it came from
    retrieved_at    TEXT,                          -- ISO-8601

    sha256          TEXT    NOT NULL UNIQUE,       -- reproducibility anchor
    filename        TEXT    NOT NULL,
    local_path      TEXT    NOT NULL,
    n_pages         INTEGER,
    text_chars      INTEGER,                       -- chars in the text layer
    -- SHA-256 of the EXTRACTED TEXT at ingest, as distinct from sha256 above,
    -- which hashes the file. A document can be re-OCR'd, or silently replaced
    -- at a rolling URL, and still contain a criterion's quoted words while the
    -- surrounding text -- and so what the criterion actually says -- has moved.
    -- verify_citations compares this and says loudly when it has. It is why we
    -- do not freeze the text to a separate artefact: the reviewer keeps reading
    -- the same PDF the citation points at, and drift is still caught.
    text_sha256     TEXT,
    source_quality  TEXT,   -- native | ocr | no_text_layer | garbled_text

    -- Total competitive points the document itself states are available.
    -- Compared against v_qap_computed_total to catch missed or double-counted
    -- criteria; a mismatch is the single most useful automated check here.
    stated_total    REAL,
    stated_total_page INTEGER,

    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_qaps_state ON qaps(state);


-- ---------------------------------------------------------------------------
-- Exclusivity groups
-- ---------------------------------------------------------------------------
-- Criteria that cannot all be earned together. Without this, summing
-- points_max overstates what a project can actually score.
--
--   max_one     pick-one menu; group contributes MAX(member points)
--               e.g. "Rehab 5" OR "Historic rehab 5"  -> 5, not 10
--   capped_sum  family with a cap; contributes MIN(SUM(members), group_cap)
--               e.g. "up to 10 points across (a)-(d)" where (a)-(d) list 15
--   independent members are additive; group exists only for grouping/display
--
-- Tiers WITHIN a single criterion are point_tiers, not a group.
CREATE TABLE IF NOT EXISTS exclusivity_groups (
    id           INTEGER PRIMARY KEY,
    qap_id       INTEGER NOT NULL REFERENCES qaps(id) ON DELETE CASCADE,
    label        TEXT,
    rule         TEXT    NOT NULL DEFAULT 'max_one'
                 CHECK (rule IN ('max_one', 'capped_sum', 'independent')),
    group_cap    REAL,                             -- required when capped_sum
    source_quote TEXT,                             -- text establishing the rule
    page_start   INTEGER,
    note         TEXT,
    -- Scopes the loader's idempotent delete. See the note on track_totals:
    -- without this, a second extraction file against the same qap_id wipes
    -- the groups the first one wrote.
    extractor_version TEXT,
    CHECK (rule <> 'capped_sum' OR group_cap IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ix_groups_qap ON exclusivity_groups(qap_id);


-- ---------------------------------------------------------------------------
-- Criteria
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS criteria (
    id            INTEGER PRIMARY KEY,
    qap_id        INTEGER NOT NULL REFERENCES qaps(id) ON DELETE CASCADE,
    ord           INTEGER,                         -- order of appearance
    section_label TEXT,                            -- 'III.A.1', 'Sec. 5.A.1'
    heading       TEXT,
    verbatim_text TEXT,                            -- full criterion text

    -- Provenance. quote must appear on page_start..page_end in the PDF;
    -- citation_verified records whether we actually found it there.
    quote         TEXT,
    page_start    INTEGER,
    page_end      INTEGER,
    -- Spreadsheet sources only. A workbook is read as a document whose pages
    -- are sheets, so page_start still applies; this names one cell within it,
    -- e.g. '3)Scoring Overview!H7'. Where present the loader checks the quote
    -- against that cell alone, which is stricter than any page citation.
    -- Kentucky publishes its scoring only as .xlsx; see qapdb/sheets.py.
    cell_ref      TEXT,
    citation_verified INTEGER NOT NULL DEFAULT 0,  -- 0 unchecked/failed, 1 found

    -- Maximum this criterion alone can yield. NULL for threshold criteria.
    points_max    REAL,

    -- The unit points_max is denominated in. NOT always points: Vermont ranks
    -- Ceiling Credit applications with "checkmarks", which staff then weight
    -- to produce a ranking. Storing 4 checkmarks in a points column without
    -- this would silently make them comparable to 4 Connecticut points, which
    -- they are not. Totals and charts must never mix units.
    scoring_unit  TEXT NOT NULL DEFAULT 'points'
                  CHECK (scoring_unit IN ('points','checkmarks','rank','none')),
    points_type   TEXT DEFAULT 'fixed'
                  CHECK (points_type IN ('fixed','tiered','formula',
                                         'per_unit','unlimited','negative','none')),

    -- What sort of criterion this is. Replaces the earlier is_threshold /
    -- is_tiebreaker booleans: Connecticut's Preservation track ranks
    -- applications against nine ordered priorities that carry no points at
    -- all, which is neither competitive scoring nor a threshold, and a pair
    -- of booleans cannot express it.
    kind          TEXT NOT NULL DEFAULT 'competitive'
                  CHECK (kind IN ('competitive','threshold','ranked_priority',
                                  'tiebreaker','set_aside')),
    rank_order    INTEGER,                         -- for ranked_priority/tiebreaker

    -- Some QAPs run parallel evaluation tracks that are scored differently and
    -- must not be pooled. Connecticut splits into a Preservation Classification
    -- (ranked, no points) and a New Construction Classification (100 points).
    -- Totals are computed per track, never across them.
    track         TEXT,

    -- The category heading the QAP itself uses ("Rental Affordability").
    -- Recorded verbatim and kept separate from our own taxonomy, which is
    -- built later; this costs nothing now and is a useful cross-check on it.
    native_category TEXT,

    is_negative   INTEGER NOT NULL DEFAULT 0,      -- point deduction

    -- Scored against the other applications in the round rather than against a
    -- fixed standard. Hawaii awards its cost points to whichever application
    -- has the lowest cost per square foot that year; Wisconsin rank-orders
    -- below-market financing; New York compares project costs "to the costs
    -- proposed in other project applications". points_max is then a ceiling
    -- nobody can plan for, and cross-state comparison of these values means
    -- something different from comparing fixed thresholds. Worth a column
    -- rather than a sentence in a note, because "which states score relatively"
    -- is a question the database should be able to answer.
    scored_against_round INTEGER NOT NULL DEFAULT 0,

    -- How a criterion's tiers combine. Both kinds exist and they look
    -- identical in the data: North Dakota's universal design tiers add up to
    -- its maximum, while Hawaii's green certification tiers are alternatives
    -- and only the best applies. Without this, naive_total cannot tell
    -- genuine double-counting from a criterion whose parts are meant to sum.
    tier_mode     TEXT CHECK (tier_mode IN ('alternative','additive','mixed')),

    -- Where the actual test lives, when it is not in this document. South
    -- Dakota gives 100 of its 800 points to a section that says only "as
    -- detailed in Exhibit 4"; Wisconsin defers 25 points to Appendix W;
    -- Arkansas's opportunity index is published on a map. The points are
    -- extractable and the criteria are not, and a reader deserves to see
    -- which figures rest on a document we do not hold.
    detail_external TEXT,

    exclusivity_group_id INTEGER REFERENCES exclusivity_groups(id) ON DELETE SET NULL,

    -- Free-text flag from extraction: ambiguities, drafting errors in the
    -- QAP itself, anything the reviewer should see before accepting. These
    -- are the whole point of a review queue, so they must reach the reviewer.
    note          TEXT,

    extractor_version TEXT,
    model_confidence  REAL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_criteria_qap   ON criteria(qap_id);
CREATE INDEX IF NOT EXISTS ix_criteria_group ON criteria(exclusivity_group_id);
CREATE INDEX IF NOT EXISTS ix_criteria_kind  ON criteria(kind);
CREATE INDEX IF NOT EXISTS ix_criteria_track ON criteria(qap_id, track);


-- Tiered point structures within one criterion.
-- "5 pts if >=50% of units at 30% AMI, 3 pts if 30-50%" -> two tiers.
-- The criterion's points_max should equal MAX(tier points).
CREATE TABLE IF NOT EXISTS point_tiers (
    id             INTEGER PRIMARY KEY,
    criterion_id   INTEGER NOT NULL REFERENCES criteria(id) ON DELETE CASCADE,
    ord            INTEGER,
    tier_label     TEXT,
    points         REAL,
    condition_text TEXT
);

CREATE INDEX IF NOT EXISTS ix_tiers_criterion ON point_tiers(criterion_id);


-- ---------------------------------------------------------------------------
-- Categories (deferred - tables present, intentionally unpopulated)
-- ---------------------------------------------------------------------------
-- Built bottom-up from reviewed criteria later. Defined now so adding the
-- taxonomy is an INSERT rather than a migration.
CREATE TABLE IF NOT EXISTS categories (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    parent_id       INTEGER REFERENCES categories(id),
    definition      TEXT,
    inclusion_rules TEXT,
    exclusion_rules TEXT,
    codebook_version TEXT,
    UNIQUE (name, codebook_version)
);

CREATE TABLE IF NOT EXISTS criterion_categories (
    criterion_id INTEGER NOT NULL REFERENCES criteria(id) ON DELETE CASCADE,
    category_id  INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    is_primary   INTEGER NOT NULL DEFAULT 0,
    assigned_by  TEXT,                             -- 'model' | reviewer name
    PRIMARY KEY (criterion_id, category_id)
);

-- Exactly one primary category per criterion: primary drives every total and
-- chart, secondary labels are search-only. This is what prevents a criterion
-- being counted under two categories at once.
CREATE UNIQUE INDEX IF NOT EXISTS ux_one_primary_category
    ON criterion_categories(criterion_id) WHERE is_primary = 1;


-- ---------------------------------------------------------------------------
-- Review (blind, multi-reviewer)
-- ---------------------------------------------------------------------------
-- One row per (criterion, reviewer). Reviewers never overwrite each other;
-- disagreements are resolved by adding an adjudication row, so the original
-- disagreement is preserved rather than lost.
CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY,
    criterion_id  INTEGER NOT NULL REFERENCES criteria(id) ON DELETE CASCADE,
    reviewer      TEXT    NOT NULL,
    status        TEXT    NOT NULL
                  CHECK (status IN ('accepted','edited','rejected','skipped','adjudicated')),
    -- Field-level corrections as JSON, e.g. {"points_max": 7, "heading": "..."}.
    -- Field-level so two reviewers agreeing on points but differing on
    -- something else registers as a partial, not a total, disagreement.
    corrected_json TEXT,
    note          TEXT,
    is_adjudication INTEGER NOT NULL DEFAULT 0,
    reviewed_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (criterion_id, reviewer, is_adjudication)
);

CREATE INDEX IF NOT EXISTS ix_reviews_criterion ON reviews(criterion_id);


-- Stated maxima are per-TRACK where a QAP scores in stages. Massachusetts
-- states 100 points for Section XI-A (Fundamental Project Characteristics)
-- and no maximum for Section XI-B, so a single document-level stated_total
-- would falsely flag XI-B as failing to reconcile.
-- extractor_version scopes the loader's idempotent delete. A state has one
-- qap_id but several extraction files against it (competitive and thresholds
-- are separate passes over the same PDF), so a delete scoped to qap_id alone
-- lets whichever file loads last wipe the rows the earlier one wrote.
CREATE TABLE IF NOT EXISTS track_totals (
    qap_id       INTEGER NOT NULL REFERENCES qaps(id) ON DELETE CASCADE,
    track        TEXT,
    stated_total REAL,
    page         INTEGER,
    note         TEXT,
    extractor_version TEXT,
    PRIMARY KEY (qap_id, track)
);


-- ---------------------------------------------------------------------------
-- Prior hand-coding (validation signal, not ground truth)
-- ---------------------------------------------------------------------------
-- Rows lifted from the existing QAPCompetitiveScoring workbook. Used as an
-- automated third check alongside the two blind human passes.
--
-- IMPORTANT: the prior coding is known to be INCOMPLETE (max points only, and
-- not every criterion). The comparison is therefore ASYMMETRIC:
--
--   prior present + extraction absent  -> real flag, likely a missed criterion
--   prior present + points differ      -> real flag, one of the two is wrong
--   extraction present + prior absent  -> EXPECTED, not an error
--
-- Treating it as ground truth would manufacture false errors on exactly the
-- criteria the new pipeline is supposed to add.
CREATE TABLE IF NOT EXISTS prior_codings (
    id           INTEGER PRIMARY KEY,
    qap_id       INTEGER REFERENCES qaps(id) ON DELETE SET NULL,
    source_file  TEXT NOT NULL,
    sheet        TEXT,
    row_label    TEXT,                             -- as written in the sheet
    points_max   REAL,
    category     TEXT,                             -- their original label
    is_threshold INTEGER NOT NULL DEFAULT 0,
    raw_json     TEXT                              -- whole row, for reference
);

CREATE INDEX IF NOT EXISTS ix_prior_qap ON prior_codings(qap_id);

CREATE TABLE IF NOT EXISTS prior_matches (
    id           INTEGER PRIMARY KEY,
    prior_id     INTEGER REFERENCES prior_codings(id) ON DELETE CASCADE,
    criterion_id INTEGER REFERENCES criteria(id) ON DELETE CASCADE,
    match_type   TEXT NOT NULL
                 CHECK (match_type IN ('agree','points_disagree',
                                       'prior_only','extracted_only')),
    match_score  REAL,                             -- fuzzy similarity 0-1
    points_delta REAL,
    resolved     INTEGER NOT NULL DEFAULT 0,
    note         TEXT
);

CREATE INDEX IF NOT EXISTS ix_prior_matches_crit ON prior_matches(criterion_id);


-- ---------------------------------------------------------------------------
-- Derived views
-- ---------------------------------------------------------------------------

-- What each exclusivity group contributes to the competitive total.
CREATE VIEW IF NOT EXISTS v_group_contribution AS
SELECT
    g.id     AS group_id,
    g.qap_id AS qap_id,
    c.track  AS track,
    g.rule   AS rule,
    CASE g.rule
        WHEN 'max_one'    THEN MAX(c.points_max)
        WHEN 'capped_sum' THEN MIN(SUM(c.points_max), g.group_cap)
        ELSE                   SUM(c.points_max)
    END AS points
FROM exclusivity_groups g
JOIN criteria c ON c.exclusivity_group_id = g.id
WHERE c.kind = 'competitive' AND c.is_negative = 0
GROUP BY g.id, c.track;

-- Competitive points actually available, honouring exclusivity. Computed per
-- (qap, track) - pooling Connecticut's Preservation and New Construction
-- tracks would be meaningless, since only one of them uses points.
CREATE VIEW IF NOT EXISTS v_qap_computed_total AS
SELECT
    q.id AS qap_id,
    tr.track AS track,
    tr.scoring_unit AS scoring_unit,
    COALESCE((SELECT SUM(c.points_max) FROM criteria c
              WHERE c.qap_id = q.id
                AND IFNULL(c.track,'') = IFNULL(tr.track,'')
                AND c.scoring_unit = tr.scoring_unit
                AND c.exclusivity_group_id IS NULL
                AND c.kind = 'competitive'
                AND c.is_negative = 0), 0)
  + COALESCE((SELECT SUM(v.points) FROM v_group_contribution v
              WHERE v.qap_id = q.id
                AND IFNULL(v.track,'') = IFNULL(tr.track,'')), 0)
    AS computed_total,
    -- Flat sum ignoring exclusivity, at the finest grain the document states
    -- points at: every tier value where a criterion is tiered, else its
    -- points_max. Summing points_max alone would MISS the largest source of
    -- double-counting, which in Connecticut is entirely within criteria (a
    -- criterion capped at 8 whose four tiers list 8+5+3+2), not across them.
    COALESCE((SELECT SUM(MAX(COALESCE(ts.tier_sum, 0), COALESCE(c.points_max, 0)))
              FROM criteria c
              LEFT JOIN (SELECT criterion_id, SUM(points) AS tier_sum
                         FROM point_tiers GROUP BY criterion_id) ts
                     ON ts.criterion_id = c.id
              WHERE c.qap_id = q.id
                AND IFNULL(c.track,'') = IFNULL(tr.track,'')
                AND c.scoring_unit = tr.scoring_unit
                AND c.kind = 'competitive'
                AND c.is_negative = 0), 0)
    AS naive_total
FROM qaps q
JOIN (SELECT DISTINCT qap_id, track, scoring_unit FROM criteria
      WHERE kind = 'competitive') tr ON tr.qap_id = q.id;

-- Reconciliation: computed vs the total the document itself states.
CREATE VIEW IF NOT EXISTS v_total_reconciliation AS
SELECT
    q.id, q.state, q.cycle_start, q.cycle_end, t.track, t.scoring_unit,
    COALESCE(tt.stated_total, CASE WHEN (SELECT COUNT(DISTINCT IFNULL(track,''))
        FROM criteria c WHERE c.qap_id = q.id) = 1 THEN q.stated_total END) AS stated_total,
    t.computed_total,
    t.naive_total,
    ROUND(t.computed_total - COALESCE(tt.stated_total,
        CASE WHEN (SELECT COUNT(DISTINCT IFNULL(track,'')) FROM criteria c
                   WHERE c.qap_id = q.id) = 1 THEN q.stated_total END), 2) AS delta,
    ROUND(t.naive_total - t.computed_total, 2)   AS double_counted,
    CASE WHEN COALESCE(tt.stated_total, CASE WHEN (SELECT COUNT(DISTINCT IFNULL(track,''))
              FROM criteria c WHERE c.qap_id = q.id) = 1 THEN q.stated_total END) IS NULL
              THEN 'no stated total'
         WHEN ABS(t.computed_total - COALESCE(tt.stated_total, q.stated_total)) < 0.01
              THEN 'OK'
         ELSE 'MISMATCH' END AS status
FROM qaps q
JOIN v_qap_computed_total t ON t.qap_id = q.id
LEFT JOIN track_totals tt ON tt.qap_id = q.id
                         AND IFNULL(tt.track,'') = IFNULL(t.track,'');

-- Review progress and disagreement surface.
CREATE VIEW IF NOT EXISTS v_review_status AS
SELECT
    c.id  AS criterion_id,
    c.qap_id,
    COUNT(r.id) FILTER (WHERE r.is_adjudication = 0) AS n_reviews,
    COUNT(DISTINCT r.status) FILTER (WHERE r.is_adjudication = 0
                                       AND r.status <> 'skipped') AS n_distinct_status,
    MAX(r.is_adjudication) AS adjudicated
FROM criteria c
LEFT JOIN reviews r ON r.criterion_id = c.id
GROUP BY c.id;

-- Prior-coding flags worth a human look. Deliberately excludes
-- 'extracted_only', which is the expected case given the prior coding is
-- incomplete, and would otherwise swamp the queue with non-errors.
CREATE VIEW IF NOT EXISTS v_prior_flags AS
SELECT
    m.id            AS match_id,
    m.match_type,
    m.points_delta,
    m.match_score,
    p.source_file, p.sheet, p.row_label,
    p.points_max    AS prior_points,
    c.id            AS criterion_id,
    c.heading       AS extracted_heading,
    c.points_max    AS extracted_points,
    c.page_start,
    q.state, q.cycle_start, q.cycle_end
FROM prior_matches m
LEFT JOIN prior_codings p ON p.id = m.prior_id
LEFT JOIN criteria      c ON c.id = m.criterion_id
LEFT JOIN qaps          q ON q.id = COALESCE(c.qap_id, p.qap_id)
WHERE m.match_type IN ('prior_only', 'points_disagree')
  AND m.resolved = 0;
