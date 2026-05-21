"""cli.py - Simple command-line interface for mutual-review-mcp.

Usage examples:
    mutual-review path/to/file.py
    mutual-review --code "def foo(): pass" --language python
    mutual-review --diff changes.diff
    cat changes.diff | mutual-review --diff -
"""
from __future__ import annotations

import argparse
import io
import pathlib
import sys

from . import __version__, reviewer


def _force_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 so non-ASCII review text prints on Windows cp932."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, io.UnsupportedOperation):
            pass


def _read_stdin_or_file(token: str) -> str:
    if token == "-":
        return sys.stdin.read()
    p = pathlib.Path(token)
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mutual-review",
        description="Mutual code review: Claude + GPT-4o.",
    )
    parser.add_argument("--version", action="version", version=f"mutual-review-mcp {__version__}")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("path", nargs="?", help="Path to a file to review")
    group.add_argument("--code", help="Inline code to review (or path / '-' for stdin)")
    group.add_argument("--diff", help="Unified diff text (or path / '-' for stdin)")
    parser.add_argument("--language", help="Language hint (auto-detected for --path)")
    parser.add_argument("--context", help="Optional context")
    parser.add_argument("--no-synth", action="store_true", help="Skip synthesis step")
    return parser


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    synthesize = not args.no_synth

    try:
        if args.path:
            result = reviewer.review_file(
                args.path,
                language=args.language,
                context=args.context,
                synthesize_result=synthesize,
            )
        elif args.code is not None:
            code = _read_stdin_or_file(args.code)
            result = reviewer.review_code(
                code,
                language=args.language,
                context=args.context,
                synthesize_result=synthesize,
            )
        else:  # --diff
            diff = _read_stdin_or_file(args.diff)
            result = reviewer.review_diff(
                diff,
                context=args.context,
                synthesize_result=synthesize,
            )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(reviewer.format_result(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
