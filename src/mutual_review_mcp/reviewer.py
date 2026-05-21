"""reviewer.py - Core mutual code review logic (Claude + GPT-4o)."""
from __future__ import annotations

import json
import pathlib
from datetime import datetime
from typing import Optional

from . import config

REVIEW_SYSTEM = (
    "You are an expert code reviewer. Review the provided code and identify:\n"
    "1. Bugs and logic errors\n"
    "2. Security vulnerabilities\n"
    "3. Performance issues\n"
    "4. Code quality and maintainability concerns\n"
    "5. Specific improvement suggestions\n\n"
    "Be concrete and actionable. Format your response as:\n"
    "## Summary\n## Issues Found\n## Suggestions\n## Overall Assessment"
)

SYNTH_SYSTEM = (
    "You are a senior engineer synthesizing code reviews from multiple AI reviewers. "
    "Be concise and prioritize actionable findings."
)

# Extension -> language hint for the code fence
EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".vue": "vue",
    ".svelte": "svelte",
    ".lua": "lua",
    ".r": "r",
    ".dart": "dart",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
}

# Pricing per 1M tokens (USD). Used only when ENABLE_COST_TRACKING is on.
PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
}


def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING.get(model, {"input": 5.0, "output": 15.0})
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


def _track(provider: str, model: str, input_tokens: int, output_tokens: int, context_label: str) -> None:
    if not config.is_cost_tracking_enabled():
        return
    record = {
        "ts": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "input": input_tokens,
        "output": output_tokens,
        "cost_usd": _calc_cost(model, input_tokens, output_tokens),
        "context": context_label,
    }
    log_path = config.get_cost_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def guess_language(filename: str | None) -> Optional[str]:
    if not filename:
        return None
    suffix = pathlib.Path(filename).suffix.lower()
    return EXT_TO_LANG.get(suffix)


def _build_prompt(code: str, filename: str | None, context: str | None, language: str | None) -> str:
    parts: list[str] = []
    if context:
        parts.append(f"Context: {context}")
    if filename:
        parts.append(f"File: {filename}")
    fence_lang = language or ""
    parts.append(f"```{fence_lang}\n{code}\n```")
    return "\n\n".join(parts)


def review_with_claude(code: str, filename: str | None = None,
                       context: str | None = None,
                       language: str | None = None) -> dict:
    model = config.get_claude_model()
    try:
        client = config.anthropic_client()
        msg = client.messages.create(
            model=model,
            max_tokens=2048,
            system=REVIEW_SYSTEM,
            messages=[{"role": "user", "content": _build_prompt(code, filename, context, language)}],
        )
    except Exception as exc:
        raise RuntimeError(config.bilingual_api_error("Anthropic", exc)) from exc

    _track("anthropic", model, msg.usage.input_tokens, msg.usage.output_tokens, "review")
    return {
        "reviewer": f"Claude ({model})",
        "review": msg.content[0].text,
        "tokens": {"input": msg.usage.input_tokens, "output": msg.usage.output_tokens},
    }


def review_with_gpt(code: str, filename: str | None = None,
                    context: str | None = None,
                    language: str | None = None) -> dict:
    model = config.get_gpt_model()
    try:
        client = config.openai_client()
        resp = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM},
                {"role": "user", "content": _build_prompt(code, filename, context, language)},
            ],
        )
    except Exception as exc:
        raise RuntimeError(config.bilingual_api_error("OpenAI", exc)) from exc

    _track("openai", model, resp.usage.prompt_tokens, resp.usage.completion_tokens, "review")
    return {
        "reviewer": f"GPT ({model})",
        "review": resp.choices[0].message.content,
        "tokens": {"input": resp.usage.prompt_tokens, "output": resp.usage.completion_tokens},
    }


