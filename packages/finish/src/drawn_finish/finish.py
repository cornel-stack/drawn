"""Finishing stage: music bed, loudnorm to -14 LUFS, mux, and sidecar files.

Input is Remotion's ``assembly.mp4``; output is the final ``video.mp4`` plus
``captions.srt`` and ``meta.md`` in the lesson's out directory. A channel music
bed (``assets/music/<channel>.mp3``) is mixed in low if present.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml
from drawn_schema import paths
from drawn_schema.lesson import Lesson

from drawn_finish.captions import build_srt
from drawn_finish.meta import build_meta

LOUDNORM_TARGETS = {"I": -14.0, "TP": -1.5, "LRA": 11.0}
MUSIC_VOLUME = 0.12
AUDIO_RATE = 48000


@dataclass
class FinishResult:
    video: Path
    captions: Path
    meta: Path
    thumbnail: Path | None


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def _inputs(assembly: Path, music: Path | None) -> list[str]:
    args = ["-i", str(assembly)]
    if music and music.is_file():
        args += ["-stream_loop", "-1", "-i", str(music)]
    return args


def _pre_loudnorm_graph(music: Path | None) -> str:
    """Audio graph producing label [pre] before loudnorm."""
    if music and music.is_file():
        return (
            f"[1:a]volume={MUSIC_VOLUME}[m];"
            f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[pre]"
        )
    return "[0:a]anull[pre]"


def _measure_loudness(assembly: Path, music: Path | None) -> dict:
    """Pass 1: measure loudness of the final audio graph (loudnorm JSON)."""
    t = LOUDNORM_TARGETS
    graph = (
        f"{_pre_loudnorm_graph(music)};"
        f"[pre]loudnorm=I={t['I']}:TP={t['TP']}:LRA={t['LRA']}:print_format=json[a]"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        *_inputs(assembly, music),
        "-filter_complex", graph, "-map", "[a]", "-f", "null", "-",
    ]
    proc = _run(cmd)
    text = proc.stderr
    start = text.rfind("{")
    end = text.rfind("}")
    return json.loads(text[start : end + 1])


def _mux(assembly: Path, music: Path | None, out_video: Path) -> None:
    out_video.parent.mkdir(parents=True, exist_ok=True)
    t = LOUDNORM_TARGETS
    m = _measure_loudness(assembly, music)
    loudnorm = (
        f"loudnorm=I={t['I']}:TP={t['TP']}:LRA={t['LRA']}:"
        f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
        f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
        f"offset={m['target_offset']}:linear=true:print_format=summary"
    )
    graph = f"{_pre_loudnorm_graph(music)};[pre]{loudnorm}[a]"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        *_inputs(assembly, music),
        "-filter_complex", graph,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", str(AUDIO_RATE), "-ac", "2",
        "-shortest",
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
