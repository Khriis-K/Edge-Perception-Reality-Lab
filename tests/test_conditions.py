"""Condition assignment from the refined metadata: clear, fog, snow and rain, each by day and by night."""

import pytest

from backend.conditions import CONDITIONS, Excluded, assign_condition


def refined(fog=None, precipitation=None, daytime="day", twilight=False):
    """A refined-metadata dict as SeeingThroughFog writes it (fields the adapter ignores left out)."""
    snow = {"heavySnow": precipitation == "heavySnow", "lightSnow": precipitation == "lightSnow"}
    return {
        "daytime": {"day": daytime == "day", "night": daytime == "night"},
        "fog": {"no": fog is None, "yes": {"denseFog": fog == "denseFog", "lightFog": fog == "lightFog"}},
        "precipitation": {"no": precipitation is None, "yes": {"rain": precipitation == "rain", "snow": snow}},
        "twilight": twilight,
    }


def test_the_vocabulary_is_four_weathers_by_day_and_night():
    assert CONDITIONS == (
        "clear-day", "clear-night", "fog-day", "fog-night", "snow-day", "snow-night", "rain-day", "rain-night",
    )


@pytest.mark.parametrize(
    "fog, precipitation, daytime, expected",
    [
        (None, None, "day", "clear-day"),
        (None, None, "night", "clear-night"),
        ("denseFog", None, "day", "fog-day"),
        ("lightFog", None, "night", "fog-night"),
        (None, "heavySnow", "day", "snow-day"),
        (None, "lightSnow", "night", "snow-night"),
        (None, "rain", "day", "rain-day"),
        (None, "rain", "night", "rain-night"),
    ],
)
def test_assigns_one_condition(fog, precipitation, daytime, expected):
    assert assign_condition(refined(fog, precipitation, daytime)) == expected


@pytest.mark.parametrize("fog", ["denseFog", "lightFog"])
@pytest.mark.parametrize("precipitation", ["rain", "heavySnow", "lightSnow"])
def test_fog_with_precipitation_is_excluded(fog, precipitation):
    assert assign_condition(refined(fog, precipitation)) == Excluded("fog with rain or snow")


@pytest.mark.parametrize("daytime", ["day", "night"])
def test_twilight_is_excluded_whatever_else_is_set(daytime):
    result = assign_condition(refined(daytime=daytime, twilight=True))

    assert result == Excluded("twilight")


def test_rain_and_snow_together_is_excluded():
    meta = refined(precipitation="rain")
    meta["precipitation"]["yes"]["snow"]["lightSnow"] = True

    assert assign_condition(meta) == Excluded("rain and snow together")


@pytest.mark.parametrize("day, night", [(True, True), (False, False)])
def test_day_and_night_must_be_exactly_one(day, night):
    meta = refined()
    meta["daytime"] = {"day": day, "night": night}

    assert assign_condition(meta) == Excluded("day or night not recorded")


def test_contradictory_no_and_yes_flags_are_excluded():
    meta = refined(fog="denseFog")
    meta["fog"]["no"] = True  # says both "no fog" and "dense fog"

    assert assign_condition(meta) == Excluded("weather flags contradict each other")


def test_a_flag_with_nothing_set_is_excluded():
    meta = refined()
    meta["precipitation"]["no"] = False  # neither "no precipitation" nor any kind of it

    assert assign_condition(meta) == Excluded("weather flags contradict each other")


@pytest.mark.parametrize("missing", ["fog", "precipitation", "daytime", "twilight"])
def test_missing_keys_are_excluded_not_raised(missing):
    meta = refined()
    del meta[missing]

    assert assign_condition(meta) == Excluded("metadata incomplete")


def test_the_original_schema_is_not_mistaken_for_clear():
    original = {"weather": {"clear": False, "dense_fog": True}, "daytime": {"day": True, "night": False}}

    assert assign_condition(original) == Excluded("metadata incomplete")
