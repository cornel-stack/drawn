"""Fact-check gate: scaffold, completeness verification, check re-run."""

from drawn_schema import review
from drawn_schema.lesson import Lesson


def _lesson() -> Lesson:
    return Lesson.model_validate(
        {
            "schema_version": 1,
            "id": "ME-99",
            "channel": "pen-and-pendulum",
            "title": "Test",
            "target_minutes": 6,
            "source": {"book": "OpenStax UP Vol 1", "section": "§1.1", "license": "CC BY 4.0"},
            "scenes": [
                {
                    "id": "s1",
                    "kind": "derivation",
                    "narration": "We write {eq} and note {lbl}.",
                    "board": [
                        {"id": "eq", "latex": "F = m a", "say": "F equals m a"},
                        {"id": "lbl", "text": "Newton's second law"},
                    ],
                },
                {
                    "id": "s2",
                    "kind": "problem",
                    "narration": "Find the force {ans}.",
                    "board": [
                        {"id": "ans", "latex": "F = 6", "say": "F equals six", "role": "answer"},
                    ],
                    "check": {"expr": "2 * 3", "value": 6.0, "tol": 0.01},
                },
            ],
        }
    )


def test_scaffold_lists_equations_and_checks(tmp_path):
    lesson = _lesson()
    path = tmp_path / "ME-99.review.md"
    review.scaffold(lesson, path)
    fm, body = review.load_review(path)
    assert fm["status"] == "draft"
    assert [e["id"] for e in fm["equations"]] == ["eq", "ans"]
    assert [c["scene"] for c in fm["checks"]] == ["s2"]
    assert "Fact-check — ME-99" in body


def test_verify_flags_incomplete_scaffold(tmp_path):
    lesson = _lesson()
    path = tmp_path / "ME-99.review.md"
    review.scaffold(lesson, path)
    problems = review.verify(lesson, path)
    assert any("status" in p for p in problems)
    assert any("eq" in p for p in problems)


def test_verify_passes_when_complete(tmp_path):
    lesson = _lesson()
    path = tmp_path / "ME-99.review.md"
    front = {
        "lesson": "ME-99",
        "status": "complete",
        "equations": [
            {"id": "eq", "source": "OpenStax §1.1 Eq 1.1 p.5", "verdict": "ok"},
            {"id": "ans", "source": "OpenStax §1.1 Example p.6", "verdict": "ok"},
        ],
        "numbers": [{"name": "s2 answer", "verdict": "ok"}],
        "checks": [{"scene": "s2", "verdict": "ok"}],
    }
    import yaml

    path.write_text("---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\nevidence\n")
    assert review.verify(lesson, path) == []


def test_verify_reruns_check_and_catches_wrong_answer(tmp_path):
    lesson = _lesson()
    lesson.scenes[1].check.value = 7.0  # 2*3 != 7
    path = tmp_path / "ME-99.review.md"
    front = {
        "lesson": "ME-99",
        "status": "complete",
        "equations": [
            {"id": "eq", "source": "s", "verdict": "ok"},
            {"id": "ans", "source": "s", "verdict": "ok"},
        ],
        "numbers": [],
        "checks": [{"scene": "s2", "verdict": "ok"}],
    }
    import yaml

    path.write_text("---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\nx\n")
    problems = review.verify(lesson, path)
    assert any("recomputed" in p for p in problems)


def test_verify_no_file(tmp_path):
    assert review.verify(_lesson(), tmp_path / "missing.review.md")
