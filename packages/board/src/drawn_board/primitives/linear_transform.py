"""A 2x2 matrix acting on the plane: grid, basis vectors, the column picture.

Reused across linear-algebra lessons — systems (the column picture of A x = b),
linear maps, eigenvectors, determinants as area scaling, change of basis. A
lesson triggers the actions below via ``{id}`` placeholders.

params:
  x_range, y_range: plane extent in grid units (default [-6, 6], [-4, 4])
  matrix: [[a, b], [c, d]] — its columns are the images of the basis vectors
"""

from __future__ import annotations

import numpy as np

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_VEC_STROKE = 6
_TIP = 0.25


@register("linear_transform")
class LinearTransform(Primitive):
    is_3d = False

    def build(self) -> None:
        from manim import NumberPlane

        p = self.params
        self.xr = p.get("x_range", [-6, 6])
        self.yr = p.get("y_range", [-4, 4])
        xs, ys = self.xr[1] - self.xr[0], self.yr[1] - self.yr[0]
        # keep grid squares square and fit the lower animation region, leaving the
        # top band clear for the scene's formula.
        unit = min(style.ANIM_WIDTH / xs, style.ANIM_HEIGHT / ys)
        self.plane = NumberPlane(
            x_range=[self.xr[0], self.xr[1], 1],
            y_range=[self.yr[0], self.yr[1], 1],
            x_length=xs * unit,
            y_length=ys * unit,
            background_line_style={
                "stroke_color": self.color(None),
                "stroke_width": 1,
                "stroke_opacity": 0.35,
            },
            axis_config={"stroke_color": self.color(None), "stroke_width": 2.5},
        )
        self.plane.move_to(style.ANIM_CENTER)
        self.scene.add(self.plane)
        self.matrix = np.array(p.get("matrix", [[1, 0], [0, 1]]), dtype=float)
        self._basis: dict = {}

    # -- helpers -----------------------------------------------------------

    def _pt(self, x, y):
        return self.plane.c2p(x, y)

    def _arrow(self, x, y, color, x0=0.0, y0=0.0):
        from manim import Arrow

        return Arrow(
            self._pt(x0, y0), self._pt(x, y), buff=0,
            color=self.color(color), stroke_width=_VEC_STROKE,
            tip_length=_TIP, max_tip_length_to_length_ratio=0.3,
        )

    def _label(self, tex, x, y, color, shift):
        from manim import MathTex

        return MathTex(tex, color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            self._pt(x, y), direction=shift, buff=0.12)

    # -- steps -------------------------------------------------------------

    @step
    def draw_basis(self, run_time: float, i_color: str = "blue", j_color: str = "green", **_):
        """Draw the unit basis vectors i-hat = (1,0) and j-hat = (0,1)."""
        from manim import RIGHT, UP, GrowArrow, Write

        i = self._arrow(1, 0, i_color)
        j = self._arrow(0, 1, j_color)
        self._basis["i"], self._basis["j"] = i, j
        self.scene.play(GrowArrow(i), GrowArrow(j), run_time=run_time * 0.6)
        self.scene.play(
            Write(self._label(r"\hat{\imath}", 1, 0, i_color, _down() + RIGHT)),
            Write(self._label(r"\hat{\jmath}", 0, 1, j_color, _left() + UP)),
            run_time=run_time * 0.4,
        )

    @step
    def apply_matrix(self, run_time: float, matrix=None, **_):
        """Animate the whole grid (and basis) deforming under the matrix."""
        from manim import ApplyMatrix

        m = np.array(matrix, dtype=float) if matrix is not None else self.matrix
        self.matrix = m
        movers = [self.plane, *self._basis.values()]
        self.scene.play(
            *[ApplyMatrix(m, mob, about_point=self._pt(0, 0)) for mob in movers],
            run_time=run_time,
        )

    @step
    def columns(self, run_time: float, matrix=None, c1_color: str = "blue",
                c2_color: str = "green", labels=None, **_):
        """Draw the two column vectors of the matrix from the origin."""
        from manim import DOWN, UP, GrowArrow, Write

        m = np.array(matrix, dtype=float) if matrix is not None else self.matrix
        self.matrix = m
        self.col1 = self._arrow(m[0, 0], m[1, 0], c1_color)
        self.col2 = self._arrow(m[0, 1], m[1, 1], c2_color)
        self.scene.play(GrowArrow(self.col1), GrowArrow(self.col2), run_time=run_time * 0.7)
        if labels:
            self.scene.play(
                Write(self._label(labels[0], m[0, 0], m[1, 0], c1_color, DOWN)),
                Write(self._label(labels[1], m[0, 1], m[1, 1], c2_color, UP)),
                run_time=run_time * 0.3,
            )

    @step
    def vector(self, run_time: float, x: float = 0, y: float = 0, color: str = "orange",
               label: str = None, **_):
        """Draw an arbitrary target vector b from the origin."""
        from manim import RIGHT, GrowArrow, Write

        arr = self._arrow(x, y, color)
        self.scene.play(GrowArrow(arr), run_time=run_time * (0.7 if label else 1.0))
        if label:
            self.scene.play(Write(self._label(label, x, y, color, RIGHT)),
                            run_time=run_time * 0.3)

    @step
    def combo(self, run_time: float, matrix=None, x: float = 1, y: float = 1,
              c1_color: str = "blue", c2_color: str = "green", **_):
        """Show x*col1 then + y*col2 tip-to-tail, landing on the target b."""
        from manim import GrowArrow

        m = np.array(matrix, dtype=float) if matrix is not None else self.matrix
        # x * column 1, from the origin
        xc = self._arrow(x * m[0, 0], x * m[1, 0], c1_color)
        self.scene.play(GrowArrow(xc), run_time=run_time * 0.5)
        # y * column 2, laid tip-to-tail from the end of x*col1
        start = (x * m[0, 0], x * m[1, 0])
        end = (start[0] + y * m[0, 1], start[1] + y * m[1, 1])
        yc = self._arrow(end[0], end[1], c2_color, x0=start[0], y0=start[1])
        self.scene.play(GrowArrow(yc), run_time=run_time * 0.5)

    @step
    def span_demo(self, run_time: float, matrix=None, color: str = "green", **_):
        """Dot the plane with reachable points to show the columns span it."""
        from manim import Dot, VGroup

        m = np.array(matrix, dtype=float) if matrix is not None else self.matrix
        dots = VGroup()
        for x in (-1.0, 0.0, 1.0, 2.0):
            for y in (-1.0, 0.0, 1.0, 2.0):
                px = x * m[0, 0] + y * m[0, 1]
                py = x * m[1, 0] + y * m[1, 1]
                if self.xr[0] <= px <= self.xr[1] and self.yr[0] <= py <= self.yr[1]:
                    dots.add(Dot(self._pt(px, py), radius=0.045,
                                 color=self.color(color), fill_opacity=0.6))
        self.scene.play(_fade_in(self.scene, dots), run_time=run_time)


def _fade_in(scene, mob):
    from manim import FadeIn

    return FadeIn(mob)


def _down():
    from manim import DOWN

    return DOWN


def _left():
    from manim import LEFT

    return LEFT
