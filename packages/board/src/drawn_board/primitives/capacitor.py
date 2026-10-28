"""A parallel-plate capacitor: two plates, the charge on them, the uniform field
between, and an optional dielectric slab.

The field between the plates is uniform (equally spaced parallel arrows), which is
what makes the capacitor the cleanest place to see the link between charge,
potential difference and stored energy. Reused across the capacitor and RC-circuit
series.
"""

from __future__ import annotations

import numpy as np

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_PLATE_STROKE = 7
_ARR_STROKE = 5


@register("capacitor")
class Capacitor(Primitive):
    """params:
      separation: gap between the plates in frame units (default 2.4)
      height: plate height in frame units (default 2.6)
      center: [x, y] (default the animation centre)

    steps: draw_plates, charge, field, dielectric.
    """

    is_3d = False

    def build(self) -> None:
        c = self.params.get("center", [style.ANIM_CENTER[0], style.ANIM_CENTER[1]])
        self._c = np.array([c[0], c[1], 0.0])
        self.sep = float(self.params.get("separation", 2.4))
        self.h = float(self.params.get("height", 2.6))
        self._xl = self._c[0] - self.sep / 2.0
        self._xr = self._c[0] + self.sep / 2.0
        self._yt = self._c[1] + self.h / 2.0
        self._yb = self._c[1] - self.h / 2.0
        self._field = None

    def _mlabel(self, tex, point, color, direction):
        from manim import MathTex

        return MathTex(tex, color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            point, direction=direction, buff=0.14)

    # -- steps -------------------------------------------------------------

    @step
    def draw_plates(self, run_time: float, color: str = None, **_):
        """Two vertical conducting plates, a gap apart."""
        from manim import Create, Line

        col = self.color(None) if color in (None, "white", "ink") else self.color(color)
        self.left = Line([self._xl, self._yb, 0], [self._xl, self._yt, 0],
                         color=col, stroke_width=_PLATE_STROKE)
        self.right = Line([self._xr, self._yb, 0], [self._xr, self._yt, 0],
                          color=col, stroke_width=_PLATE_STROKE)
        self.scene.play(Create(self.left), Create(self.right), run_time=run_time)

    @step
    def charge(self, run_time: float, pos_color: str = "red", neg_color: str = "blue",
               n: int = 4, labels: bool = True, **_):
        """Mark +Q on the left plate and -Q on the right, with a few +/- signs."""
        from manim import MathTex, VGroup, Write

        plus, minus = VGroup(), VGroup()
        for i in range(int(n)):
            y = self._yb + self.h * (i + 0.5) / int(n)
            plus.add(MathTex("+", color=self.color(pos_color), font_size=LABEL_FONT_SIZE)
                     .move_to([self._xl - 0.22, y, 0]))
            minus.add(MathTex("-", color=self.color(neg_color), font_size=LABEL_FONT_SIZE)
                      .move_to([self._xr + 0.22, y, 0]))
        anims = [Write(plus), Write(minus)]
        if labels:
            anims.append(Write(self._mlabel("+Q", [self._xl, self._yt, 0], pos_color, _up())))
            anims.append(Write(self._mlabel("-Q", [self._xr, self._yt, 0], neg_color, _up())))
        self.scene.play(*anims, run_time=run_time)

    @step
    def field(self, run_time: float, color: str = "purple", rows: int = 4,
              label: str = None, **_):
        """Uniform field arrows from the positive plate to the negative plate."""
        from manim import Arrow, GrowArrow, VGroup

        arrows = VGroup()
        for i in range(int(rows)):
            y = self._yb + self.h * (i + 0.5) / int(rows)
            arrows.add(Arrow([self._xl + 0.12, y, 0], [self._xr - 0.12, y, 0], buff=0,
                             color=self.color(color), stroke_width=_ARR_STROKE,
                             max_tip_length_to_length_ratio=0.12))
        self._field = arrows
        self.scene.play(*[GrowArrow(a) for a in arrows], run_time=run_time * (0.8 if label else 1.0))
        if label:
            from manim import Write

            self.scene.play(Write(self._mlabel(label, [self._c[0], self._yb, 0], color, _down())),
                            run_time=run_time * 0.2)

    @step
    def dielectric(self, run_time: float, color: str = "green", label: str = "\\kappa",
                   weaken: float = 0.55, **_):
        """Slide a dielectric slab between the plates; the bound charges it develops
        partly cancel the field, so the arrows shorten by the factor `weaken`."""
        from manim import Rectangle, Write

        slab = Rectangle(width=self.sep - 0.3, height=self.h - 0.2,
                         color=self.color(color), fill_opacity=0.22,
                         stroke_width=2).move_to(self._c)
        self.scene.play(_fade_in(slab), run_time=run_time * 0.45)
        if self._field is not None:
            from manim import Arrow, VGroup

            shrunk = VGroup()
            for i in range(len(self._field)):
                y = self._yb + self.h * (i + 0.5) / len(self._field)
                half = (self.sep - 0.24) * 0.5 * float(weaken)
                shrunk.add(Arrow([self._c[0] - half, y, 0], [self._c[0] + half, y, 0], buff=0,
                                 color=self._field[0].get_color(), stroke_width=_ARR_STROKE,
                                 max_tip_length_to_length_ratio=0.14))
            self.scene.play(self._field.animate.become(shrunk), run_time=run_time * 0.35)
        lbl = self._mlabel(label, self._c + np.array([0.0, 0.0, 0.0]), color, _up() * 0)
        lbl.move_to(self._c)
        self.scene.play(Write(lbl), run_time=run_time * 0.2)


def _fade_in(m):
    from manim import FadeIn

    return FadeIn(m)


def _up():
    from manim import UP

    return UP


def _down():
    from manim import DOWN

    return DOWN
