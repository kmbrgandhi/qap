# Bundled PDFs

24 documents committed to the repo on purpose, behind the 22 states coded from
here. Every one is coded; Washington's QAP is here for context, since its
scoring lives in the 9% Policies.

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

**Oregon is deliberately absent.** `oregon-qap-2025.pdf` was a candidate until
it was opened: pages 44–142 are a public comment-and-response log, with named
commenters and replies, not a scoring plan. Its only point values appear inside
a reply discussing proposed resilient construction scoring. Oregon needs a
different document collected before it can be coded.

Keep this folder a working set, not a mirror. If you need a document that is
not here, take it from the shared drop folder via `$QAP_PDF_DIR` rather than
adding to the repo by default.

## Not yet coded — the remaining four

Every other state in the corpus is coded. These four are what is left, and all
four are researched: `data/sources.csv` records the source URL and what each
document actually contains.

| State | File | Pages | Notes |
|---|---|---|---|
| **SC** | `southcarolina-appendix-c1-9pct-2026-amendments.pdf` | 12 | **Start here — shortest job in the corpus.** Despite the name this is the CLEAN consolidated Appendix C-1, where the 9% scoring lives. Verified free of redline artifacts. The companion file without `-amendments` is the redline and reads `Max - 65 70 points`; **70 is correct**. |
| **SC** | `southcarolina-qap-2026-amendments.pdf` | 23 | The governing 2026 QAP, signed 30 December 2025. Also the clean version. Scoring is in the appendix, not here. |
| **MD** | `maryland-multifamily-program-guide-2026.pdf` | 109 | **This carries the scoring**, not the QAP. Chapter 4 from printed p.52; Scoring Summary Table totals **221**. Printed page numbers run 5 behind PDF pages. Bonus points (10, or 15 for intergenerational/elderly/PSH) sit outside the 221. |
| **MD** | `maryland-qap-2026.pdf` | 34 | The QAP itself, bundled for context only. |
| **NE** | `nebraska-9pct-scoresheet-2026-2027-2028.pdf` | 5 | **This carries the point values**, not the plan. States a 40-point minimum and maxima of 87 non-metro / 85 metro. Needs an image-based pass: the text layer interleaves labels and values across columns, exactly as Wyoming's summary did — and Wyoming was read successfully from rendered page images. |
| **NE** | `nebraska-9pct-allocation-plan-2026-2027-2028.pdf` | 36 | Three-year plan for 2026-2028. Its summary table on pp.5-6 is headed "PROPOSED SCORING" in an otherwise final document and its group totals sum to 94, disagreeing with the scoresheet. **Treat the scoresheet as authoritative.** |
| **UT** | `utah-qap-2027.pdf` | 168 | **Scores by WEIGHT, not points** — use `scoring_unit`, do not flatten. Each criterion is a raw score times a weight: Lower Income Targeting x50 (cap 5,000), Project Location x20 (cap 300, from 15 raw), Project Characteristics x20 (530), Applicant Characteristics x20 (200), Special Housing Needs x20 (500), Credit Efficiency x20 (240). **No grand total is stated anywhere in the QAP** — do not compute one and present it as stated. |

Order: South Carolina (12 pages), then Maryland, then Nebraska, then Utah.
Utah last: it is the first weight-scored state in the corpus and its totals are
not comparable with anyone else's.
