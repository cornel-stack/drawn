"""TTS stage: per-scene WAV + word-timestamp JSON for one lesson.

Idempotent and resumable: each scene stores a content hash in its words JSON and
is skipped on re-run when narration, spoken text and voice settings are
unchanged (unless ``force``). This mirrors the content-hash caching used by the
other stages.
"""

from __future__ import annotations

import hashlib
import json
import wave
from dataclasses import dataclass
from pathlib import Path

import yaml
from drawn_schema import paths
from drawn_schema.channel import ChannelConfig, load_channel
from drawn_schema.lesson import Lesson, Scene

from drawn_tts.align import build_spoken, item_write_starts, transcribe_words
from drawn_tts.service import (
    SAMPLE_RATE,
    SpeechService,
    SpeechServiceError,
    make_service,
    wav_duration,
)


@dataclass
class SceneTTS:
    scene_id: str
    wav: Path
    words_json: Path
    duration: float
    skipped: bool


def _scene_hash(scene: Scene, channel: ChannelConfig, service_name: str) -> str:
    payload = {
        "narration": scene.narration,
        "items": [[it.id, it.spoken] for it in scene.board],
        "voice": channel.voice.model_dump(),
        "service": service_name,
        "sr": SAMPLE_RATE,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()


def _write_silence(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(SAMPLE_RATE * max(seconds, 0.2))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(b"\x00\x00" * frames)


def _silence_seconds(scene: Scene, channel: ChannelConfig) -> float:
    if scene.kind == "end":
        return channel.outro_seconds
    if scene.kind == "title":
        return channel.intro_seconds
    return 1.5


def _synth_with_fallback(
    service: SpeechService, text: str, wav: Path, channel: ChannelConfig
) -> SpeechService:
    """Synthesise, falling back from Kokoro to edge-tts on failure. Returns the
    service that actually succeeded so the rest of the lesson stays consistent."""
    try:
        service.synthesize(text, wav)
        return service
    except SpeechServiceError as exc:
        if service.name != "kokoro":
            raise
        print(f"  kokoro failed ({exc}); falling back to edge-tts")
        fallback = make_service(channel.voice, prefer="edge")
        fallback.synthesize(text, wav)
        return fallback


def run_tts(
    repo_root: Path,
    lesson_path: Path,
    *,
    force: bool = False,
    model_size: str = "base",
) -> list[SceneTTS]:
    data = yaml.safe_load(Path(lesson_path).read_text())
    lesson = Lesson.model_validate(data)
    channel = load_channel(repo_root, lesson.channel)
    service = make_service(channel.voice)

    results: list[SceneTTS] = []
    for scene in lesson.scenes:
        wav = paths.scene_wav(repo_root, lesson.channel, lesson.id, scene.id)
        wj = paths.scene_words(repo_root, lesson.channel, lesson.id, scene.id)
        want_hash = _scene_hash(scene, channel, service.name)

        if not force and wav.is_file() and wj.is_file():
            try:
                existing = json.loads(wj.read_text())
                if existing.get("hash") == want_hash:
                    results.append(
                        SceneTTS(scene.id, wav, wj, existing["duration"], skipped=True)
                    )
                    print(f"  {scene.id}: cached")
                    continue
            except (json.JSONDecodeError, KeyError):
                pass

        words, _ = build_spoken(scene)
        text = " ".join(words).strip()

        if not text:
            _write_silence(wav, _silence_seconds(scene, channel))
            transcribed = []
        else:
            service = _synth_with_fallback(service, text, wav, channel)
            transcribed = transcribe_words(wav, model_size=model_size)

        duration = wav_duration(wav)
        starts = item_write_starts(scene, words, transcribed, duration)

        wj.parent.mkdir(parents=True, exist_ok=True)
        wj.write_text(
            json.dumps(
                {
                    "scene": scene.id,
                    "kind": scene.kind,
                    "hash": want_hash,
                    "duration": round(duration, 4),
                    "sample_rate": SAMPLE_RATE,
                    "words": [
                        {"word": w.word, "start": round(w.start, 4), "end": round(w.end, 4)}
                        for w in transcribed
                    ],
                    "items": [
                        {"id": iid, "start": round(start, 4)}
                        for iid, start in starts.items()
                    ],
                },
                indent=2,
            )
        )
        print(f"  {scene.id}: {duration:.2f}s, {len(transcribed)} words")
        results.append(SceneTTS(scene.id, wav, wj, duration, skipped=False))

    return results
