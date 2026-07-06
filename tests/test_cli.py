"""cli.py: argument handling, input sources, fail-fast, exit codes."""
from __future__ import annotations

import io

import pytest

from mutual_review_mcp import cli, reviewer


@pytest.fixture
def stub_review(monkeypatch):
    """Stub all reviewer entry points; record calls; bypass real formatting."""
    calls = {}

    def fake_review_file(path, language=None, context=None, synthesize_result=True):
        calls["mode"] = "file"
        calls["args"] = dict(path=path, language=language, context=context,
                             synthesize_result=synthesize_result)
        return {"sentinel": True}

    def fake_review_code(code, language=None, filename=None, context=None, synthesize_result=True):
        calls["mode"] = "code"
        calls["args"] = dict(code=code, language=language, context=context,
                             synthesize_result=synthesize_result)
        return {"sentinel": True}

    def fake_review_diff(diff, context=None, synthesize_result=True):
        calls["mode"] = "diff"
        calls["args"] = dict(diff=diff, context=context, synthesize_result=synthesize_result)
        return {"sentinel": True}

    monkeypatch.setattr(reviewer, "review_file", fake_review_file)
    monkeypatch.setattr(reviewer, "review_code", fake_review_code)
    monkeypatch.setattr(reviewer, "review_diff", fake_review_diff)
    monkeypatch.setattr(reviewer, "format_result", lambda result: "FORMATTED")
    return calls


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as ei:
        cli.main(["--version"])
    assert ei.value.code == 0
    assert "mutual-review-mcp" in capsys.readouterr().out


def test_no_args_is_usage_error():
    with pytest.raises(SystemExit) as ei:
        cli.main([])
    assert ei.value.code == 2


def test_code_mode(api_keys, stub_review, capsys):
    rc = cli.main(["--code", "def foo(): pass", "--language", "python"])
    assert rc == 0
    assert stub_review["mode"] == "code"
    assert stub_review["args"]["code"] == "def foo(): pass"
    assert stub_review["args"]["language"] == "python"
    assert stub_review["args"]["synthesize_result"] is True
    assert "FORMATTED" in capsys.readouterr().out


def test_code_from_stdin(api_keys, stub_review, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("stdin-code"))
    rc = cli.main(["--code", "-"])
    assert rc == 0
    assert stub_review["args"]["code"] == "stdin-code"


def test_code_from_existing_file(api_keys, stub_review, tmp_path):
    p = tmp_path / "snippet.py"
    p.write_text("x = 42", encoding="utf-8")
    rc = cli.main(["--code", str(p)])
    assert rc == 0
    assert stub_review["args"]["code"] == "x = 42"


def test_path_mode_with_no_synth(api_keys, stub_review, tmp_path):
    p = tmp_path / "target.py"
    p.write_text("y = 1", encoding="utf-8")
    rc = cli.main([str(p), "--no-synth", "--context", "bg"])
    assert rc == 0
    assert stub_review["mode"] == "file"
    assert stub_review["args"]["path"] == str(p)
    assert stub_review["args"]["context"] == "bg"
    assert stub_review["args"]["synthesize_result"] is False


def test_diff_from_stdin(api_keys, stub_review, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("DIFF-TEXT"))
    rc = cli.main(["--diff", "-"])
    assert rc == 0
    assert stub_review["mode"] == "diff"
    assert stub_review["args"]["diff"] == "DIFF-TEXT"


def test_missing_keys_fail_fast_before_review(stub_review, capsys):
    # No api_keys fixture: keys are absent (hermetic env), so main must
    # exit 2 without ever calling a reviewer function.
    rc = cli.main(["--code", "x"])
    assert rc == 2
    assert "mode" not in stub_review  # reviewer never invoked
    err = capsys.readouterr().err
    assert "ERROR:" in err and "ANTHROPIC_API_KEY" in err


def test_reviewer_runtime_error_exits_2(api_keys, stub_review, monkeypatch, capsys):
    def boom(**kwargs):
        raise RuntimeError("api down")

    monkeypatch.setattr(reviewer, "review_code", lambda *a, **k: boom())
    rc = cli.main(["--code", "x"])
    assert rc == 2
    assert "api down" in capsys.readouterr().err


def test_read_stdin_or_file_literal_passthrough():
    assert cli._read_stdin_or_file("not a real path **") == "not a real path **"
