"""Supply and demand on price-quantity axes: curves, equilibrium, shifts.

Straight lines: demand P = a - b Q (downward), supply P = c + d Q (upward).
Distinguishes a *shift* of a whole curve from a *movement along* it — the core
idea of the lesson.
"""

from __future__ import annotations

from drawn_board import style
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
            x_length=style.ANIM_WIDTH, y_length=style.ANIM_HEIGHT,
            axis_config={"color": self.color(None), "stroke_width": 3,
                         "include_ticks": True, "tip_width": 0.16, "tip_height": 0.16,
                         "font_size": 26, "include_numbers": True},
        )
        # the animation lives in the lower region; the top band is left clear for
        # the scene's formula so the two never overlap.
        self.axes.move_to(style.ANIM_CENTER)
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
        """Draw the TRUE line P = p_of_q(Q), clipped to the axes box.

        Clip along the line itself (find the Q-interval where 0 <= P <= p_max),
        never by clamping P — clamping would bend the line to a wrong slope, so
        the equilibrium dot would no longer sit on the drawn crossing.
        """
        from manim import Line

        k = p_of_q(0.0)
        m = p_of_q(1.0) - k  # slope dP/dQ (lines are straight)
        lo, hi = 0.0, self.q_max
        if abs(m) > 1e-9:
            qa = (0.0 - k) / m            # Q where P hits the bottom edge (0)
            qb = (self.p_max - k) / m     # Q where P hits the top edge (p_max)
            lo = max(lo, min(qa, qb))
            hi = min(hi, max(qa, qb))
        lo = min(max(lo, 0.0), self.q_max)
        hi = min(max(hi, 0.0), self.q_max)
        if hi <= lo:
            lo, hi = 0.0, self.q_max
        return Line(self.axes.c2p(lo, p_of_q(lo)), self.axes.c2p(hi, p_of_q(hi)),
                    color=self.color(color), stroke_width=_CURVE_STROKE)

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
        # if an equilibrium dot was marked, slide it to the new crossing
        if getattr(self, "_eq_dot", None) is not None:
            q, p = self._equilibrium()
            self.scene.play(self._eq_dot.animate.move_to(self.axes.c2p(q, p)),
                            run_time=run_time * 0.4)
        else:
            self.scene.wait(run_time * 0.4)

    @step
    def show_gap(self, run_time: float, price: float = 6.0, color: str = "red",
                 label: str = "surplus", **_):
        """At a given price, mark the gap between quantity demanded and supplied.

        A dashed line at the price, dots where it meets each curve, and a
        double-arrow between them — the visible surplus (price above
        equilibrium) or shortage (price below).
        """
        from manim import DashedLine, Dot, DoubleArrow, MathTex

        qd = (self.a - price) / self.b if self.b else 0.0
        qs = (price - self.c) / self.d if self.d else 0.0
        qd = min(max(qd, 0.0), self.q_max)
        qs = min(max(qs, 0.0), self.q_max)
        pline = DashedLine(self.axes.c2p(0, price), self.axes.c2p(max(qd, qs), price),
                           color=self.color(None), stroke_width=2)
        dd = Dot(self.axes.c2p(qd, price), color=self.color("orange"), radius=0.08)
        ds = Dot(self.axes.c2p(qs, price), color=self.color("blue"), radius=0.08)
        arrow = DoubleArrow(self.axes.c2p(qd, price), self.axes.c2p(qs, price),
                            color=self.color(color), buff=0.05, tip_length=0.18,
                            stroke_width=5)
        lbl = MathTex(rf"\text{{{label}}}", color=self.color(color),
                      font_size=LABEL_FONT_SIZE).next_to(arrow, _up(), buff=0.12)
        self.scene.play(_create(pline), _grow(dd), _grow(ds), run_time=run_time * 0.5)
        self.scene.play(_grow(arrow), _write(lbl), run_time=run_time * 0.5)

    @step
    def mark_points(self, run_time: float, curve: str = "demand", points: list = None,
                    color: str = "yellow", **_):
        """Drop labelled dots at given quantities on a curve, with dashed guides."""
        from manim import DashedLine, Dot, MathTex

        p_of_q = self._demand_p if curve == "demand" else self._supply_p
        pts = points or []
        seg = run_time / max(len(pts), 1)
        for spec in pts:
            q = float(spec["q"])
            p = p_of_q(q)
            dot = Dot(self.axes.c2p(q, p), color=self.color(color), radius=0.09)
            gx = DashedLine(self.axes.c2p(q, 0), self.axes.c2p(q, p),
                            color=self.color(None), stroke_width=2)
            gy = DashedLine(self.axes.c2p(0, p), self.axes.c2p(q, p),
                            color=self.color(None), stroke_width=2)
            anims = [_create(gx), _create(gy), _grow(dot)]
            if spec.get("label"):
                lbl = MathTex(spec["label"], color=self.color(color),
                              font_size=LABEL_FONT_SIZE).next_to(dot, _up() + _right(), buff=0.12)
                anims.append(_write(lbl))
            self.scene.play(*anims, run_time=seg)

    @step
    def revenue_box(self, run_time: float, curve: str = "demand", q: float = 4.0,
                    color: str = "purple", label: str = None, **_):
        """Draw the total-revenue rectangle [0,Q] x [0,P] under a point on a curve."""
        from manim import MathTex, Polygon

        p_of_q = self._demand_p if curve == "demand" else self._supply_p
        p = p_of_q(float(q))
        box = Polygon(self.axes.c2p(0, 0), self.axes.c2p(q, 0),
                      self.axes.c2p(q, p), self.axes.c2p(0, p),
                      color=self.color(color), fill_opacity=0.3, stroke_width=3)
        anims = [_fade_in(box)]
        if label:
            lbl = MathTex(label, color=self.color(color),
                          font_size=LABEL_FONT_SIZE).move_to(self.axes.c2p(q / 2, p / 2))
            anims.append(_write(lbl))
        self.scene.play(*anims, run_time=run_time)

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


def _fade_in(m):
    from manim import FadeIn

    return FadeIn(m)


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
