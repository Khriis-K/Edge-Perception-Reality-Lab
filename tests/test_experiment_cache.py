"""Persistence: the deterministic experiment id, and the on-disk store of finished experiments."""

import os
import shutil

import pytest

from backend.detection import ModelInfo
from backend.experiment import AppliedDegradation, DegradationSettings, Experiment, FrameResult
from backend.experiment_cache import EXPERIMENT_ID, ExperimentCache, experiment_id, fingerprint

MODEL = ModelInfo(name="Stub detector", version="fixture-1", runtime="none")
SETTINGS = {
    "input_fingerprint": "a" * 64,
    "model": MODEL,
    "class_mapping_version": 1,
    "confidence_floor": 0.05,
    "degradation": DegradationSettings(kind="fog", severity=0.5, seed=0),
}


def an_id(**change):
    return experiment_id(**{**SETTINGS, **change})


# --- the id -------------------------------------------------------------------------


def test_identical_settings_give_the_same_id():
    assert an_id() == an_id()
    assert an_id(degradation=DegradationSettings(kind="fog", severity=0.5, seed=0)) == an_id()


def test_the_id_is_a_well_formed_experiment_id():
    assert EXPERIMENT_ID.fullmatch(an_id())


@pytest.mark.parametrize(
    "change",
    [
        {"input_fingerprint": "b" * 64},
        {"model": MODEL.model_copy(update={"version": "fixture-2"})},
        {"model": MODEL.model_copy(update={"name": "Another detector"})},
        {"class_mapping_version": 2},
        {"confidence_floor": 0.1},
        {"degradation": DegradationSettings(kind="blur", severity=0.5, seed=0)},
        {"degradation": DegradationSettings(kind="fog", severity=0.51, seed=0)},
        {"degradation": DegradationSettings(kind="fog", severity=0.5, seed=1)},
    ],
    ids=["input", "model-version", "model-name", "class-mapping", "confidence-floor", "kind", "severity", "seed"],
)
def test_changing_any_result_affecting_setting_gives_a_different_id(change):
    assert an_id(**change) != an_id()


def test_the_runtime_is_not_part_of_the_id():
    # The same weights under another onnxruntime build are the same model version.
    assert an_id(model=MODEL.model_copy(update={"runtime": "onnxruntime 9"})) == an_id()


# --- input fingerprint ----------------------------------------------------------------


def test_fingerprint_follows_the_file_content(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"one")
    first = fingerprint(video)

    assert fingerprint(video) == first
    video.write_bytes(b"two")
    os.utime(video, ns=(0, 10**9))  # a new mtime, even on filesystems with coarse timestamps
    assert fingerprint(video) != first


def test_fingerprint_does_not_depend_on_the_path(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"same")
    (tmp_path / "b.mp4").write_bytes(b"same")

    assert fingerprint(tmp_path / "a.mp4") == fingerprint(tmp_path / "b.mp4")


# --- the store --------------------------------------------------------------------------


def an_experiment(experiment_id="0" * 64, sample_id="synthetic-traffic", frames=2):
    return Experiment(
        id=experiment_id,
        sample_id=sample_id,
        degradation=AppliedDegradation(kind="fog", severity=0.5, seed=0, parameters={"transmission": 0.6}),
        model=MODEL,
        confidence_floor=0.05,
        frame_width=320,
        frame_height=240,
        frames=[FrameResult(index=i, clean=[], degraded=[]) for i in range(frames)],
    )


@pytest.fixture
def cache(tmp_path):
    return ExperimentCache(tmp_path / "cache")


def save(cache, experiment, job_id="job"):
    """What a job does: write frames into its staging folder, then commit."""
    folder = cache.open_staging(job_id)
    ExperimentCache.frame_in(folder, "clean", 0).write_bytes(b"jpeg")
    cache.commit(folder, experiment)


