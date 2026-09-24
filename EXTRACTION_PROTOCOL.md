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
  you would otherwise miss.

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
  `points_type: "negative"` and a negative `points_max`.

## 3. Fields

| Field | Rule |
|---|---|
| `ord` | Order of appearance in the document. |
| `section_label` | **Must be unique within the QAP.** The taxonomy is keyed on `(state, section_label)`, so duplicates silently collide. Where the document letters items A, B, C inside unnumbered sections, prefix the section: `III.B.Fin.A`, `III.B.Inc.A`. |
| `heading` | The document's own heading, lightly normalised. |
| `native_category` | The QAP's own category name, verbatim. Never our taxonomy's. |
| `points_max` | What this criterion alone can yield. Null for thresholds. |
| `points_type` | `fixed`, `tiered`, `formula`, `per_unit`, `unlimited`, `negative`, `none`. |
| `scoring_unit` | `points` unless the document scores in something else. Vermont scores in checkmarks; Utah uses weights (weight × score). Never mix units in one total. |
| `kind` | `competitive`, `threshold`, `ranked_priority`, `tiebreaker`, `set_aside`. |
| `track` | Only where the QAP runs parallel scored tracks that must not be pooled. |
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
- **no stated total** — the QAP states no maximum. Fine, but say so.

## 7. Thresholds and non-competitive criteria

- Thresholds go in a separate `<STATE>_thresholds.json` with its own
  `extractor_version`. The loader deletes by `(qap_id, extractor_version)`, so
  a shared version string makes the second file wipe the first.
- Thresholds carry `points_max: null`, `points_type: "none"`,
  `scoring_unit: "none"`.
- Map thresholds to categories in `data/threshold_categories.json`, keyed
  `STATE|section_label`.

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
before anything is written.

## 9. What to hand the reviewer

The human review queue is for judgement, not for typos. Flag in `note`:

- any value read from a page image rather than the text layer
- any contradiction inside the document
- alternatives that are not additive
- anything the document leaves genuinely ambiguous
- criteria whose points depend on a document published elsewhere (a developer
  handbook, a program bulletin, a data table)

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
