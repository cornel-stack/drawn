"""Write meta.md — a ready-to-paste YouTube upload bundle.

Title, description (summary + chapters + source attribution + hashtags), and the
keyword tags. Everything the ``publish:`` block provides is used verbatim; when a
field is absent it is derived from the lesson so meta.md is always complete.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from drawn_schema import paths
from drawn_schema.lesson import Lesson

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "why",
    "what", "how", "is", "are", "really", "with", "one", "its", "that", "this",
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
    first = re.sub(r"\{[A-Za-z0-9_]+\}", "", first)   # drop placeholders
    first = re.sub(r"\s+", " ", first).strip(" ,;:—-")  # tidy leftovers
    words = first.split()
    label = " ".join(words[:6]) if words else scene.kind.capitalize()
    return label[:1].upper() + label[1:]


def _derive_tags(lesson: Lesson) -> list[str]:
    tags = [lesson.source.book.split(",")[0].strip(), lesson.title.split(":")[0].strip()]
    for word in re.findall(r"[A-Za-z]+", lesson.title.lower()):
        if len(word) > 3 and word not in _STOPWORDS and word not in tags:
            tags.append(word)
    return tags[:12]


def _derive_hashtags(lesson: Lesson) -> list[str]:
    tags: list[str] = []
    for word in re.findall(r"[A-Za-z]+", lesson.title.lower()):
        if len(word) > 3 and word not in _STOPWORDS and ("#" + word) not in tags:
            tags.append("#" + word)
        if len(tags) >= 3:
            break
    return tags


def build_meta(repo_root: Path, lesson: Lesson) -> str:
    repo_root = Path(repo_root).resolve()
    src = lesson.source
    pub = lesson.publish

    title = pub.title if pub else lesson.title
    summary = (
        pub.summary if pub and pub.summary
        else f"A clear, step-by-step look at {lesson.title}."
    )
    hashtags = pub.hashtags if pub and pub.hashtags else _derive_hashtags(lesson)
    tags = pub.tags if pub and pub.tags else _derive_tags(lesson)
    attribution = (
        f"Adapted in our own words from {src.book}, {src.section} ({src.license}). "
        f"Free and open-source."
    )

    chapters = []
    offset = 0.0
    for scene in lesson.scenes:
        data = json.loads(
            paths.scene_words(repo_root, lesson.channel, lesson.id, scene.id).read_text()
        )
        chapters.append(f"{_timestamp(offset)} {_chapter_label(scene)}")
        offset += float(data["duration"])

    # The whole "## Description" block is meant to be pasted into the YouTube
    # description verbatim; "## Title" and "## Tags" are the other upload fields.
    lines = [
        f"# {title}",
        "",
        "## Title",
        "",
        title,
        "",
        "## Description",
        "",
        summary,
        "",
        "Chapters:",
        *chapters,
        "",
        attribution,
        "",
        " ".join(hashtags),
        "",
        "## Tags",
        "",
        ", ".join(tags),
        "",
    ]
    return "\n".join(lines)
