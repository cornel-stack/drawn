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
