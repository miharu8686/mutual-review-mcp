"""Unit tests that don't require API keys."""
from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from mutual_review_mcp import reviewer  # noqa: E402
from mutual_review_mcp import config  # noqa: E402


def test_guess_language_python():
    assert reviewer.guess_language("foo.py") == "python"


def test_guess_language_typescript():
    assert reviewer.guess_language("foo.ts") == "typescript"
    assert reviewer.guess_language("foo.tsx") == "typescript"


def test_guess_language_unknown():
    assert reviewer.guess_language("foo.xyz") is None


def test_guess_language_none():
    assert reviewer.guess_language(None) is None
    assert reviewer.guess_language("") is None


def test_calc_cost_known_model():
    cost = reviewer._calc_cost("gpt-4o-mini", 1_000_000, 0)
    assert cost == 0.15


def test_calc_cost_unknown_model_falls_back():
    cost = reviewer._calc_cost("nonexistent-model", 1_000_000, 0)
    assert cost == 5.0


def test_format_result_error():
    out = reviewer.format_result({"error": "boom"})
    assert "ERROR" in out and "boom" in out


def test_review_diff_empty():
    result = reviewer.review_diff("")
    assert "error" in result


def test_review_diff_whitespace():
    result = reviewer.review_diff("   \n  \n")
    assert "error" in result


def test_review_file_missing():
    result = reviewer.review_file("/nonexistent/path/zzz.py")
    assert "error" in result


def test_missing_anthropic_key_bilingual(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("MUTUAL_REVIEW_CONFIG", str(tmp_path / "noconfig.json"))
    try:
        config.get_anthropic_key()
    except RuntimeError as exc:
        msg = str(exc)
        assert "ANTHROPIC_API_KEY" in msg
        assert "設定" in msg  # JP
        assert "is not set" in msg  # EN
    else:
        raise AssertionError("RuntimeError not raised")


def test_missing_openai_key_bilingual(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MUTUAL_REVIEW_CONFIG", str(tmp_path / "noconfig.json"))
    try:
        config.get_openai_key()
    except RuntimeError as exc:
        msg = str(exc)
        assert "OPENAI_API_KEY" in msg
        assert "is not set" in msg
    else:
        raise AssertionError("RuntimeError not raised")
