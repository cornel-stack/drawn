from drawn_schema import pronounce


def test_apply_symbol_and_term():
    m = {"\\omega": "omega", "ceteris paribus": "keteris paribus"}
    assert pronounce.apply("the rate \\omega here", m) == "the rate omega here"
    assert pronounce.apply("hold ceteris paribus", m) == "hold keteris paribus"


def test_apply_longest_match_first():
    m = {"\\Omega": "big omega", "\\omega": "omega"}
    # ensure \Omega isn't partially hit by \omega
    assert pronounce.apply("\\Omega and \\omega", m) == "big omega and omega"


def test_apply_term_is_word_bounded():
    m = {"rate": "RATE"}
    assert pronounce.apply("the rate of operating", m) == "the RATE of operating"


def test_speakable_symbols_ignores_structural():
    syms = pronounce.speakable_symbols(r"\vec{L} = I\omega \times \tau")
    assert syms == {"\\omega", "\\times", "\\tau"}
    assert "\\vec" not in syms


def test_missing_symbols():
    m = {"\\omega": "omega"}
    missing = pronounce.missing_symbols([r"\omega", r"\tau \cdot r"], m)
    assert missing == {"\\tau", "\\cdot"}
