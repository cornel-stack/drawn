"""Data-driven Manim scene with a 2D/3D split, legibility layout, hand-follow
and narration-synced animation steps.

One scene renders to a silent clip. Board items (written formulas/prose) and
animation steps share one timeline, each triggered at its ``{id}`` word-start
from the TTS stage. 3D animations (``primitive.is_3d``) render on a ThreeDScene
with board text as fixed-in-frame overlays; the hand writes in 2D scenes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from drawn_schema.channel import ChannelConfig
from drawn_schema.lesson import Lesson, Scene

from drawn_board import layout, style
from drawn_board.hand import HandFollower
from drawn_board.wobble import apply_wobble


@dataclass
class RenderData:
    repo_root: Path
    lesson: Lesson
    scene: Scene
    channel: ChannelConfig
    duration: float
    item_starts: dict[str, float] = field(default_factory=dict)
    highlights: list[tuple[str, float]] = field(default_factory=list)
    is_3d: bool = False


class BoardSceneMixin:
    """Shared construct logic; mixed onto Scene or ThreeDScene."""

    data: RenderData

    def construct(self):
        d = self.data
        from manim import DEGREES

        self.camera.background_color = d.channel.board.background
        self.ink = d.channel.board.ink
        self.font_family = d.channel.font.handwriting
        self.use_hand = True

        if d.is_3d:
            self.set_camera_orientation(phi=68 * DEGREES, theta=-50 * DEGREES, zoom=1.15)

        self.hand = HandFollower(d.repo_root, self._fh())
        if d.is_3d:
            self.add_fixed_in_frame_mobjects(self.hand.mobject)
        else:
            self.add(self.hand.mobject)

        if d.scene.kind == "title":
            self._title_card()
            return
        if d.scene.kind == "end":
            self._end()
            return

        primitive = self._build_primitive()
        written = self._written_mobjects()
        steps = self._animation_steps()
        self._run_timeline(written, steps, primitive, d.duration)

    # -- content builders --------------------------------------------------

    def _build_primitive(self):
        d = self.data
        if d.scene.animation is None:
            return None
        from drawn_board.primitives.base import get_primitive, load_custom

        anim = d.scene.animation
        if anim.custom:
            cls = load_custom(d.repo_root, d.lesson.channel, d.lesson.id, anim.custom)
        else:
            cls = get_primitive(anim.primitive)
        prim = cls(self, d.channel, anim.params)
        prim.build()
        return prim

    def _written_mobjects(self):
        """Return [(start, mobject, item)] for written board items."""
        d = self.data
        mobs = []
        for i, item in enumerate(d.scene.board):
            mobs.append((item, self._item_mobject(item, i)))
        if not mobs:
            return []
        group = layout.stack_items(
            [m for _, m in mobs],
            align_equals=(d.scene.kind == "derivation"),
            frame_width=self._fw(),
            frame_height=self._fh(),
        )
        # keep written text out of the diagram's way: diagram scenes carry
        # their formula/label at the TOP (filling the space above the diagram);
        # other animated scenes keep text in the lower third.
        if d.scene.animation is not None:
            from manim import DOWN, UP

            edge = UP if d.scene.kind == "diagram" else DOWN
            group.to_edge(edge, buff=self._fh() * style.SAFE_MARGIN_FRAC)
        else:
            # board / derivation / problem: centre in the region above the
            # bottom caption band (~14 %), scaled to fit it.
            usable = self._fh() * 0.74
            if group.height > usable:
                group.scale_to_fit_height(usable)
            group.move_to([0, self._fh() * 0.07, 0])
        self._board_group = group
        out = []
        for item, mob in mobs:
            out.append((d.item_starts.get(item.id, 0.0), mob, item))
        return out

    def _animation_steps(self):
        d = self.data
        if d.scene.animation is None:
            return []
        out = []
        for s in d.scene.animation.steps:
            out.append((d.item_starts.get(s.id, 0.0), s))
        return out

    def _title_card(self):
        """A full-frame title card: title large, channel name small, then held.

        Nothing else is drawn; the next scene starts on a cleared board.
        """
        from manim import DL, DR, FadeIn, Line, VGroup

        d = self.data
        title = self._text(d.lesson.title, self.ink, style.TITLE_FONT_SIZE)
        title.scale_to_fit_width(min(title.width, style.usable_width(self._fw())))
        rule = Line(title.get_corner(DL), title.get_corner(DR),
                    color=d.channel.resolve_color(d.channel.board.accent))
        rule.next_to(title, direction=_down(), buff=0.3)
        name = self._text(d.channel.display_name,
                          d.channel.resolve_color(d.channel.board.accent),
                          style.TEXT_FONT_SIZE)
        name.next_to(rule, direction=_down(), buff=0.5)
        VGroup(title, rule, name).move_to(_origin())

        slot = min(max(d.duration * 0.55, 1.5), 3.2)
        consumed = self._write_one(title, None, slot, [])
        self.play(FadeIn(rule), FadeIn(name), run_time=0.5)
        consumed += 0.5
        if d.duration > consumed:
            self.wait(d.duration - consumed)

    def _item_mobject(self, item, seed: int):
        color = self.data.channel.resolve_color(item.color)
        if item.is_latex:
            from manim import MathTex

            tex = item.latex or ""
            if item.tex_colors:
                m = self._coloured_formula(tex, item.tex_colors, color)
            elif "=" in tex:
                lhs, rhs = tex.split("=", 1)
                m = MathTex(lhs, "=", rhs, color=color, font_size=style.FORMULA_FONT_SIZE)
                m._equals_glyph = m[1]  # the isolated '=' submobject
                m.set_stroke(color, width=style.GLYPH_STROKE_WIDTH)
            else:
                m = MathTex(tex, color=color, font_size=style.FORMULA_FONT_SIZE)
                m.set_stroke(color, width=style.GLYPH_STROKE_WIDTH)
        else:
            m = self._text(item.text, color, style.TEXT_FONT_SIZE)
        apply_wobble(m, seed=seed)
        if item.box:
            from manim import SurroundingRectangle, VGroup

            rect = SurroundingRectangle(m, color=color, buff=0.18, corner_radius=0.08)
            m = VGroup(m, rect)
        return m

    def _coloured_formula(self, tex: str, tex_colors: dict, base_color: str):
        """One MathTex with per-substring colours via \\textcolor + \\definecolor.

        Kept as a single valid expression (unlike arg-splitting, which breaks
        \\dfrac bracing since Manim compiles each arg separately).
        """
        from manim import MathTex, TexTemplate

        tmpl = TexTemplate()
        tmpl.add_to_preamble(r"\usepackage{xcolor}")
        # Locate each substring's first occurrence in the ORIGINAL tex, then
        # splice the \textcolor wrappers in a single pass. Replacing on a mutating
        # string would let a later single-letter key (e.g. "a") match inside an
        # already-injected colour name ("drawn-a-ccent0") and break the LaTeX.
        spans = []
        for i, (sub, col) in enumerate(tex_colors.items()):
            name = f"drawnaccent{i}"
            hexv = self.data.channel.resolve_color(col).lstrip("#").upper()
            tmpl.add_to_preamble(f"\\definecolor{{{name}}}{{HTML}}{{{hexv}}}")
            idx = tex.find(sub)
            if idx >= 0:
                spans.append((idx, idx + len(sub), sub, name))
        spans.sort()
        out, pos, last_end = [], 0, 0
        for start, end, sub, name in spans:
            if start < last_end:  # overlaps a prior wrap — skip
                continue
            out.append(tex[pos:start])
            out.append(f"\\textcolor{{{name}}}{{{sub}}}")
            pos, last_end = end, end
        out.append(tex[pos:])
        return MathTex("".join(out), tex_template=tmpl, color=base_color,
                       font_size=style.FORMULA_FONT_SIZE)

    def _text(self, text: str, color: str, font_size: int):
        from manim import Text

        return Text(
            text, font=self.font_family, weight="BOLD", font_size=font_size,
            color=color, stroke_width=style.GLYPH_STROKE_WIDTH, stroke_color=color,
        )

    # -- timeline ----------------------------------------------------------

    def _run_timeline(self, written, steps, primitive, total: float):
        events = [("write", s, mob, item) for (s, mob, item) in written]
        events += [("step", s, step, None) for (s, step) in steps]
        events += [("hl", s, hid, None) for (hid, s) in self.data.highlights]
        events.sort(key=lambda e: e[1])

        mob_by_id: dict[str, object] = {}
        t = 0.0
        visible: list = []
        last_eq = False
        n = len(events)
        for i, (kind, start, payload, item) in enumerate(events):
            if start > t:
                # a gap right after an equation is reading time: hold it static
                self._fill(start - t, primitive, visible, read_hold=last_eq)
                t = start
            next_start = events[i + 1][1] if i + 1 < n else total
            slot = max(0.0, next_start - t)
            if kind == "write":
                consumed = self._write_one(payload, item, slot, visible)
                if item is not None:
                    mob_by_id[item.id] = payload
                last_eq = bool(item and getattr(item, "is_equation", False))
            elif kind == "hl":
                consumed = self._highlight_one(mob_by_id.get(payload), slot)
                last_eq = False
            else:
                # animation steps fill their slot (precession needs the time)
                consumed = max(0.5, slot)
                primitive.run_step(payload.action, payload.params, run_time=consumed)
                last_eq = False
            t += consumed
        remaining = total - t
        if remaining > 0.05:
            self._fill(remaining, primitive, visible, read_hold=last_eq)

    def _highlight_one(self, mob, slot: float) -> float:
        """Re-emphasise an already-drawn item as the narration refers to it."""
        if mob is None:
            return 0.0
        from manim import Indicate

        dur = min(0.9, slot) if slot > 0.05 else 0.9
        self.play(Indicate(mob, scale_factor=1.12), run_time=dur)
        return dur

    def _fill(self, dur: float, primitive, visible: list, read_hold: bool = False) -> None:
        """Fill `dur` — motion, unless it is reading time after an equation.

        3D: a slow ambient camera rotation. A primitive still moving on its own
        (spin/precess): let it run. 2D: a gentle breathing pulse of the active
        item. Reading time just after an equation (<=2.6 s) stays static so the
        viewer can read it. A plain wait only before anything is on screen.
        """
        if dur <= 0.05:
            return
        if read_hold and dur <= 2.6:
            self.wait(dur)  # reading time, deliberately static
            return
        if self.data.is_3d:
            self.begin_ambient_camera_rotation(rate=0.08)
            self.wait(dur)
            self.stop_ambient_camera_rotation()
        elif primitive is not None and primitive.continuous_spans():
            self.wait(dur)  # the primitive keeps moving on its own
        elif visible:
            self._pulse(visible[-1][0], dur)
        else:
            self.wait(dur)

    def _pulse(self, mob, remaining: float) -> None:
        import math

        from manim import UpdateFromAlphaFunc

        base_h = mob.height
        base_c = mob.get_center()
        cycles = max(1.0, remaining / 1.6)

        def _f(m, alpha):
            m.scale_to_fit_height(base_h * (1 + 0.03 * math.sin(alpha * 2 * math.pi * cycles)))
            m.move_to(base_c)

        self.play(UpdateFromAlphaFunc(mob, _f), run_time=remaining)

    def _write_one(self, mob, item, slot: float, visible: list) -> float:
        """Write `mob` with the hand; return the time actually consumed.

        The pen traces at a human pace (scaled by glyph count) and the hand is
        locked to the same duration, so the ink never outruns the pen. The
        clock advances by exactly what this consumes, keeping the clip in sync
        with the audio.
        """
        from manim import UpdateFromAlphaFunc, Write

        self._retire_if_full(mob, item, visible)
        if self.data.is_3d:
            self.add_fixed_in_frame_mobjects(mob)

        glyphs = mob.family_members_with_points()
        n = max(1, len(glyphs))
        want = n * style.WRITE_SECONDS_PER_GLYPH
        want = max(style.WRITE_MIN_SECONDS, min(style.WRITE_MAX_SECONDS, want))

        enter = min(style.HAND_ENTER_SECONDS, slot * 0.18) if slot > 0 else style.HAND_ENTER_SECONDS
        lift = min(style.HAND_LIFT_SECONDS, slot * 0.18) if slot > 0 else style.HAND_LIFT_SECONDS
        avail = (slot - enter - lift) if slot > 0 else want
        wdur = want if avail <= 0 else max(0.4, min(want, avail))

        tip_off = self.hand.tip_offset
        centers = [g.get_center() for g in glyphs]

        def _follow(hand, alpha):
            # pen sits on the glyph currently being revealed by Write (which
            # staggers glyph-by-glyph), so the tip stays with the ink frontier
            f = min(max(alpha, 0.0), 1.0) * (n - 1)
            i = int(f)
            j = min(i + 1, n - 1)
            target = centers[i] + (centers[j] - centers[i]) * (f - i)
            hand.move_to(target - tip_off)

        self.hand.enter(self, centers[0], run_time=enter)
        self.play(
            Write(mob),
            UpdateFromAlphaFunc(self.hand.mobject, _follow),
            run_time=wdur,
        )
        self.hand.lift(self, run_time=lift)
        extra = 0.0
        if item is not None and getattr(item, "legend", None):
            extra = self._reveal_legend(item, mob)
        visible.append((mob, item))
        return enter + wdur + lift + extra

    def _reveal_legend(self, item, mob) -> float:
        """Fade in a small symbol legend beside the equation. Returns time used."""
        from manim import RIGHT, FadeIn

        legend = self._legend_mobject(item)
        if legend is None:
            return 0.0
        legend.next_to(mob, RIGHT, buff=0.5)
        if self.data.is_3d:
            self.add_fixed_in_frame_mobjects(legend)
        # keep it on screen within the frame
        half_w = self._fw() * (0.5 - style.SAFE_MARGIN_FRAC)
        if legend.get_right()[0] > half_w:
            from manim import DOWN

            legend.next_to(mob, DOWN, buff=0.35)
        self.play(FadeIn(legend), run_time=0.5)
        return 0.5

    def _legend_mobject(self, item):
        from manim import VGroup

        rows = []
        for entry in item.legend:
            rows.append(self._legend_row(entry))
        if not rows:
            return None
        group = VGroup(*rows).arrange(_down(), aligned_edge=_left(), buff=0.18)
        return group.scale_to_fit_height(min(group.height, self._fh() * 0.5))

    def _legend_row(self, entry):
        from manim import MathTex, VGroup

        color = self.data.channel.resolve_color(self.data.channel.board.ink)
        sym = MathTex(entry.sym, color=color, font_size=style.LABEL_FONT_SIZE)
        unit = f"  [{_superscript(entry.unit)}]" if entry.unit else ""
        text = self._text(f": {entry.name}{unit}", color, style.LABEL_FONT_SIZE - 6)
        return VGroup(sym, text).arrange(_right(), buff=0.12)

    def _retire_if_full(self, mob, item, visible: list):
        from manim import FadeOut

        # a worked problem keeps its whole working on screen (scaled to fit)
        if self.data.scene.kind == "problem":
            return
        is_formula = item is not None and getattr(item, "is_latex", False)
        cap = style.MAX_FORMULA_LINES if is_formula else style.MAX_TEXT_LINES
        while len(visible) >= cap:
            old_mob, _ = visible.pop(0)
            self.play(FadeOut(old_mob), run_time=0.3)

    def _end(self):
        from manim import FadeIn

        d = self.data
        name = self._text(d.channel.display_name, self.ink, style.TITLE_FONT_SIZE)
        name.scale_to_fit_width(min(name.width, self._fw() * 0.6)).move_to(_origin())
        if self.use_hand:
            self.hand.mobject.set_opacity(0)
        self.play(FadeIn(name, run_time=0.8))
        self.wait(max(0.2, d.duration - 0.8))

    def _fw(self) -> float:
        from manim import config

        return config.frame_width

    def _fh(self) -> float:
        from manim import config

        return config.frame_height


_SUPERS = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


def _superscript(unit: str) -> str:
    """Render ``^2`` style exponents in a unit string as unicode superscripts.

    The symbol legend is written in the handwriting font (not MathTex), so a
    literal caret looks wrong; ``kg m^2/s`` becomes ``kg m²/s``.
    """
    import re

    return re.sub(r"\^(-?\d+)", lambda m: m.group(1).translate(_SUPERS), unit)


def _down():
    from manim import DOWN

    return DOWN


def _origin():
    from manim import ORIGIN

    return ORIGIN


def _left():
    from manim import LEFT

    return LEFT


def _right():
    from manim import RIGHT

    return RIGHT


def make_lesson_scene(data: RenderData):
    """Build a Scene (2D) or ThreeDScene (3D) instance carrying the data."""
    if data.is_3d:
        from manim import ThreeDScene

        base = ThreeDScene
    else:
        from manim import Scene

        base = Scene

    cls = type("LessonScene", (BoardSceneMixin, base), {})
    scene = cls()
    scene.data = data
    return scene
