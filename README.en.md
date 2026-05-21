# mutual-review-mcp

[![PyPI version](https://img.shields.io/pypi/v/mutual-review-mcp.svg)](https://pypi.org/project/mutual-review-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple.svg)](https://spec.modelcontextprotocol.io/)

**Claude × GPT-4o mutual code review MCP server**

An MCP (Model Context Protocol) server that has two LLMs independently review your code, then has Claude synthesize their findings into a single prioritized report.

## TL;DR

- Callable from Claude Desktop, Claude Code, or any MCP client
- Three tools: `review_file`, `review_code`, `review_diff`
- Auto-detects language from file extension (`.py` → python, `.ts` → typescript, ...)
- API keys via environment variables
- Cost tracking is optional (`ENABLE_COST_TRACKING=1`)

## Quick start (Claude Code)

```bash
claude mcp add mutual-review -- uvx mutual-review-mcp
```

Set `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` in your environment first.

## Install

```bash
pip install mutual-review-mcp
# Or run without installing:
uvx mutual-review-mcp
```

### Detail

#### A. uvx (recommended, ephemeral)

```bash
uvx mutual-review-mcp                                       # MCP server (stdio)
uvx --from mutual-review-mcp mutual-review path/to/foo.py   # CLI
```

#### B. pip

```bash
pip install mutual-review-mcp
mutual-review-mcp              # launch MCP server (stdio)
mutual-review path/to/foo.py   # one-shot CLI
```

#### C. From source

```bash
git clone https://github.com/miharu8686/mutual-review-mcp
cd mutual-review-mcp
pip install -e .[dev]
pytest
```

## Claude Desktop config

Edit `%APPDATA%/Claude/claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mutual-review": {
      "command": "uvx",
      "args": ["mutual-review-mcp"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

Full example: [examples/claude_desktop_config.json](examples/claude_desktop_config.json).

## Claude Code config

```bash
claude mcp add mutual-review -- uvx mutual-review-mcp
```

Or hand-edit `.mcp.json`:

```json
{
  "mcpServers": {
    "mutual-review": {
      "command": "uvx",
      "args": ["mutual-review-mcp"]
    }
  }
}
```

## Tools

### `review_file`

Read a file from disk and run both reviewers on it.

| Arg | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | Absolute path to the file |
| `language` | string | no | Language hint. Auto-detected from extension if omitted |
| `context` | string | no | Background context for the code |
| `synthesize` | boolean | no | Generate synthesis report (default: true) |

Example:
```
review_file(path="/repo/src/auth.py", context="OAuth2 callback handler")
```

### `review_code`

Review an inline code snippet.

| Arg | Type | Required | Description |
|---|---|---|---|
| `code` | string | yes | Code to review |
| `language` | string | no | Language hint |
| `filename` | string | no | Filename for context |
| `context` | string | no | Background context |
| `synthesize` | boolean | no | Generate synthesis report (default: true) |

### `review_diff`

Review a unified diff string. v0.1 does **not** shell out to git — pass the diff text directly:

```bash
git diff HEAD~1 | mutual-review --diff -
```

| Arg | Type | Required | Description |
|---|---|---|---|
| `diff` | string | yes | Unified diff text |
| `context` | string | no | Background context |
| `synthesize` | boolean | no | Generate synthesis report (default: true) |

> v0.2 will add `review_diff_git(repo_path, ref)`. See [docs/ROADMAP.md](docs/ROADMAP.md).

## CLI

A standalone CLI is included for non-MCP use:

```bash
# Review a file (language auto-detected)
mutual-review path/to/foo.py

# Inline snippet
mutual-review --code "def foo(): pass" --language python

# Diff from stdin
git diff HEAD~1 | mutual-review --diff -

# Skip synthesis
mutual-review path/to/foo.py --no-synth
```

## How it works

```
              [ Code / File / Diff ]
                       |
            +----------+----------+
            |                     |
            v                     v
   +-----------------+   +-----------------+
   | Claude reviewer |   |  GPT reviewer   |   (parallel)
   +-----------------+   +-----------------+
            |                     |
            +----------+----------+
                       |
                       v
              +------------------+
              | Claude synthesizer|   (merges both reviews)
              +------------------+
                       |
                       v
                 [ Final Report ]
```

The synthesis includes:
1. Points both reviewers agree on (high priority)
2. Unique insights from each reviewer
3. Prioritized action items
4. Verdict: Ready / Needs Minor Work / Needs Major Work

## Cost reference

Measured on `multi_agent.py` (520 lines, ~7,000 chars), full review with synthesis:

| Models | Total tokens (in / out) | Cost per file |
|---|---|---|
| `claude-haiku-4-5` + `gpt-4o-mini` | 16,130 / 4,489 | **~$0.025** |
| `claude-sonnet-4-6` + `gpt-4o`     | 16,161 / 4,204 | **~$0.105** |

> `--no-synth` skips the third (synthesis) call, saving ~30% on the Sonnet/gpt-4o setup.

Switch models with environment variables:

```bash
MUTUAL_REVIEW_CLAUDE_MODEL=claude-haiku-4-5-20251001
MUTUAL_REVIEW_GPT_MODEL=gpt-4o-mini
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | (required) Anthropic API key |
| `OPENAI_API_KEY` | — | (required) OpenAI API key |
| `MUTUAL_REVIEW_CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model name |
| `MUTUAL_REVIEW_GPT_MODEL` | `gpt-4o` | GPT model name |
| `ENABLE_COST_TRACKING` | `0` | Set to `1`/`true` to append cost records |
| `COST_LOG_PATH` | OS-default (XDG) | Output path for `usage.jsonl` |
| `MUTUAL_REVIEW_CONFIG` | OS-default | JSON config file path (API key fallback) |

## Config file (optional)

You can store API keys in a JSON file instead of env vars.

Default location:
- Windows: `%APPDATA%\mutual-review-mcp\config.json`
- macOS: `~/Library/Application Support/mutual-review-mcp/config.json`
- Linux: `~/.config/mutual-review-mcp/config.json`

```json
{
  "anthropic_api_key": "sk-ant-...",
  "openai_api_key": "sk-..."
}
```

## Error messages

Errors are bilingual (Japanese + English):

```
ANTHROPIC_API_KEY が設定されていません / ANTHROPIC_API_KEY is not set. ...
Anthropic API への接続に失敗しました: ... / Failed to call Anthropic API: ...
```

## License

[MIT](LICENSE)

## See also

- Japanese README: [README.md](README.md)
- Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)
- MCP spec: https://spec.modelcontextprotocol.io/
