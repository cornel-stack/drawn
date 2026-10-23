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

from drawn_schema.lesson import Scene
from drawn_schema.placeholders import PLACEHOLDER_RE


@dataclass
class Word:
    word: str
    start: float
    end: float


def build_spoken(scene: Scene) -> tuple[list[str], dict[str, int]]:
    """Return (spoken words, {item_id: first-word index}) for a scene."""
    spoken_map = {item.id: item.spoken for item in scene.board}
    words: list[str] = []
    item_start: dict[str, int] = {}
    # re.split with a capturing group interleaves the captured ids at odd indices.
    parts = PLACEHOLDER_RE.split(scene.narration)
    for k, part in enumerate(parts):
        if k % 2 == 1:  # placeholder id
            item_start[part] = len(words)  # where this item's words begin
            words.extend(spoken_map.get(part, "").split())
        else:
            words.extend(part.split())
    return words, item_start


def spoken_text(scene: Scene) -> str:
    words, _ = build_spoken(scene)
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
    scene: Scene, intended: list[str], actual: list[Word], duration: float
) -> dict[str, float]:
    """Resolve each board item's write-start time in seconds."""
    _, item_index = build_spoken(scene)
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
