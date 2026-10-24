"""Primitive base class and registry.

A primitive is a reusable, parameterised, narration-synced animation. It exposes
named **actions** (methods decorated with :func:`step`) that a lesson triggers
via ``{id}`` placeholders. Each action is called with the owning Manim scene and
the step's params, and either plays a timed animation or starts a continuous one
(e.g. a spinning wheel) that persists until the scene ends.

``is_3d`` selects the scene base class (ThreeDScene vs Scene). ``continuous_spans``
lets the pacing check treat ongoing motion as non-static.
"""

from __future__ import annotations

from collections.abc import Callable


def step(func: Callable) -> Callable:
    """Mark a method as a triggerable animation action."""
    func._is_step = True  # noqa: SLF001
    return func


class Primitive:
    is_3d: bool = False
    # actions that start motion lasting until the scene ends (pacing check)
    continuous_actions: set[str] = set()

    def __init__(self, scene, channel, params: dict):
        self.scene = scene
        self.channel = channel
        self.params = params or {}
        self._continuous: list[tuple[float, float]] = []

    # -- lifecycle ---------------------------------------------------------

    def build(self) -> None:
        """Create the initial (static) mobjects and add them to the scene."""

    def run_step(self, action: str, params: dict, run_time: float) -> None:
        method = getattr(self, action, None)
        if method is None or not getattr(method, "_is_step", False):
            raise ValueError(
                f"{type(self).__name__} has no animation step {action!r} "
                f"(available: {sorted(self.step_names())})"
            )
        method(run_time=run_time, **(params or {}))

    @classmethod
    def step_names(cls) -> list[str]:
        return [n for n in dir(cls) if getattr(getattr(cls, n), "_is_step", False)]

    # -- pacing ------------------------------------------------------------

    def mark_continuous(self, start: float, end: float) -> None:
        self._continuous.append((start, end))

    def continuous_spans(self) -> list[tuple[float, float]]:
        return list(self._continuous)

    # -- helpers -----------------------------------------------------------

    def color(self, name: str | None):
        from manim import ManimColor

        return ManimColor(self.channel.resolve_color(name))


_REGISTRY: dict[str, type[Primitive]] = {}


def register(name: str):
    def deco(cls: type[Primitive]) -> type[Primitive]:
        _REGISTRY[name] = cls
        return cls

    return deco


def _import_optional() -> None:
    """Import real primitive modules that supersede planned stubs, if present."""
    for mod in ("axes_plot", "supply_demand", "linear_system"):
        try:
            __import__(f"drawn_board.primitives.{mod}")
        except ModuleNotFoundError:
            pass


def get_primitive(name: str) -> type[Primitive]:
    # import side-effect modules so registrations happen. `stubs` is imported
    # first so real modules below override the planned-stub registration.
    from drawn_board.primitives import (  # noqa: F401
        gyroscope,
        stubs,  # noqa: F401
        vectors,
        vectors3d,
        wheel,
    )
    _import_optional()

    if name not in _REGISTRY:
        raise ValueError(
            f"unknown primitive {name!r}; registered: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


def load_custom(repo_root, channel: str, code: str, class_name: str) -> type[Primitive]:
    """Load a custom primitive class from channels/<channel>/lessons/<CODE>.py."""
    import importlib.util
    from pathlib import Path

    path = Path(repo_root) / "channels" / channel / "lessons" / f"{code}.py"
    if not path.is_file():
        raise FileNotFoundError(f"custom animation module not found: {path}")
    spec = importlib.util.spec_from_file_location(f"lesson_{code}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, class_name, None)
    if cls is None or not issubclass(cls, Primitive):
        raise ValueError(f"{path} has no Primitive subclass named {class_name!r}")
    return cls
