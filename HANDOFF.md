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

Every coded state reconciles its computed maximum against a total stated in its
own document, or records in `track_totals` why it cannot. Nevada is the first
whose stated total its own section maxima cannot produce; see below.

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
manifest.py         rewrites data/manifest.csv from the database
```

## Working from the git repo alone

The full corpus is 123 MB in a shared drop folder and is **not** committed.
`data/pdfs_bundled/` carries eleven documents covering ten states (all but Indiana now coded) so
that a repo-only session has real work available. See its README.

`qapdb/paths.py` resolves every PDF: the path recorded at ingest, then
`data/pdfs_bundled/`, then `$QAP_PDF_DIR`. A document that cannot be found is
reported, never fatal — so `verify_citations` runs anywhere and simply says
which PDFs it could not open.

To rebuild the database from scratch with only the bundled PDFs:

```bash
pip install pymupdf
sqlite3 data/qap.db < schema.sql          # the DB is gitignored; create it first
python -m qapdb.ingest data/pdfs_bundled --commit
python -m qapdb.apply_sources --commit
for f in data/extractions/*.json; do python -m qapdb.load_extraction "$f" --commit; done
python -m qapdb.taxonomy --commit
python -m qapdb.verify_citations
```

Extractions whose PDF is absent will report `no qap row` and skip. That is
expected and harmless; the JSONs stay in the repo and load once the document is
available.

The dashboard is `python -m app.server`, then http://127.0.0.1:8000.

## Next states to code

Ten states have their PDFs committed in `data/pdfs_bundled/`; all but Indiana
are now coded. All were
checked to carry real point values before being bundled.

| State | File | Pages | Notes |
|---|---|---|---|

All ten bundled states are now coded; see below for what remains.

## Deliberately deferred, with reasons

- **Nebraska, South Carolina** — need an image-based pass. Nebraska's scoresheet
  separates labels from values across columns that the text layer interleaves;
  South Carolina's amendments are redline PDFs where struck and replacement
  values merge in the text layer ("Max - 65 70 points", where 70 is correct).
  Read rendered page images, do not trust the text layer.
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
  flagged in the protocol and still want reviewer confirmation.
- A blind-agent check over already-coded states is planned. Returning to a PDF
  later to pull more fields costs only the reading, not re-derivation — the
  extraction JSON is additive and reloads idempotently.
- Human review of every coded state is still pending and is expected to happen
  against the PDFs, which is why citations are page-plus-quote rather than
  character offsets.

## Contradictions worth knowing about

Recorded, not resolved, per protocol rule 3.

- **Delaware** states 234 total points on p.34 and 231 on p.52. The gap is one
  criterion listed at 15 in the summary and `(0-12)` in the body. 12 is coded.
- **Delaware** also heads Community Compatibility "up to fourteen (14) points"
  and caps it at twelve two sentences later. 14 is coded, because the section
  header of 59 requires it.
- **Nevada** states "The maximum number of points is 97" (p.24), but its 7.3
  and 7.4 section maxima alone sum to 99, before the 10 to 15 project-type
  priority points in 7.2. Computed 115, recorded as MISMATCH in
  `NV_2026.json` for the reviewer. Its bond track reconciles at 40.

The notes in `DE_2026.json` and `NV_2026.json` ask the reviewer to confirm
against the PDF.
