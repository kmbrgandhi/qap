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
