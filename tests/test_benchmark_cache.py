"""Benchmark experiments in the cache: an id covering the manifest and every result-affecting setting, and storage
that keeps them apart from Synthetic runs."""

import pytest

from backend.benchmark import BenchmarkFrame
from backend.benchmark_run import BenchmarkExperiment
from backend.detection import ModelInfo
from backend.experiment_cache import ExperimentCache, benchmark_experiment_id
from backend.subset import Manifest

MODEL = ModelInfo(name="Stub detector", version="fixture-1", runtime="none")
MANIFEST = Manifest(seed=0, cap=300, vocabulary_version=1, frames={"clear-day": ["a", "b"], "fog-day": ["c"]})
BASE = {"manifest": MANIFEST, "model": MODEL, "class_mapping_version": 1, "confidence_floor": 0.05}


def test_the_same_settings_give_the_same_id():
    assert benchmark_experiment_id(**BASE) == benchmark_experiment_id(**BASE)


@pytest.mark.parametrize(
    "change",
    [
        {"manifest": Manifest(seed=1, cap=300, vocabulary_version=1, frames=MANIFEST.frames)},
        {"manifest": Manifest(seed=0, cap=5, vocabulary_version=1, frames=MANIFEST.frames)},
        {"manifest": Manifest(seed=0, cap=300, vocabulary_version=2, frames=MANIFEST.frames)},
        {"manifest": Manifest(seed=0, cap=300, vocabulary_version=1, frames={"clear-day": ["a"], "fog-day": ["c"]})},
        {"manifest": Manifest(seed=0, cap=300, vocabulary_version=1, frames={"clear-day": ["a", "b"], "fog-night": ["c"]})},
        {"model": MODEL.model_copy(update={"version": "fixture-2"})},
        {"class_mapping_version": 2},
        {"confidence_floor": 0.1},
    ],
)
def test_changing_any_result_affecting_setting_gives_another_id(change):
    assert benchmark_experiment_id(**{**BASE, **change}) != benchmark_experiment_id(**BASE)


def test_the_runtime_is_not_part_of_the_id():
    other_runtime = {**BASE, "model": MODEL.model_copy(update={"runtime": "onnxruntime 9"})}

    assert benchmark_experiment_id(**other_runtime) == benchmark_experiment_id(**BASE)


def experiment():
    return BenchmarkExperiment(
        id=benchmark_experiment_id(**BASE),
        manifest=MANIFEST,
        model=MODEL,
        class_mapping_version=1,
        confidence_floor=0.05,
        frames={"clear-day": [BenchmarkFrame(id="a", predictions=[], truths=[])]},
        warnings=["a warning"],
    )


def test_a_committed_benchmark_loads_back_whole(tmp_path):
    cache = ExperimentCache(tmp_path)
    stored = experiment()
    folder = cache.staging("job-1")
    folder.mkdir(parents=True)

    cache.commit(folder, stored)

    assert cache.load_benchmark(stored.id) == stored
    assert not folder.exists()


def test_benchmarks_are_neither_synthetic_runs_nor_listed_as_them(tmp_path):
    cache = ExperimentCache(tmp_path)
    stored = experiment()
    folder = cache.staging("job-1")
    folder.mkdir(parents=True)
    cache.commit(folder, stored)

    assert cache.load(stored.id) is None
    assert cache.entries() == []


def test_an_unknown_or_malformed_benchmark_id_loads_nothing(tmp_path):
    cache = ExperimentCache(tmp_path)

    assert cache.load_benchmark("f" * 64) is None
    assert cache.load_benchmark("..\\..\\etc") is None
