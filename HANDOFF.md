# Handoff

Where this project stands, what is done, and what to do next. Written for a
session starting fresh — including one with only the git repo and no access to
this machine.

Read `EXTRACTION_PROTOCOL.md` before extracting anything. It governs. This file
says *where we are*; the protocol says *how to work*.

## State of the corpus

| | |
|---|---|
| States collected | 50 |
| Documents | 68 |
| **States coded** | **30** |
| Criteria | 1111 (755 competitive, 278 threshold) |
| Point tiers | 1284 |
| Track totals | 43 |
| Documents with a source URL | 33 of 68 |
| Citations verifying | 1111 of 1111 |

Coded: AK AL AR AZ CO CT DE HI IA IN MA ME MI MN MO NC ND NH NJ NV NY OH OK PA RI SD VA VT WI WY

The figures combine the 20 states coded against the full corpus with the ten
coded from `data/pdfs_bundled/`. A repo-only session can rebuild and re-verify
only the ten bundled states (497 criteria); the other 614 need the shared drop
folder.

Every coded state reconciles its computed maximum against a total stated in its
own document, records the MISMATCH and its cause, or records in `track_totals`
that no total is stated.

### Where the ten bundled states landed

| State | Criteria | Tracks | Stated | Computed | Status |
|---|---|---|---|---|---|
| AK | 49 | one | 231 | 231 | OK |
| AZ | 44 | rehab 170, new construction 185, tribal add-on 25 | none | — | no stated total |
| CO | 34 | one | none | 220.5 | no stated total; a ceiling with one criterion's values held elsewhere |
| IA | 55 | base 63, appeal remedy 5 | none | 63 | no stated total |
| IN | 69 | core 121, 9% add-on 25, bond add-on 4 | 165 | 121 | MISMATCH by design, fully decomposed |
| MN | 40 | one (worksheet) + QAP file | none | 258 | no stated total; a ceiling of caps |
| NJ | 66 | core 75, family 22, senior 13, supportive 23 | none | — | no stated total |
| NV | 73 | 9%, bond | 97 / 40 | 115 / 40 | MISMATCH (unexplained) / OK |
| OK | 28 | 9%, state credit | none | 83 / 12 | no stated total |
| WY | 39 | one | 495 | 495 | OK; negatives reconcile to −1,510 |

Six of ten state no total. For them the hand-sum made before loading is the
only completeness check there is; see protocol §6.

## The shape of the work

The extraction JSONs in `data/extractions/` are the real product. `data/qap.db`
is a build artefact — it can be rebuilt from the PDFs plus those JSONs, and is
gitignored. Nothing in the database is hand-edited; everything arrives through
`load_extraction.py`, which refuses to write a citation it cannot find on the
page it names.

```
PDFs ──ingest.py──> qaps rows ──┐
                                 ├── load_extraction.py ──> criteria, tiers, totals
data/extractions/*.json ────────┘         (verifies every quote first)

taxonomy.py         assigns the cross-state category labels
verify_citations.py re-checks every quote, and warns if a PDF's text has drifted
apply_sources.py    applies data/sources.csv (URLs, agencies, manual cycles)
manifest.py         rewrites data/manifest.csv, keeping rows it cannot see
```

## Working from the git repo alone

The full corpus is 123 MB in a shared drop folder and is **not** committed.
`data/pdfs_bundled/` carries 24 documents: the 11 behind the ten states already
coded from the repo, so their citations can be re-verified anywhere, plus 13
covering 12 uncoded states for the next batch. See its README.

`qapdb/paths.py` resolves every PDF: the path recorded at ingest, then
`data/pdfs_bundled/`, then `$QAP_PDF_DIR`. A document that cannot be found is
reported, never fatal — so `verify_citations` runs anywhere and simply says
which PDFs it could not open.

To rebuild the database from scratch with only the bundled PDFs:

```bash
pip install pymupdf
sqlite3 data/qap.db < schema.sql          # the DB is gitignored; create it first
# no sqlite3 binary? python -c "import sqlite3; sqlite3.connect('data/qap.db').executescript(open('schema.sql').read())"
python -m qapdb.ingest data/pdfs_bundled --commit
python -m qapdb.apply_sources --commit
for f in data/extractions/*.json; do python -m qapdb.load_extraction "$f" --commit; done
python -m qapdb.taxonomy --commit
python -m qapdb.verify_citations
```

Extractions whose PDF is absent report `no qap row` and skip. That is expected
and harmless; the JSONs stay in the repo and load once the document is
available.

Do not commit `data/manifest.csv` wholesale from this partial database. It keeps
the rows it cannot see, but recomputes the rows it can, and `is_most_recent`
recomputed over eleven documents flips Minnesota's QAP and worksheet. Commit
only the rows for the state you coded.

The dashboard is `python -m app.server`, then http://127.0.0.1:8000.

## What to do next

All ten of the first bundle are coded. **A second bundle of 13 documents
covering 12 uncoded states is now in `data/pdfs_bundled/`**, so a repo-only
session has work available without the shared drop folder.

1. **Code the second bundle.** Every document was opened and confirmed to carry
   real point values first; `data/pdfs_bundled/README.md` has the per-state
   notes. Illinois, New Mexico, Kansas and Idaho are the most straightforward.
   Two need warning in advance:
   - **Louisiana** keeps its scoring in Appendix A from p.39, a self-score
     sheet whose values sit in a column separate from their labels. Expect the
     text layer to interleave them, as Nebraska's does.
   - **Washington** scores in the 84-page 9% Policies document, not the
     10-page QAP. Both are bundled; code the Policies.

   California (regulations format, CCR §10325) and Texas (218 pages) are the
   hardest. Leave them until last.
