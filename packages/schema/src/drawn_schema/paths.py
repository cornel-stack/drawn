"""Shared build-output layout.

All intermediate and final artifacts for a lesson live under
``out/<channel>/<CODE>/`` (gitignored). Centralised here so every stage agrees
on where things go.
"""

from __future__ import annotations

from pathlib import Path


def lesson_out_dir(repo_root: Path, channel: str, code: str) -> Path:
    return Path(repo_root) / "out" / channel / code


def audio_dir(repo_root: Path, channel: str, code: str) -> Path:
    return lesson_out_dir(repo_root, channel, code) / "audio"


def words_dir(repo_root: Path, channel: str, code: str) -> Path:
    return lesson_out_dir(repo_root, channel, code) / "words"


def scenes_dir(repo_root: Path, channel: str, code: str) -> Path:
    """Per-scene silent video clips rendered by Manim."""
    return lesson_out_dir(repo_root, channel, code) / "scenes"


def scene_wav(repo_root: Path, channel: str, code: str, scene_id: str) -> Path:
    return audio_dir(repo_root, channel, code) / f"{scene_id}.wav"


def scene_words(repo_root: Path, channel: str, code: str, scene_id: str) -> Path:
    return words_dir(repo_root, channel, code) / f"{scene_id}.json"


def scene_clip(repo_root: Path, channel: str, code: str, scene_id: str) -> Path:
    return scenes_dir(repo_root, channel, code) / f"{scene_id}.mp4"
