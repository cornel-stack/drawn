"""The hand that follows the pen tip as things are written.

The hand is a transparent PNG; its config (``assets/hand/hand.yaml``) records
the pen-tip location as normalised image coordinates so swapping in a real
photo is a one-file change: drop the PNG in and set ``tip``/``scale``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_HAND_CONFIG = "assets/hand/hand.yaml"


@dataclass
class HandConfig:
    image: str  # path relative to repo root
    tip: tuple[float, float]  # (x from left, y from top), normalised 0..1
    scale: float  # rendered height in Manim units

    @classmethod
    def load(cls, repo_root: Path, rel: str = DEFAULT_HAND_CONFIG) -> HandConfig:
        data = yaml.safe_load((Path(repo_root) / rel).read_text())
        tx, ty = data["tip"]
        return cls(image=data["image"], tip=(float(tx), float(ty)), scale=float(data["scale"]))


def path_point(mobject, alpha: float):
    """Approximate the pen position at fraction ``alpha`` of drawing ``mobject``.

    Uses the mobject's ordered family points, which track drawing order closely
    enough for Write() — and unlike ``point_from_proportion`` it works for both
    MathTex and multi-glyph Text.
    """
    import numpy as np

    pts = mobject.get_all_points()
    if len(pts) == 0:
        return mobject.get_center()
    a = min(max(alpha, 0.0), 1.0)
    idx = int(round(a * (len(pts) - 1)))
    return np.asarray(pts[idx])


class HandFollower:
    """Wraps the hand ImageMobject and keeps its pen tip on a target point."""

    def __init__(self, repo_root: Path, config: HandConfig | None = None):
        from manim import ImageMobject

        self.config = config or HandConfig.load(repo_root)
        image_path = (Path(repo_root) / self.config.image).resolve()
        self.mobject = ImageMobject(str(image_path))
        self.mobject.height = self.config.scale
        self._compute_tip_offset()

    def _compute_tip_offset(self):
        import numpy as np

        w = self.mobject.width
        h = self.mobject.height
        nx, ny = self.config.tip
        # offset from the image centre to the pen tip (y up in Manim)
        self.tip_offset = np.array([(nx - 0.5) * w, (0.5 - ny) * h, 0.0])

    def place_tip_at(self, point) -> None:
        self.mobject.move_to(point - self.tip_offset)

    def follow_updater(self, mobject, tracker):
        """Return an updater that keeps the pen tip on mobject's drawing frontier."""

        def _update(hand_mob):
            target = path_point(mobject, tracker.get_value())
            hand_mob.move_to(target - self.tip_offset)

        return _update
