"""A simple two-loop DC circuit schematic: a rectangle with a middle branch, so
there are two junctions (top and bottom) and three vertical branches — left,
middle, right. Components (battery, resistors) sit on the branches, with current
arrows and loop indicators. Built for Kirchhoff's rules and reused across the
circuits series.
"""

from __future__ import annotations

import numpy as np

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_WIRE = 4


@register("circuit")
class Circuit(Primitive):
    """params:
      width, height: circuit box size in frame units (default 5.0, 3.0)
      center: [x, y] (default the animation centre)

    Branches: 'left', 'middle', 'right' (vertical). Junctions: 'top', 'bottom'.
    steps: draw_wires, battery, resistor, junction, current, loop.
    """

    is_3d = False

    def build(self) -> None:
        c = self.params.get("center", [style.ANIM_CENTER[0], style.ANIM_CENTER[1]])
        self.cx, self.cy = float(c[0]), float(c[1])
        self.w = float(self.params.get("width", 5.0))
        self.h = float(self.params.get("height", 3.0))
        hw, hh = self.w / 2, self.h / 2
        self._x = {"left": self.cx - hw, "middle": self.cx, "right": self.cx + hw}
        self._yt, self._yb = self.cy + hh, self.cy - hh

    def _branch(self, name):
        x = self._x[name]
        return np.array([x, self._yb, 0.0]), np.array([x, self._yt, 0.0])

    def _mlabel(self, tex, point, color, direction):
        from manim import MathTex

        return MathTex(tex, color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            point, direction=direction, buff=0.14)

    # -- steps -------------------------------------------------------------

    @step
    def draw_wires(self, run_time: float, color: str = None, **_):
        """The outer rectangle plus the middle vertical branch."""
        from manim import Create, Line, VGroup

        col = self.color(None) if color in (None, "white", "ink") else self.color(color)
        hw, hh = self.w / 2, self.h / 2
        tl = [self.cx - hw, self._yt, 0]; tr = [self.cx + hw, self._yt, 0]
        bl = [self.cx - hw, self._yb, 0]; br = [self.cx + hw, self._yb, 0]
        tm = [self.cx, self._yt, 0]; bm = [self.cx, self._yb, 0]
        wires = VGroup(
            Line(tl, tr, color=col, stroke_width=_WIRE),   # top
            Line(bl, br, color=col, stroke_width=_WIRE),   # bottom
            Line(tl, bl, color=col, stroke_width=_WIRE),   # left
            Line(tr, br, color=col, stroke_width=_WIRE),   # right
            Line(tm, bm, color=col, stroke_width=_WIRE),   # middle
        )
        self.scene.play(Create(wires), run_time=run_time)

    @step
    def battery(self, run_time: float, branch: str = "left", label: str = "\\varepsilon",
                color: str = "red", **_):
        """A cell (long + short plate) on a vertical branch."""
        from manim import Line, VGroup, Write

        x = self._x[branch]
        y = self.cy
        long = Line([x - 0.28, y + 0.12, 0], [x + 0.28, y + 0.12, 0],
                    color=self.color(color), stroke_width=6)
        short = Line([x - 0.15, y - 0.12, 0], [x + 0.15, y - 0.12, 0],
                     color=self.color(color), stroke_width=10)
        grp = VGroup(long, short)
        self.scene.play(_create(grp), run_time=run_time * 0.7)
        self.scene.play(Write(self._mlabel(label, [x, y, 0], color, _left())),
                        run_time=run_time * 0.3)

    @step
    def resistor(self, run_time: float, branch: str = "middle", label: str = "R",
                 color: str = "orange", **_):
        """A resistor (box) on a vertical branch."""
        from manim import Rectangle, Write

        x = self._x[branch]
        box = Rectangle(width=0.5, height=0.9, color=self.color(color),
                        stroke_width=5).move_to([x, self.cy, 0])
        self.scene.play(_create(box), run_time=run_time * 0.7)
        side = _right() if branch != "right" else _left()
        self.scene.play(Write(self._mlabel(label, [x, self.cy, 0], color, side)),
                        run_time=run_time * 0.3)

    @step
    def junction(self, run_time: float, node: str = "top", label: str = "a",
                 color: str = "yellow", **_):
        """Mark a junction dot at the top or bottom middle node."""
        from manim import Dot, Write

        y = self._yt if node == "top" else self._yb
        dot = Dot([self.cx, y, 0], radius=0.1, color=self.color(color))
        d = _up() if node == "top" else _down()
        self.scene.play(_grow(dot), run_time=run_time * 0.6)
        self.scene.play(Write(self._mlabel(label, [self.cx, y, 0], color, d)),
                        run_time=run_time * 0.4)

    @step
    def current(self, run_time: float, branch: str = "left", direction: str = "up",
                label: str = "I", color: str = "blue", **_):
        """A current arrow along a vertical branch (up or down), labelled."""
        from manim import Arrow, GrowArrow, Write

        x = self._x[branch]
        y0, y1 = self.cy - 0.6, self.cy + 0.6
        if direction == "down":
            y0, y1 = y1, y0
        arr = Arrow([x, y0, 0], [x, y1, 0], buff=0, color=self.color(color),
                    stroke_width=6, max_tip_length_to_length_ratio=0.3)
        off = _left() if branch == "left" else _right()
        self.scene.play(GrowArrow(arr), run_time=run_time * 0.7)
        self.scene.play(Write(self._mlabel(label, arr.get_center(), color, off)),
                        run_time=run_time * 0.3)

    @step
    def loop(self, run_time: float, which: str = "left", label: str = None,
             color: str = "green", **_):
        """A circular arrow inside the left or right loop showing the chosen sense."""
        from manim import CurvedArrow, Write

        xc = (self._x["left"] + self._x["middle"]) / 2 if which == "left" \
            else (self._x["middle"] + self._x["right"]) / 2
        r = 0.6
        start = [xc + r, self.cy, 0]
        end = [xc - r, self.cy, 0]
        arc = CurvedArrow(np.array(start), np.array(end), angle=-5.0,
                          color=self.color(color), tip_length=0.2)
        self.scene.play(_create(arc), run_time=run_time * (0.8 if label else 1.0))
        if label:
            self.scene.play(Write(self._mlabel(label, [xc, self.cy, 0], color, _up() * 0)),
                            run_time=run_time * 0.2)


def _create(m):
    from manim import Create

    return Create(m)


def _grow(m):
    from manim import GrowFromCenter

    return GrowFromCenter(m)


def _up():
    from manim import UP

    return UP


def _down():
    from manim import DOWN

    return DOWN


def _left():
    from manim import LEFT

    return LEFT


def _right():
    from manim import RIGHT

    return RIGHT
