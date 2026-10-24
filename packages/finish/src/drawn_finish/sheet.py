"""Contact sheet: one frame every 5 s, 4 columns, for quick legibility review."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

COLUMNS = 4
EVERY_SECONDS = 5
TILE_WIDTH = 640  # per-cell width in px


def _duration(video: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(video),
        ],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def build_sheet(video: Path, out_png: Path) -> Path:
    duration = _duration(video)
    n = max(1, int(duration // EVERY_SECONDS) + 1)
    rows = math.ceil(n / COLUMNS)
    vf = (
        f"fps=1/{EVERY_SECONDS},scale={TILE_WIDTH}:-1,"
        f"tile={COLUMNS}x{rows}:padding=6:margin=6:color=0x202020"
    )
    out_png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
            "-vf", vf, "-frames:v", "1", str(out_png),
        ],
        check=True,
    )
    return out_png
