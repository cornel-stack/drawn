"""Word alignment with faster-whisper and placeholder → write-start mapping.

The TTS stage substitutes ``{id}`` placeholders with each board item's spoken
text. This module:

1. rebuilds the exact spoken word sequence and records, per item, the index of
   the first word it contributes (for silent text items, the index of the word
   that follows the placeholder);
2. transcribes the synthesised audio with faster-whisper to get word-level
   timestamps;
3. aligns the intended word sequence to the transcribed one (``difflib``) so
   each item's write-start time survives whisper tokenising the audio slightly
   differently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from drawn_schema.lesson import EQUATION_POST_PAUSE, EQUATION_PRE_PAUSE, Scene
from drawn_schema.placeholders import PLACEHOLDER_RE


@dataclass
class Word:
    word: str
    start: float
    end: float


@dataclass
class Segment:
    """One chunk of a scene's audio: either speech to synthesise or silence."""

    kind: str  # "speech" | "silence"
    text: str = ""
    seconds: float = 0.0


# Matches a pause, a highlight, or an {id} placeholder, in order.
_SEG_RE = re.compile(
    r"\{pause:\s*([0-9]*\.?[0-9]+)\s*\}|\{hl:([A-Za-z0-9_]+)\}|\{([A-Za-z0-9_]+)\}"
)


def build_segments(
    scene: Scene, pronounce_map: dict | None = None
) -> tuple[list[Segment], dict[str, tuple[int, int]], list[tuple[str, int, int]]]:
    """Split a scene's narration into speech/silence segments.

    Equation items get a silence of ``EQUATION_PRE_PAUSE`` before their spoken
    text (its own speech segment) and ``EQUATION_POST_PAUSE`` after, giving the
    pen time to write and the viewer time to read. ``{pause:N}`` tokens become
    silence. Returns the segment list and, per placeholder id, the
    ``(speech-segment index, intended-word offset)`` of where it begins.
    """
    from drawn_schema import pronounce as _pron

    pm = pronounce_map or {}
    spoken = {pid: _pron.apply(say, pm) for pid, say in scene.placeholders()}
    is_eq = {it.id: it.is_equation for it in scene.board}

    segments: list[Segment] = []
    anchors: dict[str, tuple[int, int]] = {}
    hl_anchors: list[tuple[str, int, int]] = []
    cur: list[str] = []
    pending: list[tuple[str, int]] = []  # inline items awaiting their segment index
    pending_hl: list[tuple[str, int]] = []

    def flush() -> None:
        if cur:
            idx = len(segments)
            segments.append(Segment("speech", text=" ".join(cur)))
            for pid, off in pending:
                anchors[pid] = (idx, off)
            for hid, off in pending_hl:
                hl_anchors.append((hid, idx, off))
            pending.clear()
            pending_hl.clear()
            cur.clear()

    pos = 0
    for m in _SEG_RE.finditer(scene.narration):
        cur.extend(_pron.apply(scene.narration[pos:m.start()], pm).split())
        if m.group(1) is not None:  # {pause:N}
            flush()
            segments.append(Segment("silence", seconds=float(m.group(1))))
        elif m.group(2) is not None:  # {hl:id} — emphasise at this moment
            pending_hl.append((m.group(2), len(cur)))
        else:  # {id}
            pid = m.group(3)
            sub = spoken.get(pid, "")
            if is_eq.get(pid):
                flush()
                segments.append(Segment("silence", seconds=EQUATION_PRE_PAUSE))
                anchors[pid] = (len(segments), 0)
                segments.append(Segment("speech", text=sub))
                segments.append(Segment("silence", seconds=EQUATION_POST_PAUSE))
            else:
                pending.append((pid, len(cur)))
                cur.extend(sub.split())
        pos = m.end()
    cur.extend(_pron.apply(scene.narration[pos:], pm).split())
    flush()
    for pid, off in pending:
        anchors[pid] = (len(segments), off)
    for hid, off in pending_hl:
        hl_anchors.append((hid, len(segments), off))
    return segments, anchors, hl_anchors


