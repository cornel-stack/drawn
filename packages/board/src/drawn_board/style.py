"""Legibility constants (Phase 1.5 bar).

Manim sizes are in frame units (frame_height = 8), so a given ``font_size`` and
``stroke_width`` compose identically at preview and final; preview is just
lower resolution. These values are chosen so that at 1080p they clear the
minimums: MathTex >= 60, Text >= 44, titles >= 72, stroke >= 3 px.
"""

from __future__ import annotations

# Font sizes (Manim points; >= the 1080p minimums).
TITLE_FONT_SIZE = 72
FORMULA_FONT_SIZE = 64
TEXT_FONT_SIZE = 46
LABEL_FONT_SIZE = 40  # small diagram labels

# Written-stroke thickness. MathTex/Text are filled glyphs; a light stroke in
# the ink colour guarantees >= 3 px at 1080p and keeps Kalam looking bold.
GLYPH_STROKE_WIDTH = 3.0

# 5 % safe margins on every side. Frame is 14.222 x 8 units at 16:9.
SAFE_MARGIN_FRAC = 0.05

# Board capacity before the oldest items are retired.
MAX_FORMULA_LINES = 4
MAX_TEXT_LINES = 6

# Diagram-scene layout. The frame is 8 units tall (y in [-4, 4]); the bottom
# ~14 % is the caption band. A diagram scene's formula/legend sits in a top band
# centred at FORMULA_BAND_Y, and the animation draws in the region below it
# (centred at ANIM_CENTER, sized ANIM_WIDTH x ANIM_HEIGHT) so the two never
# overlap.
FORMULA_BAND_Y = 3.05
ANIM_CENTER = (0.0, -0.95, 0.0)
ANIM_WIDTH = 8.6
ANIM_HEIGHT = 3.5

# Path wobble capped to <= 1 px at 1080p (1 px = 8/1080 units ~ 0.0074).
# Effectively off: legibility comes from Write + the hand, not glyph distortion.
WOBBLE_AMPLITUDE_UNITS = 0.0

# Vertical gap between stacked items (units).
STACK_BUFF = 0.45

# Writing pace. The pen traces at a human speed: time scales with how much is
# being written (glyph count), clamped. Hand and ink are locked to this.
WRITE_SECONDS_PER_GLYPH = 0.22
WRITE_MIN_SECONDS = 1.2
WRITE_MAX_SECONDS = 4.0
HAND_ENTER_SECONDS = 0.35
HAND_LIFT_SECONDS = 0.35


def usable_width(frame_width: float) -> float:
    return frame_width * (1 - 2 * SAFE_MARGIN_FRAC)


def usable_height(frame_height: float) -> float:
    return frame_height * (1 - 2 * SAFE_MARGIN_FRAC)
