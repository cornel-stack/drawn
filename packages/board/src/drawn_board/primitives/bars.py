"""Value bars that accumulate into a total, with negative-segment support.

Economics breakdowns: build a quantity (e.g. GDP) from stacked, labelled
segments; let a segment go **negative** (a notch that pulls the running total
down, as net exports do in a trade deficit); draw a separate total bar; and
drop a dashed reference level so several stacks that reach the same total by
different slicings can be compared side by side.

A value is mapped to frame height by ``value_max`` (the value that reaches the
top of the usable band) above a ``baseline_y`` zero line. Each named ``stack``
accumulates its segments at its own x. Reused across the macro/micro series.
"""

from __future__ import annotations

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_BAR_STROKE = 3


@register("bars")
class Bars(Primitive):
    """params:
      value_max: float    # value mapped to the top of the usable height
      baseline_y: float   # frame y of the zero line (default: bottom of anim band)
      height: float       # frame height spanning [0, value_max] (default ANIM_HEIGHT*0.9)
      bar_width: float    # width of each bar (default 1.0)

    steps: axis, segment, total, level.
    """

    is_3d = False

    def build(self) -> None:
        p = self.params
        self.value_max = float(p.get("value_max", 100.0))
        self.base_y = float(
            p.get("baseline_y", style.ANIM_CENTER[1] - style.ANIM_HEIGHT / 2 + 0.25)
        )
        self.h = float(p.get("height", style.ANIM_HEIGHT * 0.9))
        self.bar_w = float(p.get("bar_width", 1.0))
        self._top: dict = {}   # stack -> running top (frame y)
        self._x: dict = {}     # stack -> x centre (frame)

    # -- helpers -----------------------------------------------------------

    def _dy(self, value: float) -> float:
        return (float(value) / self.value_max) * self.h

    def _ensure(self, stack: str, x: float):
        if stack not in self._top:
            self._top[stack] = self.base_y
            self._x[stack] = float(x)

    def _bar(self, x, y_lo, y_hi, color, opacity):
        from manim import Rectangle

        rect = Rectangle(width=self.bar_w, height=max(abs(y_hi - y_lo), 1e-3))
        rect.move_to([x, (y_lo + y_hi) / 2, 0.0])
        rect.set_fill(self.color(color), opacity=opacity)
        rect.set_stroke(self.color(None), width=_BAR_STROKE)
        return rect

    def _text(self, s, color):
        from manim import Text

        return Text(s, font=self.channel.font.handwriting, weight="BOLD",
                    font_size=LABEL_FONT_SIZE - 4, color=self.color(color))

    # -- steps -------------------------------------------------------------

    @step
    def axis(self, run_time: float, label: str = None, **_):
        """Draw the zero baseline (and an optional axis caption)."""
        from manim import Line, Write

        x0 = style.ANIM_CENTER[0] - style.ANIM_WIDTH / 2
        x1 = style.ANIM_CENTER[0] + style.ANIM_WIDTH / 2
        base = Line([x0, self.base_y, 0], [x1, self.base_y, 0],
                    color=self.color(None), stroke_width=3)
        self.scene.play(_create(base), run_time=run_time * (0.7 if label else 1.0))
        if label:
            cap = self._text(label, None).next_to([x0, self.base_y, 0], _up() + _right(), buff=0.1)
            self.scene.play(Write(cap), run_time=run_time * 0.3)

    @step
    def segment(self, run_time: float, stack: str = "main", value: float = 0.0,
                color: str = "blue", label: str = None, x: float = 0.0,
                col_label: str = None, **_):
        """Add a segment of `value` to `stack`, stacking on its running top.

        A negative `value` draws downward (a notch that lowers the running
        total). `label` sits beside the segment; `col_label` (first segment
        only) captions the whole column below the baseline.
        """
        from manim import FadeIn, Write

        self._ensure(stack, x)
        x0 = self._x[stack]
        top = self._top[stack]
        dy = self._dy(value)
        rect = self._bar(x0, top, top + dy, color, 0.88)
        self._top[stack] = top + dy

        shift = (_up() if value >= 0 else _down()) * 0.15
        anims = [FadeIn(rect, shift=shift)]
        if label:
            lbl = self._text(label, color).next_to(rect, _right(), buff=0.12)
            anims.append(Write(lbl))
        if col_label:
            cap = self._text(col_label, None).next_to([x0, self.base_y, 0], _down(), buff=0.18)
            anims.append(Write(cap))
        self.scene.play(*anims, run_time=run_time)

    @step
    def total(self, run_time: float, stack: str = "main", color: str = "green",
              label: str = None, x: float = 0.0, **_):
        """Draw a solid total bar at `x` equal to the net height of `stack`."""
        from manim import DashedLine, FadeIn, Write

        top = self._top.get(stack, self.base_y)
        rect = self._bar(x, self.base_y, top, color, 0.95)
        link = DashedLine([self._x.get(stack, 0.0), top, 0], [x, top, 0],
                          color=self.color(None), stroke_width=2)
        anims = [_create(link), FadeIn(rect, shift=_up() * 0.15)]
        if label:
            lbl = self._text(label, color).next_to(rect, _up(), buff=0.12)
            anims.append(Write(lbl))
        self.scene.play(*anims, run_time=run_time)

    @step
    def level(self, run_time: float, value: float = 0.0, label: str = None,
              color: str = "green", **_):
        """Dashed horizontal reference line at `value` across the band."""
        from manim import DashedLine, Write

        y = self.base_y + self._dy(value)
        x0 = style.ANIM_CENTER[0] - style.ANIM_WIDTH / 2
        x1 = style.ANIM_CENTER[0] + style.ANIM_WIDTH / 2
        line = DashedLine([x0, y, 0], [x1, y, 0], color=self.color(color), stroke_width=3)
        self.scene.play(_create(line), run_time=run_time * (0.7 if label else 1.0))
        if label:
            lbl = self._text(label, color).next_to([x1, y, 0], _up() + _left(), buff=0.1)
            self.scene.play(Write(lbl), run_time=run_time * 0.3)


def _create(m):
    from manim import Create

    return Create(m)


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