def assemble_timeline(
    segments: list[Segment],
    seg_words: list[list[Word] | None],
    seg_maps: list[dict[int, int] | None],
    seg_durations: list[float],
    anchors: dict[str, tuple[int, int]],
    hl_anchors: list[tuple[str, int, int]] | None = None,
) -> tuple[list[Word], dict[str, float], list[tuple[str, float]], float]:
    """Lay segments on a global timeline; return (words, item-starts, total).

    ``seg_words``/``seg_maps`` are per-speech-segment: the aligned actual words
    (times relative to the segment) and the intended→actual index map.
    ``seg_durations`` is each segment's wall-clock length (measured wav for
    speech, the pause length for silence). Pure arithmetic — unit-tested without
    any audio.
    """
    cursor = 0.0
    seg_start: list[float] = []
    words: list[Word] = []
    for i, seg in enumerate(segments):
        seg_start.append(cursor)
        if seg.kind == "speech" and seg_words[i]:
            for w in seg_words[i]:
                words.append(Word(w.word, w.start + cursor, w.end + cursor))
        cursor += seg_durations[i]
    total = cursor

    def _anchor_time(seg_idx: int, off: int) -> float:
        if seg_idx < len(segments) and seg_words[seg_idx]:
            amap = seg_maps[seg_idx] or {}
            aidx = _nearest(off, amap, len(seg_words[seg_idx]))
            return seg_words[seg_idx][aidx].start + seg_start[seg_idx]
        return seg_start[seg_idx] if seg_idx < len(seg_start) else total

    starts = {pid: _anchor_time(seg_idx, off) for pid, (seg_idx, off) in anchors.items()}
    hl_starts = [(hid, _anchor_time(seg_idx, off)) for hid, seg_idx, off in (hl_anchors or [])]
    return words, starts, hl_starts, total


def _nearest(off: int, amap: dict[int, int], n_actual: int) -> int:
    probe = off
    while probe not in amap and probe < off + 50:
        probe += 1
    if probe in amap:
        return min(amap[probe], n_actual - 1)
    probe = off - 1
    while probe not in amap and probe > off - 50:
        probe -= 1
    if probe in amap:
        return min(amap[probe], n_actual - 1)
    return min(off, n_actual - 1) if n_actual else 0


def intended_to_actual(intended: list[str], actual: list[Word]) -> dict[int, int]:
    """Public: map intended word indices to actual-word indices (difflib)."""
    return _intended_to_actual(intended, actual)


def build_spoken(
    scene: Scene, pronounce_map: dict | None = None
) -> tuple[list[str], dict[str, int]]:
    """Return (spoken words, {item_id: first-word index}) for a scene.

    Covers board items and animation steps (both use the {id} system).
    Pronunciation is applied per-part (before splitting) so item start indices
    stay correct even when a replacement changes the word count.
    """
    from drawn_schema import pronounce as _pron

    pronounce_map = pronounce_map or {}
    spoken_map = {k: _pron.apply(v, pronounce_map) for k, v in scene.placeholders()}
    words: list[str] = []
    item_start: dict[str, int] = {}
    # re.split with a capturing group interleaves the captured ids at odd indices.
    parts = PLACEHOLDER_RE.split(scene.narration)
    for k, part in enumerate(parts):
        if k % 2 == 1:  # placeholder id
            item_start[part] = len(words)  # where this item's words begin
            words.extend(spoken_map.get(part, "").split())
        else:
            words.extend(_pron.apply(part, pronounce_map).split())
    return words, item_start


def spoken_text(scene: Scene, pronounce_map: dict | None = None) -> str:
    words, _ = build_spoken(scene, pronounce_map)
    return " ".join(words)


def _norm(token: str) -> str:
    return re.sub(r"[^a-z0-9]", "", token.lower())


def _intended_to_actual(intended: list[str], actual: list[Word]) -> dict[int, int]:
    """Map each intended word index to an actual-word index via longest matches."""
    a = [_norm(w) for w in intended]
    b = [_norm(w.word) for w in actual]
    mapping: dict[int, int] = {}
    for i, j, n in SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(n):
            mapping[i + k] = j + k
    return mapping


def item_write_starts(
    scene: Scene, intended: list[str], actual: list[Word], duration: float,
    pronounce_map: dict | None = None,
) -> dict[str, float]:
    """Resolve each board item's write-start time in seconds."""
    _, item_index = build_spoken(scene, pronounce_map)
    mapping = _intended_to_actual(intended, actual)
    starts: dict[str, float] = {}
    for item_id, idx in item_index.items():
        starts[item_id] = _time_at_index(idx, mapping, actual, duration)
    return starts


def _time_at_index(
    idx: int, mapping: dict[int, int], actual: list[Word], duration: float
) -> float:
    if not actual:
        return 0.0
    # find the nearest intended index at or after idx that was matched
    probe = idx
    while probe not in mapping and probe < idx + 50:
        probe += 1
    if probe in mapping:
        j = min(mapping[probe], len(actual) - 1)
        return actual[j].start
    # fall back: nearest earlier matched index
    probe = idx - 1
    while probe not in mapping and probe > idx - 50:
        probe -= 1
    if probe in mapping:
        j = min(mapping[probe], len(actual) - 1)
        return actual[j].end
    return duration


@lru_cache(maxsize=2)
def _load_model(model_size: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe_words(wav_path: Path, model_size: str = "base") -> list[Word]:
    model = _load_model(model_size)
    segments, _info = model.transcribe(str(wav_path), word_timestamps=True)
    words: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            words.append(Word(word=w.word.strip(), start=float(w.start), end=float(w.end)))
    return words
