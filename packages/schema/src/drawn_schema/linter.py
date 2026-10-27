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
from drawn_schema.placeholders import (
    PLACEHOLDER_RE,
    count_words,
    iter_placeholders,
    substitute,
)


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

    from drawn_schema.placeholders import iter_highlights

    for hid in iter_highlights(scene.narration):
        if hid not in id_set:
            result.error(
                f"scene {scene.id!r}: highlight {{hl:{hid}}} references {hid!r} "
                f"but no board item or step has that id"
            )

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


# ~words spoken in 3 s at Kokoro's ~175 wpm; past this the board sits empty too
# long before the first draw. A pre-flight estimate; the render's pacing check
# (which uses real word timings, and exempts 3D/continuous scenes) is final.
_MAX_LEADIN_WORDS = 9


def _check_leadin(scene: Scene, result: LintResult, speed: float = 1.0) -> None:
    """Estimate when the first visual appears and mirror CI's 3s pacing gate.

    The render's pacing check (post-TTS) fails a scene whose first ``{id}`` lands
    more than 3 s into the audio. Estimate that time here from the recalibrated
    speech rate so the failure surfaces at ``just lint`` instead of mid-render.
    """
    from drawn_schema.lesson import wpm_for_kind

    if scene.kind in ("title", "end"):
        return
    match = PLACEHOLDER_RE.search(scene.narration)
    if match is None:
        return
    lead_words = count_words(scene.narration[: match.start()])
    secs = lead_words / (wpm_for_kind(scene.kind) * speed) * 60.0
    first = f"{{{match.group(1)}}}"
    if secs > 3.0:
        result.error(
            f"scene {scene.id!r}: ~{secs:.1f}s before the first visual {first} "
            f"(CI fails > 3s) — open the scene on a draw/plot within ~6 words"
        )
    elif secs > 2.4:
        result.warn(
            f"scene {scene.id!r}: ~{secs:.1f}s before the first visual {first} — "
            f"close to the 3s limit; move it earlier to be safe"
        )


def _spoken_narration(scene: Scene, pronounce_map: dict | None = None) -> str:
    from drawn_schema import pronounce as _pron

    spoken = dict(scene.placeholders())
    text = substitute(scene.narration, spoken)
    return _pron.apply(text, pronounce_map or {})


def _scene_seconds(scene: Scene, pronounce_map: dict, speed: float = 1.0) -> float:
    """Estimated spoken time at the given voice speed.

    Words at the kind's calibrated 1x rate (scaled by the channel's ``speed``),
    plus explicit ``{pause:N}`` and the per-equation read-holds (which are 0 now
    that formulae are spoken inline).
    """
    from drawn_schema.lesson import (
        EQUATION_POST_PAUSE,
        EQUATION_PRE_PAUSE,
        wpm_for_kind,
    )
    from drawn_schema.placeholders import PAUSE_RE

    words = count_words(_spoken_narration(scene, pronounce_map))
    speech = words / (wpm_for_kind(scene.kind) * speed) * 60.0
    pauses = sum(float(m.group(1)) for m in PAUSE_RE.finditer(scene.narration))
    pauses += scene.equation_count() * (EQUATION_PRE_PAUSE + EQUATION_POST_PAUSE)
    return speech + pauses


def _channel_speed(repo_root: Path | None, channel: str) -> float:
    """The channel's Kokoro playback speed (for the runtime estimate)."""
    if repo_root is None:
        return 1.0
    try:
        from drawn_schema.channel import load_channel

        return float(load_channel(repo_root, channel).voice.speed)
    except Exception:  # noqa: BLE001 — estimate must never crash the linter
        return 1.0


def _check_runtime(
    lesson: Lesson, result: LintResult, pronounce_map: dict, speed: float = 1.0
) -> None:
    est = sum(_scene_seconds(s, pronounce_map, speed) for s in lesson.scenes)
    est_min = est / 60.0
    target = lesson.target_minutes
    lo = target * (1 - WORD_BUDGET_TOLERANCE)
    hi = target * (1 + WORD_BUDGET_TOLERANCE)
    if not (lo <= est_min <= hi):
        result.error(
            f"estimated runtime {est_min:.1f} min (speech + pauses at per-kind "
            f"wpm); target {target} min allows {lo:.1f}–{hi:.1f} min"
        )


