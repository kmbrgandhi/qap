# Bundled PDFs

31 documents committed to the repo on purpose, behind the 26 states coded from
here. Every one is coded. Four QAPs are here for context only, because the
scoring lives in a companion document: Washington's (9% Policies), South
Carolina's (Appendix C1), Maryland's (Program Guide) and Nebraska's plan (the
scoresheet).

The full corpus is 123 MB in a shared drop folder and stays out of git — see
the note at the top of `.gitignore`. But a session that has only the repo (a
cloud agent, a fresh clone, a new machine) would otherwise find a database full
of file paths it cannot open and no way to do any extraction at all. These are
the working set for that case.

Each file's sha256 matches its row in `data/manifest.csv`, so they are the same
bytes the rest of the corpus was built from, not re-downloads.

## Coded

Kept so their citations can be re-verified from the repo alone. The notes are
what the pre-bundling check turned up and what coding confirmed.

| State | File | Pages | Notes |
|---|---|---|---|
| AK | `alaska-qap-fy2027.pdf` | 51 | |
| AZ | `arizona-qap-2026-2027.pdf` | 50 | |
| CA | `california-qap-2026.pdf` | 108 | Regulations format; 9% scoring is CCR §10325(c). §10326 bond scoring not coded |
| CO | `colorado-qap-2025-2026.pdf` | 102 | |
| GA | `georgia-qap-2026-2027.pdf` | 126 | Applicability matrix is graphics; read from the page image |
| IA | `iowa-qap-2026-2027.pdf` | 55 | |
| ID | `idaho-qap-2026.pdf` | 108 | Maxima written in words |
| IL | `illinois-qap-2027-2028.pdf` | 77 | Reconciles to its stated 80 + 20 |
| IN | `indiana-qap-2026-2027.pdf` | 103 | |
| KS | `kansas-qap-2026.pdf` | 112 | A 2027 draft also exists; this is the final |
| LA | `louisiana-qap-2025.pdf` | 104 | Appendix A score sheet read from page images; it did not interleave |
| MN | `minnesota-qap-2026-2028.pdf` | 83 | |
| MN | `minnesota-self-scoring-worksheet-2026-2028.pdf` | 50 | |
| MS | `mississippi-qap-2026.pdf` | 116 | Running header says 2024; the text adopts the 2026 plan |
| NJ | `new-jersey-qap-2026.pdf` | 76 | |
| NM | `newmexico-qap-2026.pdf` | 98 | No stated total |
| NV | `nevada-qap-2026.pdf` | 53 | |
| OK | `oklahoma-qap-2027-CONVERTED-from-docx.pdf` | 76 | |
| TN | `tennessee-qap-2026.pdf` | 139 | States 100; says its criteria do not reach it |
| TX | `texas-qap-2026.pdf` | 218 | The longest document in the corpus |
| WA | `washington-9pct-policies-2027.pdf` | 84 | **This carries the scoring**, not the QAP |
| WA | `washington-qap-2027.pdf` | 10 | The QAP itself, bundled for context only |
| WV | `westvirginia-qap-2025-2026.pdf` | 139 | Two full parallel tracks, 993 each |
| WY | `wyoming-qap-2027.pdf` | 80 | |
| SC | `southcarolina-appendix-c1-9pct-2026-amendments.pdf` | 12 | **This carries the 9% scoring.** Despite the name it is the clean consolidated Appendix C1; the redline (not bundled) reads `Max - 65 70 points`, where 70 is correct. Table of contents is a year stale |
| SC | `southcarolina-qap-2026-amendments.pdf` | 23 | The governing QAP, also clean. Thresholds are cited here |
| MD | `maryland-multifamily-program-guide-2026.pdf` | 109 | **This carries the scoring** (Chapter 4). Printed pages run 5 behind PDF pages. Reconciles to its stated 221 |
| MD | `maryland-qap-2026.pdf` | 34 | The QAP itself, bundled for context only |
| NE | `nebraska-9pct-scoresheet-2026-2027-2028.pdf` | 5 | **This carries the point values.** Values read from page images; the text layer separates them from their labels. States 87 / 85; the printed rows do not reach either |
| NE | `nebraska-9pct-allocation-plan-2026-2027-2028.pdf` | 36 | Plan for context; its "PROPOSED SCORING" table (p.6) totals 94 and disagrees with the sheet |
| UT | `utah-qap-2027.pdf` | 168 | **Scores by weight.** Stored at weighted value in `scoring_unit = 'weighted'`; never pool with points. No grand total stated; all six category maxima reconcile |

**Oregon is deliberately absent.** `oregon-qap-2025.pdf` was a candidate until
it was opened: pages 44–142 are a public comment-and-response log, with named
commenters and replies, not a scoring plan. Its only point values appear inside
a reply discussing proposed resilient construction scoring. Oregon needs a
different document collected before it can be coded.

Keep this folder a working set, not a mirror. If you need a document that is
not here, take it from the shared drop folder via `$QAP_PDF_DIR` rather than
adding to the repo by default.
