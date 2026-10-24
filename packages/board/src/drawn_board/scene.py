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
from drawn_board.hand import HandFollower, path_point
from drawn_board.wobble import apply_wobble


@dataclass
class RenderData:
    repo_root: Path
    lesson: Lesson
    scene: Scene
    channel: ChannelConfig
    duration: float
    item_starts: dict[str, float] = field(default_factory=dict)
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
        self.use_hand = not d.is_3d

        if d.is_3d:
            self.set_camera_orientation(phi=68 * DEGREES, theta=-50 * DEGREES)

        if self.use_hand:
            self.hand = HandFollower(d.repo_root, self._fh())
            self.add(self.hand.mobject)

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
        """Return [(start, mobject, item)] for written board items / title."""
        d = self.data
        if d.scene.kind == "title":
            return [(0.0, self._title_group(), None)]

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
        # a 2D scene that also runs an animation keeps its text in the lower
        # third so the diagram has the top of the frame to itself
        if d.scene.animation is not None and not d.is_3d:
            from manim import DOWN

            group.to_edge(DOWN, buff=self._fh() * style.SAFE_MARGIN_FRAC)
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

    def _title_group(self):
        from manim import DL, DR, Line, VGroup

        d = self.data
        title = self._text(d.lesson.title, self.ink, style.TITLE_FONT_SIZE)
        title.scale_to_fit_width(min(title.width, style.usable_width(self._fw())))
        rule = Line(title.get_corner(DL), title.get_corner(DR),
                    color=d.channel.resolve_color(d.channel.board.accent))
        rule.next_to(title, direction=_down(), buff=0.3)
        return VGroup(title, rule).move_to(_origin())

    def _item_mobject(self, item, seed: int):
        color = self.data.channel.resolve_color(item.color)
        if item.is_latex:
            from manim import MathTex

            tex = item.latex or ""
            if "=" in tex:
                lhs, rhs = tex.split("=", 1)
                m = MathTex(lhs, "=", rhs, color=color, font_size=style.FORMULA_FONT_SIZE)
                m._equals_glyph = m[1]  # the isolated '=' submobject
            else:
                m = MathTex(tex, color=color, font_size=style.FORMULA_FONT_SIZE)
            m.set_stroke(color, width=style.GLYPH_STROKE_WIDTH)
        else:
            m = self._text(item.text, color, style.TEXT_FONT_SIZE)
        apply_wobble(m, seed=seed)
        return m

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
        events.sort(key=lambda e: e[1])

        t = 0.0
        visible: list = []
        n = len(events)
        for i, (kind, start, payload, item) in enumerate(events):
            start = max(start, t)
            if start > t:
                self.wait(start - t)
            next_start = events[i + 1][1] if i + 1 < n else total
            span = max(0.3, next_start - start)
            if kind == "write":
                self._write_one(payload, item, span, visible)
                t = start + min(span, _write_budget(span))
            else:
                wdur = min(span, 1.2)
                primitive.run_step(payload.action, payload.params, run_time=wdur)
                t = start + wdur
        if total > t:
            self.wait(total - t)

    def _write_one(self, mob, item, span: float, visible: list):
        from manim import ValueTracker, Write

        self._retire_if_full(mob, item, visible)

        if self.use_hand:
            enter = min(0.3, span * 0.2)
            wdur = max(0.3, span - 2 * enter)
            self.hand.enter(self, path_point(mob, 0.0), run_time=enter)
            tracker = ValueTracker(0.0)
            updater = self.hand.follow_updater(mob, tracker)
            self.hand.mobject.add_updater(updater)
            self.play(Write(mob), tracker.animate.set_value(1.0), run_time=wdur)
            self.hand.mobject.remove_updater(updater)
            self.hand.lift(self, run_time=enter)
        else:
            if self.data.is_3d:
                self.add_fixed_in_frame_mobjects(mob)
            self.play(Write(mob), run_time=min(span, 1.1))
        visible.append((mob, item))

    def _retire_if_full(self, mob, item, visible: list):
        from manim import FadeOut

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


def _write_budget(span: float) -> float:
    return max(0.3, min(1.1, span * 0.8))


def _down():
    from manim import DOWN

    return DOWN


def _origin():
    from manim import ORIGIN

    return ORIGIN


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
