"""Evaluation conditions, assigned from SeeingThroughFog's refined metadata (`labeltool_labels_refined`).

Condition mapping (vocabulary version 1). The refined files record fog and precipitation on separate axes, each with
a "no" flag, plus day/night and twilight:

| Refined metadata                                           | Condition           |
| ---------------------------------------------------------- | ------------------- |
| `fog.no` and `precipitation.no`                            | clear               |
| `fog.yes.denseFog` or `fog.yes.lightFog`, no precipitation | fog                 |
| `precipitation.yes.snow.heavySnow` or `.lightSnow`, no fog | snow                |
| `precipitation.yes.rain`, no fog                           | rain                |
| `daytime.day` / `daytime.night`                            | -day / -night split |

Excluded and counted, never guessed:

- fog together with rain or snow (in the real data this is always fog with snow, 53% of fog samples; see
  docs/research/seeingthroughfog-data-inspection.md);
- `twilight`, whatever else is set;
- rain together with snow;
- day and night both set or both unset, or a "no" flag that contradicts its "yes" flags;
- metadata missing any of these keys.

Changing this mapping changes which frames a condition holds, so bump VOCABULARY_VERSION with it.
"""

from dataclasses import dataclass

VOCABULARY_VERSION = 1
WEATHERS = ("clear", "fog", "snow", "rain")
CONDITIONS = tuple(f"{weather}-{light}" for weather in WEATHERS for light in ("day", "night"))

TWILIGHT = "twilight"
FOG_WITH_PRECIPITATION = "fog with rain or snow"
RAIN_AND_SNOW = "rain and snow together"
DAYTIME_UNCLEAR = "day or night not recorded"
FLAGS_CONTRADICT = "weather flags contradict each other"
METADATA_INCOMPLETE = "metadata incomplete"


@dataclass(frozen=True)
class Excluded:
    reason: str


def assign_condition(meta: dict) -> str | Excluded:
    """One of CONDITIONS, or why the sample's condition can't be determined."""
    try:
        twilight = meta["twilight"]
        day, night = meta["daytime"]["day"], meta["daytime"]["night"]
        no_fog, fog_kinds = meta["fog"]["no"], meta["fog"]["yes"]
        no_precipitation, precipitation = meta["precipitation"]["no"], meta["precipitation"]["yes"]
        foggy = fog_kinds["denseFog"] or fog_kinds["lightFog"]
        rain = precipitation["rain"]
        snow = precipitation["snow"]["heavySnow"] or precipitation["snow"]["lightSnow"]
    except (KeyError, TypeError):
        return Excluded(METADATA_INCOMPLETE)

    if twilight:
        return Excluded(TWILIGHT)
    if day == night:
        return Excluded(DAYTIME_UNCLEAR)
    if no_fog == foggy or no_precipitation == (rain or snow):
        return Excluded(FLAGS_CONTRADICT)
    if foggy and (rain or snow):
        return Excluded(FOG_WITH_PRECIPITATION)
    if rain and snow:
        return Excluded(RAIN_AND_SNOW)

    weather = "fog" if foggy else "snow" if snow else "rain" if rain else "clear"
    return f"{weather}-{'day' if day else 'night'}"
