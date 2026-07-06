"""reviewer.py core paths with mocked API clients (no network, no cost)."""
from __future__ import annotations

import json

import pytest

from conftest import RaisingClient

from mutual_review_mcp import reviewer


def test_review_code_full_flow(fake_clients):
    result = reviewer.review_code("print(1)", language="python", filename="a.py", context="ctx")

    assert result["filename"] == "a.py"
    assert result["language"] == "python"
    assert result["claude"]["review"] == "CLAUDE-REVIEW"
    assert result["gpt"]["review"] == "GPT-REVIEW"
    assert result["synthesis"]["text"] == "SYNTH-REPORT"
    assert result["claude"]["tokens"] == {"input": 100, "output": 50}
    assert result["gpt"]["tokens"] == {"input": 80, "output": 40}

    # Claude called twice: review + synthesis, with the right system prompts.
    assert len(fake_clients.claude.calls) == 2
    assert fake_clients.claude.calls[0]["system"] == reviewer.REVIEW_SYSTEM
    assert fake_clients.claude.calls[1]["system"] == reviewer.SYNTH_SYSTEM
    # GPT called once with the review system prompt as a system message.
    assert len(fake_clients.gpt.calls) == 1
    assert fake_clients.gpt.calls[0]["messages"][0] == {"role": "system", "content": reviewer.REVIEW_SYSTEM}
    # Prompt carries context, filename and the fenced code.
    user_prompt = fake_clients.claude.calls[0]["messages"][0]["content"]
    assert "Context: ctx" in user_prompt
    assert "File: a.py" in user_prompt
    assert "```python\nprint(1)\n```" in user_prompt


def test_review_code_no_synth(fake_clients):
    result = reviewer.review_code("x = 1", synthesize_result=False)
    assert "synthesis" not in result
    assert len(fake_clients.claude.calls) == 1


def test_review_code_auto_language_from_filename(fake_clients):
    result = reviewer.review_code("x", filename="foo.rs", synthesize_result=False)
    assert result["language"] == "rust"


def test_review_file_happy(fake_clients, tmp_path):
    p = tmp_path / "sample.py"
    p.write_text("def f():\n    return 1\n", encoding="utf-8")
    result = reviewer.review_file(str(p), synthesize_result=False)
    assert result["filename"] == "sample.py"
    assert result["language"] == "python"
    assert "error" not in result


def test_review_diff_happy(fake_clients):
    result = reviewer.review_diff("--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n", synthesize_result=False)
    assert result["filename"] == "changes.diff"
    assert result["language"] == "diff"


def test_synthesize_truncates_long_code(fake_clients):
    code = "A" * 4000
    reviewer.synthesize(
        code,
        {"reviewer": "Claude (m)", "review": "r1"},
        {"reviewer": "GPT (m)", "review": "r2"},
    )
    prompt = fake_clients.claude.calls[-1]["messages"][0]["content"]
    assert "A" * 3000 + "..." in prompt
    assert "A" * 3001 not in prompt


def test_review_with_claude_api_error(monkeypatch):
    from mutual_review_mcp import config
    monkeypatch.setattr(config, "anthropic_client", lambda: RaisingClient(ConnectionError("down")))
    with pytest.raises(RuntimeError) as ei:
        reviewer.review_with_claude("x")
    msg = str(ei.value)
    assert "Anthropic" in msg and "down" in msg
    assert "失敗しました" in msg and "Failed to call" in msg


def test_review_with_gpt_api_error(monkeypatch):
    from mutual_review_mcp import config
    monkeypatch.setattr(config, "openai_client", lambda: RaisingClient(ConnectionError("down")))
    with pytest.raises(RuntimeError) as ei:
        reviewer.review_with_gpt("x")
    assert "OpenAI" in str(ei.value)


# ---- cost tracking ----------------------------------------------------------

def test_track_enabled_writes_jsonl(monkeypatch, tmp_path, fake_clients):
    log = tmp_path / "usage.jsonl"
    monkeypatch.setenv("ENABLE_COST_TRACKING", "1")
    monkeypatch.setenv("COST_LOG_PATH", str(log))
    reviewer.review_code("x", synthesize_result=False)

    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2  # one record per provider call
    records = [json.loads(line) for line in lines]
    assert {r["provider"] for r in records} == {"anthropic", "openai"}
    for r in records:
        assert r["cost_usd"] > 0
        assert r["context"] == "review"


def test_track_disabled_writes_nothing(monkeypatch, tmp_path, fake_clients):
    log = tmp_path / "usage.jsonl"
    monkeypatch.setenv("COST_LOG_PATH", str(log))
    reviewer.review_code("x", synthesize_result=False)
    assert not log.exists()


def test_track_swallows_oserror(monkeypatch, tmp_path, fake_clients):
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file", encoding="utf-8")
    monkeypatch.setenv("ENABLE_COST_TRACKING", "1")
    # Parent of the log path is a FILE -> mkdir/open raises OSError, which must be swallowed.
    monkeypatch.setenv("COST_LOG_PATH", str(blocker / "usage.jsonl"))
    result = reviewer.review_code("x", synthesize_result=False)
    assert "error" not in result


# ---- formatting ---------------------------------------------------------------

def _result_dict(with_synth: bool) -> dict:
    d = {
        "filename": "a.py",
        "language": "python",
        "claude": {"reviewer": "Claude (m1)", "review": "CR", "tokens": {"input": 1, "output": 2}},
        "gpt": {"reviewer": "GPT (m2)", "review": "GR", "tokens": {"input": 3, "output": 4}},
    }
    if with_synth:
        d["synthesis"] = {"text": "SY", "tokens": {"input": 5, "output": 6}}
    return d


def test_format_result_with_synthesis():
    out = reviewer.format_result(_result_dict(True))
    assert "# Mutual Review: a.py" in out
    assert "## Claude (m1)" in out and "CR" in out
    assert "## GPT (m2)" in out and "GR" in out
    assert "## Synthesis" in out and "SY" in out
    assert "_Tokens: 5 in / 6 out_" in out


def test_format_result_without_synthesis():
    out = reviewer.format_result(_result_dict(False))
    assert "## Synthesis" not in out
