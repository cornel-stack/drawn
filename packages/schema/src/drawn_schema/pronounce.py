"""Pronunciation: map symbols/terms to spoken forms before synthesis.

``channels/<name>/pronounce.yaml`` holds a ``map`` of pattern → spoken form,
e.g. ``"\\omega": "omega"``, ``"ceteris paribus": "ceteris paribus"``. The map
is applied to narration and to ``say`` text before TTS; the linter warns about
LaTeX symbols used in a lesson that have no entry, so the mapping stays complete
as it is reused across lessons.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

# LaTeX commands whose spoken form matters (Greek letters + common operators
# and relations). Structural commands (\dfrac, \vec, \left …) are not "spoken".
GREEK = {
    r"\alpha", r"\beta", r"\gamma", r"\delta", r"\epsilon", r"\varepsilon",
    r"\zeta", r"\eta", r"\theta", r"\vartheta", r"\iota", r"\kappa", r"\lambda",
    r"\mu", r"\nu", r"\xi", r"\pi", r"\rho", r"\sigma", r"\tau", r"\upsilon",
    r"\phi", r"\varphi", r"\chi", r"\psi", r"\omega",
    r"\Gamma", r"\Delta", r"\Theta", r"\Lambda", r"\Xi", r"\Pi", r"\Sigma",
    r"\Phi", r"\Psi", r"\Omega",
}
OPERATORS = {
    r"\times", r"\cdot", r"\partial", r"\nabla", r"\sum", r"\int", r"\infty",
    r"\approx", r"\leq", r"\geq", r"\neq", r"\pm", r"\mp", r"\propto",
    r"\rightarrow", r"\to", r"\Rightarrow", r"\hat", r"\bar",
}
SPEAKABLE = GREEK | OPERATORS

_COMMAND_RE = re.compile(r"\\[A-Za-z]+")


def load_pronounce(repo_root: Path, channel: str) -> dict[str, str]:
    path = Path(repo_root) / "channels" / channel / "pronounce.yaml"
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    mapping = data.get("map", data) if isinstance(data, dict) else {}
    return {str(k): str(v) for k, v in mapping.items()}


def apply(text: str, mapping: dict[str, str]) -> str:
    """Replace mapped patterns with their spoken form (longest key first)."""
    if not mapping:
        return text
    for key in sorted(mapping, key=len, reverse=True):
        spoken = mapping[key]
        if key[:1].isalpha():
            # whole-word, case-insensitive for alphabetic terms
            text = re.sub(rf"(?<!\w){re.escape(key)}(?!\w)", spoken, text, flags=re.IGNORECASE)
        else:
            text = text.replace(key, spoken)
    return text


def speakable_symbols(latex: str) -> set[str]:
    """Return the speakable LaTeX commands used in a latex string."""
    return {cmd for cmd in _COMMAND_RE.findall(latex) if cmd in SPEAKABLE}


def missing_symbols(latex_strings: list[str], mapping: dict[str, str]) -> set[str]:
    """Speakable symbols used but absent from the pronunciation map."""
    used: set[str] = set()
    for s in latex_strings:
        used |= speakable_symbols(s)
    return {sym for sym in used if sym not in mapping}


# Capitalised words that are ordinary, not names to pronunciation-check.
_NOT_NAMES = {
    "I", "A", "An", "The", "This", "That", "These", "Those", "We", "You", "It",
    "If", "So", "But", "And", "Or", "Now", "Here", "There", "When", "Then",
    "British", "English", "Greek", "Latin", "GDP", "AP", "IB", "US", "UK",
}
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?:;])\s+|\n+")
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")


def proper_nouns(narration: str) -> set[str]:
    """Capitalised, non-sentence-initial words — likely names to pronounce-check."""
    found: set[str] = set()
    for sentence in _SENTENCE_SPLIT.split(narration):
        words = _WORD.findall(sentence)
        for w in words[1:]:  # skip the sentence-initial word
            if w[0].isupper() and len(w) > 2 and w not in _NOT_NAMES:
                found.add(w)
    return found
