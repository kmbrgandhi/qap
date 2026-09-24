# Bundled PDFs

Eleven documents covering ten states, committed to the repo on purpose. All ten
are now coded; these files are what lets their citations be re-verified from
the repo alone.

The full corpus is 123 MB in a shared drop folder and stays out of git — see
the note at the top of `.gitignore`. But a session that has only the repo (a
cloud agent, a fresh clone, a new machine) would otherwise find a database full
of file paths it cannot open and no way to do any extraction at all. These
eleven are the working set for that case.

Each file's sha256 matches its row in `data/manifest.csv`, so they are the same
bytes the rest of the corpus was built from, not re-downloads.

| State | File | Pages |
|---|---|---|
| AK | `alaska-qap-fy2027.pdf` | 51 |
| AZ | `arizona-qap-2026-2027.pdf` | 50 |
| CO | `colorado-qap-2025-2026.pdf` | 102 |
| IA | `iowa-qap-2026-2027.pdf` | 55 |
| IN | `indiana-qap-2026-2027.pdf` | 103 |
| MN | `minnesota-qap-2026-2028.pdf` | 83 |
| MN | `minnesota-self-scoring-worksheet-2026-2028.pdf` | 50 |
| NJ | `new-jersey-qap-2026.pdf` | 76 |
| NV | `nevada-qap-2026.pdf` | 53 |
| OK | `oklahoma-qap-2027-CONVERTED-from-docx.pdf` | 76 |
| WY | `wyoming-qap-2027.pdf` | 80 |

All eleven were checked to carry real point values before being bundled.
`HANDOFF.md` records where each state landed and which states to bundle next.

Keep this folder small. It is a working set, not a mirror. If you need a
document that is not here, take it from the shared drop folder via
`$QAP_PDF_DIR` rather than adding to the repo by default.
