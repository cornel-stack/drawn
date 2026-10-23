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
    assert lesson.word_budget == 290
