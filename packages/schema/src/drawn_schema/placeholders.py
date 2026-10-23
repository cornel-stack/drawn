"""Placeholder handling for scene narration.

Narration references board items inline as ``{id}`` tokens. Before synthesis the
TTS step substitutes each ``{id}`` with the item's ``say`` text; text items
without a ``say`` substitute to nothing. The write-start time of each item is
later taken from the timestamp of its first substituted word.

Braces in narration are reserved for placeholders — prose should not contain a
literal ``{``/``}``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping

#: Matches ``{id}`` where id is a run of word characters.
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")


def iter_placeholders(narration: str) -> Iterator[str]:
    """Yield placeholder ids in the order they appear (duplicates included)."""
    for match in PLACEHOLDER_RE.finditer(narration):
        yield match.group(1)


def substitute(narration: str, spoken: Mapping[str, str]) -> str:
    """Replace every ``{id}`` with ``spoken[id]``.

    Unknown ids are left untouched (the linter reports them separately).
    Whitespace left by empty substitutions is collapsed so the word count is
    accurate.
    """

    def repl(match: re.Match[str]) -> str:
        return spoken.get(match.group(1), match.group(0))

    out = PLACEHOLDER_RE.sub(repl, narration)
    return re.sub(r"\s+", " ", out).strip()


def count_words(text: str) -> int:
    return len([w for w in text.split() if w])
