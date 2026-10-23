"""Content-hash caching per pipeline stage.

Each stage derives a key from its inputs (lesson snippet + code + voice/render
settings). If an output already exists under the same key, the stage is skipped.
Phase 1 uses this for a shared hash function and a small fingerprint helper; the
per-stage skip logic currently lives in each stage (TTS, board) and will be
centralised here in Phase 2.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def content_hash(*parts: object) -> str:
    """Stable SHA-256 over any JSON-serialisable parts."""
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(blob).hexdigest()


def is_fresh(fingerprint: str, marker: Path) -> bool:
    """True when ``marker`` records the same fingerprint (stage can be skipped)."""
    return marker.is_file() and marker.read_text().strip() == fingerprint


def write_marker(fingerprint: str, marker: Path) -> None:
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(fingerprint)


__all__ = ["content_hash", "is_fresh", "write_marker"]
