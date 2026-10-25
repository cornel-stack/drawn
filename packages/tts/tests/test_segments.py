"""Segment-aware TTS timing: verified purely in code, no audio needed."""

from drawn_schema.lesson import EQUATION_POST_PAUSE, EQUATION_PRE_PAUSE, Scene
from drawn_tts.align import Word, assemble_timeline, build_segments


def _scene() -> Scene:
    return Scene.model_validate(
        {
            "id": "s1",
            "kind": "derivation",
            "narration": "First {step} then write {eq} done {pause:1.5} end {label}",
            "board": [
                {"id": "eq", "latex": "x = 1", "say": "x equals one"},
                {"id": "label", "text": "note", "say": "a note"},
            ],
            "animation": {
                "primitive": "vectors",
                "steps": [{"id": "step", "action": "draw", "say": ""}],
            },
        }
    )


def test_build_segments_structure():
    segs, anchors = build_segments(_scene())
    kinds = [(s.kind, s.text or round(s.seconds, 2)) for s in segs]
    assert kinds == [
        ("speech", "First then write"),
        ("silence", EQUATION_PRE_PAUSE),
        ("speech", "x equals one"),
        ("silence", EQUATION_POST_PAUSE),
        ("speech", "done"),
        ("silence", 1.5),
        ("speech", "end a note"),
    ]
    assert anchors["step"] == (0, 1)   # 'then'
    assert anchors["eq"] == (2, 0)     # start of the equation speech segment
    assert anchors["label"] == (6, 1)  # 'a'


def _words(text, times):
    return [Word(w, t, t + 0.3) for w, t in zip(text.split(), times, strict=True)]


def _ident(n):
    return {i: i for i in range(n)}


def test_assemble_timeline_offsets_and_equation_pause():
    segs, anchors = build_segments(_scene())
    seg_words = [
        _words("First then write", [0.0, 0.5, 1.0]),
        None,
        _words("x equals one", [0.0, 0.4, 0.8]),
        None,
        _words("done", [0.0]),
        None,
        _words("end a note", [0.0, 0.4, 0.8]),
    ]
    seg_maps = [_ident(3), None, _ident(3), None, _ident(1), None, _ident(3)]
    seg_durations = [1.5, EQUATION_PRE_PAUSE, 1.2, EQUATION_POST_PAUSE, 0.4, 1.5, 1.2]

    words, starts, total = assemble_timeline(segs, seg_words, seg_maps, seg_durations, anchors)

    assert round(total, 2) == 8.0
    # the equation's write-start lands AFTER the 1.2 s pre-pause (1.5 + 1.2)
    assert round(starts["eq"], 2) == 2.7
    assert round(starts["step"], 2) == 0.5
    assert round(starts["label"], 2) == 7.2
    # a word in the last speech segment is shifted by the full cumulative offset
    assert round(words[-1].start, 2) == 7.6
