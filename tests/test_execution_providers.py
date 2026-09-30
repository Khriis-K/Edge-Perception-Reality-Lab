"""Which ONNX Runtime execution providers the detector asks for: an accelerated one when available, CPU always."""

import pytest

from backend.yolox_runner import CPU, choose_providers, session_providers


def test_cpu_alone_when_nothing_accelerated_is_available():
    assert choose_providers(["CPUExecutionProvider"]) == [CPU]


def test_an_available_accelerated_provider_comes_first_with_cpu_behind_it():
    assert choose_providers(["CUDAExecutionProvider", "CPUExecutionProvider"]) == ["CUDAExecutionProvider", CPU]


def test_cuda_is_preferred_over_directml():
    available = ["DmlExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]

    assert choose_providers(available) == ["CUDAExecutionProvider", CPU]


@pytest.mark.parametrize("provider", ["AzureExecutionProvider", "SomethingNewExecutionProvider"])
def test_providers_we_have_not_vetted_are_not_used(provider):
    assert choose_providers([provider, "CPUExecutionProvider"]) == [CPU]


def test_cpu_is_kept_even_if_not_listed():
    assert choose_providers([]) == [CPU]


def test_cuda_runs_without_tf32_and_other_providers_with_their_defaults():
    # TF32 is ORT's CUDA default on Ampere and newer; it moves confidences by ~1e-2 against the CPU.
    assert session_providers(["CUDAExecutionProvider", CPU]) == [
        ("CUDAExecutionProvider", {"use_tf32": "0"}),
        (CPU, {}),
    ]
