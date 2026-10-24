"""Path wobble, capped to <= 1 px at 1080p (Phase 1.5: effectively off).

The hand-drawn feel comes from the stroke-by-stroke Write animation and the
hand — not from distorting glyphs, which hurt legibility.
"""

from __future__ import annotations

from drawn_board.style import WOBBLE_AMPLITUDE_UNITS

# Hard cap: 1 px at 1080p = 8/1080 units.
_MAX_AMPLITUDE = 8.0 / 1080.0


def apply_wobble(mobject, amplitude: float = WOBBLE_AMPLITUDE_UNITS, seed: int = 0) -> None:
    amplitude = min(amplitude, _MAX_AMPLITUDE)
    if amplitude <= 0:
        return
    import numpy as np

    rng = np.random.default_rng(seed)
    for sub in mobject.family_members_with_points():
        pts = sub.get_points()
        if len(pts) == 0:
            continue
        noise = rng.normal(scale=amplitude, size=pts.shape)
        noise[:, 2] = 0.0
        sub.set_points(pts + noise)
