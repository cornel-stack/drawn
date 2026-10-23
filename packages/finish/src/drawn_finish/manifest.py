"""Build the Remotion input props for a lesson.

Remotion renders with ``--public-dir out/<channel>/<CODE>`` so assets are
referenced relative to that directory via ``staticFile`` (e.g. ``scenes/s1.mp4``,
``audio/s1.wav``). The lesson's own ``title`` and ``end`` scenes act as the
channel intro/outro, so scene clips simply concatenate — captions and chapters
line up with cumulative scene durations without a separate offset.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from drawn_schema import paths
from drawn_schema.channel import load_channel
from drawn_schema.lesson import Lesson

_DIMS = {
    "preview": (854, 480, 15),
    "final": (1920, 1080, 30),
}


def _scene_words(repo_root: Path, channel: str, code: str, scene_id: str) -> dict:
    wj = paths.scene_words(repo_root, channel, code, scene_id)
    return json.loads(wj.read_text())


def build_props(repo_root: Path, lesson_path: Path, quality: str = "preview") -> dict:
    repo_root = Path(repo_root).resolve()
    lesson = Lesson.model_validate(yaml.safe_load(Path(lesson_path).read_text()))
    channel = load_channel(repo_root, lesson.channel)
    width, height, fps = _DIMS[quality]

    scenes = []
    for scene in lesson.scenes:
        words = _scene_words(repo_root, lesson.channel, lesson.id, scene.id)
        scenes.append(
            {
                "id": scene.id,
                "kind": scene.kind,
                "clip": f"scenes/{scene.id}.mp4",
                "audio": f"audio/{scene.id}.wav",
                "duration": float(words["duration"]),
                "words": words.get("words", []),
            }
        )

    props = {
        "lesson": {"id": lesson.id, "title": lesson.title, "channel": lesson.channel},
        "channel": {
            "display_name": channel.display_name,
            "board": channel.board.model_dump(),
            "palette": channel.palette,
            "font_family": channel.font.handwriting,
            "intro_seconds": channel.intro_seconds,
            "outro_seconds": channel.outro_seconds,
        },
        "fps": fps,
        "width": width,
        "height": height,
        "scenes": scenes,
    }
    return props


def write_props(
    repo_root: Path, lesson_path: Path, quality: str = "preview"
) -> Path:
    props = build_props(repo_root, lesson_path, quality)
    out_dir = paths.lesson_out_dir(
        Path(repo_root).resolve(), props["lesson"]["channel"], props["lesson"]["id"]
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    props_path = out_dir / "props.json"
    props_path.write_text(json.dumps(props, indent=2))
    return props_path