def synthesize(code: str, claude_r: dict, gpt_r: dict,
               filename: str | None = None,
               language: str | None = None) -> dict:
    model = config.get_claude_model()
    snippet = code[:3000] + ("..." if len(code) > 3000 else "")
    fence_lang = language or ""
    prompt = (
        f"Two AI reviewers have reviewed the following code:\n\n"
        f"File: {filename or '<snippet>'}\n```{fence_lang}\n{snippet}\n```\n\n"
        f"=== {claude_r['reviewer']} ===\n{claude_r['review']}\n\n"
        f"=== {gpt_r['reviewer']} ===\n{gpt_r['review']}\n\n"
        "Synthesize into a final report:\n"
        "1. Points both reviewers agree on (high priority)\n"
        "2. Unique insights from each reviewer\n"
        "3. Prioritized action items\n"
        "4. Final verdict: Ready / Needs Minor Work / Needs Major Work"
    )
    try:
        client = config.anthropic_client()
        msg = client.messages.create(
            model=model,
            max_tokens=2048,
            system=SYNTH_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise RuntimeError(config.bilingual_api_error("Anthropic", exc)) from exc

    _track("anthropic", model, msg.usage.input_tokens, msg.usage.output_tokens, "synthesis")
    return {
        "text": msg.content[0].text,
        "tokens": {"input": msg.usage.input_tokens, "output": msg.usage.output_tokens},
    }


def review_code(code: str, language: str | None = None,
                filename: str | None = None,
                context: str | None = None,
                synthesize_result: bool = True) -> dict:
    if language is None:
        language = guess_language(filename)
    claude_r = review_with_claude(code, filename, context, language)
    gpt_r = review_with_gpt(code, filename, context, language)
    result: dict = {
        "filename": filename,
        "language": language,
        "claude": claude_r,
        "gpt": gpt_r,
    }
    if synthesize_result:
        result["synthesis"] = synthesize(code, claude_r, gpt_r, filename, language)
    return result


def review_file(path: str, language: str | None = None,
                context: str | None = None,
                synthesize_result: bool = True) -> dict:
    p = pathlib.Path(path)
    if not p.exists():
        return {"error": f"ファイルが見つかりません: {path} / File not found: {path}"}
    code = p.read_text(encoding="utf-8", errors="replace")
    if language is None:
        language = guess_language(p.name)
    return review_code(code, language=language, filename=p.name,
                       context=context, synthesize_result=synthesize_result)


def review_diff(diff: str, context: str | None = None,
                synthesize_result: bool = True) -> dict:
    if not diff or not diff.strip():
        return {"error": "diff が空です / diff is empty"}
    # diff has its own structure; don't fence as a programming language
    return review_code(diff, language="diff", filename="changes.diff",
                       context=context, synthesize_result=synthesize_result)


def format_result(result: dict) -> str:
    if "error" in result:
        return f"ERROR: {result['error']}"

    parts: list[str] = []
    fn = result.get("filename")
    if fn:
        parts.append(f"# Mutual Review: {fn}")

    cr = result["claude"]
    parts.append(f"## {cr['reviewer']}")
    parts.append(cr["review"])
    parts.append(f"_Tokens: {cr['tokens']['input']} in / {cr['tokens']['output']} out_")

    gr = result["gpt"]
    parts.append(f"## {gr['reviewer']}")
    parts.append(gr["review"])
    parts.append(f"_Tokens: {gr['tokens']['input']} in / {gr['tokens']['output']} out_")

    if "synthesis" in result:
        sr = result["synthesis"]
        parts.append("## Synthesis")
        parts.append(sr["text"])
        parts.append(f"_Tokens: {sr['tokens']['input']} in / {sr['tokens']['output']} out_")

    return "\n\n".join(parts)


__all__ = [
    "EXT_TO_LANG",
    "PRICING",
    "guess_language",
    "review_code",
    "review_file",
    "review_diff",
    "review_with_claude",
    "review_with_gpt",
    "synthesize",
    "format_result",
]
