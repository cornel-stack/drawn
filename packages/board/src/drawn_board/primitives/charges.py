"""Point charges with Coulomb force arrows and vector superposition (2D).

Electrostatics diagrams built from three ideas:

* a point charge drawn as a signed dot (``+`` or ``-``) with a label;
* the Coulomb force on one charge due to another, its direction set by the sign
  product — **repulsive** for like charges (pushed away), **attractive** for
  unlike charges (pulled toward);
* the net force as the **tip-to-tail vector sum** of the separate pairwise
  forces (the superposition principle).

Coordinates are the diagram's own units (no visible axes — electrostatics
pictures rarely want them); ``origin`` places the diagram's (0, 0) in the frame
and ``scale`` sets units-per-coordinate. Reused across the Electricity &
Magnetism series (Coulomb's law, the field of point charges, superposition
problems).
"""

from __future__ import annotations

import numpy as np

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step
from drawn_board.style import LABEL_FONT_SIZE

_FORCE_STROKE = 7
_TIP_RATIO = 0.24
_DOT_RADIUS = 0.22


@register("charges")
class Charges(Primitive):
    """params:
      origin: [x, y]     # frame coords of the diagram's (0, 0); default ANIM_CENTER
      scale: float       # units per coordinate (default 1.0)
      charges: {name: {at: [x, y], sign: "+"|"-", color: <accent>, label: "q_1"}}

    steps: place, separation, force, net.
    """

    is_3d = False

    def build(self) -> None:
        self._specs = self.params.get("charges", {})
        c = self.params.get("origin", style.ANIM_CENTER)
        self._origin = np.array([c[0], c[1], 0.0])
        self.scale = float(self.params.get("scale", 1.0))
        self._pos: dict = {}      # name -> frame-coord point
        self._forces: dict = {}   # on-name -> list of force vectors (frame coords)

    # -- helpers -----------------------------------------------------------

    def _p(self, xy):
        return self._origin + np.array([xy[0] * self.scale, xy[1] * self.scale, 0.0])

    def _dir(self, v):
        n = np.linalg.norm(v)
        return v / n if n > 1e-9 else np.array([1.0, 0.0, 0.0])

    # -- steps -------------------------------------------------------------

    @step
    def place(self, run_time: float, name: str = None, **_):
        """Draw charge `name` as a signed dot with its label."""
        from manim import Dot, FadeIn, GrowFromCenter, MathTex, Text, Write

        spec = self._specs[name]
        pos = self._p(spec["at"])
        self._pos[name] = pos
        col = self.color(spec.get("color"))
        dot = Dot(pos, radius=_DOT_RADIUS, color=col)
        dot.set_fill(col, opacity=1.0)
        sign = str(spec.get("sign", "+"))
        sign_mob = Text(sign, font=self.channel.font.handwriting, weight="BOLD",
                        font_size=LABEL_FONT_SIZE, color=self.color(None))
        sign_mob.scale_to_fit_height(_DOT_RADIUS * 1.0).move_to(pos)
        anims = [GrowFromCenter(dot), FadeIn(sign_mob)]
        if spec.get("label"):
            lbl = MathTex(spec["label"], color=col, font_size=LABEL_FONT_SIZE + 6)
            lbl.next_to(pos, direction=_up() + _right(), buff=0.10)
            anims.append(Write(lbl))
        self.scene.play(*anims, run_time=run_time)

    @step
    def separation(self, run_time: float, a: str = None, b: str = None,
                   label: str = "r", color: str = None, **_):
        """Mark the distance between charges `a` and `b` with a dashed line."""
        from manim import DashedLine, MathTex, Write

        pa, pb = self._pos[a], self._pos[b]
        line = DashedLine(pa, pb, color=self.color(color), stroke_width=3)
        lbl = MathTex(label, color=self.color(color), font_size=LABEL_FONT_SIZE)
        lbl.next_to((pa + pb) / 2, direction=_up(), buff=0.12)
        self.scene.play(_create(line), run_time=run_time * 0.6)
        self.scene.play(Write(lbl), run_time=run_time * 0.4)

    @step
    def force(self, run_time: float, on: str = None, frm: str = None, length: float = 1.5,
              color: str = "green", label: str = None, **_):
        """Draw the Coulomb force on charge `on` due to charge `frm`.

        Direction from the sign product: like charges repel (arrow points away
        from `frm`), unlike charges attract (arrow points toward `frm`).
        `length` is the arrow length in frame units (illustrative scale).
        """
        from manim import Arrow, GrowArrow, MathTex, Write

        p_on, p_frm = self._pos[on], self._pos[frm]
        like = str(self._specs[on].get("sign", "+")) == str(self._specs[frm].get("sign", "+"))
        direction = self._dir(p_on - p_frm)      # away from frm
        if not like:
            direction = -direction               # toward frm (attraction)
        start = p_on + direction * _DOT_RADIUS
        end = p_on + direction * (length + _DOT_RADIUS)
        arrow = Arrow(start, end, buff=0, color=self.color(color),
                      stroke_width=_FORCE_STROKE, max_tip_length_to_length_ratio=_TIP_RATIO)
        self._forces.setdefault(on, []).append(direction * length)
        anims = [GrowArrow(arrow)]
        if label:
            lbl = MathTex(label, color=self.color(color), font_size=LABEL_FONT_SIZE + 4)
            lbl.next_to(end, direction=direction, buff=0.14)
            anims.append(Write(lbl))
        self.scene.play(*anims, run_time=run_time)

    @step
    def net(self, run_time: float, on: str = None, color: str = "yellow",
            label: str = None, show_components: bool = True, **_):
        """Tip-to-tail sum of the forces already drawn on `on` → the net force."""
        from manim import Arrow, DashedLine, GrowArrow, MathTex, Write

        p_on = self._pos[on]
        vecs = self._forces.get(on, [])
        total = np.sum(vecs, axis=0) if vecs else np.zeros(3)

        if show_components and len(vecs) > 1:
            tail = p_on + self._dir(vecs[0]) * _DOT_RADIUS
            seg_t = run_time * 0.4 / len(vecs)
            for v in vecs:
                ghost = DashedLine(tail, tail + v, color=self.color(None), stroke_width=3)
                self.scene.play(_create(ghost), run_time=seg_t)
                tail = tail + v

        direction = self._dir(total)
        start = p_on + direction * _DOT_RADIUS
        res = Arrow(start, p_on + total, buff=0, color=self.color(color),
                    stroke_width=_FORCE_STROKE + 1, max_tip_length_to_length_ratio=_TIP_RATIO)
        anims = [GrowArrow(res)]
        if label:
            lbl = MathTex(label, color=self.color(color), font_size=LABEL_FONT_SIZE + 6)
            lbl.next_to(p_on + total, direction=direction, buff=0.16)
            anims.append(Write(lbl))
        self.scene.play(*anims, run_time=run_time * (0.6 if show_components else 1.0))


def _create(m):
    from manim import Create

    return Create(m)


def _up():
    from manim import UP

    return UP


def _right():
    from manim import RIGHT

    return RIGHT
