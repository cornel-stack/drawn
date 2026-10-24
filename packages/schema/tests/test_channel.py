from pathlib import Path

import pytest
from drawn_schema import load_channel


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "channels").is_dir() and (parent / "CLAUDE.md").is_file():
            return parent
    pytest.skip("repo root not found")


@pytest.mark.parametrize("name", ["chalk-and-vector", "pen-and-pendulum", "marginal-ink"])
def test_channel_config_loads_and_font_exists(name):
    root = _repo_root()
    cfg = load_channel(root, name)
    assert cfg.name == name
    assert cfg.board.style in ("paper", "board")
    assert (root / cfg.font.file).is_file()
    assert cfg.voice.kokoro_voice and cfg.voice.edge_voice


def test_resolve_color():
    root = _repo_root()
    cfg = load_channel(root, "pen-and-pendulum")
    assert cfg.board.background == "#000000"
    assert cfg.board.ink == "#ffffff"
    assert cfg.resolve_color("blue") == cfg.accents["blue"]
    assert cfg.resolve_color("#123456") == "#123456"
    assert cfg.resolve_color(None) == cfg.board.ink
    import pytest as _pytest
    with _pytest.raises(ValueError):
        cfg.resolve_color("chartreuse")
