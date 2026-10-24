"""The data-driven Manim scene.

One ``LessonScene`` renders one scene of a lesson to a silent video clip, timing
each board item's Write() to the audio word-start recorded by the TTS stage.
The audio itself is added later by the assembly stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from drawn_schema.channel import ChannelConfig
from drawn_schema.lesson import Lesson, Scene

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


def _lesson_scene_base():
    from manim import Scene as ManimScene

    class LessonScene(ManimScene):
        data: RenderData

        def construct(self):
            d = self.data
            self.camera.background_color = d.channel.board.background
            self.ink = d.channel.board.ink
            self.accent = d.channel.board.accent
            self.font_family = d.channel.font.handwriting

            self.hand = HandFollower(d.repo_root)
            self.add(self.hand.mobject)

            dispatch = {
                "title": self._title,
                "end": self._end,
            }
            dispatch.get(d.scene.kind, self._write_board)()

        # -- scene kinds ---------------------------------------------------

        def _title(self):
            from manim import DL, DR, Line, VGroup

            d = self.data
            title = self._text(d.lesson.title, self.ink)
            title.scale_to_fit_width(min(title.width, self._fw() * 0.82))
            rule = Line(title.get_corner(DL), title.get_corner(DR), color=self.accent)
            rule.next_to(title, direction=_down(), buff=0.3)
            group = VGroup(title, rule).move_to(_origin())
            self._write_sequence([(0.0, group)], d.duration)

        def _end(self):
            from manim import FadeIn

            d = self.data
            name = self._text(d.channel.display_name, self.ink)
            name.scale_to_fit_width(min(name.width, self._fw() * 0.6)).move_to(_origin())
            self.hand.mobject.set_opacity(0)
            self.play(FadeIn(name, run_time=0.8))
            self.wait(max(0.2, d.duration - 0.8))

        def _write_board(self):
            from manim import VGroup

            d = self.data
            mobs: list[tuple[str, object]] = []
            for i, item in enumerate(d.scene.board):
                mobs.append((item.id, self._item_mobject(item, i)))

            group = VGroup(*[m for _, m in mobs])
            group.arrange(_down(), aligned_edge=_left(), buff=0.45)
            if group.width > self._fw() * 0.88:
                group.scale_to_fit_width(self._fw() * 0.88)
            if group.height > self._fh() * 0.82:
                group.scale_to_fit_height(self._fh() * 0.82)
            group.move_to(_origin())

            entries = sorted(
                ((d.item_starts.get(item_id, 0.0), mob) for item_id, mob in mobs),
                key=lambda e: e[0],
            )
            self._write_sequence(entries, d.duration)

        # -- helpers -------------------------------------------------------

        def _item_mobject(self, item, seed: int):
            if item.is_latex:
                from manim import MathTex

                m = MathTex(item.latex, color=self.ink)
                apply_wobble(m, amplitude=0.012, seed=seed)
            else:
                m = self._text(item.text, self.ink)
                apply_wobble(m, amplitude=0.02, seed=seed)
            return m

        def _text(self, text: str, color: str):
            from manim import Text

            return Text(text, font=self.font_family, color=color)

        def _write_sequence(self, entries, total: float):
            t = 0.0
            n = len(entries)
            for i, (start, mob) in enumerate(entries):
                start = max(start, t)
                if start > t:
                    self.wait(start - t)
                next_start = entries[i + 1][0] if i + 1 < n else total
                span = next_start - start
                wdur = 0.6 if span <= 0 else max(0.3, min(1.1, span * 0.8))
                self._write_one(mob, wdur)
                t = start + wdur
            if total > t:
                self.wait(total - t)

        def _write_one(self, mob, wdur: float):
            from manim import ValueTracker, Write

            tracker = ValueTracker(0.0)
            self.hand.mobject.set_opacity(1)
            self.hand.place_tip_at(path_point(mob, 0.0))
            updater = self.hand.follow_updater(mob, tracker)
            self.hand.mobject.add_updater(updater)
            self.play(Write(mob), tracker.animate.set_value(1.0), run_time=wdur)
            self.hand.mobject.remove_updater(updater)

        def _fw(self) -> float:
            from manim import config

            return config.frame_width

        def _fh(self) -> float:
            from manim import config

            return config.frame_height

    return LessonScene


# Lazy direction/point helpers so this module imports without manim present.
def _down():
    from manim import DOWN

    return DOWN


def _left():
    from manim import LEFT

    return LEFT


def _origin():
    from manim import ORIGIN

    return ORIGIN


def make_lesson_scene(data: RenderData):
    cls = _lesson_scene_base()
    scene = cls()
    scene.data = data
    return scene
