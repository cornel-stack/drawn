"""Segment-aware TTS timing: verified purely in code, no audio needed."""

from drawn_schema.lesson import Scene
from drawn_tts.align import Word, assemble_timeline, build_segments


def _scene() -> Scene:
    return Scene.model_validate(
        {
            "id": "s1",
            "kind": "derivation",
            "narration": "First {step} then write {eq} done {pause:1.5} end {hl:eq} {label}",
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


def test_build_segments_inline_formula_and_pause_split():
    # The formula {eq} is spoken inline (one continuous utterance); only the
    # explicit {pause:1.5} splits the scene into two speech segments.
    segs, anchors, hl_anchors = build_segments(_scene())
    kinds = [(s.kind, s.text or round(s.seconds, 2)) for s in segs]
    assert kinds == [
        ("speech", "First then write x equals one done"),
        ("silence", 1.5),
        ("speech", "end a note"),
    ]
    assert anchors["step"] == (0, 1)   # 'then'
    assert anchors["eq"] == (0, 3)     # 'x' of "x equals one", inline
    assert anchors["label"] == (2, 1)  # 'a'
    assert hl_anchors == [("eq", 2, 1)]


def _words(text, times):
    return [Word(w, t, t + 0.3) for w, t in zip(text.split(), times, strict=True)]


def _ident(n):
    return {i: i for i in range(n)}


def test_assemble_timeline_offsets_inline():
    segs, anchors, hl_anchors = build_segments(_scene())
    seg_words = [
        _words("First then write x equals one done", [0.0, 0.5, 1.0, 1.5, 1.9, 2.3, 2.8]),
        None,
        _words("end a note", [0.0, 0.4, 0.8]),
    ]
    seg_maps = [_ident(7), None, _ident(3)]
    seg_durations = [3.5, 1.5, 1.2]

    words, starts, highlights, total = assemble_timeline(
        segs, seg_words, seg_maps, seg_durations, anchors, hl_anchors
    )

    assert round(total, 2) == 6.2
    assert round(starts["step"], 2) == 0.5    # 'then' in segment 0
    assert round(starts["eq"], 2) == 1.5      # 'x' inline in segment 0
    assert round(starts["label"], 2) == 5.4   # 'a' in segment 2 (starts at 5.0)
    assert round(words[-1].start, 2) == 5.8    # 'note'
    assert [(h, round(t, 2)) for h, t in highlights] == [("eq", 5.4)]
