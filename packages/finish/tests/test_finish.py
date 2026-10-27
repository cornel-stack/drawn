from drawn_finish.captions import _fmt
from drawn_finish.meta import _chapter_label, _derive_tags, _timestamp
from drawn_schema.lesson import Lesson


def test_srt_timestamp_format():
    assert _fmt(0) == "00:00:00,000"
    assert _fmt(1.5) == "00:00:01,500"
    assert _fmt(3661.25) == "01:01:01,250"


def test_chapter_timestamp_format():
    assert _timestamp(0) == "00:00"
    assert _timestamp(75) == "01:15"


def _lesson() -> Lesson:
    return Lesson.model_validate(
        {
            "schema_version": 1,
            "id": "ME-25",
            "channel": "pen-and-pendulum",
            "title": "Gyroscopic precession: why the spinning wheel refuses to fall",
            "target_minutes": 2,
            "source": {
                "book": "OpenStax University Physics Vol. 1",
                "section": "§11.4",
                "license": "CC BY 4.0",
            },
            "scenes": [],
        }
    )


def test_tags_drop_stopwords_and_include_book():
    tags = _derive_tags(_lesson())
    assert "OpenStax University Physics Vol. 1" in tags
    assert "precession" in tags
    assert "why" not in tags


def test_chapter_label_strips_placeholders():
    from drawn_schema.lesson import Scene

    scene = Scene.model_validate(
        {
            "id": "s2",
            "kind": "board",
            "narration": "A spinning wheel has momentum {L} along its axis.",
            "board": [{"id": "L", "latex": r"\vec L", "say": "L"}],
        }
    )
    label = _chapter_label(scene)
    assert "{" not in label
    assert label.startswith("A spinning wheel")
