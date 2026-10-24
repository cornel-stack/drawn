"""Auto-layout for board items: vertical stack within the safe area.

Stacks mobjects top-to-bottom, left-aligned, with derivations aligned on their
``=`` sign. Scales the group to fit inside the 5 % safe margins. Exposes
:func:`check_layout` so a test can assert nothing overlaps or leaves the frame.
"""

from __future__ import annotations

from drawn_board.style import (
    SAFE_MARGIN_FRAC,
    STACK_BUFF,
    usable_height,
    usable_width,
)


def stack_items(mobjects: list, *, align_equals: bool, frame_width: float, frame_height: float):
    """Arrange mobjects into a left-aligned vertical stack, fit to safe area.

    Returns the positioned VGroup (mobjects are modified in place).
    """
    from manim import LEFT, VGroup

    group = VGroup(*mobjects)
    group.arrange(_down(), aligned_edge=LEFT, buff=STACK_BUFF)

    if align_equals:
        _align_on_equals(mobjects)

    uw = usable_width(frame_width)
    uh = usable_height(frame_height)
    if group.width > uw:
        group.scale_to_fit_width(uw)
    if group.height > uh:
        group.scale_to_fit_height(uh)
    group.move_to(_origin())
    return group


def _align_on_equals(mobjects: list) -> None:
    """Shift each mobject horizontally so its first '=' shares one x position."""
    xs = []
    for m in mobjects:
        eq = _equals_submobject(m)
        xs.append(eq.get_center()[0] if eq is not None else None)
    anchor = max((x for x in xs if x is not None), default=None)
    if anchor is None:
        return
    for m, x in zip(mobjects, xs, strict=False):
        if x is not None:
            m.shift(_right() * (anchor - x))


def _equals_submobject(mobject):
    """Return the '=' glyph submobject if this mobject was built with it isolated."""
    return getattr(mobject, "_equals_glyph", None)


def check_layout(group, frame_width: float, frame_height: float) -> list[str]:
    """Return a list of layout violations (empty == OK).

    Flags items whose bounding boxes leave the safe frame or overlap each other.
    """

    problems: list[str] = []
    half_w = frame_width * (0.5 - SAFE_MARGIN_FRAC)
    half_h = frame_height * (0.5 - SAFE_MARGIN_FRAC)
    boxes = []
    for i, m in enumerate(group.submobjects):
        left = m.get_left()[0]
        right = m.get_right()[0]
        top = m.get_top()[1]
        bottom = m.get_bottom()[1]
        boxes.append((left, right, bottom, top))
        if left < -half_w - 1e-6 or right > half_w + 1e-6:
            problems.append(f"item {i} exceeds horizontal safe margin")
        if bottom < -half_h - 1e-6 or top > half_h + 1e-6:
            problems.append(f"item {i} exceeds vertical safe margin")

    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            li, ri, bi, ti = boxes[i]
            lj, rj, bj, tj = boxes[j]
            overlap_x = min(ri, rj) - max(li, lj)
            overlap_y = min(ti, tj) - max(bi, bj)
            if overlap_x > 1e-3 and overlap_y > 1e-3:
                problems.append(f"items {i} and {j} overlap")
    return problems


def _down():
    from manim import DOWN

    return DOWN


def _right():
    from manim import RIGHT

    return RIGHT


def _origin():
    from manim import ORIGIN

    return ORIGIN
