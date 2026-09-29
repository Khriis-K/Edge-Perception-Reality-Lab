"""The pre-commit mock-only check: flags tests whose only content is mocking, not tests that mock and assert."""

import importlib.util
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "check_test_integrity.py"
spec = importlib.util.spec_from_file_location("check_test_integrity", HOOK)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def added(*lines: str) -> str:
    """A diff that adds these lines."""
    return "\n".join(["+++ b/tests/test_x.py", *(f"+{line}" for line in lines)])


def test_bare_pytest_assert_counts_as_an_assertion():
    diff = added(
        "def test_binds_localhost(monkeypatch):",
        "    monkeypatch.setattr(entry.uvicorn, 'run', fake_run)",
        "    entry.main([])",
        "    assert calls['host'] == '127.0.0.1'",
    )

    assert checker.check_for_mock_only_tests(diff) == []


def test_mock_assert_method_counts_as_an_assertion():
    diff = added(
        "def test_calls_run():",
        "    run = MagicMock()",
        "    start(run)",
        "    run.assert_called_once_with(port=8000)",
    )

    assert checker.check_for_mock_only_tests(diff) == []


def test_mock_without_any_assertion_is_flagged():
    diff = added(
        "def test_nothing_checked(monkeypatch):",
        "    monkeypatch.setattr(entry.uvicorn, 'run', fake_run)",
        "    entry.main([])",
    )

    assert checker.check_for_mock_only_tests(diff) == [
        "Test 'test_nothing_checked' uses mocks but has no real assertions"
    ]


def test_word_containing_assert_is_not_an_assertion():
    diff = added(
        "def test_reassert(monkeypatch):",
        "    monkeypatch.setattr(entry, 'reasserted', True)",
        "    reassertion = entry.main([])",
    )

    assert len(checker.check_for_mock_only_tests(diff)) == 1
