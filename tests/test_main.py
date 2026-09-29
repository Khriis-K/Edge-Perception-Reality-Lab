"""The start command binds to 127.0.0.1 only, on the requested port."""

import pytest

import backend.__main__ as entry


def test_server_binds_to_localhost_only(monkeypatch):
    calls = {}
    monkeypatch.setattr(entry.uvicorn, "run", lambda app, **kw: calls.update(kw))

    entry.main(["--port", "9123"])

    assert calls["host"] == "127.0.0.1"
    assert calls["port"] == 9123


def test_there_is_no_host_option():
    with pytest.raises(SystemExit):
        entry.build_parser().parse_args(["--host", "0.0.0.0"])


def test_dev_flag_defaults_off():
    assert entry.build_parser().parse_args([]).dev is False
