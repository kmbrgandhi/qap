# Extraction protocol

**Read this before coding any QAP. Update it after coding any QAP.**

The database's one promise is that every figure has a page citation somebody
else can re-find and check. Everything below exists to protect that promise.
The rules are not style preferences: each one is here because something went
wrong without it, and the section that records what went wrong is at the end.

---

## 0. The three rules that outrank everything

1. **Never write a number you have not read.** Not from a summary table you
   half-remember, not inferred from what the other values sum to, not carried
   over from last year's plan. If a value is not legible, go and look at the
   rendered page image. If it is still not legible, leave it null and say why
   in `note`.
2. **Every quote must be findable on the page it cites.** The loader checks
   this and refuses to trust what it cannot find. A criterion whose citation
   fails verification is worse than a missing criterion.
3. **Contradictions in the QAP get recorded, not resolved.** When a document
   disagrees with itself, extract what the operative text says, and put the
   contradiction in `note` or `track_totals.note`. It is a finding.

---

## 1. Before you extract

Work through this in order. It takes ten minutes and saves hours.

- **Confirm the document is the one that governs the round.** Check
  `qaps.doc_status`, and read the cover. Drafts are fine to extract but must
  be labelled; do not let one silently stand in for an adopted plan.
- **Check the text layer.** `source_quality` from ingest tells you: `native`,
  `garbled_text`, or `no_text_layer`. Anything but `native` must be OCR'd
  first (`ocrmypdf --force-ocr`), the OCR'd copy put in the drop folder, and
  the extraction pointed at *that* file. Rhode Island's scan had zero
  characters across 56 pages.
- **Find out where the scoring actually lives.** Do not assume it is in the
  QAP. Search the document for "point" and count. If the count is near zero,
  the points are in a companion document — a scoring sheet, an appendix, a
  workbook — and the QAP alone will produce an empty extraction. Known cases:
  Michigan (separate Scoring Criteria file), Wisconsin (Appendix C), Washington
  (9% Policies, not the QAP), Minnesota (self-scoring worksheet), Nebraska
  (9% scoresheet), Kentucky (an .xlsx workbook), Florida (nothing — scoring is
  delegated to RFAs), Montana (no point system exists at all).
- **Find the document's own summary table, if it has one.** Rhode Island's
  p.32 Scoring/Point Allocation Summary gave every section maximum and the
  total, and settled a contradiction elsewhere in the document. It is the
  single most useful page in the QAP. Read it first, not last.
- **Map the scoring section** by listing headings and page numbers before
  reading in detail, so you know how much there is and can spot an appendix
  you would otherwise miss. In a converted document, map from the text layer:
  Oklahoma's table of contents kept the page numbers of the .docx it came from.
- **A low "point" count is a prompt to look, not a verdict.** Colorado's 102
  pages carry 68 mentions because its largest criterion is a formula; the
  scoring was all there. Read the pages that carry the mentions before
  deferring a state.
- **Reconcile any score sheet against the body in both directions.** Oklahoma's
  self-score sheet omits the largest criterion (cost efficiency, scored by
  staff against the round, 24 of 83 points). Indiana's summary counts items its
  own body says cannot be combined.
- **Look for points outside the scoring section:** appeal remedies (Iowa
  7.10.B), a statutory state-credit ranking (Oklahoma), penalty schedules in
  another chapter (Minnesota 2.J), deductions among the thresholds (North
  Dakota).

## 2. What counts as one criterion

One row per thing a project is scored on, at the grain the document scores it.

- A criterion with alternatives at different values is **one criterion with
  tiers**, not several criteria.
- Two ladders that cannot both be claimed are still **one criterion**; record
  both ladders as tiers and explain in `note` that they are alternatives.
  Rhode Island's ELI/homeless criterion has 25/20/15/10 with services and
  18/15/12/9 without.
- Separately lettered items in the document are separate criteria even when
  they cover similar ground.
- Point deductions are criteria too, with `is_negative: true`,
  `points_type: "negative"` and a negative `points_max` (null where the
  document states no maximum: Alaska's penalty points, New Jersey's per-defect
  cure deduction).
- A criterion that scores in both directions (a vacancy ladder running from
  +25 to −10) stays **one row**, with the negative bands in the note; a purely
  negative item is its own row (Virginia, Wyoming).
