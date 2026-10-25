import pytest
from drawn_schema import BoardItem, Lesson
from pydantic import ValidationError


def test_latex_item_requires_say():
    with pytest.raises(ValidationError):
        BoardItem(id="L", latex=r"\vec{L}")  # no say


def test_latex_item_with_say_ok():
    item = BoardItem(id="L", latex=r"\vec{L}", say="L")
    assert item.is_latex
    assert item.spoken == "L"


def test_text_item_without_say_is_allowed_and_silent():
    item = BoardItem(id="note", text="A note")
    assert not item.is_latex
    assert item.spoken == ""


def test_item_needs_exactly_one_of_latex_text():
    with pytest.raises(ValidationError):
        BoardItem(id="x")  # neither
    with pytest.raises(ValidationError):
        BoardItem(id="x", latex="a", text="b", say="a")  # both


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        BoardItem(id="x", text="y", cue="old-field")


def test_word_budget_property():
    lesson = Lesson.model_validate(
        {
            "schema_version": 1,
            "id": "ME-25",
            "channel": "pen-and-pendulum",
            "title": "t",
            "target_minutes": 2,
            "source": {"book": "b", "section": "s", "license": "CC BY 4.0"},
            "scenes": [],
        }
    )
    assert lesson.word_budget == 280  # 2 min x 140 wpm


def test_title_card_rejects_animation():
    with pytest.raises(ValidationError):
        Lesson.model_validate({
            "schema_version": 1, "id": "X", "channel": "c", "title": "t",
            "target_minutes": 1,
            "source": {"book": "b", "section": "s", "license": "CC BY 4.0"},
            "scenes": [{"id": "s1", "kind": "title", "narration": "hi",
                        "animation": {"primitive": "wheel", "steps": []}}],
        })


def test_problem_requires_check_and_answer():
    base = {
        "schema_version": 1, "id": "X", "channel": "c", "title": "t",
        "target_minutes": 1,
        "source": {"book": "b", "section": "s", "license": "CC BY 4.0"},
        "scenes": [{"id": "p1", "kind": "problem", "narration": "{ans}",
                    "board": [{"id": "ans", "latex": "T=2", "say": "T is two",
                               "role": "answer", "box": True}],
                    "check": {"expr": "2.0", "value": 2.0}}],
    }
    assert Lesson.model_validate(base)  # ok
    import copy
    no_check = copy.deepcopy(base); del no_check["scenes"][0]["check"]
    with pytest.raises(ValidationError):
        Lesson.model_validate(no_check)
    no_ans = copy.deepcopy(base); no_ans["scenes"][0]["board"][0]["role"] = "step"
    with pytest.raises(ValidationError):
        Lesson.model_validate(no_ans)


def test_legend_and_is_equation():
    item = BoardItem(id="e", latex=r"\Omega = \frac{rmg}{I\omega}", say="omega",
                     legend=[{"sym": r"\omega", "name": "spin rate", "unit": "rad/s"}])
    assert item.is_equation
    assert item.legend[0].unit == "rad/s"
    assert not BoardItem(id="l", latex=r"\omega", say="omega").is_equation  # no '='
