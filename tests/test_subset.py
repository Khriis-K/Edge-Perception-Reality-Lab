"""Seeded per-condition subsets, their manifest, and the per-condition counts the Subset table shows."""

import random

import pytest

from backend.conditions import CONDITIONS, VOCABULARY_VERSION
from backend.dataset import Frame
from backend.subset import LOW_N_OBJECTS, draw_subset, summarize


def frames(condition, n, start=0, counts=None):
    counts = counts or {"PassengerCar": 1}
    return [Frame(f"2018-02-03_10-00-00_{i:05d}", condition, counts) for i in range(start, start + n)]


POOL = frames("clear-day", 100) + frames("fog-night", 40, start=100) + frames("rain-day", 3, start=200)


def test_same_seed_cap_and_frames_give_the_same_manifest():
    assert draw_subset(POOL, seed=7, cap=10) == draw_subset(POOL, seed=7, cap=10)


def test_a_different_seed_gives_a_different_manifest():
    assert draw_subset(POOL, seed=7, cap=10).frames != draw_subset(POOL, seed=8, cap=10).frames


def test_the_order_frames_were_found_in_does_not_matter():
    shuffled = POOL[:]
    random.Random(1).shuffle(shuffled)

    assert draw_subset(shuffled, seed=7, cap=10) == draw_subset(POOL, seed=7, cap=10)


def test_each_condition_is_capped_and_small_ones_are_taken_whole():
    manifest = draw_subset(POOL, seed=7, cap=10)

    assert len(manifest.frames["clear-day"]) == 10
    assert len(manifest.frames["fog-night"]) == 10
    assert len(manifest.frames["rain-day"]) == 3


def test_frames_are_drawn_from_their_own_condition_without_repeats():
    manifest = draw_subset(POOL, seed=7, cap=10)
    by_id = {f.id: f.condition for f in POOL}

    for condition, ids in manifest.frames.items():
        assert len(set(ids)) == len(ids)
        assert all(by_id[i] == condition for i in ids)


def test_growing_one_condition_leaves_the_others_draw_unchanged():
    grown = POOL + frames("clear-day", 50, start=300)

    before, after = draw_subset(POOL, seed=7, cap=10), draw_subset(grown, seed=7, cap=10)

    assert after.frames["fog-night"] == before.frames["fog-night"]


def test_manifest_records_seed_cap_vocabulary_and_every_condition():
    manifest = draw_subset(POOL, seed=7, cap=10)

    assert (manifest.seed, manifest.cap, manifest.vocabulary_version) == (7, 10, VOCABULARY_VERSION)
    assert list(manifest.frames) == list(CONDITIONS)
    assert manifest.frames["snow-day"] == []


def test_manifest_ids_are_sorted_so_the_file_diffs_cleanly():
    for ids in draw_subset(POOL, seed=7, cap=10).frames.values():
        assert ids == sorted(ids)


@pytest.mark.parametrize("cap", [0, -1])
def test_cap_must_be_positive(cap):
    with pytest.raises(ValueError):
        draw_subset(POOL, seed=7, cap=cap)


# --- summary ---------------------------------------------------------------------


def test_summary_counts_frames_objects_and_the_smallest_class():
    pool = frames("clear-day", 2, counts={"PassengerCar": 3, "Pedestrian": 1}) + frames(
        "clear-day", 1, start=2, counts={"PassengerCar": 1, "LargeVehicle": 2, "RidableVehicle": 1}
    )
    manifest = draw_subset(pool, seed=0, cap=10)

    row = next(r for r in summarize(pool, manifest) if r.condition == "clear-day")

    assert row.frames == 3
    # PassengerCar 3+3+1, Pedestrian 1+1, LargeVehicle 2, RidableVehicle 1.
    assert row.objects == 12
    assert (row.smallest_class, row.smallest_class_count) == ("RidableVehicle", 1)


def test_summary_only_counts_frames_in_the_manifest():
    manifest = draw_subset(POOL, seed=7, cap=10)

    row = next(r for r in summarize(POOL, manifest) if r.condition == "clear-day")

    assert row.frames == 10 and row.objects == 10


def test_a_class_with_no_objects_is_the_smallest_at_zero():
    manifest = draw_subset(POOL, seed=7, cap=10)

    row = next(r for r in summarize(POOL, manifest) if r.condition == "fog-night")

    assert row.smallest_class_count == 0


def test_every_condition_has_a_row_in_vocabulary_order():
    manifest = draw_subset(POOL, seed=7, cap=10)

    assert [r.condition for r in summarize(POOL, manifest)] == list(CONDITIONS)


def test_low_n_when_the_smallest_class_is_under_the_minimum():
    every_class = {"PassengerCar": 1, "LargeVehicle": 1, "RidableVehicle": 1, "Pedestrian": 1}
    enough = frames("clear-day", LOW_N_OBJECTS, counts=every_class)
    just_short = frames("clear-night", LOW_N_OBJECTS - 1, start=500, counts=every_class)
    pool = enough + just_short

    rows = {r.condition: r for r in summarize(pool, draw_subset(pool, seed=0, cap=1000))}

    assert not rows["clear-day"].low_n
    assert rows["clear-night"].low_n
    assert rows["snow-day"].low_n  # empty
