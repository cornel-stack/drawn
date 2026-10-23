import pytest
from drawn_board.hand import HandConfig
from drawn_board.quality import QUALITIES, quality_config


def test_quality_presets():
    assert quality_config("preview") == {"pixel_width": 854, "pixel_height": 480, "frame_rate": 15}
    assert quality_config("final")["pixel_width"] == 1920
    assert quality_config("final")["frame_rate"] == 30
    assert set(QUALITIES) == {"preview", "final"}


def test_unknown_quality_raises():
    with pytest.raises(ValueError):
        quality_config("ultra")


def test_hand_config_parsing(tmp_path):
    (tmp_path / "assets").mkdir()
    cfg_dir = tmp_path / "assets" / "hand"
    cfg_dir.mkdir()
    (cfg_dir / "hand.yaml").write_text(
        "image: assets/hand/placeholder-hand.png\ntip: [0.08, 0.06]\nscale: 1.7\n"
    )
    cfg = HandConfig.load(tmp_path, "assets/hand/hand.yaml")
    assert cfg.image == "assets/hand/placeholder-hand.png"
    assert cfg.tip == (0.08, 0.06)
    assert cfg.scale == 1.7
