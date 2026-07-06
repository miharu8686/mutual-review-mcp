"""server.py: MCP tool schemas, dispatch, and startup fail-fast."""
from __future__ import annotations

import asyncio

import pytest

from mutual_review_mcp import reviewer, server


def _run(coro):
    return asyncio.run(coro)


# ---- tool definitions -----------------------------------------------------

def test_list_tools_names_and_schemas():
    tools = _run(server.list_tools())
    by_name = {t.name: t for t in tools}
    assert set(by_name) == {"review_file", "review_code", "review_diff"}

    assert by_name["review_file"].inputSchema["required"] == ["path"]
    assert by_name["review_code"].inputSchema["required"] == ["code"]
    assert by_name["review_diff"].inputSchema["required"] == ["diff"]

    for tool in tools:
        schema = tool.inputSchema
        assert schema["type"] == "object"
        assert "synthesize" in schema["properties"]
        assert schema["properties"]["synthesize"]["default"] is True
        assert tool.description


# ---- dispatch ----------------------------------------------------------------

def test_call_tool_review_file_passes_args(monkeypatch):
    seen = {}

    def fake(path, language, context, synthesize):
        seen.update(path=path, language=language, context=context, synthesize=synthesize)
        return {"error": "stub"}

    monkeypatch.setattr(reviewer, "review_file", fake)
    out = _run(server.call_tool("review_file", {"path": "/x.py", "language": "python"}))
    assert seen == {"path": "/x.py", "language": "python", "context": None, "synthesize": True}
    assert out[0].type == "text"
    assert out[0].text == "ERROR: stub"


def test_call_tool_review_code_passes_args(monkeypatch):
    seen = {}

    def fake(code, language, filename, context, synthesize):
        seen.update(code=code, language=language, filename=filename,
                    context=context, synthesize=synthesize)
        return {"error": "stub"}

    monkeypatch.setattr(reviewer, "review_code", fake)
    _run(server.call_tool("review_code", {"code": "x=1", "synthesize": False}))
    assert seen == {"code": "x=1", "language": None, "filename": None,
                    "context": None, "synthesize": False}


def test_call_tool_review_diff_passes_args(monkeypatch):
    seen = {}

    def fake(diff, context, synthesize):
        seen.update(diff=diff, context=context, synthesize=synthesize)
        return {"error": "stub"}

    monkeypatch.setattr(reviewer, "review_diff", fake)
    _run(server.call_tool("review_diff", {"diff": "DIFF", "context": "c"}))
    assert seen == {"diff": "DIFF", "context": "c", "synthesize": True}


def test_call_tool_unknown():
    out = _run(server.call_tool("nope", {}))
    assert out[0].text == "Unknown tool: nope"


def test_call_tool_exception_becomes_text(monkeypatch):
    def fake(*args):
        raise ValueError("boom")

    monkeypatch.setattr(reviewer, "review_diff", fake)
    out = _run(server.call_tool("review_diff", {"diff": "d"}))
    assert out[0].text.startswith("Error: boom")


# ---- startup fail-fast -----------------------------------------------------------

def test_validate_startup_ok(api_keys):
    assert server._validate_startup() is None


def test_validate_startup_missing_keys_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        server._validate_startup()
    assert ei.value.code == 2
    err = capsys.readouterr().err
    assert "ERROR:" in err
    assert "ANTHROPIC_API_KEY" in err
    assert "is not set" in err  # guidance is bilingual
