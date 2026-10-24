"""3D labelled vectors: draw and cross product (right-hand rule)."""

from __future__ import annotations

import numpy as np

from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_ARROW = dict(thickness=0.03, base_radius=0.12, height=0.3)


@register("vectors3d")
class Vectors3D(Primitive):
    """Vectors in 3D sharing the origin.

    params:
      vectors: {name: {to: [x, y, z], color: <accent>, label: "A"}}
      show_axes: bool (default true)
    """

    is_3d = True

    def build(self) -> None:
        self._specs = self.params.get("vectors", {})
        self._arrows: dict = {}
        self._vecs: dict = {}
        self.origin = np.array([0.0, 0.0, 0.0])
        if self.params.get("show_axes", True):
            from manim import ThreeDAxes

            self.axes = ThreeDAxes(
                x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[-3, 3, 1],
                x_length=6, y_length=6, z_length=6,
            )
            self.axes.set_stroke(width=2)
            self.scene.add(self.axes)

    def _arrow(self, start, end, color):
        from manim import Arrow3D

        return Arrow3D(start, end, color=self.color(color), **_ARROW)

    def _label(self, tex, point, color):
        from manim import MathTex

        lbl = MathTex(tex, color=self.color(color), font_size=LABEL_FONT_SIZE)
        lbl.move_to(point)
        self.scene.add_fixed_orientation_mobjects(lbl)
        return lbl

    @step
    def draw(self, run_time: float, name: str = None, **_):
        from manim import Create

        spec = self._specs[name]
        v = np.array(spec["to"], dtype=float)
        self._vecs[name] = v
        arrow = self._arrow(self.origin, v, spec.get("color"))
        self._arrows[name] = arrow
        self.scene.play(Create(arrow), run_time=run_time)
        if spec.get("label"):
            self._label(spec["label"], v * 1.12, spec.get("color"))

    @step
    def cross(self, run_time: float, a: str = None, b: str = None,
              result: str = "AxB", color: str = "green", label: str = r"A\times B", **_):
        """Draw a × b (perpendicular, right-hand rule) with a curl from a to b."""
        from manim import ArcBetweenPoints, Create

        va, vb = self._vecs[a], self._vecs[b]
        c = np.cross(va, vb)
        n = np.linalg.norm(c)
        if n > 1e-9:
            c = c / n * max(1.5, min(np.linalg.norm(va), np.linalg.norm(vb)))
        arrow = self._arrow(self.origin, c, color)
        self._arrows[result] = arrow
        # right-hand curl from a towards b
        curl = ArcBetweenPoints(va * 0.5, vb * 0.5, angle=np.pi / 2,
                                color=self.color(color), stroke_width=4)
        self.scene.play(Create(curl), run_time=run_time * 0.4)
        self.scene.play(Create(arrow), run_time=run_time * 0.6)
        self._label(label, c * 1.12, color)