def _check_animations(lesson: Lesson, repo_root: Path | None, result: LintResult) -> None:
    # title/end are full-frame cards; derivation and problem scenes are
    # hand-written step by step (the hand is the moving object). None of these
    # need a separate animation block.
    _no_anim = ("title", "end", "derivation", "problem")
    needs_anim = [s for s in lesson.scenes if s.kind not in _no_anim]
    for scene in needs_anim:
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
    # named laws / proper nouns in narration (capitalised, not sentence-initial).
    # Strip {id} placeholders and {pause}/{hl} tokens first so their ids are not
    # mistaken for words (and so sentence boundaries survive).
    from drawn_schema.placeholders import PLACEHOLDER_RE, strip_control

    narration = "\n".join(
        PLACEHOLDER_RE.sub(" ", strip_control(s.narration)) for s in lesson.scenes
    )
    for name in sorted(_pron.proper_nouns(narration)):
        if name.lower() not in {k.lower() for k in pronounce_map}:
            result.warn(
                f"proper noun {name!r} has no entry in "
                f"channels/{lesson.channel}/pronounce.yaml (check its pronunciation)"
            )


# Phrases banned outright — narrative/hype framing has no place in the script.
_BANNED = [
    "imagine", "journey", "story", "magic", "magical", "let's dive in",
    "dive in", "in this video", "hey guys", "let's get started", "buckle up",
    "fasten your seat", "mind-blowing", "mind blowing", "awesome", "amazing",
]


def _check_tone(scene: Scene, result: LintResult) -> None:
    low = scene.narration.lower()
    for phrase in _BANNED:
        if phrase in low:
            result.error(
                f"scene {scene.id!r}: banned framing {phrase!r} — write plainly "
                f"and declaratively, as an expert would"
            )
    questions = scene.narration.count("?")
    if questions > 1:
        result.warn(
            f"scene {scene.id!r}: {questions} questions — avoid rhetorical "
            f"questions as filler; prefer declarative statements"
        )


def _check_publish(lesson: Lesson, result: LintResult) -> None:
    """Every lesson needs YouTube publishing metadata (title/description/hashtags)."""
    p = lesson.publish
    if p is None:
        result.warn(
            "no 'publish' block — the upload bundle (meta.md) will fall back to "
            "derived title/description/tags; add publish.title, publish.summary, "
            "publish.hashtags and publish.tags for a proper YouTube listing"
        )
        return
    if len(p.title) > 100:
        result.error(f"publish.title is {len(p.title)} chars; YouTube caps titles at 100")
    for h in p.hashtags:
        if not h.startswith("#") or " " in h:
            result.error(f"publish hashtag {h!r} must start with '#' and contain no spaces")
    if p.hashtags and len(p.hashtags) > 5:
        result.warn("more than 5 hashtags — YouTube ignores the extras; keep the best 2–4")


def _check_thumbnail(lesson: Lesson, result: LintResult) -> None:
    """Every lesson needs a punchy thumbnail hook (not the dull full title)."""
    t = lesson.thumbnail
    if t is None:
        result.warn(
            "no 'thumbnail' hook — the thumbnail falls back to the full title, "
            "which is dull; add thumbnail.hook (a short, click-worthy line) and "
            "thumbnail.keyword to highlight"
        )
        return
    n = len(t.hook.split())
    if n > 7:
        result.warn(f"thumbnail hook is {n} words; keep it punchy (<= ~6)")
    if t.keyword and t.keyword.lower() not in t.hook.lower():
        result.error(f"thumbnail keyword {t.keyword!r} is not a substring of the hook")


def _check_problems(lesson: Lesson, result: LintResult) -> None:
    from drawn_schema.checks import eval_check

    for scene in lesson.scenes:
        if scene.check is None:
            continue
        res = eval_check(scene.check.expr, scene.check.value, scene.check.tol)
        if not res.ok:
            result.error(f"scene {scene.id!r}: {res.message}")


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

    speed = _channel_speed(repo_root, lesson.channel)
    for scene in lesson.scenes:
        _check_scene_placeholders(scene, result)
        _check_leadin(scene, result, speed)
        _check_tone(scene, result)
    _check_animations(lesson, repo_root, result)
    _check_pronounce(lesson, pronounce_map, result)
    _check_problems(lesson, result)
    _check_runtime(lesson, result, pronounce_map, speed)
    _check_thumbnail(lesson, result)
    _check_publish(lesson, result)
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
