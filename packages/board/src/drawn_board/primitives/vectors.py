"""2D labelled-vector primitive: draw, rotate, add tip-to-tail."""

from __future__ import annotations

from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import GLYPH_STROKE_WIDTH, LABEL_FONT_SIZE


@register("vectors")
class Vectors(Primitive):
    """A set of labelled vectors sharing an origin.

    params:
      origin: [x, y] (default [0, 0])
      vectors: {name: {to: [x, y], color: <accent>, label: "v"}}
    """

    is_3d = False

    def build(self) -> None:
        import numpy as np

        self.origin = np.array([*self.params.get("origin", [0, 0]), 0], dtype=float)
        self._specs = self.params.get("vectors", {})
        self._arrows: dict = {}
        self._labels: dict = {}

    def _make_arrow(self, spec):
        import numpy as np
        from manim import Arrow

        tip = self.origin + np.array([*spec["to"], 0], dtype=float)
        return Arrow(
            self.origin, tip, color=self.color(spec.get("color")),
            buff=0, stroke_width=6, max_tip_length_to_length_ratio=0.25,
        )

    @step
    def draw(self, run_time: float, name: str = None, **_):
        from manim import GrowArrow, Text, Write

        spec = self._specs[name]
        arrow = self._make_arrow(spec)
        self._arrows[name] = arrow
        anims = [GrowArrow(arrow)]
        if spec.get("label"):
            label = Text(
                spec["label"], font=self.channel.font.handwriting, weight="BOLD",
                font_size=LABEL_FONT_SIZE, color=self.color(spec.get("color")),
                stroke_width=GLYPH_STROKE_WIDTH, stroke_color=self.color(spec.get("color")),
            )
            label.next_to(arrow.get_end(), direction=_normalized_offset(arrow))
            self._labels[name] = label
            anims.append(Write(label))
        self.scene.play(*anims, run_time=run_time)

    @step
    def rotate(self, run_time: float, name: str = None, angle: float = 90, **_):
        import numpy as np
        from manim import Rotate

        arrow = self._arrows[name]
        self.scene.play(
            Rotate(arrow, angle=np.deg2rad(angle), about_point=self.origin),
            run_time=run_time,
        )

    @step
    def add_tip_to_tail(self, run_time: float, a: str = None, b: str = None,
                        result: str = None, color: str = None, **_):
        """Translate vector b to the tip of a and draw the resultant."""
        from manim import Arrow

        va = self._arrows[a]
        vb = self._arrows[b]
        shifted = vb.copy().shift(va.get_end() - vb.get_start())
        res = Arrow(
            va.get_start(), shifted.get_end(), color=self.color(color), buff=0,
            stroke_width=6, max_tip_length_to_length_ratio=0.25,
        )
        self._arrows[result or "sum"] = res
        self.scene.play(vb.animate.become(shifted), run_time=run_time * 0.5)
        from manim import GrowArrow

        self.scene.play(GrowArrow(res), run_time=run_time * 0.5)


def _normalized_offset(arrow):
    import numpy as np

    v = arrow.get_end() - arrow.get_start()
    n = np.linalg.norm(v)
    if n == 0:
        from manim import UP

        return UP
    return v / n
