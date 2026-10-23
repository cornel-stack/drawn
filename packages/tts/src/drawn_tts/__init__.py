"""SpeechService (Kokoro + edge-tts) and whisper word alignment for drawn."""

from drawn_tts.service import (
    EdgeSpeechService,
    KokoroSpeechService,
    SpeechService,
    SpeechServiceError,
    make_service,
)
from drawn_tts.stage import run_tts

__all__ = [
    "SpeechService",
    "SpeechServiceError",
    "KokoroSpeechService",
    "EdgeSpeechService",
    "make_service",
    "run_tts",
]
