"""Finishing stage: music bed, loudnorm to -14 LUFS, mux, and sidecar files.

Input is Remotion's ``assembly.mp4``; output is the final ``video.mp4`` plus
``captions.srt`` and ``meta.md`` in the lesson's out directory. A channel music
bed (``assets/music/<channel>.mp3``) is mixed in low if present.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml
from drawn_schema import paths
from drawn_schema.lesson import Lesson

from drawn_finish.captions import build_srt
from drawn_finish.meta import build_meta

LOUDNORM = "loudnorm=I=-14:TP=-1.5:LRA=11"
MUSIC_VOLUME = 0.12


@dataclass
class FinishResult:
    video: Path
    captions: Path
    meta: Path
    thumbnail: Path | None


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _mux(assembly: Path, music: Path | None, out_video: Path) -> None:
    out_video.parent.mkdir(parents=True, exist_ok=True)
    if music and music.is_file():
        filt = (
            f"[1:a]volume={MUSIC_VOLUME}[m];"
            f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[mix];"
            f"[mix]{LOUDNORM}[a]"
        )
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(assembly),
            "-stream_loop", "-1", "-i", str(music),
            "-filter_complex", filt,
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(out_video),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(assembly),
            "-af", LOUDNORM,
            "-map", "0:v", "-map", "0:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            str(out_video),
        ]
    _run(cmd)


def run_finish(repo_root: Path, lesson_path: Path) -> FinishResult:
    repo_root = Path(repo_root).resolve()
    lesson = Lesson.model_validate(yaml.safe_load(Path(lesson_path).read_text()))
    out_dir = paths.lesson_out_dir(repo_root, lesson.channel, lesson.id)

    assembly = out_dir / "assembly.mp4"
    if not assembly.is_file():
        raise FileNotFoundError(
            f"missing {assembly}; run the assemble stage before finish"
        )

    music = repo_root / "assets" / "music" / f"{lesson.channel}.mp3"
    video = out_dir / "video.mp4"
    _mux(assembly, music, video)

    captions = out_dir / "captions.srt"
    captions.write_text(build_srt(repo_root, lesson))

    meta = out_dir / "meta.md"
    meta.write_text(build_meta(repo_root, lesson))

    thumb = out_dir / "thumbnail.png"
    thumbnail = thumb if thumb.is_file() else None

    print(f"finish: {video}")
    print(f"  captions: {captions.name}  meta: {meta.name}"
          + (f"  thumbnail: {thumbnail.name}" if thumbnail else "  (no thumbnail yet)"))
    return FinishResult(video=video, captions=captions, meta=meta, thumbnail=thumbnail)
