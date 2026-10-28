"""Relative velocity: a boat crossing a flowing river.

The boat's velocity relative to the ground is the vector sum of its velocity
relative to the water and the water's velocity relative to the ground:
v_bg = v_bw + v_wg. The boat is steered straight across yet lands downstream,
because the current carries it — the clearest picture of adding velocities
measured in different frames.
"""

from __future__ import annotations

import numpy as np

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_ARR_STROKE = 6
_TIP_RATIO = 0.28


@register("river_crossing")
class RiverCrossing(Primitive):
    """params:
      boat: [bx, by]   # boat velocity relative to the water (frame units; by>0 crosses up)
      current: c       # water velocity relative to the ground (+x), frame units
      start: [x, y]    # launch point on the near bank (default lower-left of the river)

    steps: draw_river, boat_velocity, current_velocity, resultant, cross.
    """

    is_3d = False

    def build(self) -> None:
        cx, cy = style.ANIM_CENTER[0], style.ANIM_CENTER[1]
        self._half_w = 3.3                       # river half-width (x)
        self._bottom = cy - 1.5                  # near bank (y)
        self._top = cy + 1.5                     # far bank (y)
        self._xc = cx
        self.boat = np.array([*self.params.get("boat", [0.0, 1.3]), 0.0])
        self.current = float(self.params.get("current", 1.0))
        st = self.params.get("start", [cx - 2.2, self._bottom])
        self._start = np.array([st[0], st[1], 0.0])

    def _mlabel(self, tex, point, color, direction):
        from manim import MathTex

        return MathTex(tex, color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            point, direction=direction, buff=0.12)

    def _arrow(self, start, end, color):
        from manim import Arrow

        return Arrow(start, end, buff=0, color=self.color(color), stroke_width=_ARR_STROKE,
                     max_tip_length_to_length_ratio=_TIP_RATIO)

    # -- steps -------------------------------------------------------------

    @step
    def draw_river(self, run_time: float, color: str = "blue", **_):
        """Two banks with the water between them, and flow arrows for the current."""
        from manim import Create, Line, VGroup

        left, right = self._xc - self._half_w, self._xc + self._half_w
        bank_b = Line([left, self._bottom, 0], [right, self._bottom, 0],
                      color=self.color(None), stroke_width=4)
        bank_t = Line([left, self._top, 0], [right, self._top, 0],
                      color=self.color(None), stroke_width=4)
        flows = VGroup()
        for frac in (0.3, 0.55, 0.8):
            y = self._bottom + (self._top - self._bottom) * frac
            flows.add(self._arrow([left + 0.6, y, 0], [left + 2.1, y, 0], color))
        for m in (bank_b, bank_t):
            m.set_stroke(opacity=0.9)
        self.scene.play(Create(bank_b), Create(bank_t), run_time=run_time * 0.5)
        self.scene.play(*[Create(f) for f in flows], run_time=run_time * 0.3)
        from manim import Write

        self.scene.play(Write(self._mlabel(r"\text{current}", flows[-1].get_end(),
                                           color, _up())), run_time=run_time * 0.2)

    @step
    def boat_velocity(self, run_time: float, color: str = "green",
                      label: str = "v_{bw}", **_):
        """The boat's velocity relative to the water (how it is steered)."""
        from manim import GrowArrow, Write

        end = self._start + self.boat
        self._vbw = self._arrow(self._start, end, color)
        self.scene.play(GrowArrow(self._vbw), run_time=run_time * 0.7)
        if label:
            self.scene.play(Write(self._mlabel(label, end, color, _left())),
                            run_time=run_time * 0.3)

    @step
    def current_velocity(self, run_time: float, color: str = "blue",
                         label: str = "v_{wg}", **_):
        """The water's velocity relative to the ground (the current), drawn from
        the tip of the boat-velocity arrow, ready to add tip-to-tail."""
        from manim import GrowArrow, Write

        tail = self._start + self.boat
        end = tail + np.array([self.current, 0.0, 0.0])
        self._vwg = self._arrow(tail, end, color)
        self.scene.play(GrowArrow(self._vwg), run_time=run_time * 0.7)
        if label:
            self.scene.play(Write(self._mlabel(label, end, color, _up())),
                            run_time=run_time * 0.3)

    @step
    def resultant(self, run_time: float, color: str = "red", label: str = "v_{bg}", **_):
        """The ground velocity v_bg = v_bw + v_wg, from the start to the far tip."""
        from manim import GrowArrow, Write

        end = self._start + self.boat + np.array([self.current, 0.0, 0.0])
        self._vbg = self._arrow(self._start, end, color)
        self.scene.play(GrowArrow(self._vbg), run_time=run_time * 0.7)
        if label:
            self.scene.play(Write(self._mlabel(label, (self._start + end) / 2, color,
                                               _right())), run_time=run_time * 0.3)

    @step
    def cross(self, run_time: float, color: str = "red", boat_color: str = "yellow", **_):
        """Send the boat across along its ground velocity, tracing the real path;
        it lands downstream of straight across, carried by the current."""
        from manim import DashedLine, Dot, Triangle

        # time to cross: vertical distance / vertical speed
        t_cross = (self._top - self._bottom) / self.boat[1]
        drift = (self.boat[0] + self.current) * t_cross
        land = np.array([self._start[0] + drift, self._top, 0.0])
        path = DashedLine(self._start, land, color=self.color(color), stroke_width=3)
        boat = Triangle(color=self.color(boat_color), fill_opacity=0.9).scale(0.18)
        boat.move_to(self._start)
        # where straight-across (no current) would have landed
        straight = np.array([self._start[0] + self.boat[0] * t_cross, self._top, 0.0])
        ghost = Dot(straight, color=self.color(None), radius=0.06)
        self.scene.play(_create(path), run_time=run_time * 0.25)
        self.scene.add(boat)
        self.scene.play(boat.animate.move_to(land), run_time=run_time * 0.6)
        self.scene.play(_grow(ghost), run_time=run_time * 0.15)


def _create(m):
    from manim import Create

    return Create(m)


def _grow(m):
    from manim import GrowFromCenter

    return GrowFromCenter(m)


def _up():
    from manim import UP

    return UP


def _left():
    from manim import LEFT

    return LEFT


def _right():
    from manim import RIGHT

    return RIGHT
