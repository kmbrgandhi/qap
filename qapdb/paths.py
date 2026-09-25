"""Find a QAP source document on whatever machine we are running on.

`qaps.local_path` records where a document sat when it was ingested. That path
is right on the machine that did the ingest and wrong everywhere else: the
corpus lives in a shared drop folder mounted at a different path for each of
us, and a session working from the git repo alone (a cloud agent, a fresh
clone) does not have the drop folder at all.

So every place that opens a PDF resolves it here instead of trusting
`local_path` directly. The order is: the recorded path if it still exists,
then the committed subset in `data/pdfs_bundled/`, then `$QAP_PDF_DIR`. The
bundled subset is small and deliberate -- see data/pdfs_bundled/README.md --
and exists so that a repo-only session has real documents to code from rather
than a database full of paths it cannot open.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLED = REPO_ROOT / "data" / "pdfs_bundled"


def pdf_dir_from_env() -> Path | None:
    """QAP_PDF_DIR from the environment or a local .env, if either is set."""
    if os.environ.get("QAP_PDF_DIR"):
        return Path(os.environ["QAP_PDF_DIR"])
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("QAP_PDF_DIR="):
                return Path(line.split("=", 1)[1].strip())
    return None


def resolve_pdf(local_path: str | None, filename: str | None) -> Path | None:
    """Where is this document actually readable, if anywhere?

    Returns None rather than raising, so callers can report which documents
    they could not check instead of dying on the first one that is missing.
    """
    if local_path:
        p = Path(local_path)
        if p.exists():
            return p
    if filename:
        bundled = BUNDLED / filename
        if bundled.exists():
            return bundled
        if (d := pdf_dir_from_env()) and (p := d / filename).exists():
            return p
    return None
