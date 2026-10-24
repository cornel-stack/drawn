import copy

from drawn_schema.linter import lint_lesson

# A minimal valid lesson. target_minutes 1 → budget 145, allowed 123–167.
# Narration: 140 filler words + two placeholders whose `say` adds 4 words = 144.
_FILLER = " ".join(["alpha"] * 140)


def valid_lesson() -> dict:
    return {
        "schema_version": 1,
        "id": "ME-25",
        "channel": "pen-and-pendulum",
        "title": "Demo",
        "target_minutes": 1,
        "source": {"book": "OpenStax", "section": "§1", "license": "CC BY 4.0"},
        "scenes": [
            {
                "id": "s1",
                "kind": "board",
                "narration": f"{_FILLER} {{L}} {{tau}}",
                "board": [
                    {"id": "L", "latex": r"\vec{L} = I\vec{\omega}", "say": "L equals I omega"},
                    {"id": "tau", "latex": r"\tau", "say": "tau"},
                ],
            }
        ],
    }


def test_valid_lesson_passes():
    result = lint_lesson(valid_lesson())
    assert result.ok, result.errors


def test_wrong_schema_version_is_error():
    data = valid_lesson()
    data["schema_version"] = 99
    result = lint_lesson(data)
    assert not result.ok
    assert any("schema_version" in e for e in result.errors)


def test_unknown_placeholder_is_error():
    data = valid_lesson()
    data["scenes"][0]["narration"] += " {ghost}"
    result = lint_lesson(data)
    assert any("ghost" in e for e in result.errors)


def test_unreferenced_item_is_error():
    data = valid_lesson()
    # drop the {tau} reference but keep the item
    data["scenes"][0]["narration"] = f"{_FILLER} {{L}}"
    result = lint_lesson(data)
    assert any("tau" in e and "never" in e for e in result.errors)


def test_item_referenced_twice_is_error():
    data = valid_lesson()
    data["scenes"][0]["narration"] = f"{_FILLER} {{L}} {{tau}} {{tau}}"
    result = lint_lesson(data)
    assert any("tau" in e and "exactly once" in e for e in result.errors)


def test_word_budget_too_short_is_error():
    data = valid_lesson()
    data["scenes"][0]["narration"] = "{L} {tau}"
    result = lint_lesson(data)
    assert any("budget" in e for e in result.errors)


def test_word_budget_too_long_is_error():
    data = valid_lesson()
    data["scenes"][0]["narration"] = " ".join(["alpha"] * 400) + " {L} {tau}"
    result = lint_lesson(data)
    assert any("budget" in e for e in result.errors)


def test_nc_licence_is_warning_not_error():
    data = valid_lesson()
    data["source"]["license"] = "CC BY-NC-SA 4.0"
    result = lint_lesson(data)
    assert result.ok, result.errors
    assert any("NonCommercial" in w for w in result.warnings)


def test_cc_by_sa_is_accepted():
    data = valid_lesson()
    data["source"]["license"] = "CC BY-SA 3.0"
    result = lint_lesson(data)
    assert result.ok, result.errors


def test_non_cc_licence_is_error():
    data = valid_lesson()
    data["source"]["license"] = "All rights reserved"
    result = lint_lesson(data)
    assert any("CC-BY family" in e for e in result.errors)


def test_latex_without_say_is_error():
    data = valid_lesson()
    del data["scenes"][0]["board"][0]["say"]
    result = lint_lesson(data)
    assert not result.ok


def test_duplicate_item_id_is_error():
    data = valid_lesson()
    data["scenes"][0]["board"][1]["id"] = "L"
    data["scenes"][0]["narration"] = f"{_FILLER} {{L}}"
    result = lint_lesson(data)
    assert any("duplicate" in e for e in result.errors)


def test_deepcopy_isolation():
    # guard against tests mutating the shared template
    a = valid_lesson()
    b = copy.deepcopy(a)
    assert a == b


def _diagram_lesson() -> dict:
    # target 1 min -> budget 145 (123-167). 140 filler + step/item says.
    filler = " ".join(["alpha"] * 140)
    return {
        "schema_version": 1,
        "id": "ME-25",
        "channel": "pen-and-pendulum",
        "title": "Demo",
        "target_minutes": 1,
        "source": {"book": "OpenStax", "section": "§1", "license": "CC BY 4.0"},
        "scenes": [
            {
                "id": "s1",
                "kind": "diagram",
                "narration": f"{filler} draw {{spin}} then {{L}}",
                "board": [
                    {"id": "L", "latex": r"\vec L = I\vec\omega", "say": "L equals I omega",
                     "color": "blue"},
                ],
                "animation": {
                    "primitive": "gyroscope",
                    "params": {"spin": "ccw"},
                    "steps": [
                        {"id": "spin", "action": "start_spin"},
                    ],
                },
            }
        ],
    }


def test_animation_step_is_valid_placeholder():
    result = lint_lesson(_diagram_lesson())
    assert result.ok, result.errors


def test_animation_step_must_be_referenced_once():
    data = _diagram_lesson()
    data["scenes"][0]["narration"] = " ".join(["alpha"] * 140) + " draw {L}"  # drop {spin}
    result = lint_lesson(data)
    assert any("spin" in e and "never" in e for e in result.errors)


def test_animation_requires_exactly_one_of_primitive_custom():
    data = _diagram_lesson()
    data["scenes"][0]["animation"]["custom"] = "Thing"  # now both set
    result = lint_lesson(data)
    assert not result.ok


def test_item_color_accepted():
    data = _diagram_lesson()
    assert lint_lesson(data).ok


def test_leadin_warning():
    data = valid_lesson()
    # {L} is after 140 filler words -> long lead-in (warning, not error)
    result = lint_lesson(data)
    assert result.ok, result.errors
    assert any("words before the first" in w for w in result.warnings)


def test_no_leadin_warning_when_early():
    data = valid_lesson()
    data["scenes"][0]["narration"] = "{L} " + " ".join(["alpha"] * 142) + " {tau}"
    result = lint_lesson(data)
    assert not any("words before the first" in w for w in result.warnings)
