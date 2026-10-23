from drawn_schema.lesson import Scene
from drawn_tts.align import Word, build_spoken, item_write_starts


def _scene() -> Scene:
    return Scene.model_validate(
        {
            "id": "s1",
            "kind": "board",
            "narration": "the vector {L} has a torque {tau} shown",
            "board": [
                {"id": "L", "latex": r"\vec L", "say": "L"},
                {"id": "tau", "latex": r"\tau", "say": "tau equals"},
            ],
        }
    )


def test_build_spoken_substitutes_and_indexes():
    words, item_start = build_spoken(_scene())
    assert words == ["the", "vector", "L", "has", "a", "torque", "tau", "equals", "shown"]
    assert item_start == {"L": 2, "tau": 6}


def test_silent_text_item_indexes_to_following_word():
    scene = Scene.model_validate(
        {
            "id": "s2",
            "kind": "summary",
            "narration": "see {note} now",
            "board": [{"id": "note", "text": "a label"}],
        }
    )
    words, item_start = build_spoken(scene)
    assert words == ["see", "now"]
    assert item_start == {"note": 1}  # points at 'now'


def test_item_write_starts_maps_through_whisper_words():
    scene = _scene()
    intended, _ = build_spoken(scene)
    # whisper transcribes the same words, one per second
    actual = [Word(word=w, start=float(i), end=float(i) + 0.9) for i, w in enumerate(intended)]
    starts = item_write_starts(scene, intended, actual, duration=float(len(intended)))
    assert starts["L"] == 2.0
    assert starts["tau"] == 6.0


def test_item_write_starts_survives_extra_whisper_token():
    scene = _scene()
    intended, _ = build_spoken(scene)
    # whisper inserts a spurious leading token; matching should still line up
    actual = [Word(word="uh", start=0.0, end=0.4)]
    actual += [Word(word=w, start=float(i) + 1, end=float(i) + 1.9) for i, w in enumerate(intended)]
    starts = item_write_starts(scene, intended, actual, duration=99.0)
    assert starts["L"] == 3.0  # index 2 shifted by one inserted token
    assert starts["tau"] == 7.0
