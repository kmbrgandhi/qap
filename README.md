# QAP competitive-criteria database

A searchable database of state Qualified Allocation Plan scoring criteria for
9% LIHTC, with a verified page citation behind every figure.

## Coding a QAP

Read [EXTRACTION_PROTOCOL.md](EXTRACTION_PROTOCOL.md) first, every time. It
holds the rules for what counts as a criterion, how to quote and cite, how
points and exclusivity are recorded, and the running log of what each
extraction taught us. Update its lessons log when you finish a state.

## Where the PDFs live

**The QAPs are not in this repo.** They live in a shared drop folder that both
collaborators sync. Two reasons: they are large binaries that would bloat git
history permanently, and adding a document should not require touching the repo.

What *is* in the repo is `data/manifest.csv` — one row per document with its
SHA-256, state, cycle, and source URL. That is what makes the corpus
reproducible without shipping the binaries.

### Setup (once per machine)

```bash
cp .env.example .env
# then edit .env and set QAP_PDF_DIR to your local path for the shared folder
```

The path differs on every machine — Dropbox, Google Drive and OneDrive all mount
shared folders differently — which is exactly why it is per-machine config and
`.env` is gitignored.

### Adding a QAP

Drag the PDF into the shared folder. Subfolders are fine; ingest searches
recursively. Then:

```bash
python -m qapdb.ingest --commit      # reads $QAP_PDF_DIR
python -m qapdb.manifest             # refresh the manifest, then commit it
```

Ingest identifies the state, cycle, and draft/final status from the document
itself, hashes it, and flags anything it could not determine rather than
guessing. Re-running is safe: documents are deduplicated by SHA-256, so the same
file added twice under different names is ingested once.

**Please record the source URL** for anything you add — the agency page you took
it from. Without it nobody else can re-fetch the document, and
`python -m qapdb.manifest` will list every document still missing one.

Record it in `data/sources.csv`, which is committed, and apply it with:

```bash
python -m qapdb.apply_sources --commit
```

The URL cannot live only in the database: `data/qap.db` is a build artefact and
is rebuilt from scratch. `data/sources.csv` is keyed by SHA-256, so renaming a
PDF does not break the link, and it also carries the handful of corrections a
human verified against the agency's own site — the agency name, and a cycle for
documents whose text never states one. Virginia's plan, for instance, contains
the string "2026" nowhere; that is the agency's label for it. A cycle set this
way is stored with `cycle_source = 'manual'` so it is never mistaken for one the
document stated.

Note a few documents are mirrors or derivatives rather than the agency's own
file — Rhode Island's scan came from a Novogradac copy and was then OCR'd
locally — and the `note` column says so for each.

### What ingest will skip or flag

- **Skipped silently:** `~$` lock files, dotfiles, and cloud-sync artefacts
  (`conflicted copy`, `(1)`, ` - copy`). A Dropbox conflicted copy is a real,
  readable PDF and would otherwise ingest as a separate document.
- **Flagged, not skipped:** scans with no text layer, and — more insidiously —
  PDFs whose text layer extracts but is unreadable. Vermont's June 2026 draft
  yielded 51,819 characters at a 3% letter ratio because it used a font with no
  Unicode mapping. Character count alone cannot catch that, so ingest checks the
  letter ratio and tells you to re-run it through OCR.

For a scan or a garbled file:

```bash
ocrmypdf --force-ocr "input.pdf" "output-ocr.pdf"
```

Put the OCR'd version in the shared folder and ingest that.

## Running things

```bash
sqlite3 data/qap.db < schema.sql                          # create the database
# without the sqlite3 binary: python -c "import sqlite3; sqlite3.connect('data/qap.db').executescript(open('schema.sql').read())"
python -m qapdb.ingest --commit                           # load documents
python -m qapdb.load_extraction data/extractions/CT_2026.json --commit
python -m qapdb.taxonomy --commit                         # apply the category codebook
python -m qapdb.verify_citations                          # re-check every citation
python -m uvicorn app.server:app --port 8000              # review + search app
```

### Re-checking citations

`load_extraction` verifies each quote against its cited page as it loads. That
check is worth repeating later, because a document can be re-OCR'd, a PDF
replaced, or an extraction edited by hand long after it was loaded:

```bash
python -m qapdb.verify_citations                       # all states
python -m qapdb.verify_citations --state RI            # one state
python -m qapdb.verify_citations --json out.json       # machine-readable
```

A quote that has moved is reported with the page it is actually on, since the
usual cause is a printed page number recorded instead of a PDF page index.

## What is committed, and what is not

| Committed | Not committed |
|---|---|
| `schema.sql`, `qapdb/`, `app/` | the QAP PDFs |
| `data/extractions/*.json` — the extracted criteria | `data/qap.db` — rebuildable |
| `data/manifest.csv` — what the corpus contains | `.env` — per-machine paths |

The database is a build artefact: given the shared folder and the extraction
JSONs, it regenerates completely. The extraction JSONs are the real work product
and are the thing worth protecting in version control.

## A note on the numbers

Points are only comparable *within* a state. Totals differ by design —
Connecticut scores its New Construction track to 100, New Hampshire states no
maximum at all, Massachusetts runs a 100-point gate followed by a separate
85-point stage — and one state's scoring unit is not another's. Vermont scored in
"checkmarks" as recently as its 2024-25 QAP.

Where a criterion lists tiers, usually only one applies, so the maximum sits well
below the tier total. Summing every stated point value overstates what a project
can actually earn by 50–65% in the states extracted so far.

A stated total is not always reachable, and many states state none. Indiana
states 165 while its own exclusion rules cap a 9% application at 146, and six of
the last ten states coded state no maximum at all. Where a computed figure is a
ceiling rather than a score, the `track_totals` note says so.
