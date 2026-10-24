"""Cartesian axes with lines, functions, points, intersections, tangents, areas.

Reused across maths and physics lessons. Lines are given as a x + b y = c (handy
for linear systems); functions are named (YAML can't carry a lambda).
"""

from __future__ import annotations

import numpy as np

from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_LINE_STROKE = 6

_FUNCS = {
    "parabola": (lambda x: 0.3 * x * x, "x^2"),
    "line": (lambda x: x, "x"),
    "sin": (lambda x: 2.0 * np.sin(x), r"\sin x"),
    "cos": (lambda x: 2.0 * np.cos(x), r"\cos x"),
    "exp": (lambda x: np.exp(0.5 * x), "e^{x}"),
    "cubic": (lambda x: 0.12 * x ** 3, "x^3"),
}


@register("axes_plot")
class AxesPlot(Primitive):
    """params:
      x: [min, max, step], y: [min, max, step]
      x_length, y_length, center
      x_label, y_label (optional)
    """

    is_3d = False

    def build(self) -> None:
        from manim import Axes

        p = self.params
        self.axes = Axes(
            x_range=p.get("x", [-5, 5, 1]), y_range=p.get("y", [-4, 4, 1]),
            x_length=p.get("x_length", 8.0), y_length=p.get("y_length", 4.6),
            axis_config={"color": self.color(None), "stroke_width": 3,
                         "include_ticks": True, "tip_width": 0.16, "tip_height": 0.16},
        )
        # sit above the bottom caption band (~14 % of the frame)
        self.axes.move_to(p.get("center", [0, 0.5, 0]))
        self.scene.add(self.axes)
        if p.get("x_label"):
            self.scene.add(self._axis_label(p["x_label"], self.axes.x_axis.get_end(), _right()))
        if p.get("y_label"):
            self.scene.add(self._axis_label(p["y_label"], self.axes.y_axis.get_end(), _up()))
        self._lines: dict = {}
        self._funcs: dict = {}

    # -- helpers -----------------------------------------------------------

    def _axis_label(self, tex, point, direction):
        from manim import MathTex

        return MathTex(tex, color=self.color(None), font_size=LABEL_FONT_SIZE).next_to(
            point, direction=direction, buff=0.2)

    def _xr(self):
        r = self.params.get("x", [-5, 5, 1])
        return r[0], r[1]

    def _line_endpoints(self, a, b, c):
        """Endpoints of a x + b y = c clipped to the x-range (b != 0 assumed)."""
        x0, x1 = self._xr()
        if abs(b) < 1e-9:  # vertical line x = c/a
            xv = c / a
            yr = self.params.get("y", [-4, 4, 1])
            return self.axes.c2p(xv, yr[0]), self.axes.c2p(xv, yr[1])
        return self.axes.c2p(x0, (c - a * x0) / b), self.axes.c2p(x1, (c - a * x1) / b)

    def _mlabel(self, tex, point, color, direction):
        from manim import MathTex

        return MathTex(tex, color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            point, direction=direction, buff=0.18)

    # -- steps -------------------------------------------------------------

    @step
    def plot_line(self, run_time: float, name: str = None, a: float = 1, b: float = 1,
                  c: float = 0, color: str = "blue", label: str = None, **_):
        from manim import Create, Line, Write

        p0, p1 = self._line_endpoints(a, b, c)
        line = Line(p0, p1, color=self.color(color), stroke_width=_LINE_STROKE)
        self._lines[name or f"L{len(self._lines)}"] = (line, a, b, c)
        self.scene.play(Create(line), run_time=run_time * (0.75 if label else 1.0))
        if label:
            lbl = self._mlabel(label, p1, color, _up())
            self.scene.play(Write(lbl), run_time=run_time * 0.25)

    @step
    def plot_function(self, run_time: float, func: str = "parabola", color: str = "blue",
                      label: str = None, **_):
        from manim import Create, Write

        f, tex = _FUNCS[func]
        graph = self.axes.plot(f, color=self.color(color), stroke_width=_LINE_STROKE)
        self._funcs[func] = f
        self.scene.play(Create(graph), run_time=run_time * (0.75 if label else 1.0))
        if label:
            end = self.axes.c2p(self._xr()[1], f(self._xr()[1]))
            self.scene.play(Write(self._mlabel(label or tex, end, color, _up())),
                            run_time=run_time * 0.25)

    @step
    def mark_point(self, run_time: float, x: float = 0, y: float = 0, color: str = "green",
                   label: str = None, dashed: bool = True, **_):
        from manim import DashedLine, Dot, Write

        pt = self.axes.c2p(x, y)
        dot = Dot(pt, color=self.color(color), radius=0.09)
        anims = [_grow(dot)]
        if dashed:
            anims += [_create(DashedLine(self.axes.c2p(0, y), pt, color=self.color(None),
                                         stroke_width=2)),
                      _create(DashedLine(self.axes.c2p(x, 0), pt, color=self.color(None),
                                         stroke_width=2))]
        self.scene.play(*anims, run_time=run_time * (0.7 if label else 1.0))
        if label:
            self.scene.play(Write(self._mlabel(label, pt, color, _up() + _right())),
                            run_time=run_time * 0.3)

    @step
    def intersect(self, run_time: float, line1: str = None, line2: str = None,
                  color: str = "green", label: str = None, **_):
        from manim import Dot, Flash

        (_, a1, b1, c1) = self._lines[line1]
        (_, a2, b2, c2) = self._lines[line2]
        m = np.array([[a1, b1], [a2, b2]], dtype=float)
        x, y = np.linalg.solve(m, np.array([c1, c2], dtype=float))
        pt = self.axes.c2p(x, y)
        dot = Dot(pt, color=self.color(color), radius=0.11)
        self.scene.play(_grow(dot), run_time=run_time * 0.6)
        self.scene.play(Flash(dot, color=self.color(color)), run_time=run_time * 0.4)
        if label:
            from manim import Write

            self.scene.play(Write(self._mlabel(label, pt, color, _up() + _right())),
                            run_time=run_time * 0.3)

    @step
    def tangent(self, run_time: float, func: str = "parabola", x0: float = 1.0,
                color: str = "orange", **_):
        from manim import Create, Dot, Line

        f = self._funcs.get(func) or _FUNCS[func][0]
        h = 1e-4
        slope = (f(x0 + h) - f(x0 - h)) / (2 * h)
        x_lo, x_hi = x0 - 1.6, x0 + 1.6

        def ty(x):
            return f(x0) + slope * (x - x0)

        line = Line(self.axes.c2p(x_lo, ty(x_lo)), self.axes.c2p(x_hi, ty(x_hi)),
                    color=self.color(color), stroke_width=_LINE_STROKE)
        dot = Dot(self.axes.c2p(x0, f(x0)), color=self.color(color), radius=0.08)
        self.scene.play(_grow(dot), run_time=run_time * 0.3)
        self.scene.play(Create(line), run_time=run_time * 0.7)

    @step
    def area(self, run_time: float, func: str = "parabola", x0: float = 0.0, x1: float = 3.0,
             color: str = "green", **_):
        from manim import Create

        f = self._funcs.get(func) or _FUNCS[func][0]
        graph = self.axes.plot(f, x_range=[x0, x1], color=self.color(color))
        region = self.axes.get_area(graph, x_range=[x0, x1], color=self.color(color), opacity=0.4)
        self.scene.play(Create(region), run_time=run_time)

    @step
    def trace(self, run_time: float, func: str = "parabola", color: str = "yellow", **_):
        from manim import Dot, MoveAlongPath

        f = self._funcs.get(func) or _FUNCS[func][0]
        graph = self.axes.plot(f, color=self.color(color))
        self._funcs[func] = f
        dot = Dot(graph.get_start(), color=self.color(color), radius=0.09)
        self.scene.add(dot)
        self.scene.play(MoveAlongPath(dot, graph), run_time=run_time)


def _create(m):
    from manim import Create

    return Create(m)


def _grow(m):
    from manim import GrowFromCenter

    return GrowFromCenter(m)


def _up():
    from manim import UP

    return UP


def _right():
    from manim import RIGHT

    return RIGHT
