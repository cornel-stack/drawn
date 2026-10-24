"""The hand that writes: a transparent PNG whose pen tip follows the stroke.

Config lives in ``assets/hand/anchors.json`` (written by the hand pipeline):

    {"write": {"image": "...png", "tip": [nx, ny]},
     "rest":  {"image": "...png", "tip": [nx, ny]},   # optional
     "height_frac": 0.40}

``tip`` is the pen-tip pixel as a fraction of the image (x from left, y from
top). The follower keeps the tip on the current stroke's frontier, enters from
the bottom-right before an item, lifts away when it finishes, and offsets the
palm below/right so it never covers the writing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ANCHORS_JSON = "assets/hand/anchors.json"
# How far down-right the hand sits off its pen tip is derived from the tip
# anchor, so the palm never covers the fresh ink.
ENTER_OFFSET = (2.2, -1.6)  # units, relative to tip, when entering/resting
LIFT_SECONDS = 0.3
ROTATE_MAX_DEG = 5.0


@dataclass
class HandPose:
    image: str
    tip: tuple[float, float]


def path_point(mobject, alpha: float):
    import numpy as np

    pts = mobject.get_all_points()
    if len(pts) == 0:
        return mobject.get_center()
    a = min(max(alpha, 0.0), 1.0)
    idx = int(round(a * (len(pts) - 1)))
    return np.asarray(pts[idx])


class HandFollower:
    def __init__(self, repo_root: Path, frame_height: float):
        from drawn_board.hand_pipeline import ensure_hand

        repo_root = Path(repo_root)
        anchors_path = ensure_hand(repo_root)  # builds a fallback if needed
        data = json.loads(anchors_path.read_text())
        self._write = HandPose(data["write"]["image"], tuple(data["write"]["tip"]))
        self.height_frac = float(data.get("height_frac", 0.40))
        self.repo_root = repo_root
        self.frame_height = frame_height
        self._build()

    def _build(self):
        import numpy as np
        from manim import ImageMobject

        img = (self.repo_root / self._write.image).resolve()
        self.mobject = ImageMobject(str(img))
        self.mobject.height = self.height_frac * self.frame_height
        # a small static tilt reads as a natural pen angle
        self.mobject.rotate(np.deg2rad(-ROTATE_MAX_DEG))
        w, h = self.mobject.width, self.mobject.height
        nx, ny = self._write.tip
        self.tip_offset = np.array([(nx - 0.5) * w, (0.5 - ny) * h, 0.0])
        self.mobject.set_opacity(0.0)

    # -- placement ---------------------------------------------------------

    def _center_for_tip(self, point):
        return point - self.tip_offset

    def place_tip_at(self, point) -> None:
        self.mobject.move_to(self._center_for_tip(point))

    def enter(self, scene, point, run_time: float = LIFT_SECONDS) -> None:
        import numpy as np

        start = self._center_for_tip(point) + np.array([*ENTER_OFFSET, 0.0])
        self.mobject.move_to(start).set_opacity(0.0)
        target = self._center_for_tip(point)
        self.mobject.generate_target()
        self.mobject.target.move_to(target).set_opacity(1.0)
        from manim import MoveToTarget

        scene.play(MoveToTarget(self.mobject), run_time=run_time)

    def lift(self, scene, run_time: float = LIFT_SECONDS) -> None:
        import numpy as np

        shift = np.array([ENTER_OFFSET[0] * 0.5, ENTER_OFFSET[1] * 0.5, 0.0])
        self.mobject.generate_target()
        self.mobject.target.shift(shift).set_opacity(0.0)
        from manim import MoveToTarget

        scene.play(MoveToTarget(self.mobject), run_time=run_time)

    def follow_updater(self, mobject, tracker):
        """Keep the pen tip on the current stroke's frontier."""
        base_offset = self.tip_offset.copy()

        def _update(hand):
            target = path_point(mobject, tracker.get_value())
            hand.move_to(target - base_offset)

        return _update

    def imports_ok(self) -> bool:
        return True
