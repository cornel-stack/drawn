"""2D rotating rigid body: a wheel with spokes (disc + rim + hub)."""

from __future__ import annotations

from drawn_board.primitives.base import Primitive, register, step


@register("wheel")
class Wheel(Primitive):
    """A spoked wheel that can spin up and hold a continuous rotation.

    params:
      radius: float (default 1.6)
      spokes: int (default 8)
      color: accent name for the rim (default white ink)
      position: [x, y]
    """

    is_3d = False
    continuous_actions = {"start_spin"}

    def build(self) -> None:
        import numpy as np
        from manim import Circle, Dot, Line, VGroup

        r = float(self.params.get("radius", 1.6))
        n = int(self.params.get("spokes", 8))
        pos = np.array([*self.params.get("position", [0, 0]), 0], dtype=float)
        col = self.color(self.params.get("color"))

        rim = Circle(radius=r, color=col, stroke_width=6)
        hub = Dot(point=[0, 0, 0], radius=0.08, color=col)
        spokes = VGroup(
            *[
                Line([0, 0, 0], [r * np.cos(a), r * np.sin(a), 0], color=col, stroke_width=4)
                for a in np.linspace(0, 2 * np.pi, n, endpoint=False)
            ]
        )
        self.wheel = VGroup(rim, hub, spokes).move_to(pos)
        self._spin_rate = 0.0

    @step
    def appear(self, run_time: float, **_):
        from manim import Create

        self.scene.play(Create(self.wheel), run_time=run_time)

    @step
    def start_spin(self, run_time: float, rate: float = 4.0, **_):
        """Begin a continuous spin that persists for the rest of the scene."""
        self._spin_rate = float(rate)

        def _spin(mob, dt):
            mob.rotate(self._spin_rate * dt)

        self.wheel.add_updater(_spin)
        # mark continuous motion from now until a large time (scene end clamps it)
        self.mark_continuous(0.0, 1e9)
        self.scene.wait(run_time)
