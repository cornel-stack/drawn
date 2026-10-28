"""Uniform circular motion: an object orbiting a circle with a tangent velocity
arrow and a centre-pointing (centripetal) acceleration arrow, plus the velocity
triangle showing that Δv points toward the centre.

The velocity is constant in length but ever-changing in direction, so there is
an acceleration even at constant speed — the heart of the centripetal-force
lesson. Reused across the rotational-motion series.
"""

from __future__ import annotations

import numpy as np

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_ARR_STROKE = 6
_TIP_RATIO = 0.3


@register("circular_motion")
class CircularMotion(Primitive):
    """params:
      center: [x, y]   # frame centre of the circle (default a little low)
      radius: float    # circle radius in frame units (default 1.8)

    steps: draw_circle, radius_line, start_orbit, velocity_triangle.
    """

    is_3d = False
    continuous_actions = {"start_orbit"}

    def build(self) -> None:
        c = self.params.get("center", [0.0, style.ANIM_CENTER[1]])
        self._centre = np.array([c[0], c[1], 0.0])
        self.r = float(self.params.get("radius", 1.8))
        self._theta = 0.0

    def _pt(self, th):
        return self._centre + self.r * np.array([np.cos(th), np.sin(th), 0.0])

    def _mlabel(self, tex, point, color, direction):
        from manim import MathTex

        return MathTex(tex, color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            point, direction=direction, buff=0.12)

    # -- steps -------------------------------------------------------------

    @step
    def draw_circle(self, run_time: float, color: str = None, label: str = None, **_):
        """Draw the circular path and its centre."""
        from manim import Circle, Create, Dot

        col = self.color(None) if color in (None, "white", "ink") else self.color(color)
        self.circle = Circle(radius=self.r, color=col, stroke_width=4).move_to(self._centre)
        self.hub = Dot(self._centre, radius=0.06, color=self.color(None))
        self.scene.play(Create(self.circle), run_time=run_time)
        self.scene.add(self.hub)

    @step
    def radius_line(self, run_time: float, color: str = "yellow", label: str = "r",
                    angle: float = 0.6, **_):
        """Draw the radius out to the rim (fixed angle), labelled."""
        from manim import Create, Line, Write

        end = self._pt(angle)
        line = Line(self._centre, end, color=self.color(color), stroke_width=3)
        self.scene.play(Create(line), run_time=run_time * 0.7)
        if label:
            mid = (self._centre + end) / 2
            self.scene.play(Write(self._mlabel(label, mid, color, _up())),
                            run_time=run_time * 0.3)

    @step
    def start_orbit(self, run_time: float, rate: float = 0.9, v_color: str = "blue",
                    a_color: str = "red", v_len: float = 1.0, a_len: float = 0.8, **_):
        """Orbit the object, with a live tangent velocity arrow and a live
        centre-pointing acceleration arrow (continuous to the scene end)."""
        from manim import Arrow, Dot, VGroup

        def mk_v(th):
            p = self._pt(th)
            tang = np.array([-np.sin(th), np.cos(th), 0.0])  # counter-clockwise
            return Arrow(p, p + tang * v_len, buff=0, color=self.color(v_color),
                         stroke_width=_ARR_STROKE, max_tip_length_to_length_ratio=_TIP_RATIO)

        def mk_a(th):
            p = self._pt(th)
            inward = self._centre - p
            inward = inward / np.linalg.norm(inward)
            return Arrow(p, p + inward * a_len, buff=0, color=self.color(a_color),
                         stroke_width=_ARR_STROKE, max_tip_length_to_length_ratio=_TIP_RATIO)

        obj = Dot(self._pt(self._theta), radius=0.09, color=self.color(None))
        varr = mk_v(self._theta)
        aarr = mk_a(self._theta)
        vlbl = self._mlabel("v", varr.get_end(), v_color, _up())
        albl = self._mlabel("a_c", aarr.get_end(), a_color, _down())
        grp = VGroup(obj, varr, aarr)

        def upd(m, dt):
            self._theta += rate * dt
            obj.move_to(self._pt(self._theta))
            varr.become(mk_v(self._theta))
            aarr.become(mk_a(self._theta))

        self.scene.play(_grow(obj), _grow(varr), _grow(aarr), run_time=run_time * 0.35)
        from manim import Write

        self.scene.play(Write(vlbl), Write(albl), run_time=run_time * 0.15)
        grp.add_updater(upd)
        self.scene.add(grp)
        self.mark_continuous(0.0, 1e9)
        self.scene.wait(run_time * 0.5)

    @step
    def velocity_triangle(self, run_time: float, v_color: str = "blue",
                          dv_color: str = "orange", **_):
        """The velocity triangle: two equal-length velocity vectors and their
        difference Δv, which points toward the centre."""
        from manim import Arrow, GrowArrow, Write

        tail = self._centre + np.array([self.r + 1.3, 0.0, 0.0])
        d1 = np.array([0.4, 1.0, 0.0]); d1 /= np.linalg.norm(d1)
        d2 = np.array([-0.4, 1.0, 0.0]); d2 /= np.linalg.norm(d2)
        v1 = Arrow(tail, tail + d1 * 1.2, buff=0, color=self.color(v_color),
                   stroke_width=_ARR_STROKE, max_tip_length_to_length_ratio=_TIP_RATIO)
        v2 = Arrow(tail, tail + d2 * 1.2, buff=0, color=self.color(v_color),
                   stroke_width=_ARR_STROKE, max_tip_length_to_length_ratio=_TIP_RATIO)
        dv = Arrow(v1.get_end(), v2.get_end(), buff=0, color=self.color(dv_color),
                   stroke_width=_ARR_STROKE, max_tip_length_to_length_ratio=_TIP_RATIO)
        self.scene.play(GrowArrow(v1), GrowArrow(v2), run_time=run_time * 0.5)
        self.scene.play(GrowArrow(dv),
                        Write(self._mlabel(r"\Delta v", dv.get_center(), dv_color, _up())),
                        run_time=run_time * 0.5)


def _grow(m):
    from manim import GrowFromCenter

    return GrowFromCenter(m)


def _up():
    from manim import UP

    return UP


def _down():
    from manim import DOWN

    return DOWN
