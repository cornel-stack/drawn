"""Per-channel configuration: palette, board colour, handwriting font, voice.

Everything channel-specific lives in ``channels/<name>/channel.yaml``; shared
code reads it through :func:`load_channel`. One voice per channel.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict


class BoardStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: Literal["paper", "board"]
    background: str  # hex, e.g. "#f4ecd8"
    ink: str  # primary writing colour
    accent: str  # highlight / underline colour


class FontConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handwriting: str  # font family name as registered with Pango
    file: str  # path relative to repo root, e.g. assets/fonts/Kalam-Regular.ttf


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: Literal["kokoro", "edge"] = "kokoro"
    kokoro_voice: str  # Kokoro voice id, e.g. bm_george
    edge_voice: str  # edge-tts fallback voice, e.g. en-GB-RyanNeural
    speed: float = 1.0


class ChannelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    display_name: str
    board: BoardStyle
    palette: list[str]
    font: FontConfig
    voice: VoiceConfig
    intro_seconds: float = 2.0
    outro_seconds: float = 3.0


def load_channel(repo_root: Path, name: str) -> ChannelConfig:
    path = Path(repo_root) / "channels" / name / "channel.yaml"
    data = yaml.safe_load(path.read_text())
    return ChannelConfig.model_validate(data)
