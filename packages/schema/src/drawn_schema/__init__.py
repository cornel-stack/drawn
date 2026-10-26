"""Versioned Lesson schema and linter for drawn."""

from drawn_schema.channel import (
    BoardStyle,
    ChannelConfig,
    FontConfig,
    VoiceConfig,
    load_channel,
)
from drawn_schema.lesson import (
    SCHEMA_VERSION,
    Animation,
    AnimationStep,
    BoardItem,
    Check,
    LegendEntry,
    Lesson,
    Scene,
    Source,
)
from drawn_schema.linter import LintResult, lint_lesson, lint_lesson_file
from drawn_schema.placeholders import PLACEHOLDER_RE, iter_placeholders, substitute

__all__ = [
    "SCHEMA_VERSION",
    "Animation",
    "AnimationStep",
    "BoardItem",
    "Check",
    "LegendEntry",
    "Lesson",
    "Scene",
    "Source",
    "BoardStyle",
    "ChannelConfig",
    "FontConfig",
    "VoiceConfig",
    "load_channel",
    "LintResult",
    "lint_lesson",
    "lint_lesson_file",
    "PLACEHOLDER_RE",
    "iter_placeholders",
    "substitute",
]
