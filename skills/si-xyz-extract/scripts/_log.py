"""Tiny helper for appending to ``paper_fetch_log.md``.

A log file is created with a `REVIEW` and a `VERIFIED` section on first write;
subsequent writes append items under one of the two headings. The contract
lives in ``docs/plan.md``.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Literal


_HEADER = (
    "# paper-fetch-smiles log — {paper}\n\n"
    "Generated {ts}\n\n"
    "## REVIEW — needs human attention\n\n"
    "## VERIFIED — reviewer-confirmed\n"
)


def _ensure(path: Path, paper_name: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_HEADER.format(
        paper=paper_name,
        ts=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    ))


def append(
    path: Path,
    kind: Literal["REVIEW", "VERIFIED"],
    message: str,
    *,
    paper_name: str = "(unknown paper)",
    source: str | None = None,
) -> None:
    """Append a single-line item under the REVIEW or VERIFIED heading.

    ``source`` is appended in parens (typically the script name, e.g.
    ``scripts/si_xyz.py``) so reviewers can trace each item to its origin.
    """
    _ensure(path, paper_name)
    text = path.read_text()
    heading = f"## {kind}"
    if heading not in text:
        # Edge case: someone replaced the log header. Append a fresh section.
        text += f"\n\n{heading}\n\n"
    insert = f"- [ ] {message}" if kind == "REVIEW" else f"- {message}"
    if source:
        insert += f"  _({source})_"
    insert += "\n"

    # Insert the new line at the END of the chosen section (just before the
    # NEXT heading, or at file end if it's the last section).
    sections = text.split("## ")
    # sections[0] is preamble (with leading "# title"), sections[1:] start with
    # the section name + body.
    for i, sec in enumerate(sections[1:], start=1):
        if sec.startswith(kind):
            body = sec.rstrip() + "\n" + insert
            sections[i] = body + ("\n" if i < len(sections) - 1 else "")
            break
    path.write_text("## ".join(sections))