- When a matrix pays only through an average or a count (Iowa's Site Appeal,
  Indiana's amenity charts), code the thing that is scored, not every cell.

## 3. Fields

| Field | Rule |
|---|---|
| `ord` | Order of appearance in the document. |
| `section_label` | **Must be unique within the QAP.** The taxonomy is keyed on `(state, section_label)`, so duplicates silently collide. Where the document letters items A, B, C inside unnumbered sections, prefix the section: `III.B.Fin.A`, `III.B.Inc.A`. |
| `heading` | The document's own heading, lightly normalised. |
| `native_category` | The QAP's own category name, verbatim. Never our taxonomy's. |
| `points_max` | What this criterion alone can yield. Null for thresholds, for deductions with no stated maximum, and where the values live in a document the corpus does not hold (then `detail_external` names it: Colorado's Housing Need exhibits). |
| `points_type` | `fixed`, `tiered`, `formula`, `per_unit`, `unlimited`, `negative`, `none`. |
| `scoring_unit` | `points` unless the document scores in something else. Vermont scores in checkmarks; Utah uses weights (weight × score). Never mix units in one total. |
| `kind` | `competitive`, `threshold`, `ranked_priority`, `tiebreaker`, `set_aside`. |
| `track` | Where the QAP runs scoring universes that must not be pooled. Two kinds, which look identical in the data, so every `track_totals.note` must say which it is: **alternatives**, where a project is in exactly one (Michigan urban/rural, Arizona rehab/new construction, Oklahoma 9%/state credit); and **add-ons**, extra criteria on top of a shared core (Arizona tribal, New Jersey's three cycles, Indiana 9%/bond). When scales share most criteria, code the core once plus one add-on track per scale rather than duplicating it; suffix any criterion that must appear on two tracks (`.family`, `.senior`). |
| `page_start` / `page_end` | **PDF page indices**, not printed page numbers. |
| `quote` | See §4. |
| `note` | Ambiguities, contradictions, alternatives, anything a reviewer should see. Generous notes are cheap; silent judgement calls are not. |
| `scored_against_round` | True where the criterion is scored against the other applications rather than a fixed standard. Set it whenever the text says "lowest in the round", "rank order the applications", "compared with other applications" or similar. |
| `tier_mode` | `alternative` where only the best tier applies, `additive` where the tiers are components that sum to the maximum, `mixed` where neither. Say which; the two look identical in the data and the double-counting figures depend on it. |
| `detail_external` | Names the document that holds the actual test, where the QAP states only a point value: `Exhibit 4`, `Appendix W`, `Program Guide`. Leave null when the test is in the document. |

## 4. Quotes and citations

- Quote from **the text layer of the file being ingested**, not from the page
  image and not from your reading of it. The verification searches that text
  layer; a quote that is true to the page but absent from the layer fails.
- **Short and distinctive beats long and complete.** Long quotes cross line
  breaks, hyphenation and column boundaries, and are likelier to fail.
- **Avoid punctuation-heavy spans.** Verification normalises punctuation, but
  OCR mangles it worst. In an OCR'd document, pick clean prose.
- If the obvious sentence is OCR-mangled, quote a neighbouring clean sentence
  on the same page. The citation points at the page; it does not have to be
  the single most central sentence.
- Never adjust a quote to make it verify. Adjust which passage you quote.
- **Two-column tables need the page image.** Where the text layer interleaves
  columns (Wyoming's Negative and Maximum Points summary, Indiana's rent
  table), read the figures from the rendered page, say so in `_comment`, and
  quote clean body text for the citation.

## 5. Points arithmetic

- `points_max` is the **maximum this criterion alone can yield**, which for a
  tiered criterion is normally the largest tier, not the sum of tiers. Summing
  tiers overstates by 50–65% in the states extracted so far.
- **Mutually exclusive options get an exclusivity group** with `rule` and
  `group_cap`, and the criteria carry `group`. Rhode Island's three Housing
  2030 community categories are alternatives capped at 10.
- **Exclusivity runs across criteria, not only inside one.** North Dakota's
  Housing for Older Persons rules out three other categories, so a project
  takes either K (6) or H+I+J (9). `max_one` would record 6 and understate it;
  `capped_sum` with the cap set to the better route records 9. Read every
  criterion for sentences of the form "applications seeking points under X are
  not eligible for points under this category" — they are easy to miss because
  they sit in the body text, not in the point table.
- **An exclusion that bars one tier or route, not the whole criterion, is a
  `capped_sum` at the best allowed route.** Minnesota's Rental Assistance is
  barred to Preservation Tier 1 but not Tier 2: cap 46, where `max_one` would
  record 45.
- **Unit-level and source-level exclusions cannot be groups.** "Cannot be
  claimed for the same units" limits the real maximum in a way the schema
  cannot hold. Put it in the notes and say in the track note that the computed
  figure is a ceiling (Minnesota).
- **A formula with no stated cap may record its ceiling, labelled as
  computed.** Colorado's targeting score is a weighted share; `points_max`
  holds 92.5, the top weight applied to every unit, and the note and
  `_comment` both say it is derived. Never let a derived figure pass as stated.
- **A heading range that is the only statement of a maximum still gets
  checked against the options** (Minnesota's "(7 to 37 Points)").
- **Deductions never count toward a total.** The views exclude `is_negative`;
  so should any arithmetic you do by hand.
- Record the document's own stated total in `track_totals` with the page it
  appears on, and a note quoting how the document states it.

## 6. Reconciliation is the check that matters

After loading, `v_total_reconciliation` compares the computed total against
the stated one:

- **OK** — they agree. This is strong evidence the extraction is complete and
  the exclusivity groups are right.
- **MISMATCH** — do not adjust numbers to close the gap. Find the missing
  criterion, the missed exclusivity group, or the contradiction in the
  document, and write down which it was.
- **no stated total** — the QAP states no maximum. Fine, but say so, and treat
  the hand-sum as a completeness check. Say how much of it rests on item
  values rather than stated section maxima (Iowa: 28 of 63).
- **MISMATCH by design** — where a stated total counts items the document says
  cannot combine, or spans scoring universes, keep the stated figure against
  its track and decompose the gap in the note until it sums exactly (Indiana:
  121 + 25 + 4 + 12 + 3 = 165).
- **Reconcile negatives too** where the document states them (Wyoming's
  −1,510), and check worked examples against the rule they illustrate
  (Wyoming's donations example contradicts its rule).

## 7. Thresholds and non-competitive criteria

- Thresholds go in a separate `<STATE>_thresholds.json` with its own
  `extractor_version`. The loader deletes by `(qap_id, extractor_version)`, so
  a shared version string makes the second file wipe the first.
- Thresholds carry `points_max: null`, `points_type: "none"`,
  `scoring_unit: "none"`.
- Map thresholds to categories in `data/threshold_categories.json`, keyed
  `STATE|section_label`.
- A floor that applies to one category rather than the total (Wyoming: 100 of
  158 in Housing Needs) is a threshold row whose note says what it applies to.
  A floor stated as a share of an unstated maximum (New Jersey's 65%) gets the
  computed value in its note, labelled as ours.
- **When a companion document holds the points, give the QAP its own small
  file** for whatever the companion defers to it (Minnesota's tie breakers and
  the RD/Small Projects floor are in `MN_qap_2026_2028.json`, matched to the QAP
  PDF), so every citation stays on the page it names.

## 8. The sequence

```bash
python -m qapdb.ingest --commit                              # document in
python -m qapdb.load_extraction data/extractions/XX_YYYY.json          # dry run
python -m qapdb.load_extraction data/extractions/XX_YYYY.json --commit
python -m qapdb.load_extraction data/extractions/XX_thresholds.json --commit
python -m qapdb.verify_citations --state XX
python -m qapdb.taxonomy --commit                            # add XX to ASSIGN first
python -m qapdb.manifest
```

Never skip the dry run. It verifies every citation and prints the arithmetic
before anything is written, applying exclusivity groups exactly as the
database views do, so its computed figure is the one reconciliation will use.

Two operational notes. If the `sqlite3` binary is missing, create the database
with `python -c "import sqlite3; sqlite3.connect('data/qap.db').executescript(open('schema.sql').read())"`.
And `manifest.py` run against a partial database (the bundled PDFs only) keeps
the rows it cannot see but recomputes the rows it can, including
`is_most_recent` over the partial set; read the diff and commit only the rows
for the state you coded.

## 9. What to hand the reviewer

The human review queue is for judgement, not for typos. Flag in `note`:

- any value read from a page image rather than the text layer
- any contradiction inside the document
- alternatives that are not additive
- anything the document leaves genuinely ambiguous
- criteria whose points depend on a document published elsewhere (a developer
  handbook, a program bulletin, a data table)
- any figure you computed rather than read (a formula ceiling, a floor
  expressed as a share of an unstated maximum), labelled as computed
- cross-references that point to the wrong section, with the section you took
  them to mean

Numbers in notes are held to rule 1 like any other: count them or leave them
out. "Some 90 amenities" is an estimate, and estimates do not belong in the
database.

---

## Lessons log

Append after each extraction. One entry per state, newest last. If a lesson
changes a rule above, change the rule and say so here.

### Rhode Island, 2026 (first extraction under this protocol)

- **OCR gets numbers wrong, and numbers are the whole point.** Three errors in
  one document: a graduation rate read 64% where the page says 84%, a tier
  read 9 points where the page says 0, and a "Up to 20 points" label dropped
  entirely. → Rule added: in any OCR'd document, verify *every* point value
  against the rendered page image, and note where each came from.
- **The summary table settles arguments.** The section header said "Up to 66
  points"; the summary table and the itemised maxima both said 60. Without
  p.32 there would have been no way to know which to trust. → Rule added: find
  the summary table before reading the detail.
- **Section labels collide.** Letters restart at A in every section, so five
  criteria shared `III.B.A` and the taxonomy could not key them. Caught only
  because the assignment step reported them. → Rule added: unique labels,
  prefixed by section.
- **Negative points broke the totals report** — the loader counted deductions
  toward the computed total and reported a false mismatch against a stated
  total that excluded them. Fixed in `load_extraction.py`.
- **Picking the quote is a skill.** Several first-choice sentences failed
  verification because OCR had mangled their punctuation. Quoting a clean
  neighbouring sentence on the same page fixed every one. 30 of 30 citations
  verified on the first commit.

### North Dakota, 2027

31 criteria, 31 citations verified on the first dry run, computed maximum 99
against a plan that states no maximum.

- **Exclusivity across criteria.** See the new rule in §5. Found only by
  reading the body text of H, I and J, each of which quietly excludes itself
  if K is claimed.
- **Penalties can live in the threshold section.** Section 5 ends with "a
  2-point scoring deduction will be assessed for each missing Threshold
  Requirement" — a scored consequence with no points anywhere near it. → Read
  the threshold section for deductions, not just the scoring section.
- **A lettered scoring category can carry no points at all.** Category N,
  Geographic Location, is a cap of two projects per city. Recorded rather than
  dropped, with a note saying the `kind` is the closest available fit.
- **Ambiguity is worth recording even when it does not change a number.** The
  deepest-AMI column is worth 45 and the plan never says whether a project can
  claim in more than one AMI band. The note says so, and that is exactly the
  kind of thing the human reviewer should settle.
- **Operational, and my mistake.** Clearing documents with
  `DELETE FROM qaps WHERE filename LIKE '%DRAFT%'` also deleted Vermont's
  `vermont-draft-qap-6-23-2026-ocr.pdf`, because SQLite's LIKE is
  case-insensitive, and the cascade silently took 21 coded criteria with it.
  → Delete by exact filename or id, and check the criteria count before and
  after. The taxonomy count dropping from 132 to 130 was the only signal.

### Maryland, abandoned before extraction

Worth recording as a success of the §1 check, not a failure. Maryland's QAP is
34 pages and mentions "point" 19 times. Every one of those mentions turns out
to name a section of DHCD's separate Multifamily Rental Financing Program
Guide and its maximum — "Guide Section 4.1 Capacity of Development Team (74
maximum points)" — with the criteria themselves in the Guide. Coding the QAP
alone would have produced seven section headings and no criteria. Maryland
needs the Guide collected first.

### North Carolina, 2026

47 criteria, 32 competitive and 15 thresholds, all citations verified first
time. Computed maximum 106.

- **Reconciliation can work without a stated total.** North Carolina states no
  overall maximum, but it states a maximum per section: 68 site, 2 rent, 2
  bonus, 4 Olmstead, 30 design. Those sum to 106 and the extraction computed
  106. → When a QAP states section maxima but no total, sum them by hand and
  check the computed figure against that. It catches a missed criterion just
  as well as a stated total does.
- **A capped group is the right shape more often than max_one.** Nine amenity
  rows score independently by driving distance and sum to exactly the stated
  46-point subsection maximum, while tribal funding and a transit stop each
  earn *within* that cap rather than on top of it. `capped_sum` at 46 holds
  all of that; `max_one` would have recorded 12.
- **Table rows extract as label-then-value.** Quotes like `"Grocery\n12pts."`
  verify cleanly against the text layer even though the table looks nothing
  like that on the page. Useful whenever points live in a grid.
- **Record a contradiction, do not average it.** The applicant bonus says
  "MAXIMUM 2 POINTS", then "An Applicant is entitled to two bonus points",
  then "No application can receive more than one bonus point". Recorded at 2
  with the contradiction in the note, for the reviewer to settle.
- **Scope honestly.** Section VI, six pages of general and underwriting
  thresholds, is not extracted. That is stated in the file's `_comment` rather
  than left for someone to discover.

### Virginia, 2026

61 criteria, all citations verified first time. The largest extraction so far.

- **A regulation is not a QAP, and reads differently.** Virginia's plan is
  13VAC10-180, so criteria are nested subdivisions (E.3.a.1.b) rather than a
  scoring table. The section label scheme has to carry that nesting, and
  sub-items that share a letter need a suffix: `E.3.a.1.b.brick` and
  `E.3.a.1.b.fibercement` are two independent criteria in one lettered item,
  and the plan says so explicitly.
- **Formula criteria are common and `points_max` means the cap, not a score.**
  Nine Virginia criteria scale with a percentage — 20 points times the share
  of brick, 100 times the percentage below the standard per-unit credit. The
  computed total of 763 is therefore a sum of caps and not a reachable score.
  Said plainly in `track_totals.note` so nobody quotes it as a maximum.
- **One criterion can score in both directions.** Efficient use of resources
  awards points below the standard credit amount and deducts above it. Left as
  a single positive criterion with the behaviour in the note, because two rows
  would double-count it.
- **The floor can be the only stated figure.** Virginia states no maximum at
  all, only that under 300 points (200 for bond deals) an application is
  rejected. Recorded as a threshold criterion so it is findable.
- **Interacting caps are not exclusivity.** Points under subdivision 2 f
  reduce the 60-point maximum of 2 e "in equal measure" — partly
  interchangeable rather than mutually exclusive. No group models that
  honestly, so both carry their stated caps and the note explains. A reviewer
  should know the two cannot simply be added.

### Arkansas 2027, Hawaii 2026, Missouri 2027

Three states in one pass, 63 criteria, every citation verified first time, and
each computed total matched a hand-sum done before loading: 99, 117, 169.

- **Hand-sum the stated maxima before you load.** Doing the arithmetic by hand
  first turns the loader's number into a check rather than a result. It is
  thirty seconds of work and it is how you find a missed row.
- **A blank in the document is a finding.** Arkansas's Points Criteria table
  ends with a row labelled "Total Points Possible:" and the value was never
  filled in. Recorded in `track_totals.note` rather than quietly summed.
- **Headings and tables disagree, often.** Hawaii's Criterion 12 is headed
  "0 to 7 points" and its table tops out at 6 for perpetual affordability.
  `points_max` records 6, the highest value actually attainable, with the
  heading's 7 in the note. → Where a heading and a table disagree, take the
  table and say so: the table is what a scorer applies.
- **A floor can be stated and then unstated.** Missouri says twice that an
  application must reach 90 combined points, then says MHDC may recommend
  applications that do not. Both recorded.
- **Some criteria cannot be scored from the document at all.** Hawaii scores
  six criteria against the rest of the round — lowest cost per square foot
  takes 6 points, highest takes 0 — and Missouri's credit efficiency safe
  harbour is set from the applications actually submitted. The point value is
  real but unknowable in advance. Say so in the note; a reader comparing
  states will otherwise assume a fixed standard.
- **Watch for values published outside the QAP.** Arkansas's opportunity index
  lives on an ArcGIS map, Missouri's cost-burden figures and rural county list
  on MHDC's website. The criterion is in the plan; the data that decides it is
  not.

### Wisconsin 2027-28, Alabama 2027, New York 2025, South Dakota 2026-27

100 criteria, every citation verified. Computed totals 155, 101, 100 and 780.

- **Subsection caps are easy to miss and change the total.** Alabama first
  computed 119 against its own stated section maxima of 104. Three caps were
  missing: new construction against rehabilitation, tenant needs (items total
  6 against a stated 5), and project type (items total 21 against a stated 12).
  → Whenever a subsection states a maximum, check whether its items sum above
  it. If they do, that is a group, not a rounding error.
- **One cap can carry two constraints.** Wisconsin's sections 1 and 3 are
  mutually exclusive, and within section 1 three sub-items are capped at 20.
  The schema cannot nest groups, but a single capped sum at 30 over all six
  criteria produces the right maximum, with the sub-cap explained in the note.
- **The absence of a stated total is not the absence of a design.** New York
  states no maximum, and its seventeen criteria compute to exactly 100. Worth
  saying in the note; the reader can then trust the extraction is complete.
- **A regulation can carry the points and not the test.** New York repeatedly
  gives a criterion a value and then defers the substance to a notice of credit
  availability or agency manual. South Dakota gives 100 points, an eighth of
  everything available, to "Project Characteristics" and defers entirely to
  Exhibit 4. Record the value, say plainly that the test is elsewhere.
- **Deductions can compound with a lost award.** South Dakota deducts 25 points
  for unresolved compliance issues and separately bars that applicant from the
  20-point track record award, so the real swing is 45. Note the interaction;
  the arithmetic alone will not show it.

### When to defer a state rather than code it badly

Three states were surveyed and set aside in this pass, each for a reason worth
recording rather than rediscovering:

- **Nebraska** publishes its scoring as a spreadsheet-style scoresheet whose
  text layer separates labels from values, sometimes printing the value before
  the label. Pairing them from the text layer would be guesswork. It needs an
  image-based pass over its five pages.
- **South Carolina** publishes only redline PDFs, so struck-out and replacement
  values merge in extraction: the raw text reads "Max - 65 70 points" where 70
  is correct. Also needs an image-based pass.
- **Nevada** and **Iowa** are not hard, only long: Nevada runs fifteen pages of
  round-relative preference points, Iowa a twelve-category site appeal matrix
  inside a larger section. Both deserve a dedicated pass rather than the tail
  end of one.

The rule this suggests: survey first, and if the document needs a different
*method* — images rather than text, or a session of its own — stop and say so.
A half-read state costs more to repair than to do properly later.

### Three fields added after sixteen states

Added once the pattern was clear across enough states to be sure of the shape,
rather than guessed at the start:

- **`scored_against_round`.** Six criteria so far are scored against the other
  applications in the round, not a fixed standard. Their `points_max` is a
  ceiling nobody can plan for, and comparing such a value across states means
  something different from comparing a fixed threshold. It was living in prose.
- **`tier_mode`.** Tiers serve two opposite purposes and look identical in the
  data: North Dakota's universal design components sum to its maximum, Hawaii's
  green certification levels are alternatives. `naive_total`, which is the
  headline double-counting figure, cannot be read honestly without knowing
  which. Backfilled by arithmetic for the sixteen states coded before the field
  existed (tiers summing to the maximum read as additive, a largest tier equal
  to the maximum reads as alternative) — **those values are inferred and should
  be confirmed during human review**; set it explicitly from here on.
- **`detail_external`.** Eighteen criteria state a point value and defer the
  test to a document the corpus does not hold, including South Dakota's 100
  points for "as detailed in Exhibit 4". A reader deserves to see which figures
  rest on something we cannot show them.

### Freezing the text, and why we did not

Considered after North Dakota: should extraction work from a frozen text
artefact rather than the live PDF?

Decided **no**, because the human reviewer reads the PDF. A citation of PDF
page plus verbatim quote is checkable directly against what the reviewer has
open; an offset into a frozen text file is not. The risk freezing addresses —
the text moving underneath a citation after a re-OCR or a silent file
replacement at a rolling URL, which New Jersey's `tc_qap.pdf` path invites —
is covered instead by `qaps.text_sha256`, the hash of the extracted text at
ingest. `verify_citations` compares it and says loudly when a document's text
has changed. For OCR'd documents the OCR'd PDF is itself the frozen artefact,
and its hash is recorded in `data/sources.csv`.

### Corpus expansion to 50 states (collection, not extraction)

Lessons that will bite the next extractions:

- **Five states do not keep scoring in the QAP**, and two have no scoring to
  extract at all (Florida delegates to RFAs, Montana has no point system).
  → Rule added to §1: count "point" occurrences before extracting.
- **Kentucky's scoring is in a spreadsheet**, not a PDF. The pipeline assumes
  PDFs end to end, so Kentucky needs a decision before it can be coded.
- **Utah scores by weight, not points** (weight × score, max 5,000). Vermont
  already scored in checkmarks. `scoring_unit` exists for exactly this; use it
  rather than flattening into points.
- **Several documents state no cycle year at all** — Alaska, Idaho, Virginia,
  New York, Washington, California. The cycle then comes from the agency's own
  page, and belongs in `data/sources.csv` with `cycle_source = 'manual'`, not
  guessed into the extraction.
- **Agency abbreviations collide across states.** CHFA is Connecticut and
  Colorado; OHFA is Ohio and Oklahoma. State names collide too: "Arkansas"
  contains "Kansas", and "West Virginia" contains "Virginia". All three
  misfiled a document before being fixed in `ingest.py`.

### Ohio, Pennsylvania, Delaware, Michigan 2026

Four states coded in one batch after the three-column schema change. All four
reconciled exactly to a stated total, which is the first batch where that
happened for every state in it.

- **Extract at the grain the state publishes.** Pennsylvania has a Selection
  Criteria Scoring Summary Table (pp.42–43) and Michigan a Quick Reference
  Sheet (p.47), each naming every criterion and its maximum. Coding to that
  grain made both reconcile first time. Where a state gives you its own index
  of criteria, use it as the spine and hang the body detail off it — do not
  invent a grain from the prose.
- **A summary table can contradict its own body, and the body usually wins.**
  Delaware states 234 total points on p.34 and 231 on p.52. The whole gap is
  one criterion: the summary lists Management Experience and Performance at
  15, the body heads it `(0-12)`, and 12 is what its sub-items (5 + 2 + 5) and
  the section header of 37 both require. Coded 12, recorded the 15. The same
  document also heads Community Compatibility "up to fourteen (14) points" and
  then caps it at twelve two sentences later. **Check section-header arithmetic
  against both the body and the summary before trusting either.** Where they
  disagree, code the one the sub-items support and record the other in the
  note with an explicit call for reviewer confirmation.
- **Tracks are for mutually exclusive scoring universes, not just set-asides.**
  Michigan has four: urban and rural opportunity criteria are alternatives to
  each other ("A project will only be eligible for points from the applicable
  Tab A or B"), supportive housing criteria apply only to PSH projects, and the
  rest apply to everyone. Four track totals, each reconciling, describe Michigan
  far better than one number could. Delaware's bonus points went on their own
  track for the same reason: they sit on top of the 231 rather than inside it.
- **A stated total belongs to a track, not to a document.** The loader used to
  compare every track against one `stated_total` and reported a mismatch on
  Delaware's bonus track that was not one. Fixed: `load_extraction.py` now
  prefers the per-track figure from `track_totals` and falls back to the
  document-level figure only for the default track.
- **Where a track total is computed rather than read, say so in the row.**
  Michigan states each section total but no total for the sections every
  project faces. The 78 recorded for its default track is the sum of three
  stated section totals; the `track_totals` note says exactly that, so the
  figure is never mistaken for one read off the page.
- **A negative criterion confirms the is_negative rule.** Michigan's section D
  totals 11, which is its two positive criteria (7 + 4) and excludes its four
  deductions (−5, −20, −20, −20). Independent confirmation that stated maxima
  exclude deductions, which is what the loader has assumed since Rhode Island.
- **Record what you did not read.** Michigan's E.3 and E.4 carry stated maxima
  whose tier composition was not fully read. Both notes say so and ask the
  reviewer to confirm, rather than presenting a partial tier list as complete.
  Same for Delaware 3.3, where the table offers 15% only in New Castle County
  and it is unclear whether that is deliberate.
- **Self-score workbooks printed to PDF read cleanly but carry spreadsheet
  litter.** Michigan's text layer includes `#DIV/0!`, empty self-score columns
  and out-of-order table fragments, and headings arrive space-padded
  ("Energy  Efficient  Building  Policy"). The loader's whitespace-normalising
  fallback handles the padding; do not retype the heading to make it look
  tidy, quote it as it sits.

### Test the bootstrap, not just the pipeline

Found by cloning the repo into a temp directory and running it as a session
with no access to this machine would.

- **`schema.sql` had drifted from the live database.** `text_sha256` was added
  to `qaps` by `ALTER TABLE` and never written back to the schema file. Every
  working machine was fine, because every working machine already had the
  column. A fresh clone built a `qaps` table that `ingest.py` could not write
  to, and ingest reported each document as ingested while committing nothing.
  → **When a column is added by ALTER TABLE, add it to `schema.sql` in the same
  change.** A schema file that only describes machines that already work is
  not a schema file.
- **A dependency on `$QAP_PDF_DIR` was fatal where it should have been
  survivable.** `verify_citations` exited if the shared drop folder was not
  configured, which is exactly the situation a repo-only session is in. Now it
  resolves through `qapdb/paths.py` and reports the PDFs it could not open.
- The check is cheap and worth repeating after any schema or path change:
  `git clone . /tmp/x`, create the database from `schema.sql`, ingest the
  bundled PDFs, load, verify.

### Nevada, 2026

73 criteria: 44 competitive, 1 tiebreaker and 28 thresholds. All 73 citations
verified first time. The bond track reconciles at 40. **The 9% track does not
reconcile, and that is the finding:** the plan states 97, and its own section
maxima cannot produce 97.

- **Hand-summing first is what made the mismatch trustworthy.** The 7.3 and
  7.4 section maxima alone come to 99 (69 + 30). That is before 7.2's project
  type priority points, which pay 10 to the top project in each category (15
  for Tribal housing), plus 1 for a veterans preference. No whole section can
  be dropped to reach 97. Because the arithmetic was done by hand before
  loading, the loader's 115 confirmed a reading rather than prompting a hunt
  for a missing row. Recorded in `track_totals.note` with the realistic
  ceilings (110 non-Tribal, 107 Tribal) and the knock-on effect: the 60%
  minimum score on p.6 is 58.2 points of 97 but 66 of 110.
- **The dry run was ignoring exclusivity groups.** `load_extraction.py`
  summed grouped criteria flat, so any state with a group printed a
  "computed" figure that the database views would never produce: Nevada read
  194 in the dry run and 115 in `v_total_reconciliation`. Fixed: the dry run
  now applies `max_one` and `capped_sum` the same way `v_group_contribution`
  does. Earlier states with groups reconciled through the view, so their
  recorded results stand, but their dry runs would have shown false
  mismatches.
- **Round-relative scoring can be a whole section.** All eight 7.2 project
  type priorities pay 10 or 15 points to the best application in the category
  and 5 to the second-best, and nothing to anyone else. They are a `max_one`
  group, because Section 4 allows one category per application, and every one
  carries `scored_against_round`. Section 1.1 ("check all category ... boxes")
  seems to allow more than one category. That tension is in the group note.
- **Cross-references in a QAP can point nowhere.** "Section 21" for deductions
  and "Section 7.15" for tie breakers do not exist, and 7.4.6 announces three
  factors and lists two. None of them changes a number, but they tell the
  reviewer how carefully the document was amended. Record them.
- **Compare scoring ladders with the threshold limits they sit beside.** The
  Clark County rehab cost ladder pays a point at "$135,000 or more", above the
  $120,000 rehab cap in Section 6.4, and skips $120,001–$134,999 entirely. The
  new construction ladders end exactly at the 6.4 limits, which makes the rehab
  gap look like a drafting error rather than a policy choice. This only showed
  up because the thresholds were read in the same pass.
- **Sentence-level contradictions hide between adjacent sentences.** 7.2 says
  eventual tenant ownership projects "are not eligible for scoring in Section
  7.2", then says Rent to Own projects "will only receive points under" 7.2.8.
  Section 4.8 defines the two terms as the same thing.
- **Operational: running `manifest.py` against a repo-only database wiped the
  corpus record.** A database built from `data/pdfs_bundled/` holds 11 of 68
  documents, and `manifest.py` overwrote the manifest with just those rows.
  The same partial database also recomputes `is_most_recent` among the
  documents it can see, which flips Minnesota's QAP and worksheet. Fixed:
  `manifest.py` now keeps manifest rows for documents it does not hold.
  → **Before committing `data/manifest.csv` from a partial database, read the
  diff.** Take only the rows for the state you coded. Here that was one field,
  Nevada's stated total.

### Iowa, 2026-2027 (second amended)

55 criteria: 35 competitive, 5 tiebreakers, 1 appeal-remedy criterion and 14
thresholds. All 55 citations verified; one needed its page corrected first (a
threshold quote was on p.22, not p.21). The computed 63 matches the hand-sum.
**Iowa states no overall maximum**, so the 63 checks completeness rather than
reconciling to a stated figure.

- **Stated section maxima cover less than it looks.** Iowa states 30 for
  Affordability, 5 for Site Appeal and 5 for Market Appeal. Location, the
  Development Team and Other have no section figure. When a hand-sum rests
  partly on item values, say in `track_totals.note` how much of it does (here
  28 of the 63), so nobody takes a completeness check for a reconciliation.
- **A per-share rate with no ceiling takes the section cap as its maximum.**
  "5 points for each 4.0% of the Tax Credit Units" has no stopping point of
  its own; the "30 points Maximum" on the section is what stops it. Coded as
  `per_unit` with `points_max` 30 inside a `capped_sum` group at 30, and the
  note says the 30 comes from the section, not the item.
- **A preamble can contradict the item it introduces.** 6.1 says categories
  A–E "are not available to an Applicant that elects the minimum set aside as
  Average Income Test"; 6.1.E is "Projects that elect Average Income Test". The
  basis boost in 5.5 treats E as live, which suggests the preamble should
  have said A–D. Coded as available and flagged, not silently fixed.
- **When a matrix only pays through an average, code the average.** Site
  Appeal has twelve categories scored 5/3/1/0, but none is worth points on
  its own: the twelve are averaged and rounded to 0–5. It is one criterion at
  5. That also avoids pairing column descriptors the text layer has flattened.
  Some categories fill only two of the four columns, and guessing which would
  break rule 1.
- **"0 to 2 points" is a range, not a tier list.** Density, Disaster Recovery
  and High Quality Jobs state only a range and defer the test to an appendix
  that is not in the document. They carry `detail_external` and no tiers. A
  1-point tier that is not on the page would be an invented number.
- **Look for points outside the scoring section.** 7.10.B awards 5 points in
  the next round to a project that won an appeal but was not funded. It is on
  its own track, like Delaware's bonus, so the base 63 is not inflated by a
  remedy few projects can claim.

### Alaska, FY2027 GOAL plan

49 criteria: 31 competitive, 2 tiebreakers and 16 thresholds. All 49
citations verified, two only after a page range was widened to cover an item
continuing onto the next page. The computed 231 matches the stated 231 and the
hand-sum.

- **The summary table was the spine, again.** pp.38–39 list every section
  maximum, every item value and "TOTAL POINTS 231". The body agrees with it
  line for line. Reading it first turned the body pass into checking rather
  than discovery.
- **When items overshoot a stated maximum by exactly one item, say so, and do
  not invent the rule.** Section 3's nine items sum to 46 against a stated 38.
  The gap is exactly the 8-point Senior Housing Offset. Its eligibility (at
  most 20% of units income-restricted) limits 3.a to 2.4 points in practice,
  which is probably what "offset" means, but the plan never says the offset
  excludes anything. Coded as a `capped_sum` at the stated 38, which is what
  the text supports, with the inference in the note for the reviewer. A
  `max_one` or cross-criterion exclusion would have encoded a rule nobody
  wrote.
- **Either/or families inside one criterion are tiers, and the note carries
  the arithmetic.** Energy Efficiency is 14 = best of (i)–(iv), worth 8, plus
  best of (v)–(vi), worth 6. Pro Forma is 30 = the hard debt ladder (24) or the
  automatic 14 for projects that cannot carry debt, plus 1 + 5. `tier_mode:
  mixed`, with the sum written out, is enough for a reviewer to check it.
- **Some criteria pull against each other by design.** Market Conditions
  rewards low vacancy and population growth, while Rehabilitation pays 4
  points each for negative growth and above-average vacancy, from the same
  data. A 20-point small-community award sits beside 45 points for
  labour-market and rental-market strength. Note the tension; the arithmetic
  will not show it.
- **Penalties with no maximum take a null `points_max`, not a guess.** The
  summary says "Penalty points – no max", and three of the four schedules are
  per-instance with no cap. Recorded as one negative criterion with
  `points_max` null and the schedules in the note.
- **Committee rankings are scored against the round too.** Project Leveraging
  (28 points) is ranked by a review committee, and points are "evenly
  distributed down the consolidated average ranking". That is
  `scored_against_round`, even though no formula names the other
  applications.

### Arizona, 2026 and 2027

44 criteria: 14 competitive, 6 tiebreakers and 24 thresholds, all verified
first time. There are three tracks and no stated totals. Hand-sums and loader
agree: rehab 170, new construction 185, and a 25-point Tribal add-on.

- **An add-on track is not the same as an alternative track.** The rehab
  criteria (V.B) and the new construction criteria (V.C) are separate
  universes: a project is in one set-aside. The Tribal set-aside, though, uses
  every V.C criterion plus one more (LOCCS Balance). Recording LOCCS as a
  `tribal` track holding only that criterion, next to the default track,
  keeps both totals honest (185 and 210). Say in `track_totals.note` which
  kind each track is, because the data cannot show it.
- **A criterion incorporated by reference still needs its values read at the
  source.** V.C.4 says only "based on the criteria described in QAP Section
  V(B)(4)". Its tiers come from p.17, and the note says so, since the page
  cited for V.C.4 carries no numbers.
- **Where a floor is filed matters.** The 160-point minimum sits under the New
  Construction threshold heading but says "the competitive 9% LIHTC round".
  Against rehab's 170 it would leave only 10 points of slack. It is recorded
  as a threshold with both readings, not assigned to a track by guesswork.
- **Threshold minimums and scoring ladders rarely meet cleanly.** Rehab must
  spend at least $25,000 per unit to be eligible, the ladder pays nothing
  below $30,001, and exactly $30,000 falls between rows. This is the Nevada
  lesson again; it is worth checking every time.
- **An unfinished cover is a document-status finding.** "Submitted on December
  1, 2025 and amended on ____" leaves unclear which version this is. It goes
  in the `_comment` for the reviewer and is not settled by guessing a date.

### New Jersey, 2026 (N.J.A.C. 5:80-33)

66 criteria: 41 competitive, 5 tiebreakers and 20 thresholds, all verified
first time. There are three cycles and no stated maximum. The core scale is 75
and the cycle add-ons are Family 22, Senior 13 and Supportive Housing 23, so
the cycle maxima are 97, 88 and 98. Every figure matched a hand-sum made
before loading.

- **When one scale is defined as another scale minus some items plus others,
  code the shared core once.** The Senior and Supportive Housing scales are
  "all point categories of the Family Cycle except …" plus their own. A core
  track of the shared categories, with one add-on track per cycle, turned
  three 25-item scales into 46 rows. Only one category had to be recorded
  twice ((a)21, in Family and Senior but not Supportive Housing), and the
  label suffix `.family`/`.senior` keeps the taxonomy keys unique.
- **A floor stated as a share of an unstated maximum still needs the
  maximum.** 33.14(a) makes 65% "of the maximum score" the eligibility floor,
  and the regulation never says what the maximum is. The computed maxima give
  the floor its value (about 63 in Family). That is worth putting next to the
  threshold row, with the caveat that it is our arithmetic, not the
  regulation's.
- **Location can cap a project below the scale maximum.** Inside a Targeted
  Urban Municipality the same 15-year extension earns 15 rather than 20, and
  the MRI item gives way to a 2-point opportunity zone item. A TUM Family
  project tops out at 91, not 97. Say so in the note; one track total cannot.
- **"Respectively" with the wrong number of items is an interpretation.**
  33.17(a) replaces two categories "respectively" with three items. The
  reading that reproduces the stated seven-point cap is coded and flagged.
- **Deductions that can stack go in at the larger stated figure, with a
  note.** (a)15 deducts 15 for one kind of noncompliance and 10 for another,
  without saying whether both can apply. Coded at −15 with the possible −25
  explained, rather than inventing a combined figure.
- **Regulations format well for extraction.** Justified text breaks lines
  mid-sentence, but the whitespace-normalising verifier does not care. Pick
  quotes that avoid line-end hyphenation ("set- asides") and they verify
  first time.

### Minnesota, 2026-2028 (self-scoring worksheet)

40 criteria across two documents: 25 competitive and 8 thresholds from the
worksheet, and 6 tiebreakers and 1 threshold from the QAP. All verified. No
maximum is stated. The computed 258 is a ceiling of caps and matched the
hand-sum.

- **When scoring lives in a companion document, code it there and give the
  QAP its own small file for what the companion defers.** The worksheet
  carries every point. The QAP carries the tie breakers and the 30-point
  floor for the RD/Small Projects set-aside, which the worksheet exempts from
  its 80-point floor without stating a figure. `MN_qap_2026_2028.json`
  matches the QAP PDF and holds only those, so every citation stays on the
  page it names.
- **Heading ranges are a gift; check each against its options anyway.** Every
  criterion is headed "(7 to 37 Points)" or similar. Reading the options
  confirmed every upper bound (30 + 7, 40 + 5, 19 + 7, 13 + 7, 4 + 8 …). One
  wrong range would have meant a wrong maximum, and the ranges are the only
  place the totals are stated.
- **Most of Minnesota's exclusions are about units, not criteria, and the
  schema cannot hold them.** "Cannot be claimed for the same units … must be
  separate and distinct" (1.C/1.D, 2.A Tier 2/2.C, 2.B/2.C) and a 25% cap on
  supportive units with Section 811 limit the real maximum well below the
  sum of caps. Only whole-project exclusions went into groups: Large Family
  or Senior, and Preservation Tier 1 or Rental Assistance. The rest are in
  notes, and the track note says plainly that 258 cannot be reached.
- **An exclusion that bars one tier, not the whole criterion, is a capped
  group at the best allowed route.** 2.B is barred to Preservation Tier 1
  projects but not to Tier 2. Tier 1 alone is worth 45; Tier 2 plus
  severity plus Rental Assistance is worth 46. A `capped_sum` at 46 is the
  North Dakota pattern again, and `max_one` would have undercounted by one.
- **Printed and PDF page numbers can drift by different amounts within one
  state's documents.** The worksheet is three pages off and the QAP eight in
  the pages cited. The protocol already says to cite PDF indices; this is
  why.

### Oklahoma, 2027 (Application Instructions, converted from .docx)

28 criteria: 12 competitive, 1 tiebreaker, 4 ranked priorities and 11
thresholds, all verified first time. There are two tracks and no stated
totals. The 9% selection criteria compute to 83 and the State Tax Credit
ranking to 12, both matching the hand-sums.

- **A converted document keeps its old table of contents.** The TOC's page
  numbers belong to the .docx, not the PDF. Map the sections by searching
  the text layer for their headings before citing anything; that took one
  command and avoided a page of wrong citations.
- **A self-score sheet can omit the criterion that matters most.**
  Attachment #11 lists nine criteria worth 62. The body has a tenth,
  Development Cost Efficiency, worth 24 and ranked against the round by
  staff after the deadline, which no applicant can self-score. Hand-summing
  from the sheet alone would have missed a quarter of the scale. Reconcile
  the summary sheet against the body in both directions.
- **"Exclusive list" can mean exhaustive.** "The following is an exclusive
  list" introduces nine additive location items capped at 10. Read it for
  meaning, not as a hint of mutual exclusivity.
- **Two criteria that cap each other can be exact as a capped group.**
  Targeted Populations pays 5 (family) or 8 (elderly), and Individuals with
  Children (3) is barred at 8. Both routes reach 8, so a `capped_sum` at 8
  is exact rather than an approximation.
- **A second scoring system can hide in a statutory section.** The Oklahoma
  Affordable Housing Act section ranks 4% State Tax Credit requests by four
  ordered preference categories and then a 12-point efficiency score. That
  uses `ranked_priority` rows for the first time since Connecticut, on a
  `state_credit` track of its own.
- **Attachments are part of the document and can contradict it.** The
  amenities certification gives a storm shelter 5 points where the body
  gives every amenity 1. The maximum is unaffected, but the note records it.

### Wyoming, 2027

39 criteria: 23 competitive, 3 tiebreakers and 13 thresholds, all verified
first time. The computed total matches the stated 495, and the stated −1,510
in negative points reconciles too.

- **Two-column summary tables need the page image, not the text layer.** The
  summary on pp.37–38 has a Negative column and a Maximum Points column, and
  the text layer interleaves them ("d) Environmental/Inappropriate Location
  -200 5"). Every figure in the reconciliation was read from the rendered
  pages, and the `_comment` says so. This is the Nebraska problem in a
  milder form. It was solvable here because the table is short and the
  images are clean.
- **Reconcile the negatives as well as the maxima when a document states
  both.** Wyoming's −1,510 is the sum of −30, −280 and −1,200. Checking it
  exposed two section headers that disagree with their own parts: −28
  against −30 for Housing Needs, and −250 against −280 for Project Location.
- **Worked examples are claims to check, not illustrations to trust.** The
  Donations rule pays 3 points per 1% of project cost. The example beside it
  gives a 10% contribution 35 points, where the rule gives 30. Two
  statements, one number each; neither is right by default, so both go in
  the note.
- **A table can reach its stated maximum only by counting alternatives.**
  Amenities sum to exactly the stated 50, but only if a project claims both
  the new-construction and the acquisition/rehab laundry rows. Coded at the
  stated 50 with the 45 and 49 single-type ceilings noted, because a mixed
  project might claim both.
- **A category-level floor is its own kind of threshold.** Housing Needs must
  reach 100 of its 158 before anything else is scored. Recorded as a
  threshold row, with a note that it applies to a category, not the total.
- **Deductions sized to eliminate are still worth recording at face value.**
  Up to −1,000 for total project costs over the limits, with a published
  escape hatch (the Statistical Outlier Method). The value is extreme but
  stated, so it goes in as written.

### Colorado, 2025-2026 (second amendment)

34 criteria: 19 competitive and 15 thresholds, all verified first time. No
maximum is stated. The computed 220.5 matched the hand-sum; it is a ceiling
with one criterion missing.

- **A low count of "point" mentions is a prompt to look, not a verdict.**
  The handoff flagged Colorado because 102 pages held only 68 mentions of
  "point". The scoring is all in Section 5, seven pages long; it is compact
  because the largest criterion is a formula. Survey the pages that carry
  the mentions before deciding to defer.
- **A weighted formula has a ceiling even when no maximum is stated, and it
  must be labelled as computed.** Low-income targeting multiplies the share
  of units at each AMI level by weights of 50, 72.5 and 92.5. The ceiling is
  92.5, and it is available only with project-based assistance; the cap of
  60% on 40% AMI units makes it 84.5 otherwise. `points_max` records 92.5,
  and the note and `_comment` say both figures are derived from stated
  weights, not stated. Where you do this, say it every place the number
  appears.
- **When the points live in a document the corpus lacks, leave
  `points_max` null.** Housing Need scores come from Application exhibits C-1
  and C-2. The criterion is recorded with `detail_external` and no maximum,
  and the total's note says it is excluded. A guessed figure would have made
  the total look complete.
- **A required election can make a scored criterion automatic.** 9% projects
  must elect 25 years of extended use, which is exactly the 40-point tier of
  the extended-use criterion. For 9% applicants the 40 points are free. The
  minimum score of 130 has to be read with that in mind.

### Indiana, 2026-2027 (v2)

69 criteria: 42 competitive, 4 tiebreakers and 23 thresholds, all verified
first time. The document states 165. The computed core is 121, with a 9%
add-on of 25 and a bond add-on of 4, and the difference is fully accounted
for.

- **A summary total can be the flat sum of items no application can
  combine.** Every section's items add up exactly to its stated subtotal,
  and the subtotals to 165. But the text makes Vacant Structure,
  Preservation (with its bonus) and Infill mutually exclusive (−12), and the
  two supportive-housing Institute items exclusive (−3). Some categories are
  9% only (25) and one is 4% only (4). 121 + 25 + 4 + 12 + 3 = 165, so the
  stated total is reachable by nobody: a 9% application tops out at 146. The
  mismatch is recorded against the core track by design, with the
  decomposition in the note. Unlike Nevada, whose gap nothing in the
  document explains, Indiana's gap is entirely its own exclusion and scope
  rules.
- **Scoring-universe scoping is often one sentence at the end of a
  criterion.** "Competitive 4%/bond/AWHTC applications will not be scored in
  this category" appears inside three criteria, and "in addition to those
  categories" opens the bond section. Read every criterion's closing lines
  for scope before deciding which track it belongs on.
- **Cross-references drift when sections are relabelled.** The exclusion
  notes in 6.2(D)–(F) name the categories one letter off, one of them naming
  itself, and 6.3(H) sends the reader to "6.4H", which does not exist. The
  intended targets were unambiguous here, so the exclusions are coded and
  the wrong references recorded. Where they are not unambiguous, record and
  do not code.
- **Checked estimates out of the notes.** First drafts described the amenity
  charts as "some 90" items and the service list as "some fifty". Neither was
  counted, so both were removed. A number in a note is still a number, and
  rule 1 applies to it.

### Ten bundled states, consolidated

After Nevada through Indiana, the recurring lessons were promoted from this log
into the rules above rather than left to be rediscovered: score-sheet versus body
in both directions and points outside the scoring section (§1); two-way
criteria and matrices scored through a count (§2); `points_max` null where the
values live elsewhere, and the two kinds of track (§3); page images for
interleaved tables (§4); tier-level exclusions, unit-level exclusions, and
labelled formula ceilings (§5); completeness checks, MISMATCH by design, and
negative reconciliation (§6); category floors and companion-document files
(§7); the dry run's group handling and the partial-database manifest (§8);
and computed figures, wrong cross-references and estimates in notes (§9).

Of the ten states, two reconciled fully to a stated total (Alaska and
Wyoming). Nevada's bond track reconciled, but its 9% track recorded a MISMATCH
that nothing in the document explains. Indiana recorded a MISMATCH that its
own exclusion and scope rules explain exactly. The other six state no total
at all. The absence of a stated total is the norm in this batch, not the
exception. That makes the hand-sum-first rule more important, not less: it is
the only check that exists.


### A plausible filename is not evidence that a document scores anything

Oregon was listed as ready to code on the strength of its page count and its
name. Opening it showed `oregon-qap-2025.pdf` is a public comment-and-response
log: pages 44–142 are named commenters and agency replies, and the only point
values in the file sit inside a reply discussing *proposed* resilient
construction scoring. Coding it would have produced criteria attributed to
Oregon that Oregon never adopted.

The signal that caught it was the one already in §1: count "point" occurrences
before extracting. Oregon has 23 across 147 pages. Colorado, at 68 across 102,
looked similar and turned out to be genuine — so a low count is not proof
either way. **Read where the occurrences fall, not just how many there are.**
In a real scoring plan they cluster in a scoring section; in Oregon they were
scattered through prose, several inside sentences like "I can't remember what
it is, but if it's historic, then you get some points for it".

This check costs one read and belongs in the pre-flight, before any state is
promised to a batch.


### Illinois 2027-2028: a summary heading can carry a rule the body omits

Illinois reconciled on every track: 80 for the general criteria, and 20 for
each of three policy tracks. An application adds one of those tracks to the
general criteria. That pattern is the add-on kind of track from §3.

The one judgement call sat in the development team rows. The body caps BIPOC
Development Control plus W/D/M Enterprises at 11 for a for-profit team and at
7 for a non-profit team. It awards Non-Profit Participation 4 points and never
says a for-profit team cannot take them. The p.41 summary files those 4 points
under "NON-PROFIT TEAM ONLY CHARACTERISTICS" and states a section subtotal of
14. Under the body alone, a team could reach 18. Only the summary's heading
makes 14 reachable, so I coded a capped group at 11 and recorded the gap. This
is §1's score sheet versus body in a new form: the disagreement sits in a table
heading, not a number. Read the summary's headings as closely as its values.

A policy-track criterion can also exclude a general one. PSH Rental Assistance
is barred to a project that earned Deeper Income Targeting. The two sit in
different tracks, so no group can express the bar, and it lives in the note.
It does not change any maximum, because the general criteria are always
scored.


### New Mexico 2026: a verified quote can still point at the wrong criterion

New Mexico states no total. The body maxima sum to 115, and three exclusions
bring that to 102. The three exclusions: one housing priority of H, I and J;
tenant ownership or a longer use period; rehabilitation or adaptive reuse. The
loader matched the hand-sum.

The lesson came from the citation check itself. I first cited the Seniors
priority with "Scoring Points Available (up to 5 points)" on pp.49–53, and it
verified. But the phrase that matched is on p.49, in the Special Needs
priority. The Seniors copy is on p.52, which the loader never looks at: it
searches only `page_start` and `page_end`. Sibling criteria that share a
template repeat headings like this. **A verified citation proves only that the
words are on that page, not that they belong to this criterion.** When a
criterion spans several pages, quote a sentence unique to it, such as its
eligibility or threshold line, not a boilerplate heading.

The summary table also letters the criteria after O one step higher than the
body does. It leaves a blank P row, so its Q is the body's P. Body letters are
coded. A summary is a cross-check on values, and it is no authority for labels
either.


### Kansas 2026: points that every application must earn are a threshold

Kansas has three kinds of points, and each needed a different home.

- **Appendix A carries 310 points** in seven categories that K.A.R. 110-10-1
  mandates. Each is all or nothing, and an application must earn all 310 just
  to be invited. Points that nobody can fail to earn and still compete do not
  rank anyone. I coded them as thresholds, with the value in the heading and
  note, and checked that they sum to the stated 310. Loading them as
  competitive would have made a 125-point plan look like a 435-point one.
- **The 4% round reuses the 9% criteria.** A chart (p.24) marks which ones
  apply, and a 55-point minimum replaces ranking. I did not duplicate 17
  criteria into a 4% track. I put the one 4%-only criterion on `four_pct` and
  named the 9%-only ones in the notes and the comment. §3's add-on track works
  here too. The 4% maximum of 85 is written down as computed and is not
  reconciled.
- **Rehabilitation has no points at all.** Six factors are ranked "in
  declining order of significance". They are coded as `ranked_priority` on a
  `rehab` track whose total says so.

Kansas also states a value once for a set of alternatives: "An application may
earn 15 points in one of the four subsections below". I gave each subsection 15
in a `max_one` group and noted that the figure is stated once, not per
subsection.


### Idaho 2026: an exclusion inferred from scope must say so

Idaho states no total. Its criteria sum to 109, and the loader matched.

One of its two exclusion groups is stated outright: older-persons housing
cannot take the children points. The other is not stated anywhere. The
rehabilitation revitalization point (item 11) is written for "Rehabilitation
Developments". The cost-per-square-foot score (item 14) is written for "New
Construction or Adaptive Reuse Developments" and excludes rehabilitation. No
project can earn both, so the computed maximum is 1 lower than the flat sum.
Coding that as a group is right. But the group's note has to say the exclusion
is **inferred from the criteria's scopes**, not quoted, and its
`source_quote` should be the sentence that fixes the scope. A reviewer
checking the group against the page should not go looking for a bar that is
not there.

Idaho's negative points apply per instance "with no maximum number of
occurrences/negative points assessed". Each is coded with `points_max` null and
a per-instance tier, as §6 already says for deductions with no maximum. The
Green Building Threshold counts component "points" toward an 8-point minimum.
Those are threshold points and stay in the thresholds file.


### Mississippi 2026: check the document's own year, not just the filename's

Every page of `mississippi-qap-2026.pdf` carries the running header "2024
QUALIFIED ALLOCATION PLAN". The body says otherwise. p.5 records the adoption
of "the 2026 Qualified Allocation Plan", and the p.19 schedule runs from
January to March 2026. So this is the 2026 plan wearing a stale header, not a
mislabelled 2024 file. Leftovers of the older template show up in the body as
well: a map layer "for the 2024 application year", and an over-concentration
chart for 2022 and 2023. The cycle is set to 2026 through `sources.csv` with
the evidence in its note, and the header is recorded as a contradiction.

The lesson for ingest: the filename, the running header and the body can
disagree. Before trusting any of them, look for a sentence that dates the
plan's adoption or its application round.

Mississippi also has a point adjustment that is not a deduction: +5, 0 or −5
for construction cost against the MCC limit. It raises the maximum by 5. It is
coded as a competitive criterion with a negative tier, not as a negative
criterion, because §6 excludes negatives from the reconciled maximum.


### Georgia 2026-2027: a table can be all graphics, and a cap can sit on another track

Georgia's applicability matrix (p.80) decides which of 22 criteria apply to
four universes: New Affordability and Preservation, each at 9% and 4%. Its
checkmarks are drawn graphics. The text layer holds the row labels and nothing
else, so it reads as a list of criteria that apply nowhere. §4's rendered page
image was the only way to read it. **When a table's text layer is all labels
and no values, suspect graphics before you suspect an empty table.**

The matrix put the structure on a shared core plus add-ons: nine criteria
common to both 9% competitions (50.5), New Affordability's site and community
criteria (+51) and Preservation's own criteria (+42). A Preservation
application also scores the New Affordability site criteria, but caps them at
20 inside its own section. That cap belongs to the preservation track while
the criteria it caps are coded on another. It is one preservation criterion
worth 20, and its tiers name the criteria it draws on. The criteria are not
duplicated. This is the capped-group idea of §5, applied across tracks, where
a `groups` entry cannot reach.

The 4% universes are described in the comment and in each criterion's note
rather than coded, as in Kansas. The exception is the two USDA Portfolio
criteria that exist only at 4%.


### Tennessee 2026: a scale is not a reachable total, and the NM lesson again

Both of Tennessee's scoring sections open the same way: "The scoring criteria
in this section are not intended to allow an Applicant to claim the maximum
100 points." That records 100 as the scale's ceiling and says in the same
sentence that no application reaches it. 100 is coded as the stated total on
both tracks. The MISMATCH against the computed 94 (new construction) and 89
(rehabilitation) is by design, and each track total's note quotes the sentence
that explains it. A reader then sees at once that the gap is the document's
intent, not a coding miss.

The multi-page citation trap from New Mexico caught me again, this time loudly.
I quoted "PHAs shall receive five points." for a criterion running pp.108–110.
The sentence is on p.109, and the loader, which checks only the first and last
page, reported it unverified. That was the right outcome: a quote from the
middle page of a range fails honestly, and a phrase repeated on the first page
passes dishonestly. **For a criterion spanning three or more pages, take the
quote from its first page.**

Tennessee's cross-references regularly name Section 16 for Section 17 items and
Section 18 for the minimum score, which Section 17 states. Each bar was coded
from its evident target and the discrepancy recorded in the criterion's note.


### West Virginia 2025-2026: one criterion, two values, two full tracks

West Virginia states 993 points for New Supply and 993 for Existing Low-Income
Housing. Nearly every criterion applies to both at different values, often
exactly half for Existing. Neither of §3's track shapes fits this. A shared core
plus add-ons would leave nothing in the core, because values differ even where
the criteria are the same. Alternatives with only their unique criteria would
leave neither universe able to reconcile on its own.

So I coded two **full parallel tracks**. Every criterion that applies to both
appears twice, and the Existing copy carries a `.E` suffix on its
`section_label`. Each track then reconciles independently against its own 993.
The duplication is stated in the file's comment, and any per-criterion count
from the database must de-duplicate `.E` rows before being compared across
states. **Use full parallel tracks only when the same criteria carry different
values in each universe and each universe has its own stated total.** Where
values match, prefer a shared core.

Both tracks compute 988. The five-point Tenant Ownership criterion and the
150-point Longest Periods preference bar each other, but the 993 counts both.
That is a MISMATCH by design, as with Indiana. The ten-band location tables,
about 150 numbers in all, were parsed from the page text by script rather than
retyped. Every band carries its page, so the script's output is checkable
against the same text layer the citation checker reads.


### Louisiana 2025: an interleaving warning is a reason to look, not a verdict

The bundle README warned that Louisiana's Appendix A keeps its values in a
separate column and might interleave the way Nebraska's does. It did not
interleave: the text layer lists the labels and then the values in the same
order. It did drop one value. The Elderly Households row's "6" sits past the
point where the column text stops. The rendered pages settled both questions in
minutes, and all three pages were read from images and checked against the
text before any value was written.

A penalty that multiplies a criterion's value, such as "three (3) times the
point value of the selection criteria that cannot be satisfied", has no point
amount of its own. My first draft coded the multipliers ×1 and ×3 as tiers of
−1 and −3. That reads as points and would have summed as points. Such a
penalty gets `points_max` null, no tiers, and the rule stated in the note.


### Washington 2027: when a bar sets one criterion against a set, cap the set

Washington's Eligible Tribal Area criterion bars every other location-targeting
criterion. That puts one criterion (worth 6, 5 or 10 by pool) against a set of
up to five (worth 7, 7 or 3). A `max_one` group picks the single largest
member, so it would compare the tribal points with Location Efficient's 2, not
with the whole set's 7. No group rule expresses "A or the sum of B..F".

I coded it as a `capped_sum` group over all of them, with the cap set at the
better route for each pool: King 7, Metro 7, Non-Metro 10. That gives the exact
maximum. It is a device, not the rule, and the group's note says so: the cap
cannot tell an application which combination is legal. **When you use a
cap as a device, say so in the group note, give both routes' arithmetic, and
keep the real rule in the criterion's note.** If the maximum is all that is
reconciled, the device is sound. The day the database answers "which
combinations are legal", it will need a real rule type.

The three geographic pools differ only in priority populations and location, so
they are add-on tracks on a 159-point shared core. The Policies document also
disagrees with itself on its own date (cover July 2026, p.2 "Republished
8/1/2025") and on its set-aside menu (the text promises 20 options where the
menu lists 17), and its examples cite an "Option 20" that does not exist. The
cycle was set to 2027 through `sources.csv`, from the Policies' own "For the
2027 allocation cycle".


### California 2026: regulations are a QAP, and a scoring paragraph can say "Reserved"

California's QAP is its regulations, CCR Title 4 §§10300–10338, and the 9%
scoring is §10325(c). It reads like statute. Nothing is labelled as a total,
maxima sit in the body of each paragraph ("No more than 15 points will be
awarded in this category"), and paragraph (5) says only "Reserved." A
reserved paragraph is the regulation's own placeholder, not a gap in the
extraction. Record it in the comment so that no one goes looking for a
criterion (5) that was never there.

Tax-exempt bond applications are scored separately under §10326. That is a
different competition, run with CDLAC, and it was not coded. The comment says
so, and so does the handoff. A second pass could add it on its own track.

The tiebreaker after the housing-type check is a computed ratio: leveraged
soft resources plus a basis ratio, with resource-area bonuses in percentage
points. It is coded as a tiebreaker with the formula in its note. Its
"percentage points" are not selection points and must not be summed with
them.
