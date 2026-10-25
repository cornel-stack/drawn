from drawn_schema.backlog import parse_prereqs, parse_target_minutes


def test_parse_target_minutes_range_is_midpoint():
    assert parse_target_minutes("6-8 min") == 7
    assert parse_target_minutes("4-6 min") == 5


def test_parse_target_minutes_single_value():
    assert parse_target_minutes("12 min") == 12
    assert parse_target_minutes("120 min") == 120


def test_parse_target_minutes_blank():
    assert parse_target_minutes(None) is None
    assert parse_target_minutes("") is None


def test_parse_prereqs_none_and_blank():
    assert parse_prereqs("None") == []
    assert parse_prereqs(None) == []
    assert parse_prereqs("  ") == []


def test_parse_prereqs_comma_split():
    assert parse_prereqs("EM-02, MM-03") == ["EM-02", "MM-03"]


def test_parse_prereqs_keeps_range_tokens_verbatim():
    assert parse_prereqs("EM-01…EM-08") == ["EM-01…EM-08"]


def test_parse_source_openstax():
    from drawn_schema.scaffold import parse_source

    s = "OpenStax University Physics Vol. 1 (CC BY 4.0) §11.4 Precession of a gyroscope"
    out = parse_source(s)
    assert out["license"] == "CC BY 4.0"
    assert out["section"].startswith("§11.4")
    assert "OpenStax University Physics Vol. 1" in out["book"]
    assert "CC BY" not in out["book"]


def test_pause_token_stripped():
    from drawn_schema.placeholders import count_words, strip_pauses, substitute
    assert strip_pauses("hold {pause:1.5} on").split() == ["hold", "on"]
    assert count_words(substitute("a {x} {pause:2} b", {"x": "X"})) == 3
