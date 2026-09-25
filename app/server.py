"""Local review + search app for the QAP database.

Two views over the same data:

  /review  blind, keyboard-driven review queue. Each criterion is shown beside
           the actual PDF page it was cited from, with the quote highlighted.
  /search  searchable table of every criterion, with per-state point breakdowns.

Pages are rendered to PNG server-side by PyMuPDF with the quote's bounding
boxes drawn on. That avoids shipping a PDF viewer, works entirely offline, and
means the highlight comes from the same search that verifies the citation - if
the box does not appear, the citation is wrong, and that is visible rather than
hidden.

Run:
    python -m uvicorn app.server:app --reload --port 8000
"""

from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path

import pymupdf

from qapdb import sheets
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "qap.db"
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="QAP review")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def rows(sql: str, args: tuple = ()) -> list[dict]:
    with db() as conn:
        return [dict(r) for r in conn.execute(sql, args)]


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC / "index.html").read_text()


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
@app.get("/api/overview")
def overview() -> JSONResponse:
    """Corpus state: what is loaded, what still needs work."""
    docs = rows("""
        SELECT q.id, q.state, q.agency, q.cycle_start, q.cycle_end, q.cycle_source,
               q.doc_status, q.n_pages, q.source_quality, q.is_most_recent,
               q.stated_total, q.notes,
               (SELECT COUNT(*) FROM criteria c WHERE c.qap_id = q.id) AS n_criteria,
               (SELECT COUNT(*) FROM criteria c
                 WHERE c.qap_id = q.id AND c.citation_verified = 0) AS n_unverified
        FROM qaps q ORDER BY q.state, q.cycle_start""")
    totals = rows("""
        SELECT state, track, scoring_unit, stated_total, computed_total,
               naive_total, double_counted, status
        FROM v_total_reconciliation
        WHERE naive_total > 0 ORDER BY state""")
    cats = rows("""
        SELECT q.state, c.track, c.scoring_unit, c.native_category,
               COUNT(*) AS n, SUM(c.points_max) AS pts
        FROM criteria c JOIN qaps q ON q.id = c.qap_id
        WHERE c.kind = 'competitive' AND c.points_max IS NOT NULL
        GROUP BY q.state, c.track, c.scoring_unit, c.native_category
        ORDER BY q.state, pts DESC""")
    kinds = rows("""
        SELECT q.state, c.kind, COUNT(*) AS n
        FROM criteria c JOIN qaps q ON q.id = c.qap_id
        GROUP BY q.state, c.kind ORDER BY q.state, c.kind""")
    return JSONResponse({"docs": docs, "totals": totals,
                         "categories": cats, "kinds": kinds})


@app.get("/api/criteria")
def criteria(
    q: str = "", state: str = "", kind: str = "", unit: str = "",
    unverified_only: bool = False, limit: int = 500,
) -> JSONResponse:
    where, args = ["1=1"], []
    if q:
        where.append("(c.heading LIKE ? OR c.quote LIKE ? OR c.native_category LIKE ?"
                     " OR c.section_label LIKE ? OR c.note LIKE ?)")
        args += [f"%{q}%"] * 5
    if state:
        where.append("qa.state = ?"); args.append(state)
    if kind:
        where.append("c.kind = ?"); args.append(kind)
    if unit:
        where.append("c.scoring_unit = ?"); args.append(unit)
    if unverified_only:
        where.append("c.citation_verified = 0")
    args.append(limit)

    data = rows(f"""
        SELECT c.id, qa.state, qa.cycle_start, qa.cycle_end, c.ord, c.section_label,
               c.heading, c.native_category, c.track, c.kind, c.scoring_unit,
               c.points_max, c.points_type, c.rank_order, c.page_start, c.page_end,
               c.quote, c.citation_verified, c.note,
               (SELECT COUNT(*) FROM point_tiers t WHERE t.criterion_id = c.id) AS n_tiers,
               (SELECT COUNT(*) FROM reviews r
                 WHERE r.criterion_id = c.id AND r.is_adjudication = 0) AS n_reviews
        FROM criteria c JOIN qaps qa ON qa.id = c.qap_id
        WHERE {' AND '.join(where)}
        ORDER BY qa.state, c.ord LIMIT ?""", tuple(args))
    return JSONResponse(data)


@app.get("/api/criterion/{cid}")
def criterion(cid: int) -> JSONResponse:
    got = rows("""
        SELECT c.*, qa.state, qa.filename, qa.cycle_start, qa.cycle_end, qa.n_pages
        FROM criteria c JOIN qaps qa ON qa.id = c.qap_id WHERE c.id = ?""", (cid,))
    if not got:
        raise HTTPException(404, "no such criterion")
    rec = got[0]
    rec["tiers"] = rows(
        "SELECT ord, tier_label, points, condition_text FROM point_tiers "
        "WHERE criterion_id = ? ORDER BY ord", (cid,))
    # Reviews are returned but the UI hides other reviewers' answers while
    # coding - blind double-coding is the default, not an option.
    rec["reviews"] = rows(
        "SELECT reviewer, status, corrected_json, note, reviewed_at, is_adjudication "
        "FROM reviews WHERE criterion_id = ? ORDER BY reviewed_at", (cid,))
    return JSONResponse(rec)


