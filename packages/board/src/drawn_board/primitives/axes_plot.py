"""Cartesian axes with lines, functions, points, intersections, tangents, areas.

Reused across maths and physics lessons. Lines are given as a x + b y = c (handy
for linear systems); functions are named (YAML can't carry a lambda).
"""

from __future__ import annotations

import numpy as np

from drawn_board import style
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
    # a concave, bowed-out production-possibilities frontier: integer-clean,
    # y'' = -0.2 < 0, intercepts (0,10) and (10,0).
    "ppf": (lambda x: 10.0 - 0.1 * x * x, "10 - 0.1x^2"),
    # a concave, increasing aggregate production function Y = 10*sqrt(k):
    # diminishing returns to capital (clip guards the sqrt near x=0).
    "prodfn": (lambda x: 10.0 * np.sqrt(np.clip(x, 0.0, None)), r"10\sqrt{k}"),
    # the same function lifted by better technology / human capital (shifts up).
    "prodfn_hi": (lambda x: 13.0 * np.sqrt(np.clip(x, 0.0, None)), r"13\sqrt{k}"),
    # Solow per-worker diagram: output y = 2*sqrt(k), saving/investment s*y with
    # s = 0.3, and depreciation drawn as a line (delta k). With delta = 0.3 the
    # saving curve 0.6*sqrt(k) meets the delta-k line at the steady state k* = 4,
    # where investment = depreciation = 1.2.
    "output_pw": (lambda x: 2.0 * np.sqrt(np.clip(x, 0.0, None)), r"f(k)"),
    "saving_pw": (lambda x: 0.6 * np.sqrt(np.clip(x, 0.0, None)), r"s\,f(k)"),
    # a downward projectile arc from (0,0) to (10,0), apex (5,4).
    "arc": (lambda x: 0.16 * x * (10.0 - x), "trajectory"),
    # RC circuit, with x = t/RC (time in units of the time constant tau). Charging
    # V(t) = V0(1 - e^{-t/RC}) and discharging V(t) = V0 e^{-t/RC}, V0 scaled to 5.
    # At one time constant (x=1): charge 63% (~3.16), discharge 37% (~1.84).
    "rc_charge": (lambda x: 5.0 * (1.0 - np.exp(-np.clip(x, 0.0, None))), r"V_0(1-e^{-t/RC})"),
    "rc_discharge": (lambda x: 5.0 * np.exp(-np.clip(x, 0.0, None)), r"V_0 e^{-t/RC}"),
    # inverse-distance falloff, e.g. the magnetic field of a straight wire
    # B = mu0 I / (2 pi r), which drops as 1/r. Scaled to 4 at r = 1, and capped at
    # 4.8 so the near-wire divergence stays inside a y-axis that tops out at 5
    # (it reads as "off the top of the scale near the wire").
    "inverse_r": (lambda x: np.minimum(4.0 / np.clip(x, 0.25, None), 4.8), r"\dfrac{\mu_0 I}{2\pi r}"),
    # a solenoid's field: uniform inside (here the interval 1 < x < 4), ~zero
    # outside — the headline result of Ampere's law, B = mu0 n I inside.
    "solenoid_field": (lambda x: np.where((x > 1.0) & (x < 4.0), 4.0, 0.0), r"\mu_0 n I"),
}

# Named right-hand sides f(x, y) for a first-order ODE y' = f(x, y), and the
# exact solutions where a clean closed form exists (else solution_curve
# integrates the field numerically). YAML can't carry a lambda, so slope
# functions are selected by name, mirroring _FUNCS.
_SLOPE_FUNCS = {
    "x": lambda x, y: x,
    "y": lambda x, y: y,
    "x_minus_y": lambda x, y: x - y,
    "x_plus_y": lambda x, y: x + y,
    "y_times_3_minus_y": lambda x, y: y * (3.0 - y),
    "x_times_y": lambda x, y: x * y,
}

