"""Registered-but-not-yet-built primitives.

Each is reserved in the registry so lessons can reference it and so adding the
real implementation is mechanical (drop a module, move the name out of here).
Referencing one today fails with a clear message at render time.
"""

from __future__ import annotations

from drawn_board.primitives.base import Primitive, register

_PLANNED = [
    "pendulum",
    "mass_spring",
    "projectile",
    "free_body",
    "number_line",
    "field_arrows",
    "circuit_current",
    "linear_transform",  # matrix acting on a grid
]


def _make_stub(name: str) -> type[Primitive]:
    class _Stub(Primitive):
        _planned_name = name

        def build(self) -> None:
            raise NotImplementedError(
                f"primitive {self._planned_name!r} is planned but not yet "
                f"implemented; build it in packages/board/primitives or use a "
                f"custom= animation for now"
            )

    _Stub.__name__ = f"Planned_{name}"
    return _Stub


for _name in _PLANNED:
    register(_name)(_make_stub(_name))