2. **Human review of the flagged items below.** Each is recorded in its state's
   notes with the page to check. They are judgement calls, which is what the
   review queue is for.
3. **States still needing a decision or a document:**

   | Group | States |
   |---|---|
   | Need a method decision first | NE, SC (image pass), MD (Program Guide not collected), KY (spreadsheet), UT (weights) |
   | Need a different document collected | OR — see below |
   | Nothing to extract | FL (RFAs), MT (no points) |

   **Oregon was wrongly listed here as ready.** `oregon-qap-2025.pdf` is a
   public comment-and-response log: pages 44–142 are named commenters and
   replies, not a scoring plan, and its only point values sit inside a reply
   discussing proposed resilient construction scoring. Collect Oregon's actual
   QAP before attempting it. The lesson is in the protocol: a high page count
   and a plausible filename are not evidence that a document scores anything.
4. **Fill `data/sources.csv`** for the 35 documents without a source URL, and
   set cycles for Alaska and Wyoming (neither document states one) and
   Arizona (ingest recorded a filename/document CONFLICT).
5. **Consider a `qapdb/stats` command** that prints this file's corpus table
   from the full database. The figures here were computed from the ten bundled
   states plus the earlier 20 states' recorded totals, which is one more place
   for arithmetic to drift.

## Deliberately deferred, with reasons

- **Nebraska, South Carolina** — need an image-based pass. Nebraska's scoresheet
  separates labels from values across columns that the text layer interleaves;
  South Carolina's amendments are redline PDFs where struck and replacement
  values merge in the text layer ("Max - 65 70 points", where 70 is correct).
  Read rendered page images, do not trust the text layer. Wyoming's summary had
  the same interleaving and was read from images successfully; Nebraska's is
  larger but may yield to the same approach.
- **Maryland** — scoring lives in the DHCD Program Guide, which is not yet
  collected.
- **Kentucky** — scoring is in a spreadsheet, not a PDF. Needs a decision before
  the pipeline can take it.
- **Florida** (delegates scoring to RFAs) and **Montana** (no point system) have
  nothing to extract.
- **Utah** scores by weight rather than points, and **Vermont** in checkmarks.
  Use `scoring_unit`; do not flatten either into points.

## Open items

- 35 of 68 documents still have no `source_url`. `data/sources.csv` is keyed by
  sha256; add rows there and run `apply_sources.py`, never edit the DB directly.
- `tier_mode` was inferred by arithmetic for the states coded before it existed
  (88 alternative, 28 additive, 21 mixed at the time). Those inferences are
  flagged in the protocol and still want reviewer confirmation. Every state
  coded since sets it explicitly.
- A blind-agent check over already-coded states is planned. Returning to a PDF
  later to pull more fields costs only the reading, not re-derivation — the
  extraction JSON is additive and reloads idempotently.
- Human review of every coded state is still pending and is expected to happen
  against the PDFs, which is why citations are page-plus-quote rather than
  character offsets.
- Threshold extraction is selective in the ten bundled states: each
  `*_thresholds.json` says in its `_comment` what was left out.

## Contradictions and judgement calls worth knowing about

Recorded, not resolved, per protocol rule 3. Each note asks the reviewer to
confirm against the page it names.

- **Delaware** states 234 total points on p.34 and 231 on p.52; one criterion
  is 15 in the summary and `(0-12)` in the body. 12 is coded. It also heads
  Community Compatibility "up to fourteen (14) points" and caps it at twelve
  two sentences later; 14 is coded, because the section header of 59 requires
  it.
- **Nevada** states "The maximum number of points is 97" (p.24), but its 7.3
  and 7.4 section maxima alone sum to 99, before the project-type points in
  7.2. Computed 115, recorded as MISMATCH. Its 7.2 also bars tenant-ownership
  projects and, one sentence later, admits Rent to Own projects, which Section
  4.8 defines as the same thing.
- **Indiana** states 165, reachable by no application: the total counts
  Vacant Structure, Preservation and Infill together although each bars the
  others, and mixes 9%-only and 4%-only categories. Several of its
  cross-references are off by a letter.
- **Iowa** closes categories 6.1.A–E to Average Income electors, while 6.1.E
  requires that election. E is coded as available.
- **Alaska** Section 3's items sum to 46 against a stated 38; the gap is exactly
  the Senior Housing Offset, but no rule says what it excludes. Coded as a cap
  at 38.
- **Wyoming** headers say −28 and −250 where their parts give −30 and −280, and
  its donations example awards 35 points where its rule gives 30.
- **Oklahoma** gives a storm shelter 5 points in Attachment #13 and 1 in the
  body; the State Tax Credit factors are named for state credits but defined as
  federal ones.
- **New Jersey**'s 33.17(a) replaces two categories "respectively" with three
  items; the reading that reproduces its stated seven-point cap is coded.
- **Arizona**'s cover leaves the amendment date blank, and its 160-point
  minimum sits under the New Construction heading while referring to the whole
  9% round.
- **Colorado**'s 92.5 targeting ceiling, **Minnesota**'s 258 and **New
  Jersey**'s 63-point floor are computed figures, not stated ones, and are
  labelled so in their files.
