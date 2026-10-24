import pytest
from drawn_board.quality import QUALITIES, quality_config


def test_quality_presets():
    assert quality_config("preview") == {"pixel_width": 854, "pixel_height": 480, "frame_rate": 15}
    assert quality_config("final") == {"pixel_width": 1920, "pixel_height": 1080, "frame_rate": 30}
    assert set(QUALITIES) == {"preview", "final"}


def test_unknown_quality_raises():
    with pytest.raises(ValueError):
        quality_config("ultra")


def test_hand_fallback_generates(tmp_path):
    from drawn_board.hand_pipeline import ensure_hand

    ap = ensure_hand(tmp_path)
    assert ap.is_file()
    import json

    data = json.loads(ap.read_text())
    assert (tmp_path / data["write"]["image"]).is_file()
    nx, ny = data["write"]["tip"]
    assert 0 <= nx <= 1 and 0 <= ny <= 1


def test_primitive_registry_has_core_and_stubs():
    from drawn_board.primitives.base import get_primitive

    assert get_primitive("gyroscope").is_3d is True
    assert get_primitive("vectors").is_3d is False
    stub = get_primitive("pendulum")
    with pytest.raises(NotImplementedError):
        stub(None, None, {}).build()
