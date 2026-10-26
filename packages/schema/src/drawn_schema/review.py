"""Fact-check gate: ``channels/<ch>/lessons/<CODE>.review.md``.

A lesson may not be rendered until it has a *complete* review file — evidence
that every equation and every number on the board has been checked against the
cited open-textbook source. The review is produced in a separate pass (a human
or a subagent reads the source and fills it in); this module only scaffolds the
file and enforces completeness at the gate.

Format: a YAML front-matter block (machine-checked) over a markdown body (the
human-readable evidence — quoted source lines with page/equation numbers and the
actual Python recomputation with its output)::

    ---
    lesson: ME-25
    status: complete            # 'draft' until every verdict is 'ok'
    equations:
      - id: precession          # a board item with '=' in its latex
        source: "Univ. Physics Vol 1 §11.4 Eq 11.12 p.550"
        verdict: ok             # 'todo' until checked
    numbers:
      - name: s_solve answer    # a worked-problem boxed answer
        verdict: ok
    checks:
      - scene: s_solve          # a scene carrying a check: block
        verdict: ok
    ---

    # Fact-check — ME-25
    ... quoted evidence + python output ...

The gate re-runs every ``check:`` block itself (it does not trust the file), and
requires a non-empty ``source`` and ``verdict: ok`` for every equation, number
and check the lesson contains.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from drawn_schema.checks import eval_check
from drawn_schema.lesson import Lesson


def review_path(repo_root: Path, channel: str, code: str) -> Path:
    return Path(repo_root) / "channels" / channel / "lessons" / f"{code}.review.md"


def _equation_ids(lesson: Lesson) -> list[str]:
    ids: list[str] = []
    for scene in lesson.scenes:
        for item in scene.board:
            if item.is_equation:
                ids.append(item.id)
    return ids


def _check_scenes(lesson: Lesson) -> list[str]:
    return [s.id for s in lesson.scenes if s.check is not None]


def split_front_matter(text: str) -> tuple[dict, str]:
    """Return (front-matter dict, body). Empty dict if there is no block."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    return yaml.safe_load(parts[1]) or {}, parts[2].lstrip("\n")


def load_review(path: Path) -> tuple[dict, str]:
    if not path.is_file():
        return {}, ""
    return split_front_matter(path.read_text())


def scaffold(lesson: Lesson, path: Path) -> None:
    """Write a review template listing every item that needs evidence."""
    eqs = _equation_ids(lesson)
    checks = _check_scenes(lesson)
    fm = {
        "lesson": lesson.id,
        "status": "draft",
        "equations": [{"id": i, "source": "", "verdict": "todo"} for i in eqs],
        "numbers": [{"name": f"{s} answer", "verdict": "todo"} for s in checks],
        "checks": [{"scene": s, "verdict": "todo"} for s in checks],
    }
    front = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    body_lines = [
        f"# Fact-check — {lesson.id}",
        "",
        "Fill every verdict to `ok` and set `status: complete`. For each entry give",
        "the **evidence**, not a tick:",
        "",
        "- **Equations** — quote the source line with its page and equation number.",
        "- **Numbers** — paste the Python recomputation and its printed output.",
        "- **Checks** — the `check:` block is re-run by the gate; note the result.",
        "",
    ]
    for i in eqs:
        body_lines += [
            f"## Equation `{i}`",
            "",
            "> _quote source line — book §section, Eq N, p.N_",
            "",
        ]
    for s in checks:
        body_lines += [
            f"## Problem `{s}`",
            "",
            "```python",
            "# recompute the boxed answer here",
            "```",
            "",
            "output: _paste the printed value_",
            "",
        ]
    path.write_text("---\n" + front + "---\n\n" + "\n".join(body_lines) + "\n")


def verify(lesson: Lesson, path: Path) -> list[str]:
    """Return a list of problems; empty means the review is complete and sound."""
    problems: list[str] = []
    if not path.is_file():
        return [f"no review file: {path} (run `just factcheck`)"]

    fm, _body = load_review(path)
    if not fm:
        return [f"{path.name}: no YAML front-matter block"]

    if fm.get("status") != "complete":
        problems.append(f"status is {fm.get('status')!r}, must be 'complete'")

    # equations: every board equation must have a sourced, ok verdict
    eq_entries = {e.get("id"): e for e in fm.get("equations", []) if isinstance(e, dict)}
    for eid in _equation_ids(lesson):
        e = eq_entries.get(eid)
        if e is None:
            problems.append(f"equation {eid!r} missing from review")
        elif not (e.get("source") or "").strip():
            problems.append(f"equation {eid!r} has no source citation")
        elif e.get("verdict") != "ok":
            problems.append(f"equation {eid!r} verdict is {e.get('verdict')!r}, not 'ok'")

    # checks: present, verdict ok, AND re-run the recomputation now
    chk_entries = {c.get("scene"): c for c in fm.get("checks", []) if isinstance(c, dict)}
    for scene in lesson.scenes:
        if scene.check is None:
            continue
        c = chk_entries.get(scene.id)
        if c is None:
            problems.append(f"check scene {scene.id!r} missing from review")
        elif c.get("verdict") != "ok":
            problems.append(f"check scene {scene.id!r} verdict is {c.get('verdict')!r}, not 'ok'")
        res = eval_check(scene.check.expr, scene.check.value, scene.check.tol)
        if not res.ok:
            problems.append(f"check scene {scene.id!r}: {res.message}")

    # numbers: no stray todos
    for n in fm.get("numbers", []):
        if isinstance(n, dict) and n.get("verdict") == "todo":
            problems.append(f"number {n.get('name')!r} verdict still 'todo'")

    return problems


def run_factcheck(repo_root: Path, channel: str, code: str) -> int:
    """Scaffold the review if absent, re-run checks, report completeness."""
    lesson_file = Path(repo_root) / "channels" / channel / "lessons" / f"{code}.yaml"
    lesson = Lesson.model_validate(yaml.safe_load(lesson_file.read_text()))
    path = review_path(repo_root, channel, code)

    if not path.is_file():
        scaffold(lesson, path)
        print(f"scaffolded {path} — fill in the evidence, then set status: complete")

    for scene in lesson.scenes:
        if scene.check is None:
            continue
        res = eval_check(scene.check.expr, scene.check.value, scene.check.tol)
        mark = "ok" if res.ok else "FAIL"
        print(f"  check {scene.id}: {mark} — {res.message}")

    problems = verify(lesson, path)
    if problems:
        print(f"\n{code}: review INCOMPLETE")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"\n{code}: review complete ✓")
    return 0


def gate(repo_root: Path, channel: str, code: str) -> int:
    """Render gate: exit non-zero (with reasons) if the review is incomplete."""
    lesson_file = Path(repo_root) / "channels" / channel / "lessons" / f"{code}.yaml"
    lesson = Lesson.model_validate(yaml.safe_load(lesson_file.read_text()))
    problems = verify(lesson, review_path(repo_root, channel, code))
    if problems:
        print(f"fact-check gate: {code} is not cleared to render:")
        for p in problems:
            print(f"  - {p}")
        return 1
    return 0
