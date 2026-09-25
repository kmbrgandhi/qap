# The public site

A static browser for the coded QAP data: one HTML file, one JSON file, no
backend and no build step.

| File | What it is |
|---|---|
| `index.html` | The whole site. Hand-written; edit it directly. |
| `qap-data.json` | Generated. `python -m qapdb.export_site` rewrites it from `data/qap.db`. |

Regenerate the data after any extraction work, or the site shows the old
figures:

```bash
python -m qapdb.export_site
```

## Hosting it

Because it is static, it runs anywhere that serves files. Nothing in it is tied
to a particular host or account.

**GitHub Pages** — this repository is already public, so the shortest path is
Settings → Pages → Deploy from a branch → `main` / `/site`. The site then lives
at `https://<user>.github.io/qap/` and redeploys on every push.

**Netlify, Vercel, Cloudflare Pages** — point the project at this repository
with publish directory `site` and no build command.

**Anywhere else** — copy the two files onto any web server.

To check it locally before publishing, serve the folder rather than opening the
file directly, because the page fetches its JSON and `file://` blocks that:

```bash
python -m http.server -d site 8080    # then open http://localhost:8080
```

## What it deliberately leaves out

The export carries the criteria, their quotes, page citations and notes, plus
the documents held for every state and a source URL where we have one. It
carries no review decisions, no local file paths and no reviewer names, so
publishing it cannot leak the internal review process.

It also cannot render highlighted PDF pages the way the review app does: that
needs the 123 MB corpus and a Python runtime. Instead each document links to the
agency's own copy where `data/sources.csv` records a URL. That is the better
citation anyway — it points at the source rather than at ours.

## Honesty requirements

The page states on load that 30 of 50 states are coded and that nothing has
completed second-reader review. **Keep that.** It also shows a state's computed
total against the total the state itself states, and marks disagreements rather
than hiding them. Those mismatches are findings; presenting a single reconciled
number would misrepresent the source documents.

States with no point system (Oregon, Montana, Florida) are labelled as such, so
an empty criteria list reads as a result rather than as missing work.
