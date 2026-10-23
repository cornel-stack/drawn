"""Slight path wobble so strokes look hand-drawn rather than vector-perfect."""

from __future__ import annotations


def apply_wobble(mobject, amplitude: float = 0.015, seed: int = 0) -> None:
    """Jitter every anchor/control point of a VMobject family in the xy plane.

    Amplitude is in Manim units; keep it small (a fraction of a glyph) so text
    stays legible. Deterministic given ``seed`` so renders are reproducible.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    for sub in mobject.family_members_with_points():
        pts = sub.get_points()
        if len(pts) == 0:
            continue
        noise = rng.normal(scale=amplitude, size=pts.shape)
        noise[:, 2] = 0.0  # keep flat in z
        sub.set_points(pts + noise)