def test_an_opened_staging_folder_has_a_folder_for_each_variant(cache):
    folder = cache.open_staging("job")

    assert ExperimentCache.frame_in(folder, "clean", 0).parent.is_dir()
    assert ExperimentCache.frame_in(folder, "degraded", 0).parent.is_dir()


def test_a_committed_experiment_loads_back_from_a_fresh_store(tmp_path, cache):
    experiment = an_experiment()
    save(cache, experiment)

    assert ExperimentCache(tmp_path / "cache").load(experiment.id) == experiment
    assert cache.frame_file(experiment.id, "clean", 0).read_bytes() == b"jpeg"


def test_commit_moves_the_staging_folder_into_place(cache):
    save(cache, an_experiment(), job_id="job")

    assert not cache.staging("job").exists()


def test_a_staging_folder_is_never_an_entry(cache):
    folder = cache.staging("job")
    ExperimentCache.frame_in(folder, "clean", 0).parent.mkdir(parents=True)
    (folder / "experiment.json").write_text(an_experiment().model_dump_json())

    assert cache.entries() == []


def test_a_fresh_store_clears_staging_left_by_a_crash(tmp_path, cache):
    cache.staging("job").mkdir(parents=True)

    fresh = ExperimentCache(tmp_path / "cache")

    assert not fresh.staging("job").exists()


def test_commit_replaces_an_unreadable_entry(cache):
    experiment = an_experiment()
    (cache.root / experiment.id).mkdir(parents=True)
    (cache.root / experiment.id / "experiment.json").write_text("{not json")

    save(cache, experiment)

    assert cache.load(experiment.id) == experiment


def test_an_unknown_id_loads_nothing(cache):
    assert cache.load("0" * 64) is None


def test_frames_without_a_saved_experiment_are_not_a_complete_entry(cache):
    # What a cancelled, failed or crashed run can leave behind.
    frame = cache.frame_file("0" * 64, "clean", 0)
    frame.parent.mkdir(parents=True)
    frame.write_bytes(b"jpeg")

    assert cache.load("0" * 64) is None
    assert cache.entries() == []


def test_an_unreadable_entry_loads_nothing(cache):
    experiment = an_experiment()
    save(cache, experiment)
    (cache.root / experiment.id / "experiment.json").write_text("{not json")

    assert ExperimentCache(cache.root).load(experiment.id) is None


def test_an_entry_deleted_by_hand_is_forgotten(cache):
    experiment = an_experiment()
    save(cache, experiment)
    assert cache.load(experiment.id) is not None

    shutil.rmtree(cache.root / experiment.id)

    assert cache.load(experiment.id) is None


@pytest.mark.parametrize("bad_id", ["..", "..\\outside", "../outside", "outside", "0" * 63, "A" * 64, "0" * 65])
def test_ids_that_are_not_experiment_ids_never_reach_the_disk(tmp_path, cache, bad_id):
    # A complete entry planted where each id would point if it were used as a folder name.
    save(cache, an_experiment())
    planted = tmp_path / "outside"
    (cache.root / ("0" * 64)).rename(planted)

    assert cache.load(bad_id) is None


def test_entries_list_complete_experiments_newest_first(cache):
    older, newer = an_experiment("1" * 64), an_experiment("2" * 64)
    save(cache, older, job_id="older")
    save(cache, newer, job_id="newer")
    os.utime(cache.root / older.id / "experiment.json", ns=(0, 10**18))
    os.utime(cache.root / newer.id / "experiment.json", ns=(0, 2 * 10**18))

    assert [entry.experiment.id for entry in cache.entries()] == [newer.id, older.id]
    assert cache.entries()[0].saved_at.timestamp() == 2 * 10**9


def test_size_counts_every_file_in_the_cache(cache):
    assert cache.size_bytes() == 0  # no folder yet
    frame = cache.frame_file("0" * 64, "clean", 0)
    frame.parent.mkdir(parents=True)
    frame.write_bytes(b"x" * 100)

    assert cache.size_bytes() == 100
