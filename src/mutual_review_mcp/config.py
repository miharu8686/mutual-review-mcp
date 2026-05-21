"""config.py - API keys and runtime settings.

Resolution order for API keys:
    1. Environment variable
    2. Optional JSON config file (path from MUTUAL_REVIEW_CONFIG, or platform default)
    3. Raise RuntimeError (bilingual message)

Platform default for config file:
    - Windows:  %APPDATA%/mutual-review-mcp/config.json
    - macOS:    ~/Library/Application Support/mutual-review-mcp/config.json
    - Linux:    $XDG_CONFIG_HOME/mutual-review-mcp/config.json
                (or ~/.config/mutual-review-mcp/config.json)
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Optional

DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_GPT_MODEL = "gpt-4o"


def _platform_config_dir() -> pathlib.Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(pathlib.Path.home() / "AppData" / "Roaming")
        return pathlib.Path(base) / "mutual-review-mcp"
    if sys.platform == "darwin":
        return pathlib.Path.home() / "Library" / "Application Support" / "mutual-review-mcp"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = pathlib.Path(xdg) if xdg else pathlib.Path.home() / ".config"
    return base / "mutual-review-mcp"


def _platform_data_dir() -> pathlib.Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(pathlib.Path.home() / "AppData" / "Local")
        return pathlib.Path(base) / "mutual-review-mcp"
    if sys.platform == "darwin":
        return pathlib.Path.home() / "Library" / "Application Support" / "mutual-review-mcp"
    xdg = os.environ.get("XDG_DATA_HOME")
    base = pathlib.Path(xdg) if xdg else pathlib.Path.home() / ".local" / "share"
    return base / "mutual-review-mcp"


def get_config_path() -> pathlib.Path:
    override = os.environ.get("MUTUAL_REVIEW_CONFIG")
    if override:
        return pathlib.Path(override)
    return _platform_config_dir() / "config.json"


def _load_config_file() -> dict:
    p = get_config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _bilingual_missing_key(env_var: str) -> str:
    return (
        f"{env_var} が設定されていません / {env_var} is not set. "
        f"環境変数を設定するか、{get_config_path()} に "
        f'{{"{_config_key_for(env_var)}": "<key>"}} を保存してください. '
        f"Set the environment variable, or save the key to that config file."
    )


def _config_key_for(env_var: str) -> str:
    return {
        "ANTHROPIC_API_KEY": "anthropic_api_key",
        "OPENAI_API_KEY": "openai_api_key",
    }.get(env_var, env_var.lower())


def get_anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    cfg = _load_config_file()
    key = (cfg.get("anthropic_api_key") or cfg.get("api_key") or "").strip()
    if key:
        return key
    raise RuntimeError(_bilingual_missing_key("ANTHROPIC_API_KEY"))


def get_openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    cfg = _load_config_file()
    key = (cfg.get("openai_api_key") or "").strip()
    if key:
        return key
    raise RuntimeError(_bilingual_missing_key("OPENAI_API_KEY"))


def get_claude_model() -> str:
    return os.environ.get("MUTUAL_REVIEW_CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL).strip() or DEFAULT_CLAUDE_MODEL


def get_gpt_model() -> str:
    return os.environ.get("MUTUAL_REVIEW_GPT_MODEL", DEFAULT_GPT_MODEL).strip() or DEFAULT_GPT_MODEL


def is_cost_tracking_enabled() -> bool:
    return os.environ.get("ENABLE_COST_TRACKING", "").lower() in ("1", "true", "yes", "on")


def get_cost_log_path() -> pathlib.Path:
    override = os.environ.get("COST_LOG_PATH")
    if override:
        return pathlib.Path(override)
    return _platform_data_dir() / "usage.jsonl"


def anthropic_client():
    import anthropic
    return anthropic.Anthropic(api_key=get_anthropic_key())


def openai_client():
    import openai
    return openai.OpenAI(api_key=get_openai_key())


def bilingual_api_error(provider: str, exc: Exception) -> str:
    return (
        f"{provider} API への接続に失敗しました: {exc} / "
        f"Failed to call {provider} API: {exc}"
    )


# Optional helper for tests
def _reset_for_test():
    pass


__all__ = [
    "DEFAULT_CLAUDE_MODEL",
    "DEFAULT_GPT_MODEL",
    "get_config_path",
    "get_anthropic_key",
    "get_openai_key",
    "get_claude_model",
    "get_gpt_model",
    "is_cost_tracking_enabled",
    "get_cost_log_path",
    "anthropic_client",
    "openai_client",
    "bilingual_api_error",
]
