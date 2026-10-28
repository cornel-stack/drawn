"""Indifference curves and the budget constraint on two-good axes.

Convex indifference curves are level sets of a Cobb-Douglas utility
U(x, y) = x^a · y^b; the budget line is p_x x + p_y y = m. The utility-maximising
bundle sits where the highest attainable indifference curve just touches the
budget line (the tangency, MRS = price ratio). Reused across the consumer-choice
series (income/substitution effects, labour-leisure).
"""

from __future__ import annotations

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_CURVE_STROKE = 6


@register("indifference")
class Indifference(Primitive):
    """params:
      x_max, y_max: axis ranges (default 10, 10)
      utility: {a, b}        # Cobb-Douglas exponents (default 1, 1)
      budget: {px, py, m}    # price of x, price of y, income
      x_label, y_label: axis names (default "x", "y")

    steps: curve, budget_line, optimum, budget_shift.
    """

    is_3d = False

    def build(self) -> None:
        from manim import Axes

        self.x_max = float(self.params.get("x_max", 10))
        self.y_max = float(self.params.get("y_max", 10))
        u = self.params.get("utility", {"a": 1.0, "b": 1.0})
        self.a, self.b = float(u["a"]), float(u["b"])
        bud = self.params.get("budget", {"px": 1.0, "py": 1.0, "m": 10.0})
        self.px, self.py, self.m = float(bud["px"]), float(bud["py"]), float(bud["m"])

        self.axes = Axes(
            x_range=[0, self.x_max, 1], y_range=[0, self.y_max, 1],
            x_length=style.ANIM_WIDTH, y_length=style.ANIM_HEIGHT,
            axis_config={"color": self.color(None), "stroke_width": 3,
                         "include_ticks": True, "tip_width": 0.16, "tip_height": 0.16,
                         "font_size": 24},
        )
        self.axes.move_to(style.ANIM_CENTER)
        self.scene.add(self.axes)
        self.scene.add(self._axis_label(self.params.get("x_label", "x"),
                                        self.axes.x_axis.get_end(), _right()))
        self.scene.add(self._axis_label(self.params.get("y_label", "y"),
                                        self.axes.y_axis.get_end(), _up()))
        self._curves: dict = {}

    # -- geometry ----------------------------------------------------------

    def _optimum(self):
        """Cobb-Douglas tangency: x* = a/(a+b)·m/px, y* = b/(a+b)·m/py."""
        s = self.a + self.b
        x = (self.a / s) * (self.m / self.px)
        y = (self.b / s) * (self.m / self.py)
        return x, y

    def _util_at(self, x, y):
        return (x ** self.a) * (y ** self.b)

    def _curve_points(self, util):
        """Points along x^a y^b = util, clipped to the axes box (0, y_max]."""
        # y = (util / x^a)^(1/b); y = y_max at x_lo, y small at x = x_max.
        x_lo = (util / (self.y_max ** self.b)) ** (1.0 / self.a)
        x_lo = max(x_lo, 0.05)
        xs = [x_lo + (self.x_max - x_lo) * i / 60.0 for i in range(61)]
        pts = []
        for x in xs:
            y = (util / (x ** self.a)) ** (1.0 / self.b)
            if 0 < y <= self.y_max:
                pts.append(self.axes.c2p(x, y))
        return pts

    def _axis_label(self, text, point, direction):
        # MathTex so subscripts like c_1, c_2 render properly (not literal "c_1")
        from manim import MathTex

        return MathTex(text, color=self.color(None), font_size=LABEL_FONT_SIZE + 6).next_to(
            point, direction=direction, buff=0.2)

    # -- steps -------------------------------------------------------------

    @step
    def curve(self, run_time: float, level: float = None, through_optimum: bool = False,
              color: str = "blue", label: str = None, **_):
        """Draw one indifference curve. `through_optimum` draws the curve that
        touches the budget line; otherwise `level` scales the optimum utility
        (e.g. 0.6 for a lower, unreachable-looking curve)."""
        from manim import Create, VMobject, Write

        if through_optimum:
            x, y = self._optimum()
            util = self._util_at(x, y)
        else:
            x, y = self._optimum()
            util = self._util_at(x, y) * float(level if level is not None else 1.0)
        pts = self._curve_points(util)
        curve = VMobject(color=self.color(color), stroke_width=_CURVE_STROKE)
        curve.set_points_smoothly(pts)
        self._curves[label or f"U{len(self._curves)}"] = curve
        self.scene.play(Create(curve), run_time=run_time * (0.8 if label else 1.0))
        if label:
            from manim import MathTex

            lbl = MathTex(label, color=self.color(color),
                          font_size=LABEL_FONT_SIZE).next_to(pts[0], _up() + _right(), buff=0.1)
            self.scene.play(Write(lbl), run_time=run_time * 0.2)

    @step
    def budget_line(self, run_time: float, color: str = "orange", label: str = None, **_):
        """Draw the budget line p_x x + p_y y = m between its two intercepts."""
        from manim import Create, Line, MathTex, Write

        x_int = self.m / self.px      # all income on x
        y_int = self.m / self.py      # all income on y
        line = Line(self.axes.c2p(0, y_int), self.axes.c2p(x_int, 0),
                    color=self.color(color), stroke_width=_CURVE_STROKE + 1)
        self._budget = line
        self.scene.play(Create(line), run_time=run_time * (0.8 if label else 1.0))
        if label:
            lbl = MathTex(label, color=self.color(color),
                          font_size=LABEL_FONT_SIZE).next_to(
                self.axes.c2p(x_int, 0), _up() + _right(), buff=0.1)
            self.scene.play(Write(lbl), run_time=run_time * 0.2)

    @step
    def optimum(self, run_time: float, color: str = "green", label: str = "E", **_):
        """Mark the utility-maximising bundle: the tangency of the budget line and
        the highest attainable indifference curve, with dashed guides."""
        from manim import DashedLine, Dot, MathTex, Write

        x, y = self._optimum()
        dot = Dot(self.axes.c2p(x, y), color=self.color(color), radius=0.1)
        gx = DashedLine(self.axes.c2p(x, 0), self.axes.c2p(x, y),
                        color=self.color(None), stroke_width=2)
        gy = DashedLine(self.axes.c2p(0, y), self.axes.c2p(x, y),
                        color=self.color(None), stroke_width=2)
        xs = MathTex("x^*", color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            self.axes.c2p(x, 0), _down(), buff=0.12)
        ys = MathTex("y^*", color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            self.axes.c2p(0, y), _left(), buff=0.12)
        self.scene.play(_create(gx), _create(gy), run_time=run_time * 0.5)
        anims = [_grow(dot), Write(xs), Write(ys)]
        if label:
            elbl = MathTex(label, color=self.color(color),
                           font_size=LABEL_FONT_SIZE).next_to(dot, _up() + _right(), buff=0.1)
            anims.append(Write(elbl))
        self.scene.play(*anims, run_time=run_time * 0.5)

    @step
    def budget_shift(self, run_time: float, px: float = None, py: float = None,
                     m: float = None, color: str = "orange", **_):
        """Change a price or income and swing/shift the budget line to its new
        intercepts (for income- and substitution-effect lessons)."""
        from manim import Line

        if px is not None:
            self.px = float(px)
        if py is not None:
            self.py = float(py)
        if m is not None:
            self.m = float(m)
        new = Line(self.axes.c2p(0, self.m / self.py), self.axes.c2p(self.m / self.px, 0),
                   color=self.color(color), stroke_width=_CURVE_STROKE + 1)
        old = getattr(self, "_budget", None)
        if old is not None:
            self.scene.play(old.animate.become(new), run_time=run_time)
        else:
            self.scene.play(_create(new), run_time=run_time)
        self._budget = new


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
