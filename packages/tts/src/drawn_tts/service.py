"""SpeechService interface and the Kokoro/edge-tts implementations.

Both services produce a mono 24 kHz WAV so the rest of the pipeline is
service-agnostic. Word timing is derived uniformly by whisper alignment
(:mod:`drawn_tts.align`), so a service only has to synthesise audio.
"""

from __future__ import annotations

import subprocess
import tempfile
import wave
from abc import ABC, abstractmethod
from pathlib import Path

from drawn_schema.channel import VoiceConfig

SAMPLE_RATE = 24_000


class SpeechServiceError(RuntimeError):
    pass


class SpeechService(ABC):
    name: str

    @abstractmethod
    def synthesize(self, text: str, out_wav: Path) -> None:
        """Write ``text`` to ``out_wav`` as mono 24 kHz PCM."""


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def _transcode_to_wav(src: Path, out_wav: Path) -> None:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(src),
            "-ac", "1", "-ar", str(SAMPLE_RATE),
            str(out_wav),
        ],
        check=True,
    )


class KokoroSpeechService(SpeechService):
    """Primary service: the Apache-2.0 ``kokoro`` package, CPU, British English."""

    name = "kokoro"

    def __init__(self, voice: VoiceConfig):
        self.voice = voice
        self._pipeline = None

    def _pipeline_lazy(self):
        if self._pipeline is None:
            try:
                from kokoro import KPipeline
            except ImportError as exc:  # pragma: no cover
                raise SpeechServiceError(f"kokoro not installed: {exc}") from exc
            # lang_code 'b' = British English; needs espeak-ng for G2P fallback.
            self._pipeline = KPipeline(lang_code="b")
        return self._pipeline

    def synthesize(self, text: str, out_wav: Path) -> None:
        import numpy as np
        import soundfile as sf

        pipeline = self._pipeline_lazy()
        chunks = []
        try:
            for _graphemes, _phonemes, audio in pipeline(
                text, voice=self.voice.kokoro_voice, speed=self.voice.speed
            ):
                chunks.append(audio)
        except Exception as exc:  # noqa: BLE001
            raise SpeechServiceError(f"kokoro synthesis failed: {exc}") from exc
        if not chunks:
            raise SpeechServiceError("kokoro produced no audio")
        audio = np.concatenate(chunks)
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_wav), audio, SAMPLE_RATE)


class EdgeSpeechService(SpeechService):
    """Fallback service: Microsoft edge-tts (network required)."""

    name = "edge"

    def __init__(self, voice: VoiceConfig):
        self.voice = voice

    def synthesize(self, text: str, out_wav: Path) -> None:
        import asyncio

        try:
            import edge_tts
        except ImportError as exc:  # pragma: no cover
            raise SpeechServiceError(f"edge-tts not installed: {exc}") from exc

        rate = f"{round((self.voice.speed - 1.0) * 100):+d}%"

        async def _run(mp3_path: str) -> None:
            communicate = edge_tts.Communicate(text, self.voice.edge_voice, rate=rate)
            await communicate.save(mp3_path)

        with tempfile.TemporaryDirectory() as tmp:
            mp3 = Path(tmp) / "speech.mp3"
            try:
                asyncio.run(_run(str(mp3)))
            except Exception as exc:  # noqa: BLE001
                raise SpeechServiceError(f"edge-tts synthesis failed: {exc}") from exc
            _transcode_to_wav(mp3, out_wav)


def make_service(voice: VoiceConfig, prefer: str | None = None) -> SpeechService:
    choice = prefer or voice.service
    if choice == "kokoro":
        return KokoroSpeechService(voice)
    return EdgeSpeechService(voice)