@app.get("/api/page.png")
def page_png(cid: int, dpi: int = 130) -> Response:
    """Render the cited page with the quote highlighted.

    The highlight uses the same search that verifies the citation, so a
    criterion whose quote is not really on the page renders with no box -
    the reviewer sees the problem instead of taking the page number on trust.
    """
    got = rows("""SELECT c.quote, c.page_start, c.cell_ref, qa.local_path
                  FROM criteria c JOIN qaps qa ON qa.id = c.qap_id
                  WHERE c.id = ?""", (cid,))
    if not got:
        raise HTTPException(404, "no such criterion")
    quote, page_no, path = got[0]["quote"], got[0]["page_start"], got[0]["local_path"]
    cell_ref = got[0]["cell_ref"]
    if not page_no:
        raise HTTPException(404, "criterion has no page")

    # A spreadsheet source has no page to rasterise. Kentucky publishes its
    # scoring only as .xlsx, so rather than 500 at the reviewer, typeset the
    # cited sheet onto a page and highlight the quote there. The reviewer
    # still sees the words in context, next to the cell reference.
    if sheets.is_sheet(path):
        return _sheet_png(path, page_no, quote, cell_ref, dpi)

    doc = pymupdf.open(path)
    if not (1 <= page_no <= doc.page_count):
        raise HTTPException(404, "page out of range")
    page = doc[page_no - 1]

    for rect in (page.search_for(quote) if quote else []):
        annot = page.add_highlight_annot(rect)
        annot.set_colors(stroke=(1, 0.85, 0.2))
        annot.update()

    pix = page.get_pixmap(dpi=dpi)
    data = pix.tobytes("png")
    doc.close()
    return Response(data, media_type="image/png",
                    headers={"Cache-Control": "no-store"})


def _sheet_png(path: str, sheet_no: int, quote: str, cell_ref: str | None,
               dpi: int) -> Response:
    """Typeset one worksheet as a page so the review UI can show it."""
    wb = sheets.SheetDoc(path)
    if not (1 <= sheet_no <= wb.page_count):
        wb.close()
        raise HTTPException(404, "sheet out of range")
    ws = wb[sheet_no - 1]
    body = ws.get_text().replace("\t", "   ")
    wb.close()

    header = f"{Path(path).name}  |  sheet {sheet_no}: {ws.title}"
    if cell_ref:
        header += f"   [cited cell: {cell_ref}]"

    out = pymupdf.open()
    page = out.new_page(width=1100, height=1500)
    page.insert_textbox(pymupdf.Rect(36, 28, 1064, 60), header,
                        fontsize=10, fontname="hebo", color=(0.18, 0.36, 0.31))
    page.insert_textbox(pymupdf.Rect(36, 68, 1064, 1470), body,
                        fontsize=8.2, fontname="cour")

    for rect in (page.search_for(quote) if quote else []):
        annot = page.add_highlight_annot(rect)
        annot.set_colors(stroke=(1, 0.85, 0.2))
        annot.update()

    data = page.get_pixmap(dpi=dpi).tobytes("png")
    out.close()
    return Response(data, media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@app.get("/api/pdf")
def pdf(cid: int) -> FileResponse:
    """The source PDF, so a reviewer can open the full document if needed."""
    got = rows("""SELECT qa.local_path, qa.filename FROM criteria c
                  JOIN qaps qa ON qa.id = c.qap_id WHERE c.id = ?""", (cid,))
    if not got:
        raise HTTPException(404, "no such criterion")
    path = got[0]["local_path"]
    media = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
             if sheets.is_sheet(path) else "application/pdf")
    return FileResponse(path, media_type=media, filename=got[0]["filename"])


@app.post("/api/review")
async def save_review(payload: dict) -> JSONResponse:
    cid = payload.get("criterion_id")
    reviewer = (payload.get("reviewer") or "").strip()
    status = payload.get("status")
    if not (cid and reviewer and status):
        raise HTTPException(400, "criterion_id, reviewer and status are required")

    corrected = payload.get("corrected") or None
    with db() as conn:
        conn.execute("""
            INSERT INTO reviews (criterion_id, reviewer, status, corrected_json,
                                 note, is_adjudication)
            VALUES (?,?,?,?,?,0)
            ON CONFLICT(criterion_id, reviewer, is_adjudication) DO UPDATE SET
                status = excluded.status,
                corrected_json = excluded.corrected_json,
                note = excluded.note,
                reviewed_at = datetime('now')""",
            (cid, reviewer, status,
             json.dumps(corrected) if corrected else None, payload.get("note")))
        conn.commit()
    return JSONResponse({"ok": True})


@app.get("/api/disagreements")
def disagreements() -> JSONResponse:
    """Criteria where reviewers gave different answers.

    Compared field by field rather than whole-record: two reviewers agreeing on
    points but differing on one edit is a partial disagreement, and collapsing
    that to a single flag both overstates the conflict and loses which field is
    actually contested.
    """
    raw = rows("""
        SELECT c.id, qa.state, c.heading, c.points_max, c.page_start,
               r.reviewer, r.status, r.corrected_json, r.note
        FROM criteria c
        JOIN qaps qa ON qa.id = c.qap_id
        JOIN reviews r ON r.criterion_id = c.id AND r.is_adjudication = 0
        ORDER BY c.id, r.reviewer""")
    by_crit: dict[int, dict] = {}
    for r in raw:
        e = by_crit.setdefault(r["id"], {
            "id": r["id"], "state": r["state"], "heading": r["heading"],
            "points_max": r["points_max"], "page_start": r["page_start"],
            "reviews": []})
        e["reviews"].append({
            "reviewer": r["reviewer"], "status": r["status"],
            "corrected": json.loads(r["corrected_json"]) if r["corrected_json"] else {},
            "note": r["note"]})

    out = []
    for e in by_crit.values():
        if len(e["reviews"]) < 2:
            continue
        fields: dict[str, list] = {}
        for rv in e["reviews"]:
            fields.setdefault("status", []).append(rv["status"])
            for k, v in (rv["corrected"] or {}).items():
                fields.setdefault(k, []).append(v)
        contested = {k: v for k, v in fields.items() if len(set(map(str, v))) > 1}
        if contested:
            out.append({**e, "contested_fields": list(contested)})
    return JSONResponse(out)
