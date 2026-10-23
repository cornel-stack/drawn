"""Manim scene library: data-driven handwriting board with hand-follow."""

from drawn_board.quality import QUALITIES, quality_config
from drawn_board.render import render_all, render_scene

__all__ = ["QUALITIES", "quality_config", "render_scene", "render_all"]
