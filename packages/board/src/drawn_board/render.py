"""Programmatic render of one lesson scene to a silent mp4.

Timing comes from the TTS stage's words JSON (scene duration + per-item
write-start). Idempotent: skips a scene whose clip already exists unless forced.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml
from drawn_schema import paths
from drawn_schema.channel import load_channel
from drawn_schema.lesson import Lesson

from drawn_board.fonts import register_handwriting_font
from drawn_board.quality import quality_config
from drawn_board.scene import RenderData, make_lesson_scene


def _scene_is_3d(repo_root: Path, lesson: Lesson, scene) -> bool:
    if scene.animation is None:
        return False
    from drawn_board.primitives.base import get_primitive, load_custom

    anim = scene.animation
    if anim.custom:
        cls = load_custom(repo_root, lesson.channel, lesson.id, anim.custom)
    else:
        cls = get_primitive(anim.primitive)
    return bool(getattr(cls, "is_3d", False))


def _load_words(repo_root: Path, channel: str, code: str, scene_id: str) -> dict:
    wj = paths.scene_words(repo_root, channel, code, scene_id)
    if not wj.is_file():
        raise FileNotFoundError(
            f"missing {wj}; run the tts stage before rendering scene {scene_id!r}"
        )
    return json.loads(wj.read_text())


def render_scene(
    repo_root: Path,
    lesson_path: Path,
    scene_id: str,
    *,
    quality: str = "preview",
    force: bool = False,
) -> Path:
    repo_root = Path(repo_root).resolve()
    lesson = Lesson.model_validate(yaml.safe_load(Path(lesson_path).read_text()))
    channel = load_channel(repo_root, lesson.channel)
    scene = next((s for s in lesson.scenes if s.id == scene_id), None)
    if scene is None:
        raise ValueError(f"scene {scene_id!r} not in {lesson_path}")

    out_path = paths.scene_clip(repo_root, lesson.channel, lesson.id, scene_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.is_file() and not force:
        print(f"  {scene_id}: cached clip")
        return out_path

    words = _load_words(repo_root, lesson.channel, lesson.id, scene_id)
    data = RenderData(
        repo_root=repo_root,
        lesson=lesson,
        scene=scene,
        channel=channel,
        duration=float(words["duration"]),
        item_starts={it["id"]: float(it["start"]) for it in words.get("items", [])},
        is_3d=_scene_is_3d(repo_root, lesson, scene),
    )

    register_handwriting_font(repo_root, channel.font.file)

    from manim import tempconfig

    work = out_path.parent / ".manim"
    cfg = quality_config(quality)
    with tempconfig(
        {
            **cfg,
            "background_color": channel.board.background,
            "media_dir": str(work),
            "output_file": scene_id,
            "disable_caching": True,
            "verbosity": "ERROR",
            "flush_cache": False,
        }
    ):
        manim_scene = make_lesson_scene(data)
        manim_scene.render()
        produced = Path(manim_scene.renderer.file_writer.movie_file_path)

    shutil.copyfile(produced, out_path)
    print(f"  {scene_id}: rendered {quality} -> {out_path.name}")
    return out_path


def render_all(
    repo_root: Path, lesson_path: Path, *, quality: str = "preview", force: bool = False
) -> list[Path]:
    lesson = Lesson.model_validate(yaml.safe_load(Path(lesson_path).read_text()))
    return [
        render_scene(repo_root, lesson_path, s.id, quality=quality, force=force)
        for s in lesson.scenes
    ]
