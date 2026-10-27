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

SceneKind = Literal[
    "title", "board", "derivation", "diagram", "graph", "problem", "summary", "end"
]

BoardRole = Literal["statement", "given", "find", "step", "answer"]

# Speaking pace by scene kind. Derivations and worked problems are slower so the
# viewer can follow each line; explainers run at the normal pace.
DEFAULT_WPM = 140
WPM_BY_KIND = {"derivation": 125, "problem": 125}
# Allowed fractional deviation from the estimated runtime before the linter fails.
WORD_BUDGET_TOLERANCE = 0.15
# Formulae are now spoken inline (no isolated synthesis, no splice silence), so
# there is no automatic silence around an equation — the voice flows naturally.
# Use an explicit ``{pause:N}`` token where a deliberate gap is wanted.
EQUATION_PRE_PAUSE = 0.0
EQUATION_POST_PAUSE = 0.0

# Kept for backwards compatibility with older callers.
WORDS_PER_MINUTE = DEFAULT_WPM


def wpm_for_kind(kind: str) -> int:
    return WPM_BY_KIND.get(kind, DEFAULT_WPM)


class LegendEntry(BaseModel):
    """One row of a symbol legend shown beside an equation."""

    model_config = ConfigDict(extra="forbid")

    sym: str  # LaTeX symbol, e.g. "\\omega"
    name: str  # plain-words meaning, e.g. "spin rate"
    unit: str | None = None  # e.g. "rad/s"


class BoardItem(BaseModel):
    """A single thing written on the board.

    Exactly one of ``latex`` or ``text`` must be set. ``latex`` items are
    rendered as MathTex (standard LaTeX) and must carry a ``say`` describing how
    the formula is spoken. ``text`` items are prose written in the handwriting
    font; their ``say`` is optional (and substitutes to nothing when absent).
    ``color`` names an accent (or a hex) so a quantity keeps one colour.
    ``legend`` names each symbol (with unit) beside an equation; ``role`` marks
    a line's part in a worked problem; ``box`` frames a boxed answer.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    latex: str | None = None
    text: str | None = None
    say: str | None = None
    color: str | None = None
    # optional per-substring colours for a latex item, e.g. {"r m g": "orange"}
    tex_colors: dict[str, str] | None = None
    legend: list[LegendEntry] | None = None
    role: BoardRole | None = None
    box: bool = False

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
    def is_equation(self) -> bool:
        """A latex item that is not a short label — gets automatic read pauses."""
        return self.is_latex and "=" in (self.latex or "")

    @property
    def spoken(self) -> str:
        """The text substituted into narration for this item ('' when silent)."""
        return self.say or ""


class AnimationStep(BaseModel):
    """One triggerable step of a diagram animation.

    ``action`` names a method the primitive (or custom class) exposes. The
    step's ``id`` is a ``{id}`` placeholder in the narration — its alignment
    time is when the step fires. ``say`` is optional (substitutes to nothing).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    action: str
    params: dict = {}
    say: str | None = None
    color: str | None = None

    @property
    def spoken(self) -> str:
        return self.say or ""


class Animation(BaseModel):
    """A diagram animation: a registered primitive or a per-lesson custom class.

    Exactly one of ``primitive`` or ``custom`` must be set. ``custom`` is a
    class name defined in ``lessons/<CODE>.py``.
    """

    model_config = ConfigDict(extra="forbid")

    primitive: str | None = None
    custom: str | None = None
    params: dict = {}
    steps: list[AnimationStep] = []

    @model_validator(mode="after")
    def _check_shape(self) -> Animation:
        if (self.primitive is None) == (self.custom is None):
            raise ValueError("animation must set exactly one of 'primitive' or 'custom'")
        return self


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    book: str
    section: str
    license: str
    file: str | None = None  # key into sources/manifest.yaml (extracted text)
    pages: str | None = None  # e.g. "540-546"


class Check(BaseModel):
    """A numeric self-check for a worked problem.

    ``expr`` is a Python expression (numpy / sympy / math namespace) that
    recomputes the answer; the linter evaluates it and fails if it disagrees
    with ``value`` by more than ``tol`` (fractional).
    """

    model_config = ConfigDict(extra="forbid")

    expr: str
    value: float
    unit: str | None = None
    tol: float = 0.01


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: SceneKind
    narration: str = ""
    board: list[BoardItem] = []
    animation: Animation | None = None
    check: Check | None = None  # worked-problem numeric check

    @model_validator(mode="after")
    def _check_kind(self) -> Scene:
        if self.kind in ("title", "end") and self.animation is not None:
            raise ValueError(
                f"scene {self.id!r}: {self.kind} cards take no animation "
                f"(they are full-frame cards, never drawn over)"
            )
        if self.kind == "problem":
            if self.check is None:
                raise ValueError(f"problem scene {self.id!r} requires a 'check' block")
            if not any(it.role == "answer" for it in self.board):
                raise ValueError(
                    f"problem scene {self.id!r} needs a board item with role 'answer'"
                )
        return self

    def placeholders(self) -> list[tuple[str, str]]:
        """All referenceable ids with their spoken substitution, in order.

        Board items first, then animation steps. Both participate in the
        ``{id}`` placeholder system (bijection enforced by the linter).
        """
        out: list[tuple[str, str]] = [(it.id, it.spoken) for it in self.board]
        if self.animation:
            out.extend((s.id, s.spoken) for s in self.animation.steps)
        return out

    def equation_count(self) -> int:
        return sum(1 for it in self.board if it.is_equation)


class Thumbnail(BaseModel):
    """A click-worthy thumbnail: a short, punchy hook, not the full title.

    ``hook`` is a provocative or curiosity-driven line of at most ~6 words (big
    and bold on the thumbnail). ``keyword`` is a word or phrase inside the hook
    rendered in the channel's accent colour for pop. ``kicker`` is a tiny label
    above the hook (the topic, e.g. "MICROECONOMICS").
    """

    model_config = ConfigDict(extra="forbid")

    hook: str
    keyword: str | None = None
    kicker: str | None = None


class Lesson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    id: str
    channel: str
    title: str
    target_minutes: float
    source: Source
    thumbnail: Thumbnail | None = None
    scenes: list[Scene]

    @property
    def word_budget(self) -> int:
        return round(self.target_minutes * WORDS_PER_MINUTE)
