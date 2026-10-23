"""Pydantic models for the Lesson contract.

A Lesson is one YAML file per video. Board items are referenced inline in the
scene narration as ``{id}`` placeholders (see :mod:`drawn_schema.placeholders`).
The schema is versioned via :data:`SCHEMA_VERSION`; the linter rejects files
that declare a different version so the contract can evolve safely.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

SCHEMA_VERSION = 1

SceneKind = Literal["title", "board", "derivation", "graph", "summary", "end"]

# Words per minute used to turn target_minutes into a word budget.
WORDS_PER_MINUTE = 145
# Allowed fractional deviation from the budget before the linter fails.
WORD_BUDGET_TOLERANCE = 0.15


class BoardItem(BaseModel):
    """A single thing written on the board.

    Exactly one of ``latex`` or ``text`` must be set. ``latex`` items are
    rendered as MathTex (standard LaTeX) and must carry a ``say`` describing how
    the formula is spoken. ``text`` items are prose written in the handwriting
    font; their ``say`` is optional (and substitutes to nothing when absent).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    latex: str | None = None
    text: str | None = None
    say: str | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> BoardItem:
        has_latex = self.latex is not None
        has_text = self.text is not None
        if has_latex == has_text:
            raise ValueError(
                f"board item {self.id!r} must set exactly one of 'latex' or 'text'"
            )
        if has_latex and not (self.say and self.say.strip()):
            raise ValueError(f"latex board item {self.id!r} requires a non-empty 'say'")
        return self

    @property
    def is_latex(self) -> bool:
        return self.latex is not None

    @property
    def spoken(self) -> str:
        """The text substituted into narration for this item ('' when silent)."""
        return self.say or ""


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    book: str
    section: str
    license: str


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: SceneKind
    narration: str = ""
    board: list[BoardItem] = []


class Lesson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    id: str
    channel: str
    title: str
    target_minutes: float
    source: Source
    scenes: list[Scene]

    @property
    def word_budget(self) -> int:
        return round(self.target_minutes * WORDS_PER_MINUTE)
