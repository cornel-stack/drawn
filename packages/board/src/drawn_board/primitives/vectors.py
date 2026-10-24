"""2D labelled vectors on optional axes: draw, components, add, dot product."""

from __future__ import annotations

import numpy as np

from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import GLYPH_STROKE_WIDTH, LABEL_FONT_SIZE

_VEC_STROKE = 7
_TIP_RATIO = 0.22


@register("vectors")
class Vectors(Primitive):
    """Labelled vectors, optionally on a coordinate frame.

    params:
      axes: {x: [min, max, step], y: [min, max, step]}   # optional
      scale: units-per-coordinate when no axes (default 1.0)
      origin: [x, y] when no axes (default [0, 0])
      vectors: {name: {to: [x, y], color: <accent>, label: "A"}}
    """

    is_3d = False

    def build(self) -> None:
        self._specs = self.params.get("vectors", {})
        self._arrows: dict = {}
        self._labels: dict = {}
        self._coords: dict = {}

        axes_cfg = self.params.get("axes")
        if axes_cfg:
            from manim import Axes

            self.axes = Axes(
                x_range=axes_cfg.get("x", [-1, 5, 1]),
                y_range=axes_cfg.get("y", [-1, 4, 1]),
                x_length=axes_cfg.get("x_length", 7.5),
                y_length=axes_cfg.get("y_length", 5.0),
                axis_config={"color": self.color(None), "stroke_width": 3,
                             "include_ticks": True, "tip_width": 0.18, "tip_height": 0.18},
            )
            self.axes.move_to(axes_cfg.get("center", [0, -0.4, 0]))
            self._c2p = self.axes.c2p
            self.scene.add(self.axes)
        else:
            self.axes = None
            self.scale = float(self.params.get("scale", 1.0))
            self._origin = np.array([*self.params.get("origin", [0, 0]), 0.0])

        self.origin = self._c2p(0, 0)

    # -- helpers -----------------------------------------------------------

    def _c2p(self, x, y):  # overwritten when axes exist
        return self._origin + np.array([x * self.scale, y * self.scale, 0.0])

    def _arrow(self, start, end, color):
        from manim import Arrow

        return Arrow(start, end, color=self.color(color), buff=0,
                     stroke_width=_VEC_STROKE, max_tip_length_to_length_ratio=_TIP_RATIO)

    def _label(self, text, point, color, direction=None):
        from manim import Text

        lbl = Text(text, font=self.channel.font.handwriting, weight="BOLD",
                   font_size=LABEL_FONT_SIZE, color=self.color(color),
                   stroke_width=GLYPH_STROKE_WIDTH, stroke_color=self.color(color))
        if direction is not None:
            lbl.next_to(point, direction=direction, buff=0.18)
        else:
            lbl.move_to(point)
        return lbl

    # -- steps -------------------------------------------------------------

    @step
    def draw(self, run_time: float, name: str = None, **_):
        from manim import GrowArrow, Write

        spec = self._specs[name]
        x, y = spec["to"]
        self._coords[name] = (x, y)
        arrow = self._arrow(self.origin, self._c2p(x, y), spec.get("color"))
        self._arrows[name] = arrow
        anims = [GrowArrow(arrow)]
        if spec.get("label"):
            lbl = self._label(spec["label"], arrow.get_end(), spec.get("color"),
                              direction=_unit(arrow))
            self._labels[name] = lbl
            anims.append(Write(lbl))
        self.scene.play(*anims, run_time=run_time)

    @step
    def components(self, run_time: float, name: str = None,
                   cx: str = "blue", cy: str = "orange", **_):
        """Drop `name` onto the axes as component arrows Ax (x) + Ay (y)."""
        from manim import DashedLine, GrowArrow, Write

        x, y = self._coords[name]
        foot_x = self._c2p(x, 0)
        tip = self._c2p(x, y)
        guide = DashedLine(foot_x, tip, color=self.color(None), stroke_width=2)
        ax = self._arrow(self.origin, foot_x, cx)
        ay = self._arrow(foot_x, tip, cy)
        lx = self._label("A_x", foot_x, cx, direction=_down())
        ly = self._label("A_y", (foot_x + tip) / 2, cy, direction=_right())
        self.scene.play(_create(guide), run_time=run_time * 0.25)
        self.scene.play(GrowArrow(ax), Write(lx), run_time=run_time * 0.4)
        self.scene.play(GrowArrow(ay), Write(ly), run_time=run_time * 0.35)

    @step
    def add_tip_to_tail(self, run_time: float, a: str = None, b: str = None,
                        result: str = None, color: str = None, **_):
        from manim import GrowArrow

        va, vb = self._arrows[a], self._arrows[b]
        shifted = vb.copy().shift(va.get_end() - vb.get_start())
        res = self._arrow(va.get_start(), shifted.get_end(), color)
        self._arrows[result or "sum"] = res
        self.scene.play(vb.animate.become(shifted), run_time=run_time * 0.5)
        self.scene.play(GrowArrow(res), run_time=run_time * 0.5)

    @step
    def dot_product(self, run_time: float, a: str = None, b: str = None,
                    color: str = "green", **_):
        """Show the angle between a and b and the projection of b onto a."""
        from manim import Angle, DashedLine, Line

        va, vb = self._arrows[a], self._arrows[b]
        arc = Angle(Line(va.get_start(), va.get_end()),
                    Line(vb.get_start(), vb.get_end()),
                    radius=0.8, color=self.color(color))
        theta = self._label(r"\theta", arc.point_from_proportion(0.5), color)
        # projection of b's tip onto a's direction
        d = va.get_end() - va.get_start()
        d = d / np.linalg.norm(d)
        proj_len = float(np.dot(vb.get_end() - vb.get_start(), d))
        foot = va.get_start() + d * proj_len
        drop = DashedLine(vb.get_end(), foot, color=self.color(None), stroke_width=2)
        projseg = Line(va.get_start(), foot, color=self.color(color), stroke_width=9)
        self.scene.play(_create(arc), _fade_in(theta), run_time=run_time * 0.4)
        self.scene.play(_create(drop), run_time=run_time * 0.3)
        self.scene.play(_create(projseg), run_time=run_time * 0.3)


def _create(m):
    from manim import Create

    return Create(m)


def _fade_in(m):
    from manim import FadeIn

    return FadeIn(m)


def _unit(arrow):
    v = arrow.get_end() - arrow.get_start()
    n = np.linalg.norm(v)
    if n == 0:
        from manim import UP

        return UP
    return v / n


def _down():
    from manim import DOWN

    return DOWN


def _right():
    from manim import RIGHT

    return RIGHT
