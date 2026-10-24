"""Supply and demand on price-quantity axes: curves, equilibrium, shifts.

Straight lines: demand P = a - b Q (downward), supply P = c + d Q (upward).
Distinguishes a *shift* of a whole curve from a *movement along* it — the core
idea of the lesson.
"""

from __future__ import annotations

import numpy as np

from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_CURVE_STROKE = 7


@register("supply_demand")
class SupplyDemand(Primitive):
    """params:
      q_max, p_max: axis ranges (default 9, 9)
      demand: {a: intercept, b: slope}   # P = a - b Q
      supply: {c: intercept, d: slope}   # P = c + d Q
    """

    is_3d = False

    def build(self) -> None:
        from manim import Axes

        self.q_max = float(self.params.get("q_max", 9))
        self.p_max = float(self.params.get("p_max", 9))
        d = self.params.get("demand", {"a": 8.0, "b": 0.8})
        s = self.params.get("supply", {"c": 1.0, "d": 0.7})
        self.a, self.b = float(d["a"]), float(d["b"])
        self.c, self.d = float(s["c"]), float(s["d"])

        self.axes = Axes(
            x_range=[0, self.q_max, 1], y_range=[0, self.p_max, 1],
            x_length=8.2, y_length=5.4,
            axis_config={"color": self.color(None), "stroke_width": 3,
                         "include_ticks": True, "tip_width": 0.16, "tip_height": 0.16},
        )
        self.axes.move_to([0, -0.5, 0])
        self.scene.add(self.axes)
        self.scene.add(self._axis_label("Q", self.axes.x_axis.get_end(), _right()))
        self.scene.add(self._axis_label("P", self.axes.y_axis.get_end(), _up()))
        self._lines: dict = {}

    # -- geometry ----------------------------------------------------------

    def _demand_p(self, q):
        return self.a - self.b * q

    def _supply_p(self, q):
        return self.c + self.d * q

    def _clip(self, p_of_q, color):
        from manim import Line

        qs = np.linspace(0, self.q_max, 2)
        pts = []
        for q in qs:
            p = p_of_q(q)
            if 0 <= p <= self.p_max:
                pts.append(self.axes.c2p(q, p))
        if len(pts) < 2:
            # find where it crosses the box edges
            q_lo, q_hi = 0, self.q_max
            pts = [self.axes.c2p(q_lo, min(max(p_of_q(q_lo), 0), self.p_max)),
                   self.axes.c2p(q_hi, min(max(p_of_q(q_hi), 0), self.p_max))]
        return Line(pts[0], pts[-1], color=self.color(color), stroke_width=_CURVE_STROKE)

    def _equilibrium(self):
        q = (self.a - self.c) / (self.b + self.d)
        return q, self._demand_p(q)

    def _axis_label(self, text, point, direction):
        from manim import Text

        return Text(text, font=self.channel.font.handwriting, weight="BOLD",
                    font_size=LABEL_FONT_SIZE, color=self.color(None)).next_to(
            point, direction=direction, buff=0.2)

    def _curve_label(self, tex, line, color, shift):
        from manim import MathTex

        lbl = MathTex(tex, color=self.color(color), font_size=LABEL_FONT_SIZE + 8)
        return lbl.next_to(line.get_end(), direction=shift, buff=0.15)

    # -- steps -------------------------------------------------------------

    @step
    def draw_supply(self, run_time: float, color: str = "blue", **_):
        from manim import Create, Write

        line = self._clip(self._supply_p, color)
        self._lines["supply"] = line
        lbl = self._curve_label("S", line, color, _up())
        self.scene.play(Create(line), run_time=run_time * 0.7)
        self.scene.play(Write(lbl), run_time=run_time * 0.3)

    @step
    def draw_demand(self, run_time: float, color: str = "orange", **_):
        from manim import Create, Write

        line = self._clip(self._demand_p, color)
        self._lines["demand"] = line
        lbl = self._curve_label("D", line, color, _right())
        self.scene.play(Create(line), run_time=run_time * 0.7)
        self.scene.play(Write(lbl), run_time=run_time * 0.3)

    @step
    def equilibrium(self, run_time: float, color: str = "green", **_):
        from manim import DashedLine, Dot, MathTex

        q, p = self._equilibrium()
        dot = Dot(self.axes.c2p(q, p), color=self.color(color), radius=0.09)
        hline = DashedLine(self.axes.c2p(0, p), self.axes.c2p(q, p),
                           color=self.color(None), stroke_width=2)
        vline = DashedLine(self.axes.c2p(q, 0), self.axes.c2p(q, p),
                           color=self.color(None), stroke_width=2)
        pstar = MathTex("P^*", color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            self.axes.c2p(0, p), direction=_left(), buff=0.15)
        qstar = MathTex("Q^*", color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            self.axes.c2p(q, 0), direction=_down(), buff=0.15)
        self._eq_dot = dot
        self.scene.play(_create(hline), _create(vline), run_time=run_time * 0.5)
        self.scene.play(_grow(dot), _write(pstar), _write(qstar), run_time=run_time * 0.5)

    @step
    def shift(self, run_time: float, curve: str = "demand", by: float = 2.0,
              color: str = None, **_):
        """Shift a whole curve (change its intercept) and move equilibrium."""
        if curve == "demand":
            self.a += by
            new = self._clip(self._demand_p, color or "orange")
        else:
            self.c += by
            new = self._clip(self._supply_p, color or "blue")
        old = self._lines[curve]
        self.scene.play(old.animate.become(new), run_time=run_time * 0.6)
        self._lines[curve] = new
        q, p = self._equilibrium()
        self.scene.play(self._eq_dot.animate.move_to(self.axes.c2p(q, p)),
                        run_time=run_time * 0.4)

    @step
    def move_along(self, run_time: float, curve: str = "demand", to_q: float = 5.0,
                   color: str = "yellow", **_):
        """Slide a dot ALONG a fixed curve (a change in quantity demanded)."""
        from manim import Dot

        p_of_q = self._demand_p if curve == "demand" else self._supply_p
        start_q = 1.0
        dot = Dot(self.axes.c2p(start_q, p_of_q(start_q)), color=self.color(color),
                  radius=0.09)
        self.scene.play(_grow(dot), run_time=run_time * 0.3)
        self.scene.play(dot.animate.move_to(self.axes.c2p(to_q, p_of_q(to_q))),
                        run_time=run_time * 0.7)


def _create(m):
    from manim import Create

    return Create(m)


def _grow(m):
    from manim import GrowFromCenter

    return GrowFromCenter(m)


def _write(m):
    from manim import Write

    return Write(m)


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
