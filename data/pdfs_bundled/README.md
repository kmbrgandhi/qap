# Bundled PDFs

28 documents committed to the repo on purpose: the 11 behind the ten states
already coded from here, plus 17 covering 14 uncoded states for the next batch.

The full corpus is 123 MB in a shared drop folder and stays out of git — see
the note at the top of `.gitignore`. But a session that has only the repo (a
cloud agent, a fresh clone, a new machine) would otherwise find a database full
of file paths it cannot open and no way to do any extraction at all. These are
the working set for that case.

Each file's sha256 matches its row in `data/manifest.csv`, so they are the same
bytes the rest of the corpus was built from, not re-downloads.

## Already coded

Kept so their citations can be re-verified from the repo alone.

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

## Not yet coded

Every one was opened and confirmed to carry real point values before being
bundled. The notes are what that check turned up.

| State | File | Pages | Notes |
|---|---|---|---|
| GA | `georgia-qap-2026-2027.pdf` | 126 | 288 "point" mentions, the densest here |
| ID | `idaho-qap-2026.pdf` | 108 | Maxima written in words |
| IL | `illinois-qap-2027-2028.pdf` | 77 | States "Maximum Points" |
| KS | `kansas-qap-2026.pdf` | 112 | A 2027 draft also exists; this is the final |
| LA | `louisiana-qap-2025.pdf` | 104 | **Scoring is Appendix A from p.39**, a self-score sheet whose values sit in a column separate from their labels. Expect the text layer to interleave them, as Nebraska's does |
| MS | `mississippi-qap-2026.pdf` | 116 | States "Maximum Points" |
| NM | `newmexico-qap-2026.pdf` | 98 | 228 "point" mentions but no stated total found; expect the hand-sum to be the only completeness check |
| TN | `tennessee-qap-2026.pdf` | 139 | States "maximum 100 points" |
| WV | `westvirginia-qap-2025-2026.pdf` | 139 | 553 "point" mentions, the most of any document in the corpus |
| WA | `washington-9pct-policies-2027.pdf` | 84 | **This carries the scoring**, not the QAP |
| WA | `washington-qap-2027.pdf` | 10 | The QAP itself, bundled for context only |
| CA | `california-qap-2026.pdf` | 108 | Regulations format; scoring is CCR §10325. Harder than the rest |
| TX | `texas-qap-2026.pdf` | 218 | The longest document in the corpus, 408 "point" mentions |
| MD | `maryland-multifamily-program-guide-2026.pdf` | 109 | **This carries the scoring**, not the QAP. Chapter 4 from printed p.52; Scoring Summary Table totals 221. Printed pages run 5 behind PDF pages |
| MD | `maryland-qap-2026.pdf` | 34 | The QAP itself, bundled for context only |
| SC | `southcarolina-appendix-c1-9pct-2026-amendments.pdf` | 12 | **Code from this file.** Despite the name it is the CLEAN consolidated Appendix C-1, where the 9% scoring lives. Verified free of redline artifacts |
| SC | `southcarolina-qap-2026-amendments.pdf` | 23 | The governing 2026 QAP, signed 30 December 2025. Also the clean version. Scoring is in the appendix, not here |

South Carolina is the shortest job here by a wide margin — 12 pages of
appendix. Then Illinois, New Mexico, Kansas and Idaho. California and Texas
are the hardest; leave them until last.

**South Carolina's filenames are inverted and this matters.** The file ending
`-amendments.pdf` is the clean consolidated document; the one without that
suffix is the redline, in which struck and replacement values merge as
`Max - 65 70 points`. 70 is the correct value. Code only from the
`-amendments` files. The protocol entry "A filename is not a document's
status" has the detail.

**Oregon is deliberately absent, but not for the reason first recorded here.**
An earlier version of this file said `oregon-qap-2025.pdf` was the wrong
document, a stray comment log. That was wrong. It is Oregon's real QAP, signed
by the Governor on 25 February 2025; the comment-and-response log on pp.38–147
is Appendix B, a formal part of it. Oregon is absent because **Oregon does not
score at all** — it selects by mandatory threshold, then a count of
supplemental criteria, then tiebreakers in fixed order, and its own text says
projects "will not be prioritized over other projects for including more than
three of these criteria". There is no total to extract. See the protocol entry
"No points here is not the same as wrong document".

Keep this folder a working set, not a mirror. If you need a document that is
not here, take it from the shared drop folder via `$QAP_PDF_DIR` rather than
adding to the repo by default.
