"""config.py: key-resolution priority (env > file > error) and settings."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

from mutual_review_mcp import config


def _write_config(tmp_path, monkeypatch, data: dict) -> pathlib.Path:
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("MUTUAL_REVIEW_CONFIG", str(p))
    return p


# ---- priority: environment variable wins -----------------------------------

def test_env_wins_over_config_file(monkeypatch, tmp_path):
    _write_config(tmp_path, monkeypatch, {"anthropic_api_key": "file-key"})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    assert config.get_anthropic_key() == "env-key"


def test_openai_env_wins(monkeypatch, tmp_path):
    _write_config(tmp_path, monkeypatch, {"openai_api_key": "file-key"})
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    assert config.get_openai_key() == "env-key"


def test_whitespace_env_falls_through_to_file(monkeypatch, tmp_path):
    _write_config(tmp_path, monkeypatch, {"anthropic_api_key": "file-key"})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    assert config.get_anthropic_key() == "file-key"


# ---- priority: config file fallback -----------------------------------------

def test_anthropic_from_config_file(monkeypatch, tmp_path):
    _write_config(tmp_path, monkeypatch, {"anthropic_api_key": "file-key"})
    assert config.get_anthropic_key() == "file-key"


def test_anthropic_legacy_api_key_field(monkeypatch, tmp_path):
    _write_config(tmp_path, monkeypatch, {"api_key": "legacy-key"})
    assert config.get_anthropic_key() == "legacy-key"


def test_openai_from_config_file(monkeypatch, tmp_path):
    _write_config(tmp_path, monkeypatch, {"openai_api_key": "file-key"})
    assert config.get_openai_key() == "file-key"


def test_broken_json_config_treated_as_missing(monkeypatch, tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("MUTUAL_REVIEW_CONFIG", str(p))
    with pytest.raises(RuntimeError):
        config.get_anthropic_key()


def test_non_object_json_config_treated_as_missing(monkeypatch, tmp_path):
    # Valid JSON, but not an object: must yield the clean bilingual
    # RuntimeError, not an AttributeError.
    p = tmp_path / "config.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setenv("MUTUAL_REVIEW_CONFIG", str(p))
    with pytest.raises(RuntimeError) as ei:
        config.get_anthropic_key()
    assert "ANTHROPIC_API_KEY" in str(ei.value)


# ---- priority: explicit error ------------------------------------------------

def test_missing_anthropic_raises_bilingual_with_guidance():
    with pytest.raises(RuntimeError) as ei:
        config.get_anthropic_key()
    msg = str(ei.value)
    assert "ANTHROPIC_API_KEY" in msg
    assert "設定されていません" in msg and "is not set" in msg
    assert "anthropic_api_key" in msg  # tells the user the config-file field name
    assert "no-config.json" in msg     # tells the user the exact path looked at


def test_missing_openai_raises_bilingual():
    with pytest.raises(RuntimeError) as ei:
        config.get_openai_key()
    msg = str(ei.value)
    assert "OPENAI_API_KEY" in msg and "is not set" in msg


def test_validate_keys_ok(monkeypatch, api_keys):
    assert config.validate_keys() is None


def test_validate_keys_fails_on_missing_openai(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    with pytest.raises(RuntimeError):
        config.validate_keys()


def test_validate_keys_reports_both_missing_at_once():
    with pytest.raises(RuntimeError) as ei:
        config.validate_keys()
    msg = str(ei.value)
    assert "ANTHROPIC_API_KEY" in msg and "OPENAI_API_KEY" in msg


# ---- config path resolution ---------------------------------------------------

def test_config_path_env_override(monkeypatch):
    monkeypatch.setenv("MUTUAL_REVIEW_CONFIG", r"Z:\custom\cfg.json")
    assert config.get_config_path() == pathlib.Path(r"Z:\custom\cfg.json")


def test_config_path_default_win32(monkeypatch, tmp_path):
    monkeypatch.delenv("MUTUAL_REVIEW_CONFIG", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert config.get_config_path() == tmp_path / "mutual-review-mcp" / "config.json"


def test_config_path_win32_no_appdata(monkeypatch):
    monkeypatch.delenv("MUTUAL_REVIEW_CONFIG", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("APPDATA", raising=False)
    expected = pathlib.Path.home() / "AppData" / "Roaming" / "mutual-review-mcp" / "config.json"
    assert config.get_config_path() == expected


def test_config_path_default_darwin(monkeypatch):
    monkeypatch.delenv("MUTUAL_REVIEW_CONFIG", raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    expected = pathlib.Path.home() / "Library" / "Application Support" / "mutual-review-mcp" / "config.json"
    assert config.get_config_path() == expected


def test_config_path_linux_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv("MUTUAL_REVIEW_CONFIG", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config.get_config_path() == tmp_path / "mutual-review-mcp" / "config.json"


def test_config_path_linux_no_xdg(monkeypatch):
    monkeypatch.delenv("MUTUAL_REVIEW_CONFIG", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    expected = pathlib.Path.home() / ".config" / "mutual-review-mcp" / "config.json"
    assert config.get_config_path() == expected


# ---- data dir / cost log -------------------------------------------------------

def test_cost_log_path_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_LOG_PATH", str(tmp_path / "u.jsonl"))
    assert config.get_cost_log_path() == tmp_path / "u.jsonl"


def test_cost_log_default_win32(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert config.get_cost_log_path() == tmp_path / "mutual-review-mcp" / "usage.jsonl"


def test_cost_log_win32_no_localappdata(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    expected = pathlib.Path.home() / "AppData" / "Local" / "mutual-review-mcp" / "usage.jsonl"
    assert config.get_cost_log_path() == expected


def test_cost_log_default_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    expected = pathlib.Path.home() / "Library" / "Application Support" / "mutual-review-mcp" / "usage.jsonl"
    assert config.get_cost_log_path() == expected


def test_cost_log_linux_xdg(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert config.get_cost_log_path() == tmp_path / "mutual-review-mcp" / "usage.jsonl"


def test_cost_log_linux_no_xdg(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    expected = pathlib.Path.home() / ".local" / "share" / "mutual-review-mcp" / "usage.jsonl"
    assert config.get_cost_log_path() == expected


# ---- models / flags --------------------------------------------------------------

def test_claude_model_default():
    assert config.get_claude_model() == config.DEFAULT_CLAUDE_MODEL


def test_claude_model_override(monkeypatch):
    monkeypatch.setenv("MUTUAL_REVIEW_CLAUDE_MODEL", "claude-haiku-4-5")
    assert config.get_claude_model() == "claude-haiku-4-5"


def test_claude_model_empty_env_falls_back(monkeypatch):
    monkeypatch.setenv("MUTUAL_REVIEW_CLAUDE_MODEL", "   ")
    assert config.get_claude_model() == config.DEFAULT_CLAUDE_MODEL


def test_gpt_model_default_and_override(monkeypatch):
    assert config.get_gpt_model() == config.DEFAULT_GPT_MODEL
    monkeypatch.setenv("MUTUAL_REVIEW_GPT_MODEL", "gpt-4o-mini")
    assert config.get_gpt_model() == "gpt-4o-mini"


@pytest.mark.parametrize("value,expected", [
    ("1", True), ("true", True), ("YES", True), ("on", True),
    ("", False), ("0", False), ("off", False), ("no", False),
])
def test_cost_tracking_flag(monkeypatch, value, expected):
    monkeypatch.setenv("ENABLE_COST_TRACKING", value)
    assert config.is_cost_tracking_enabled() is expected


def test_bilingual_api_error_mentions_provider():
    msg = config.bilingual_api_error("Anthropic", ValueError("boom"))
    assert "Anthropic" in msg and "boom" in msg
    assert "失敗しました" in msg and "Failed to call" in msg
