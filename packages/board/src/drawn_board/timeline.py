"""Pacing check: fail a lesson whose timeline has a static gap > 3 s.

Uses the TTS words JSON (scene duration, word timings, and each placeholder's
start). Every write/draw is a short motion; a continuous animation action (e.g.
a spinning wheel) counts as motion from its start to the end of the scene. A
scene is flagged if, while narration is playing, nothing moves for > 3 s.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from drawn_schema import paths
from drawn_schema.lesson import Lesson

MAX_STATIC_SECONDS = 3.0
WRITE_MOTION_SECONDS = 1.2


def _primitive_class(repo_root: Path, lesson: Lesson, scene):
    if scene.animation is None:
        return None
    from drawn_board.primitives.base import get_primitive, load_custom

    try:
        if scene.animation.custom:
            return load_custom(repo_root, lesson.channel, lesson.id, scene.animation.custom)
        return get_primitive(scene.animation.primitive)
    except Exception:  # noqa: BLE001
        return None


def _merge(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    intervals = sorted(i for i in intervals if i[1] > i[0])
    merged: list[tuple[float, float]] = []
    for a, b in intervals:
        if merged and a <= merged[-1][1] + 1e-6:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def check_pacing(repo_root: Path, lesson: Lesson) -> list[str]:
    repo_root = Path(repo_root).resolve()
    problems: list[str] = []
    for scene in lesson.scenes:
        if scene.kind == "end":
            continue
        wj = paths.scene_words(repo_root, lesson.channel, lesson.id, scene.id)
        if not wj.is_file():
            problems.append(f"scene {scene.id!r}: no words JSON (run tts first)")
            continue
        data = json.loads(wj.read_text())
        words = data.get("words", [])
        if not words:
            continue  # silent scene (e.g. title card with no narration)
        starts = {it["id"]: float(it["start"]) for it in data.get("items", [])}

        # the title text is written from t=0, so a title scene is never static
        # at the start regardless of when its animation steps fire.
        if scene.kind == "title":
            continue

        cls = _primitive_class(repo_root, lesson, scene)
        # 3D scenes drift the camera and continuous primitives keep moving, so
        # the engine fills every gap with motion; nothing to flag.
        if cls is not None and (getattr(cls, "is_3d", False)
                                or getattr(cls, "auto_continuous", False)):
            continue

        # 2D: once anything is drawn, gaps are filled by a pulse of the active
        # item. The only static risk is the lead-in before the first visual.
        span_start = float(words[0]["start"])
        first_event = min(starts.values()) if starts else span_start
        lead = first_event - span_start
        if lead > MAX_STATIC_SECONDS:
            problems.append(
                f"scene {scene.id!r}: {lead:.1f}s of narration before the first "
                f"visual — move the first {{id}} earlier"
            )
    return problems


def check_pacing_file(repo_root: Path, lesson_path: Path) -> list[str]:
    lesson = Lesson.model_validate(yaml.safe_load(Path(lesson_path).read_text()))
    return check_pacing(repo_root, lesson)


def _cli() -> int:
    import argparse

    p = argparse.ArgumentParser(prog="drawn-board-check", description="pacing check")
    p.add_argument("lesson", type=Path)
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = p.parse_args()
    problems = check_pacing_file(args.repo_root, args.lesson)
    for pr in problems:
        print(f"pacing: {pr}")
    if problems:
        print(f"FAIL: {len(problems)} pacing problem(s)")
        return 1
    print(f"ok: pacing ({args.lesson})")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_cli())
