"""Assemble the lesson video with ffmpeg — replaces the Remotion ``Lesson`` render.

Remotion composited every frame through headless Chrome (~15 min for a 1080p
final). ffmpeg does the same job — concatenate the per-scene Manim clips and
voice audio, draw the solid caption bar across the bottom 14 %, and burn
word-synced captions — in seconds. Output is ``assembly.mp4`` (video + captions
+ voice); the ``finish`` stage then adds the music bed and loudnorm.

The caption styling mirrors the old Remotion output: a ``#0a0a0a`` bar with a
3 px accent top border, centred white sans-serif text, ≤ 8 words / 3.5 s a cue.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml
from drawn_schema import paths
from drawn_schema.channel import load_channel
from drawn_schema.lesson import Lesson

from drawn_finish.captions import _cues_for_words

_BAR_FRAC = 0.14
_BORDER_PX = 3


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _build_ass(repo_root: Path, lesson: Lesson, width: int, height: int) -> str:
    font_size = round(width / 42)
    margin_v = round(height * 0.038)  # sit the text inside the bottom bar
    head = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        f"Style: cap,Sans,{font_size},&H00FFFFFF,&H00000000,&H00000000,0,0,1,2,0,"
        f"2,{round(width * 0.07)},{round(width * 0.07)},{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    offset = 0.0
    for scene in lesson.scenes:
        data = json.loads(
            paths.scene_words(repo_root, lesson.channel, lesson.id, scene.id).read_text()
        )
        for cue in _cues_for_words(data.get("words", []), offset):
            start = _ass_time(offset + cue[0]["start"])
            end = _ass_time(offset + cue[-1]["end"] + 0.15)
            text = " ".join(w["word"] for w in cue).strip().replace("\n", " ")
            head.append(f"Dialogue: 0,{start},{end},cap,,0,0,0,,{text}")
        offset += float(data["duration"])
    return "\n".join(head) + "\n"



def assemble(repo_root: Path, lesson_path: Path, quality: str = "final") -> Path:
    repo_root = Path(repo_root).resolve()
    lesson = Lesson.model_validate(yaml.safe_load(Path(lesson_path).read_text()))
    channel = load_channel(repo_root, lesson.channel)
    out_dir = paths.lesson_out_dir(repo_root, lesson.channel, lesson.id)
    work = out_dir / ".assemble"
    work.mkdir(parents=True, exist_ok=True)

    clips = [paths.scene_clip(repo_root, lesson.channel, lesson.id, s.id) for s in lesson.scenes]
    audios = [paths.scene_wav(repo_root, lesson.channel, lesson.id, s.id) for s in lesson.scenes]
    missing = [p for p in clips + audios if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"missing render inputs: {missing[0]} (+{len(missing) - 1})")

    w, h = _probe_dims(clips[0])
    ass = work / "captions.ass"
    ass.write_text(_build_ass(repo_root, lesson, w, h))

    # One ffmpeg pass: concat the clips (video) and the voice (audio) with the
    # concat FILTER — robust to any per-scene stream differences — then draw the
    # caption bar and burn the captions. A single re-encode, seconds not minutes.
    n = len(lesson.scenes)
    inputs: list[str] = []
    for p in clips + audios:
        inputs += ["-i", str(p)]
    vrefs = "".join(f"[{i}:v]" for i in range(n))
    arefs = "".join(f"[{n + i}:a]" for i in range(n))
    bar_h = round(h * _BAR_FRAC)
    border = "0x" + channel.resolve_color(channel.board.accent).lstrip("#")
    graph = (
        f"{vrefs}concat=n={n}:v=1:a=0[vcat];"
        f"{arefs}concat=n={n}:v=0:a=1[acat];"
        f"[vcat]drawbox=x=0:y=ih-{bar_h}:w=iw:h={bar_h}:color=0x0a0a0a@1:t=fill,"
        f"drawbox=x=0:y=ih-{bar_h}:w=iw:h={_BORDER_PX}:color={border}@1:t=fill,"
        f"ass={ass.resolve().as_posix()}[vo]"
    )
    assembly = out_dir / "assembly.mp4"
    _run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", graph,
        "-map", "[vo]", "-map", "[acat]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", str(assembly),
    ])
    return assembly


def _probe_dims(clip: Path) -> tuple[int, int]:
    out = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(clip),
    ]).stdout.strip()
    w, h = out.split("x")
    return int(w), int(h)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)
