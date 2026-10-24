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

_AXLE_LEN = 3.0
_WHEEL_R = 1.45
_L_EXTRA = 1.2        # how far L reaches beyond the pivot
_ARROW = dict(thickness=0.035, base_radius=0.14, height=0.34)
_LABEL_SIZE = 44


@register("gyroscope")
class Gyroscope(Primitive):
    is_3d = True
    continuous_actions = {"spin_up", "precess"}
    auto_continuous = True  # the wheel spins from build(), so motion is constant

    def build(self) -> None:
        from manim import RIGHT, UP, Circle, Dot3D, Line, VGroup

        ink = self.color(None)
        # pivot left of centre so the axle+wheel assembly sits centred
        self.pivot = np.array([-1.5, 0.4, 0.0])

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

        # the wheel spins continuously from the start (auto_continuous)
        self._spin_rate = 7.0
        center = self.wheel_center

        def _spin(mob, dt):
            mob.rotate(self._spin_rate * dt, axis=RIGHT, about_point=center)

        self.wheel.add_updater(_spin)
        self.mark_continuous(0.0, 1e9)

    # -- steps -------------------------------------------------------------

    @step
    def spin_up(self, run_time: float, rate: float = 9.0, **_):
        """Visibly ramp the spin (motion is already continuous from build)."""
        self._spin_rate = float(rate)
        self.scene.wait(run_time)

    # -- vector + label builders (each scene is self-contained) ------------

    def _arrow(self, start, end, color):
        from manim import Arrow3D

        return Arrow3D(start, end, color=self.color(color), **_ARROW)

    def _label(self, tex, point, color, add=True):
        from manim import MathTex

        label = MathTex(tex, color=self.color(color), font_size=_LABEL_SIZE)
        label.move_to(point)
        if add:
            # keep text facing the camera at its 3D position
            self.scene.add_fixed_orientation_mobjects(label)
        return label

    @property
    def _L_tip(self):
        return self.pivot + np.array([_AXLE_LEN + _L_EXTRA, 0, 0])

    def _make_L(self, color="blue"):
        return self._arrow(self.pivot, self._L_tip, color)

    def _make_torque(self, color="orange"):
        g = self._arrow(self.wheel_center, self.wheel_center + np.array([0, -1.5, 0]), None)
        tau = self._arrow(self.wheel_center, self.wheel_center + np.array([0, 0, -1.6]), color)
        return g, tau

    def _ensure_L(self, color="blue"):
        if not hasattr(self, "L"):
            self.L = self._make_L(color)
            self.scene.add(self.L)
            self._label(r"\vec{L}", self._L_tip + np.array([0.35, 0.45, 0]), color)

    def _ensure_torque(self, color="orange"):
        if not hasattr(self, "tau"):
            self.gravity, self.tau = self._make_torque(color)
            self.scene.add(self.gravity, self.tau)

    @step
    def draw_L(self, run_time: float, color: str = "blue", **_):
        self.L = self._make_L(color)
        self.scene.play(_grow(self.scene, self.L), run_time=run_time)
        self._label(r"\vec{L}", self._L_tip + np.array([0.35, 0.45, 0]), color)

    @step
    def draw_torque(self, run_time: float, color: str = "orange", **_):
        self._ensure_L()  # L stays on screen from the previous scene
        self.gravity, self.tau = self._make_torque(color)
        self.scene.play(_grow(self.scene, self.gravity), run_time=run_time * 0.5)
        self._label(r"m\vec{g}", self.wheel_center + np.array([0.1, -1.9, 0]), None)
        self.scene.play(_grow(self.scene, self.tau), run_time=run_time * 0.5)
        self._label(r"\vec{\tau}", self.wheel_center + np.array([0.2, 0.1, -2.0]), color)

    @step
    def add_dL(self, run_time: float, color: str = "orange", **_):
        """Show dL = tau dt as a small increment at L's tip, then nudge L."""
        from manim import UP, Rotate

        self._ensure_L()
        self._ensure_torque()
        tip = self._L_tip
        dL = self._arrow(tip, tip + np.array([0, 0, -1.1]), color)
        self.scene.play(_grow(self.scene, dL), run_time=run_time * 0.5)
        self._label(r"d\vec{L}", tip + np.array([0.3, 0.0, -1.4]), color)
        group = _vgroup(self.L, self.assembly, dL)
        self.scene.play(Rotate(group, angle=np.deg2rad(18), axis=UP,
                              about_point=self.pivot), run_time=run_time * 0.5)

    @step
    def precess(self, run_time: float, turns: float = 1.0, orbit: bool = True, **_):
        from manim import UP, Circle, DashedVMobject, Rotate

        self._ensure_L()
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
            self.scene.begin_ambient_camera_rotation(rate=0.12)
        # consume exactly run_time: cone draw + precession sweep sum to run_time
        cone_t = run_time * 0.3
        sweep_t = run_time - cone_t
        self.scene.play(_grow_create(self.scene, cone), run_time=cone_t)
        self.scene.play(
            Rotate(group, angle=2 * np.pi * turns, axis=UP, about_point=self.pivot),
            run_time=sweep_t,
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
