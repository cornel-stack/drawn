"""Layout engine: a stacked frame must not overlap or leave the safe area."""

import pytest

manim = pytest.importorskip("manim")


def _text(s):
    from manim import Text

    return Text(s, font_size=46)


def test_stack_no_overlap_and_in_frame():
    from drawn_board.layout import check_layout, stack_items
    from manim import config

    fw, fh = config.frame_width, config.frame_height
    items = [_text(s) for s in ["first line", "second line here", "third", "fourth row"]]
    group = stack_items(items, align_equals=False, frame_width=fw, frame_height=fh)
    assert check_layout(group, fw, fh) == []


def test_oversized_stack_is_scaled_into_frame():
    from drawn_board.layout import check_layout, stack_items
    from manim import config

    fw, fh = config.frame_width, config.frame_height
    # many long lines would overflow; the engine must scale them to fit
    items = [_text("a reasonably long line of text " * 2) for _ in range(8)]
    group = stack_items(items, align_equals=False, frame_width=fw, frame_height=fh)
    assert check_layout(group, fw, fh) == []
