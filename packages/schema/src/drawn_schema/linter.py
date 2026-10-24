"""Lesson linter.

Separates hard failures (``errors``) from advisories (``warnings``). The CLI
exits non-zero only on errors.

Errors
------
* wrong ``schema_version``
* structural / pydantic validation failure
* a latex item without ``say`` (also enforced by the model)
* duplicate board-item ids within a scene
* a ``{id}`` placeholder that resolves to no item in its scene
* a board item not referenced exactly once by its scene narration
* total narration words (after substitution) outside ±15 % of the budget
* invalid LaTeX (when a ``latex`` binary is available)
* a licence that is not in the CC-BY family

Warnings
--------
* NC licence variants (CC BY-NC, CC BY-NC-SA, …) — to be swapped later
* LaTeX compile check skipped because no ``latex`` binary was found
* channel directory missing / lesson id absent from the channel backlog
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from drawn_schema.lesson import (
    SCHEMA_VERSION,
    WORD_BUDGET_TOLERANCE,
    Lesson,
    Scene,
)
from drawn_schema.placeholders import count_words, iter_placeholders, substitute


@dataclass
class LintResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def _check_scene_placeholders(scene: Scene, result: LintResult) -> None:
    # Board items and animation steps share one {id} namespace.
    ids = [pid for pid, _ in scene.placeholders()]
    dupes = [i for i, n in Counter(ids).items() if n > 1]
    for i in dupes:
        result.error(f"scene {scene.id!r}: duplicate placeholder id {i!r}")

    id_set = set(ids)
    refs = list(iter_placeholders(scene.narration))
    ref_counts = Counter(refs)

    for ref in ref_counts:
        if ref not in id_set:
            result.error(
                f"scene {scene.id!r}: narration references {{{ref}}} "
                f"but no board item or animation step has that id"
            )
    for item_id in ids:
        n = ref_counts.get(item_id, 0)
        if n == 0:
            result.error(
                f"scene {scene.id!r}: {item_id!r} is never "
                f"referenced as {{{item_id}}} in the narration"
            )
        elif n > 1:
            result.error(
                f"scene {scene.id!r}: {item_id!r} is referenced "
                f"{n} times; each item must be referenced exactly once"
            )


def _spoken_narration(scene: Scene, pronounce_map: dict | None = None) -> str:
    from drawn_schema import pronounce as _pron

    spoken = dict(scene.placeholders())
    text = substitute(scene.narration, spoken)
    return _pron.apply(text, pronounce_map or {})


def _check_word_budget(lesson: Lesson, result: LintResult, pronounce_map: dict) -> None:
    total = sum(count_words(_spoken_narration(s, pronounce_map)) for s in lesson.scenes)
    budget = lesson.word_budget
    lo = round(budget * (1 - WORD_BUDGET_TOLERANCE))
    hi = round(budget * (1 + WORD_BUDGET_TOLERANCE))
    if not (lo <= total <= hi):
        result.error(
            f"narration is {total} words; target {lesson.target_minutes} min "
            f"gives a budget of {budget} (allowed {lo}–{hi})"
        )


def _check_animations(lesson: Lesson, repo_root: Path | None, result: LintResult) -> None:
    non_end = [s for s in lesson.scenes if s.kind != "end"]
    for scene in non_end:
        if scene.animation is None:
            result.warn(
                f"scene {scene.id!r} ({scene.kind}) has no animation block; "
                f"every non-end scene should carry an animated diagram"
            )
    if repo_root is None:
        return
    custom_module = repo_root / "channels" / lesson.channel / "lessons" / f"{lesson.id}.py"
    for scene in lesson.scenes:
        if scene.animation and scene.animation.custom and not custom_module.is_file():
            result.error(
                f"scene {scene.id!r}: animation custom="
                f"{scene.animation.custom!r} but {custom_module} does not exist"
            )


def _check_pronounce(lesson: Lesson, pronounce_map: dict, result: LintResult) -> None:
    from drawn_schema import pronounce as _pron

    latex_strings = [
        item.latex for s in lesson.scenes for item in s.board if item.is_latex
    ]
    for sym in sorted(_pron.missing_symbols(latex_strings, pronounce_map)):
        result.warn(
            f"LaTeX symbol {sym!r} has no entry in "
            f"channels/{lesson.channel}/pronounce.yaml"
        )


def _check_licence(lesson: Lesson, result: LintResult) -> None:
    lic = lesson.source.license.upper().replace("CREATIVE COMMONS", "CC")
    norm = lic.replace(".", " ").replace("-", " ")
    if "NC" in norm.split() or "NONCOMMERCIAL" in norm:
        result.warn(
            f"source licence {lesson.source.license!r} is a NonCommercial "
            f"variant; swap for a CC BY / CC BY-SA source before publishing"
        )
        return
    if "CC" in norm.split() and "BY" in norm.split():
        return  # CC BY or CC BY-SA
    result.error(
        f"source licence {lesson.source.license!r} is not in the CC-BY family "
        f"(accepted: CC BY, CC BY-SA)"
    )


def _check_latex(lesson: Lesson, result: LintResult) -> None:
    latex_bin = shutil.which("latex")
    items = [
        (s.id, item) for s in lesson.scenes for item in s.board if item.is_latex
    ]
    if not items:
        return
    if latex_bin is None:
        result.warn(
            "no 'latex' binary found; skipped LaTeX compile check "
            "(install TeX Live to enable it)"
        )
        return
    preamble = (
        "\\documentclass[preview]{standalone}\n"
        "\\usepackage{amsmath,amssymb}\n"
        "\\begin{document}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        for scene_id, item in items:
            tex = f"{preamble}$\\displaystyle {item.latex}$\n\\end{{document}}\n"
            src = Path(tmp) / "snippet.tex"
            src.write_text(tex)
            proc = subprocess.run(
                [latex_bin, "-halt-on-error", "-interaction=nonstopmode", src.name],
                cwd=tmp,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                detail = _first_tex_error(proc.stdout)
                result.error(
                    f"scene {scene_id!r} item {item.id!r}: LaTeX failed to "
                    f"compile {item.latex!r} ({detail})"
                )


def _first_tex_error(log: str) -> str:
    for line in log.splitlines():
        if line.startswith("!"):
            return line.strip()
    return "see TeX log"


def _check_backlog(lesson: Lesson, repo_root: Path | None, result: LintResult) -> None:
    if repo_root is None:
        return
    channel_dir = repo_root / "channels" / lesson.channel
    if not channel_dir.is_dir():
        result.warn(
            f"channel directory channels/{lesson.channel} not found; "
            f"cannot verify lesson id against a backlog"
        )
        return
    backlog = channel_dir / "backlog.yaml"
    if not backlog.is_file():
        result.warn(f"channels/{lesson.channel}/backlog.yaml not found")
        return
    rows = yaml.safe_load(backlog.read_text()) or []
    codes = {row.get("code") for row in rows}
    if lesson.id not in codes:
        result.warn(
            f"lesson id {lesson.id!r} is not in "
            f"channels/{lesson.channel}/backlog.yaml"
        )


def lint_lesson(data: dict, repo_root: Path | None = None) -> LintResult:
    """Lint an already-parsed lesson mapping."""
    result = LintResult()

    declared = data.get("schema_version")
    if declared != SCHEMA_VERSION:
        result.error(
            f"schema_version {declared!r} is not supported "
            f"(this build expects {SCHEMA_VERSION})"
        )

    try:
        lesson = Lesson.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            result.error(f"{loc}: {err['msg']}")
        return result  # cannot run semantic checks on an invalid structure

    pronounce_map = {}
    if repo_root is not None:
        from drawn_schema import pronounce as _pron

        pronounce_map = _pron.load_pronounce(repo_root, lesson.channel)

    for scene in lesson.scenes:
        _check_scene_placeholders(scene, result)
    _check_animations(lesson, repo_root, result)
    _check_pronounce(lesson, pronounce_map, result)
    _check_word_budget(lesson, result, pronounce_map)
    _check_licence(lesson, result)
    _check_latex(lesson, result)
    _check_backlog(lesson, repo_root, result)
    return result


def lint_lesson_file(path: str | Path, repo_root: Path | None = None) -> LintResult:
    path = Path(path)
    data = yaml.safe_load(path.read_text())
    if repo_root is None:
        repo_root = _find_repo_root(path)
    return lint_lesson(data, repo_root=repo_root)


def _find_repo_root(path: Path) -> Path | None:
    for parent in path.resolve().parents:
        if (parent / "channels").is_dir() and (parent / "CLAUDE.md").is_file():
            return parent
    return None