_EXACT_SOLS = {
    # y = x - 1 + C e^{-x}, with C fixed by (x0, y0): C = (y0 - x0 + 1) e^{x0}
    "x_minus_y": lambda x, x0, y0: x - 1.0 + (y0 - x0 + 1.0) * np.exp(x0) * np.exp(-x),
    # dy/dx = x y  =>  y = y0 * e^{(x^2 - x0^2)/2}
    "x_times_y": lambda x, x0, y0: y0 * np.exp((x * x - x0 * x0) / 2.0),
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
            x_length=p.get("x_length", style.ANIM_WIDTH),
            y_length=p.get("y_length", style.ANIM_HEIGHT),
            axis_config={"color": self.color(None), "stroke_width": 3,
                         "include_ticks": True, "tip_width": 0.16, "tip_height": 0.16,
                         "font_size": 26, "include_numbers": True},
        )
        # the animation lives in the lower region; the top band is kept clear for
        # the scene's formula (see style.ANIM_CENTER / FORMULA_BAND_Y).
        self.axes.move_to(p.get("center", style.ANIM_CENTER))
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
    def area_under_line(self, run_time: float, name: str = None, x0: float = 0.0,
                        x1: float = 3.0, color: str = "green", split: bool = False,
                        rect_color: str = "yellow", tri_color: str = "orange", **_):
        """Shade the region under a plotted line `name` between x0 and x1.

        For a velocity-time line this is the displacement. With ``split`` the
        region is drawn as a rectangle (constant-velocity part) plus a triangle
        (the part gained by accelerating), in two accents.
        """
        from manim import FadeIn, Polygon

        line, a, b, c = self._lines[name]

        def y(x):
            return (c - a * x) / b

        y0, y1 = y(x0), y(x1)
        p00 = self.axes.c2p(x0, 0)
        p10 = self.axes.c2p(x1, 0)
        if not split:
            poly = Polygon(p00, p10, self.axes.c2p(x1, y1), self.axes.c2p(x0, y0),
                           color=self.color(color), fill_opacity=0.35, stroke_width=2)
            self.scene.play(FadeIn(poly), run_time=run_time)
            return
        base = min(y0, y1)
        rect = Polygon(p00, p10, self.axes.c2p(x1, base), self.axes.c2p(x0, base),
                       color=self.color(rect_color), fill_opacity=0.35, stroke_width=2)
        tri = Polygon(self.axes.c2p(x0, base), self.axes.c2p(x1, base),
                      self.axes.c2p(x1, y1), self.axes.c2p(x0, y0),
                      color=self.color(tri_color), fill_opacity=0.35, stroke_width=2)
        self.scene.play(FadeIn(rect), run_time=run_time * 0.5)
        self.scene.play(FadeIn(tri), run_time=run_time * 0.5)

    @step
    def area(self, run_time: float, func: str = "parabola", x0: float = 0.0, x1: float = 3.0,
             color: str = "green", **_):
        from manim import Create

        f = self._funcs.get(func) or _FUNCS[func][0]
        graph = self.axes.plot(f, x_range=[x0, x1], color=self.color(color))
        region = self.axes.get_area(graph, x_range=[x0, x1], color=self.color(color), opacity=0.4)
        self.scene.play(Create(region), run_time=run_time)

    @step
    def slope_field(self, run_time: float, f: str = "x", x_step: float = 0.6,
                    y_step: float = 0.6, length: float = 0.26, color: str = "blue", **_):
        """Draw the direction field of y' = f(x, y): a short segment at each grid
        point whose slope is f there (normalised to a fixed data length)."""
        from manim import Create, LaggedStart, Line

        fn = _SLOPE_FUNCS[f]
        x0, x1 = self._xr()
        yr = self.params.get("y", [-4, 4, 1])
        segs = []
        x = x0
        while x <= x1 + 1e-9:
            y = yr[0]
            while y <= yr[1] + 1e-9:
                m = float(fn(x, y))
                n = (1.0 + m * m) ** 0.5
                ux, uy = 1.0 / n, m / n
                p0 = self.axes.c2p(x - ux * length, y - uy * length)
                p1 = self.axes.c2p(x + ux * length, y + uy * length)
                segs.append(Line(p0, p1, color=self.color(color), stroke_width=3))
                y += y_step
            x += x_step
        self.scene.play(LaggedStart(*[Create(s) for s in segs], lag_ratio=0.015),
                        run_time=run_time)

    @step
    def solution_curve(self, run_time: float, f: str = "x", x0: float = 0.0, y0: float = 0.0,
                       color: str = "blue", label: str = None, **_):
        """Draw the solution of y' = f(x, y) through (x0, y0): the exact curve if
        one is registered, else integrated numerically (RK4, both directions)."""
        from manim import Create, VMobject, Write

        xlo, xhi = self._xr()
        yr = self.params.get("y", [-4, 4, 1])
        ylo, yhi = yr[0] - 0.3, yr[1] + 0.3
        exact = _EXACT_SOLS.get(f)
        if exact is not None:
            xs = np.linspace(xlo, xhi, 240)
            data = [(float(xx), float(exact(xx, x0, y0))) for xx in xs]
        else:
            data = _integrate(_SLOPE_FUNCS[f], x0, y0, xlo, xhi)
        # keep the contiguous run of in-range points containing the start
        run = [self.axes.c2p(xx, yy) for xx, yy in data if ylo <= yy <= yhi]
        if len(run) < 2:
            return
        curve = VMobject(color=self.color(color), stroke_width=_LINE_STROKE)
        curve.set_points_smoothly(run)
        self.scene.play(Create(curve), run_time=run_time * (0.8 if label else 1.0))
        if label:
            self.scene.play(Write(self._mlabel(label, run[-1], color, _up())),
                            run_time=run_time * 0.2)

    @step
    def chord(self, run_time: float, x0: float = 0, y0: float = 0, x1: float = 1,
              y1: float = 1, color: str = "orange", label: str = None, **_):
        """Draw the straight chord between two data points (a secant), optionally
        labelled with its slope — opportunity cost as rise over run."""
        from manim import Create, Line

        p0, p1 = self.axes.c2p(x0, y0), self.axes.c2p(x1, y1)
        line = Line(p0, p1, color=self.color(color), stroke_width=_LINE_STROKE)
        self.scene.play(Create(line), run_time=run_time * (0.75 if label else 1.0))
        if label:
            from manim import Write

            self.scene.play(Write(self._mlabel(label, (p0 + p1) / 2, color, _up())),
                            run_time=run_time * 0.25)

    @step
    def trace(self, run_time: float, func: str = "parabola", color: str = "yellow", **_):
        from manim import Dot, MoveAlongPath

        f = self._funcs.get(func) or _FUNCS[func][0]
        graph = self.axes.plot(f, color=self.color(color))
        self._funcs[func] = f
        dot = Dot(graph.get_start(), color=self.color(color), radius=0.09)
        self.scene.add(dot)
        self.scene.play(MoveAlongPath(dot, graph), run_time=run_time)


def _integrate(fn, x0, y0, xlo, xhi, h=0.04):
    """RK4 for y' = fn(x, y) from (x0, y0), forward to xhi and back to xlo."""
    def march(direction, limit):
        pts, x, y = [(x0, y0)], x0, y0
        while (x < limit - 1e-9) if direction > 0 else (x > limit + 1e-9):
            s = direction * min(h, abs(limit - x))
            k1 = fn(x, y)
            k2 = fn(x + s / 2, y + s / 2 * k1)
            k3 = fn(x + s / 2, y + s / 2 * k2)
            k4 = fn(x + s, y + s * k3)
            y = y + s / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            x = x + s
            if abs(y) > 1e4:
                break
            pts.append((x, y))
        return pts

    back = march(-1, xlo)
    fwd = march(+1, xhi)
    return list(reversed(back)) + fwd[1:]


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
