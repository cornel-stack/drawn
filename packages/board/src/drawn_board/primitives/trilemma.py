"""The 'impossible trinity' triangle: three goals at the corners, a feasible
regime along each edge (you may pick any two goals), the centre unreachable.

Built for the Mundell-Fleming trilemma (MA-18) but reusable for any 'pick two of
three' trade-off. Corners carry the three goals; each edge, highlighted in turn,
carries the regime that achieves the two goals it joins; `mark_center` stamps the
unreachable middle.
"""

from __future__ import annotations

import numpy as np

from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import GLYPH_STROKE_WIDTH, LABEL_FONT_SIZE

# corner positions (Manim frame units): apex up, two feet below, clear of the
# bottom caption band (~y < -2.2).
_TOP = np.array([0.0, 2.3, 0.0])
_LEFT = np.array([-3.4, -1.3, 0.0])
_RIGHT = np.array([3.4, -1.3, 0.0])


@register("trilemma")
class Trilemma(Primitive):
    """A labelled triangle of three mutually-exclusive-in-threes goals.

    params:
      corners: {top, left, right}  # the three goal labels (short prose)
      edges:   {bottom, left, right}  # optional default regime labels per edge
    """

    is_3d = False

    def build(self) -> None:
        self._corners = self.params.get("corners", {})
        self._verts = {"top": _TOP, "left": _LEFT, "right": _RIGHT}
        self._edge_mid = {
            "bottom": (_LEFT + _RIGHT) / 2,
            "left": (_TOP + _LEFT) / 2,
            "right": (_TOP + _RIGHT) / 2,
        }

    # -- helpers -----------------------------------------------------------

    def _text(self, s, point, color, direction=None, at=None):
        from manim import Text

        lbl = Text(s, font=self.channel.font.handwriting, weight="BOLD",
                   font_size=LABEL_FONT_SIZE - 4, color=self.color(color),
                   stroke_width=GLYPH_STROKE_WIDTH, stroke_color=self.color(color))
        if at is not None:
            lbl.move_to(at)
        else:
            lbl.next_to(point, direction=direction, buff=0.2)
        return lbl

    # -- steps -------------------------------------------------------------

    @step
    def draw_triangle(self, run_time: float, color: str = None,
                      corner_color: str = "orange", **_):
        """Draw the triangle outline, a dot at each corner, and the three goal
        labels pinned outside their corners."""
        from manim import Create, Dot, FadeIn, Polygon, Write

        from manim import UP

        tri = Polygon(_TOP, _LEFT, _RIGHT, color=self.color(color), stroke_width=6)
        # label anchor points, pulled clear of the frame edges and caption band so
        # even long goal names stay fully on screen: apex above, feet below-inboard.
        anchors = {
            "top": _TOP + np.array([0.0, 0.45, 0.0]),
            "left": _LEFT + np.array([0.3, -0.55, 0.0]),
            "right": _RIGHT + np.array([-0.3, -0.55, 0.0]),
        }
        dots, labels = [], []
        for key, point in self._verts.items():
            dots.append(Dot(point, color=self.color(corner_color), radius=0.08))
            if self._corners.get(key):
                labels.append(self._text(self._corners[key], point, corner_color,
                                         at=anchors[key]))
        self.scene.play(Create(tri), run_time=run_time * 0.55)
        # dots and goal labels together, so the corners are named as they appear.
        self.scene.play(*[FadeIn(d) for d in dots], *[Write(l) for l in labels],
                        run_time=run_time * 0.45)

    @step
    def highlight_edge(self, run_time: float, edge: str = "bottom",
                       label: str = None, color: str = "blue", **_):
        """Thicken one edge (a feasible two-goal regime) and label it, pulled
        toward the centre so the text sits inside the triangle."""
        from manim import Create, Line, Write

        ends = {
            "bottom": (_LEFT, _RIGHT),
            "left": (_TOP, _LEFT),
            "right": (_TOP, _RIGHT),
        }[edge]
        seg = Line(ends[0], ends[1], color=self.color(color), stroke_width=11)
        self.scene.play(Create(seg), run_time=run_time * 0.55)
        if label:
            # fixed, well-separated anchors: the two side regimes sit outboard of
            # their edges (upper-left / upper-right), the third hugs the bottom
            # edge from inside — so the three never collide with one another, the
            # goal names, or the centre cross.
            anchor = {
                "left": np.array([-2.95, 1.05, 0.0]),
                "right": np.array([2.95, 1.05, 0.0]),
                "bottom": np.array([0.0, -0.95, 0.0]),
            }[edge]
            lbl = self._text(label, None, color, at=anchor)
            self.scene.play(Write(lbl), run_time=run_time * 0.45)

    @step
    def mark_center(self, run_time: float, color: str = "red", label: str = None, **_):
        """Stamp the unreachable centre with a red cross (two crossing lines) and
        an optional label."""
        from manim import Create, DOWN, Line, Write

        centre = (_TOP + _LEFT + _RIGHT) / 3
        d = 0.33
        l1 = Line(centre + np.array([-d, -d, 0]), centre + np.array([d, d, 0]),
                  color=self.color(color), stroke_width=10)
        l2 = Line(centre + np.array([-d, d, 0]), centre + np.array([d, -d, 0]),
                  color=self.color(color), stroke_width=10)
        self.scene.play(Create(l1), Create(l2), run_time=run_time * (0.6 if label else 1.0))
        if label:
            # label sits just above the cross, clear of the bottom-edge regime text.
            lbl = self._text(label, None, color, at=centre + np.array([0.0, 0.55, 0.0]))
            self.scene.play(Write(lbl), run_time=run_time * 0.4)
