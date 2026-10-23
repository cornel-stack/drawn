"""Build captions.srt from per-scene word timestamps.

Words are grouped into short cues (by count and by gap) and offset by the
cumulative duration of preceding scenes.
"""

from __future__ import annotations

import json
from pathlib import Path

from drawn_schema import paths
from drawn_schema.lesson import Lesson

MAX_WORDS_PER_CUE = 8
MAX_CUE_SECONDS = 3.5


def _fmt(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _cues_for_words(words: list[dict], offset: float):
    cue: list[dict] = []
    for w in words:
        if cue and (
            len(cue) >= MAX_WORDS_PER_CUE
            or (w["end"] - cue[0]["start"]) > MAX_CUE_SECONDS
        ):
            yield cue
            cue = []
        cue.append(w)
    if cue:
        yield cue


def build_srt(repo_root: Path, lesson: Lesson) -> str:
    repo_root = Path(repo_root).resolve()
    lines: list[str] = []
    index = 1
    offset = 0.0
    for scene in lesson.scenes:
        wj = paths.scene_words(repo_root, lesson.channel, lesson.id, scene.id)
        data = json.loads(wj.read_text())
        for cue in _cues_for_words(data.get("words", []), offset):
            start = offset + cue[0]["start"]
            end = offset + cue[-1]["end"]
            text = " ".join(w["word"] for w in cue).strip()
            lines.append(str(index))
            lines.append(f"{_fmt(start)} --> {_fmt(end)}")
            lines.append(text)
            lines.append("")
            index += 1
        offset += float(data["duration"])
    return "\n".join(lines)
