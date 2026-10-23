"""Render quality presets.

Final output is 1920x1080 @ 30 fps (not 60 — render time matters). Preview is
854x480 @ 15 fps for fast laptop/CI iteration.
"""

from __future__ import annotations

QUALITIES: dict[str, dict[str, int]] = {
    "preview": {"pixel_width": 854, "pixel_height": 480, "frame_rate": 15},
    "final": {"pixel_width": 1920, "pixel_height": 1080, "frame_rate": 30},
}


def quality_config(name: str) -> dict[str, int]:
    if name not in QUALITIES:
        raise ValueError(f"unknown quality {name!r}; choose from {sorted(QUALITIES)}")
    return dict(QUALITIES[name])
