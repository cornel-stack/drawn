"""Scaffold a new lesson YAML from its backlog row.

Pre-fills id/channel/title/target_minutes/source from the backlog and drops in
a title → board → summary → end skeleton for the writer to fill. The source
string is parsed best-effort into book/section/licence.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from drawn_schema.lesson import SCHEMA_VERSION


def parse_source(source: str) -> dict:
    lic = re.search(r"\(([^)]*CC[^)]*)\)", source)
    license_ = lic.group(1).strip() if lic else "CC BY 4.0"
    sec = re.search(r"(§[^,]+|Ch\.?\s*[0-9.\-–]+[^,]*|Chapter\s+\S+)", source)
    section = sec.group(1).strip() if sec else ""
    book = source
    if lic:
        book = source[: lic.start()].strip()
    if sec and sec.start() < len(book):
        book = source[: sec.start()].strip()
        book = re.sub(r"\([^)]*CC[^)]*\)", "", book).strip()
    return {"book": book.rstrip(" ,"), "section": section, "license": license_}


def _backlog_row(repo_root: Path, channel: str, code: str) -> dict:
    backlog = Path(repo_root) / "channels" / channel / "backlog.yaml"
    rows = yaml.safe_load(backlog.read_text()) or []
    for row in rows:
        if row.get("code") == code:
            return row
    raise ValueError(f"{code} not found in {backlog}")


def new_lesson(repo_root: Path, channel: str, code: str, *, force: bool = False) -> Path:
    repo_root = Path(repo_root)
    row = _backlog_row(repo_root, channel, code)
    target = row.get("target_minutes") or 6
    source = parse_source(row.get("source", ""))

    lesson = {
        "schema_version": SCHEMA_VERSION,
        "id": code,
        "channel": channel,
        "title": row.get("title", code),
        "target_minutes": target,
        "source": source,
        "scenes": [
            {"id": "s1", "kind": "title", "narration": "", "board": []},
            {
                "id": "s2",
                "kind": "board",
                "narration": (
                    "TODO: explain the core idea in your own words, referencing "
                    "{eq} where it is written."
                ),
                "board": [
                    {"id": "eq", "latex": "a = b", "say": "a equals b"},
                ],
            },
            {
                "id": "s3",
                "kind": "summary",
                "narration": "TODO: one-line summary. Next: TODO-CODE.",
                "board": [{"id": "key", "text": "Key takeaway"}],
            },
            {"id": "s4", "kind": "end", "narration": "", "board": []},
        ],
    }

    out = repo_root / "channels" / channel / "lessons" / f"{code}.yaml"
    if out.exists() and not force:
        raise FileExistsError(f"{out} exists (use --force to overwrite)")
    out.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# {code}: {row.get('title', '')}\n"
        "# Draft scaffold — fill in narration and board items, then `just lint`.\n"
    )
    out.write_text(header + yaml.safe_dump(lesson, sort_keys=False, allow_unicode=True, width=100))
    return out
