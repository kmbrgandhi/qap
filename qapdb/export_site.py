"""Export the database as the static JSON the public site reads.

The public site is one HTML file and one JSON file, with no backend. That is
deliberate: it means the site can be hosted anywhere that serves files --
GitHub Pages, Netlify, S3, a departmental web server -- and it outlives any
particular host, account or session.

The JSON is a build artefact like the database, regenerated from it:

    python -m qapdb.export_site            # writes site/qap-data.json

It carries every coded criterion with its quote, its page citation and its
note, plus the documents held for all 50 states and the source URL for each
where we have one. It deliberately does NOT carry anything internal: no review
decisions, no local file paths, no reviewer names.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "qap.db"
OUT = ROOT / "site" / "qap-data.json"

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# States with no point system, so an empty criteria list is a finding rather
# than work outstanding. Keep the reason with the state: a reader who sees a
# blank page otherwise assumes we simply have not got to it.
NO_POINTS = {
    "OR": "Oregon does not score. Selection is by mandatory threshold, then a "
          "count of supplemental criteria, then tiebreakers applied in fixed "
          "order. The QAP states that projects \"will not be prioritized over "
          "other projects for including more than three of these criteria\".",
    "MT": "Montana's plan carries no point system.",
    "FL": "Florida's QAP delegates scoring to separate Requests for "
          "Applications (RFAs), which are issued per funding cycle.",
}


def build(db_path: Path) -> dict:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    cats = {r["id"]: r["name"] for r in con.execute("SELECT id, name FROM categories")}
    catdefs = [dict(name=r["name"], definition=r["definition"])
               for r in con.execute("SELECT name, definition FROM categories ORDER BY id")]

    # The column is is_primary, not role. An earlier version guessed the name
    # and swallowed the OperationalError, so every criterion exported with no
    # category at all and the coverage page showed zero states scoring
    # anything. Let a wrong query fail loudly instead: a silently empty
    # category is worse than a crash, because the page still renders.
    primary: dict[int, str] = {}
    for r in con.execute("SELECT criterion_id, category_id FROM criterion_categories"
                         " WHERE is_primary = 1"):
        primary[r["criterion_id"]] = cats.get(r["category_id"])
    if not primary:
        raise SystemExit("no primary categories found; run python -m qapdb.taxonomy --commit")

    tiers: dict[int, list] = {}
    for r in con.execute("SELECT criterion_id, tier_label, points FROM point_tiers"
                         " ORDER BY criterion_id, ord"):
        tiers.setdefault(r["criterion_id"], []).append({"l": r["tier_label"], "p": r["points"]})

    states = []
    for code in sorted(STATE_NAMES):
        docs = []
        for r in con.execute("SELECT * FROM qaps WHERE state = ? ORDER BY n_pages DESC", (code,)):
            cyc = str(r["cycle_start"] or "")
            if r["cycle_end"] and r["cycle_end"] != r["cycle_start"]:
                cyc += f"-{r['cycle_end']}"
            docs.append(dict(file=r["filename"], agency=r["agency"], pages=r["n_pages"],
                             cyc=cyc, status=r["doc_status"], url=r["source_url"],
                             quality=r["source_quality"]))

        tracks = [dict(track=r["track"], stated_total=r["stated_total"],
                       page=r["page"], note=r["note"])
                  for r in con.execute(
                      "SELECT tt.* FROM track_totals tt JOIN qaps q ON q.id = tt.qap_id"
                      " WHERE q.state = ?", (code,))]

        criteria = []
        for r in con.execute("SELECT c.* FROM criteria c JOIN qaps q ON q.id = c.qap_id"
                             " WHERE q.state = ? ORDER BY c.kind DESC, c.ord", (code,)):
            row = dict(n=r["section_label"], h=r["heading"], pts=r["points_max"],
                       pt=r["points_type"], unit=r["scoring_unit"], kind=r["kind"],
                       track=r["track"], neg=1 if r["is_negative"] else None,
                       cat=primary.get(r["id"]), nat=r["native_category"],
                       p0=r["page_start"], p1=r["page_end"], q=r["quote"],
                       note=r["note"], tm=r["tier_mode"], ext=r["detail_external"],
                       t=tiers.get(r["id"]))
            criteria.append({k: v for k, v in row.items() if v not in (None, "", [])})

        # Take the database's own figure, which honours exclusivity groups.
        # Summing points_max here counted every option of a max_one group:
        # Maryland's three 16-point Community Context options showed as 253
        # against its stated 221, a mismatch that is not one.
        computed: dict[str, float] = {}
        for r in con.execute("SELECT v.track, v.computed_total FROM v_qap_computed_total v"
                             " JOIN qaps q ON q.id = v.qap_id WHERE q.state = ?", (code,)):
            key = str(r["track"])
            computed[key] = computed.get(key, 0) + r["computed_total"]

        states.append(dict(code=code, name=STATE_NAMES[code], docs=docs, tracks=tracks,
                           criteria=criteria, computed=computed,
                           no_points=NO_POINTS.get(code)))

    con.close()
    return dict(generated=__import__("datetime").date.today().isoformat(),
                categories=catdefs, states=states)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DB)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    data = build(args.db)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, separators=(",", ":")))

    coded = sum(1 for s in data["states"] if s["criteria"])
    crit = sum(len(s["criteria"]) for s in data["states"])
    kb = args.out.stat().st_size / 1024
    print(f"wrote {args.out} — {kb:.0f} KB, {coded} coded states, {crit} criteria")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
