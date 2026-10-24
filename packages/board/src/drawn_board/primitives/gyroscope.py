"""3D gyroscope / precession primitive (ThreeDScene).

Geometry: a pivot at the origin, a horizontal axle along +x to a spinning wheel
at its far end. Vertical is +y (UP). Gravity at the wheel points -y; the torque
about the pivid is horizontal (-z). The angular momentum L points along the
axle (+x); the increment dL = tau dt nudges L toward -z, so the axle precesses
about the vertical, sweeping a cone.

Colours follow the one-quantity-one-colour rule via step params (L=blue,
tau=orange by convention in the lesson).
"""

from __future__ import annotations

import numpy as np

from drawn_board.primitives.base import Primitive, register, step

_AXLE_LEN = 2.6
_WHEEL_R = 1.1


@register("gyroscope")
class Gyroscope(Primitive):
    is_3d = True
    continuous_actions = {"spin_up", "precess"}

    def build(self) -> None:
        from manim import UP, Circle, Dot3D, Line, VGroup

        ink = self.color(None)
        self.pivot = np.array([0.0, 0.0, 0.0])

        # stand: a short vertical post the axle pivots on
        self.stand = Line(self.pivot + np.array([0, -1.6, 0]), self.pivot, color=ink,
                          stroke_width=5)

        # axle along +x
        wheel_center = self.pivot + np.array([_AXLE_LEN, 0, 0])
        self.axle = Line(self.pivot, wheel_center, color=ink, stroke_width=5)
        self.pivot_dot = Dot3D(self.pivot, radius=0.07, color=ink)

        # wheel: rim + spokes in the y-z plane (normal along x)
        rim = Circle(radius=_WHEEL_R, color=self.color("blue"), stroke_width=7)
        spokes = VGroup(*[
            Line([0, 0, 0], [_WHEEL_R * np.cos(a), _WHEEL_R * np.sin(a), 0],
                 color=ink, stroke_width=3)
            for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)
        ])
        wheel = VGroup(rim, spokes)
        wheel.rotate(np.pi / 2, axis=UP)          # face the normal along x
        wheel.move_to(wheel_center)
        self.wheel = wheel
        self.wheel_center = wheel_center

        # assembly that precesses together
        self.assembly = VGroup(self.axle, self.wheel)
        self.scene.add(self.stand, self.pivot_dot, self.assembly)
        self._spin_rate = 0.0

    # -- steps -------------------------------------------------------------

    @step
    def spin_up(self, run_time: float, rate: float = 6.0, **_):
        from manim import RIGHT

        self._spin_rate = float(rate)
        center = self.wheel_center

        def _spin(mob, dt):
            mob.rotate(self._spin_rate * dt, axis=RIGHT, about_point=center)

        self.wheel.add_updater(_spin)
        self.mark_continuous(0.0, 1e9)
        self.scene.wait(run_time)

    @step
    def draw_L(self, run_time: float, color: str = "blue", **_):
        from manim import Arrow3D

        self.L = Arrow3D(self.pivot, self.pivot + np.array([_AXLE_LEN + 0.9, 0, 0]),
                        color=self.color(color))
        self.scene.play(_grow(self.scene, self.L), run_time=run_time)

    @step
    def draw_torque(self, run_time: float, color: str = "orange", **_):
        from manim import Arrow3D

        g = Arrow3D(self.wheel_center, self.wheel_center + np.array([0, -1.3, 0]),
                   color=self.color(None))
        tau = Arrow3D(self.wheel_center, self.wheel_center + np.array([0, 0, -1.3]),
                     color=self.color(color))
        self.gravity = g
        self.tau = tau
        self.scene.play(_grow(self.scene, g), run_time=run_time * 0.5)
        self.scene.play(_grow(self.scene, tau), run_time=run_time * 0.5)

    @step
    def add_dL(self, run_time: float, color: str = "orange", **_):
        """Show dL = tau dt as a small increment at L's tip, then nudge L."""
        from manim import UP, Arrow3D, Rotate

        tip = self.pivot + np.array([_AXLE_LEN + 0.9, 0, 0])
        dL = Arrow3D(tip, tip + np.array([0, 0, -0.9]), color=self.color(color))
        self.scene.play(_grow(self.scene, dL), run_time=run_time * 0.5)
        # rotate L and the assembly a little about the vertical to show the turn
        group = _vgroup(self.L, self.assembly, dL)
        self.scene.play(Rotate(group, angle=np.deg2rad(18), axis=UP,
                              about_point=self.pivot), run_time=run_time * 0.5)

    @step
    def precess(self, run_time: float, turns: float = 1.0, orbit: bool = True, **_):
        from manim import UP, Circle, DashedVMobject, Rotate

        # the cone the axle sweeps: a dashed circle in the x-z plane at the tip
        cone = DashedVMobject(
            Circle(radius=_AXLE_LEN, color=self.color("blue"), stroke_width=3)
            .rotate(np.pi / 2, axis=UP).move_to(self.pivot),
            num_dashes=40,
        )
        movers = [self.assembly]
        for attr in ("L", "gravity", "tau"):
            if hasattr(self, attr):
                movers.append(getattr(self, attr))
        group = _vgroup(*movers)
        if orbit:
            self.scene.begin_ambient_camera_rotation(rate=0.15)
        self.scene.play(_grow_create(self.scene, cone), run_time=min(1.0, run_time * 0.3))
        self.scene.play(
            Rotate(group, angle=2 * np.pi * turns, axis=UP, about_point=self.pivot),
            run_time=max(0.5, run_time * 0.7),
        )
        if orbit:
            self.scene.stop_ambient_camera_rotation()
        self.mark_continuous(0.0, 1e9)


def _grow(scene, arrow3d):
    from manim import Create

    return Create(arrow3d)


def _grow_create(scene, mob):
    from manim import Create

    return Create(mob)


def _vgroup(*mobjects):
    from manim import VGroup

    return VGroup(*mobjects)
