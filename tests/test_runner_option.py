"""The start command's --runner option picks the detector the app runs."""

import pytest

import backend.__main__ as entry
from backend.stub_runner import StubRunner


def test_the_default_runner_is_the_real_detector():
    assert entry.build_parser().parse_args([]).runner == "yolox"


def test_the_stub_runner_can_be_chosen(tmp_path):
    assert isinstance(entry.build_runner("stub", model_path=tmp_path / "unused.onnx"), StubRunner)


def test_missing_weights_start_the_app_without_a_detector(tmp_path, capsys):
    assert entry.build_runner("yolox", model_path=tmp_path / "missing.onnx") is None
    assert "scripts/fetch_model.py" in capsys.readouterr().err


def test_unknown_runners_are_rejected():
    with pytest.raises(SystemExit):
        entry.build_parser().parse_args(["--runner", "magic"])
