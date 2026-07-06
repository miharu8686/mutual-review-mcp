"""Shared fixtures. All tests run without network access or real API keys."""
from __future__ import annotations

import pathlib
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch, tmp_path):
    """Isolate every test from the developer machine.

    - No API keys leak in from the real environment.
    - The platform-default config.json (which may hold real keys on a dev
      machine) is never read: MUTUAL_REVIEW_CONFIG points at a nonexistent
      file unless a test overrides it.
    """
    for var in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "MUTUAL_REVIEW_CLAUDE_MODEL",
        "MUTUAL_REVIEW_GPT_MODEL",
        "ENABLE_COST_TRACKING",
        "COST_LOG_PATH",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("MUTUAL_REVIEW_CONFIG", str(tmp_path / "no-config.json"))


@pytest.fixture
def api_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")


class FakeAnthropicClient:
    """Stands in for anthropic.Anthropic. Returns queued texts in order."""

    def __init__(self, texts=("CLAUDE-REVIEW",), input_tokens=100, output_tokens=50):
        self._texts = list(texts)
        self.calls: list[dict] = []
        self._usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        text = self._texts.pop(0) if len(self._texts) > 1 else self._texts[0]
        return SimpleNamespace(content=[SimpleNamespace(text=text)], usage=self._usage)


class FakeOpenAIClient:
    """Stands in for openai.OpenAI."""

    def __init__(self, text="GPT-REVIEW", prompt_tokens=80, completion_tokens=40):
        self._text = text
        self.calls: list[dict] = []
        self._usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        completions = SimpleNamespace(create=self._create)
        self.chat = SimpleNamespace(completions=completions)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self._text)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=self._usage)


class RaisingClient:
    """A client whose create() always raises, for API-error paths."""

    def __init__(self, exc):
        self._exc = exc
        self.messages = SimpleNamespace(create=self._raise)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._raise))

    def _raise(self, **kwargs):
        raise self._exc


@pytest.fixture
def fake_clients(monkeypatch):
    """Patch config client factories with fakes; return them for assertions."""
    from mutual_review_mcp import config

    claude = FakeAnthropicClient(texts=["CLAUDE-REVIEW", "SYNTH-REPORT"])
    gpt = FakeOpenAIClient()
    monkeypatch.setattr(config, "anthropic_client", lambda: claude)
    monkeypatch.setattr(config, "openai_client", lambda: gpt)
    return SimpleNamespace(claude=claude, gpt=gpt)
