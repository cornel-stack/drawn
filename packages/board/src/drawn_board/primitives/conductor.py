"""A current-carrying wire: free electrons drifting slowly under a field.

Shows the two separate motions inside a metal — the fast random thermal motion
and the slow net drift that constitutes the current — and the conventional
current arrow, which points opposite to the electron drift. Used for the
current / resistance / Ohm's-law lessons.
"""

from __future__ import annotations

import numpy as np

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_WIRE_STROKE = 4
_ARR_STROKE = 6


@register("conductor")
class Conductor(Primitive):
    """params:
      length: wire length in frame units (default 6.0)
      height: wire channel height (default 1.4)
      n: number of electrons (default 10)
      center: [x, y] (default the animation centre)

    steps: draw_wire, electrons, field, drift, current_arrow.
    """

    is_3d = False

    def build(self) -> None:
        c = self.params.get("center", [style.ANIM_CENTER[0], style.ANIM_CENTER[1]])
        self._c = np.array([c[0], c[1], 0.0])
        self.L = float(self.params.get("length", 6.0))
        self.H = float(self.params.get("height", 1.4))
        self.n = int(self.params.get("n", 10))
        self._xl = self._c[0] - self.L / 2.0
        self._xr = self._c[0] + self.L / 2.0
        self._electrons = None
        # deterministic pseudo-scatter (no RNG: argless Random is unavailable)
        self._offsets = [((i * 2654435761) % 1000) / 1000.0 for i in range(self.n)]

    def _mlabel(self, tex, point, color, direction):
        from manim import MathTex

        return MathTex(tex, color=self.color(color), font_size=LABEL_FONT_SIZE).next_to(
            point, direction=direction, buff=0.14)

    # -- steps -------------------------------------------------------------

    @step
    def draw_wire(self, run_time: float, color: str = None, **_):
        """The wire as a horizontal channel (two rails)."""
        from manim import Create, Line, VGroup

        col = self.color(None) if color in (None, "white", "ink") else self.color(color)
        top = Line([self._xl, self._c[1] + self.H / 2, 0], [self._xr, self._c[1] + self.H / 2, 0],
                   color=col, stroke_width=_WIRE_STROKE)
        bot = Line([self._xl, self._c[1] - self.H / 2, 0], [self._xr, self._c[1] - self.H / 2, 0],
                   color=col, stroke_width=_WIRE_STROKE)
        self._rails = VGroup(top, bot)
        self.scene.play(Create(top), Create(bot), run_time=run_time)

    @step
    def electrons(self, run_time: float, color: str = "blue", label: str = None, **_):
        """Scatter free electrons (negative charges) through the wire."""
        from manim import Dot, VGroup

        grp = VGroup()
        for i in range(self.n):
            x = self._xl + 0.3 + (self.L - 0.6) * (i + 0.5) / self.n
            y = self._c[1] + (self._offsets[i] - 0.5) * (self.H - 0.4)
            grp.add(Dot([x, y, 0], radius=0.11, color=self.color(color), fill_opacity=0.9))
        self._electrons = grp
        self.scene.play(_fade_in(grp), run_time=run_time * (0.8 if label else 1.0))
        if label:
            self.scene.play(_write(self._mlabel(label, [self._xl, self._c[1] - self.H / 2, 0],
                                                color, _down())), run_time=run_time * 0.2)

    @step
    def field(self, run_time: float, color: str = "purple", label: str = "E", **_):
        """The internal electric field that drives the drift (points along the wire)."""
        from manim import Arrow, GrowArrow

        y = self._c[1] + self.H / 2 + 0.5
        arr = Arrow([self._c[0] - 1.0, y, 0], [self._c[0] + 1.0, y, 0], buff=0,
                    color=self.color(color), stroke_width=_ARR_STROKE,
                    max_tip_length_to_length_ratio=0.25)
        self.scene.play(GrowArrow(arr), run_time=run_time * 0.7)
        if label:
            self.scene.play(_write(self._mlabel(label, arr.get_end(), color, _up())),
                            run_time=run_time * 0.3)

    @step
    def drift(self, run_time: float, direction: float = -1.0, color: str = "blue",
              label: str = "v_d", **_):
        """Drift the electrons slowly along the wire (default leftward, against the
        field) — the slow net motion that is the current. They wrap at the end."""
        from manim import VGroup

        if self._electrons is None:
            self.scene.wait(run_time)
            return
        shift = np.array([direction * (self.L - 0.6) * 0.5, 0.0, 0.0])
        moved = VGroup()
        for d in self._electrons:
            p = d.get_center() + shift
            # wrap round the wire so it stays populated
            if p[0] < self._xl + 0.3:
                p[0] += (self.L - 0.6)
            elif p[0] > self._xr - 0.3:
                p[0] -= (self.L - 0.6)
            dd = d.copy().move_to(p)
            moved.add(dd)
        lbl = self._mlabel(label, self._electrons[0].get_center() + np.array([0, 0.45, 0]),
                           color, _up())
        self.scene.play(self._electrons.animate.become(moved), _write(lbl), run_time=run_time)

    @step
    def current_arrow(self, run_time: float, color: str = "yellow", label: str = "I", **_):
        """The conventional current arrow — opposite to the electron drift."""
        from manim import Arrow, GrowArrow

        y = self._c[1] - self.H / 2 - 0.55
        arr = Arrow([self._c[0] - 1.0, y, 0], [self._c[0] + 1.0, y, 0], buff=0,
                    color=self.color(color), stroke_width=_ARR_STROKE,
                    max_tip_length_to_length_ratio=0.25)
        self.scene.play(GrowArrow(arr), run_time=run_time * 0.7)
        if label:
            self.scene.play(_write(self._mlabel(label, arr.get_end(), color, _down())),
                            run_time=run_time * 0.3)


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
