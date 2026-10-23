"""Write meta.md: title, description with CC BY attribution, tags, chapters.

Chapter timestamps come from scene boundaries (cumulative durations).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from drawn_schema import paths
from drawn_schema.lesson import Lesson

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "why",
    "what", "how", "is", "are", "really", "with", "one",
}


def _timestamp(t: float) -> str:
    m = int(t // 60)
    s = int(t % 60)
    return f"{m:02d}:{s:02d}"


def _chapter_label(scene) -> str:
    if scene.kind == "title":
        return "Introduction"
    if scene.kind == "end":
        return "Summary"
    first = scene.narration.strip().split(".")[0]
    first = re.sub(r"\{[A-Za-z0-9_]+\}", "", first).strip()
    words = first.split()
    label = " ".join(words[:6]) if words else scene.kind.capitalize()
    return label[:1].upper() + label[1:]


def _tags(lesson: Lesson) -> list[str]:
    tags = [lesson.source.book.split(",")[0].strip()]
    tags.append(lesson.title.split(":")[0].strip())
    for word in re.findall(r"[A-Za-z]+", lesson.title.lower()):
        if len(word) > 3 and word not in _STOPWORDS and word not in tags:
            tags.append(word)
    return tags[:12]


def build_meta(repo_root: Path, lesson: Lesson) -> str:
    repo_root = Path(repo_root).resolve()
    src = lesson.source
    attribution = f"Adapted from {src.book}, {src.section} ({src.license})."

    chapters = []
    offset = 0.0
    for scene in lesson.scenes:
        wj = paths.scene_words(repo_root, lesson.channel, lesson.id, scene.id)
        data = json.loads(wj.read_text())
        chapters.append(f"{_timestamp(offset)} {_chapter_label(scene)}")
        offset += float(data["duration"])

    tags = ", ".join(_tags(lesson))
    lines = [
        f"# {lesson.title}",
        "",
        "## Description",
        "",
        f"{attribution}",
        "",
        "Part of the series; see the channel for prerequisites and follow-ups.",
        "",
        "## Tags",
        "",
        tags,
        "",
        "## Chapters",
        "",
        *chapters,
        "",
        "## Licence",
        "",
        f"Source material: {src.license}. This video adapts it under the same terms.",
        "",
    ]
    return "\n".join(lines)
