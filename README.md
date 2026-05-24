# mutual-review-mcp

[![PyPI version](https://img.shields.io/pypi/v/mutual-review-mcp.svg)](https://pypi.org/project/mutual-review-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple.svg)](https://spec.modelcontextprotocol.io/)

📖 解説記事 (日本語): [自作MCPサーバーを書いて公開するまで](https://zenn.dev/miharu_tools/articles/f21c642db3fb3d)

**Claude × GPT-4o 相互コードレビュー MCP サーバー**

2つの LLM がそれぞれ独立にコードをレビューし、Claude が両方の指摘を統合した最終レポートを返す MCP (Model Context Protocol) サーバーです。

## 30秒で読める要約

- Claude Desktop / Claude Code / 任意の MCP クライアントから呼べる
- `review_file` / `review_code` / `review_diff` の 3 ツール
- 拡張子から言語自動推定 (`.py` → python, `.ts` → typescript, ...)
- API キーは環境変数で渡す
- コスト追跡はオプション (`ENABLE_COST_TRACKING=1` で有効化)

## クイックスタート (Claude Code)

```bash
claude mcp add mutual-review -- uvx mutual-review-mcp
```

事前に `ANTHROPIC_API_KEY` と `OPENAI_API_KEY` を環境変数に設定してください。

## インストール

```bash
pip install mutual-review-mcp
# または、インストールせず一時実行:
uvx mutual-review-mcp
```

### 詳細

#### A. uvx (推奨・一時実行)

```bash
uvx mutual-review-mcp              # MCPサーバー起動 (stdio)
uvx --from mutual-review-mcp mutual-review path/to/foo.py  # CLI
```

#### B. pip

```bash
pip install mutual-review-mcp
mutual-review-mcp                  # MCP サーバー起動
mutual-review path/to/foo.py       # 単発 CLI
```

#### C. git clone (開発用)

```bash
git clone https://github.com/miharu8686/mutual-review-mcp
cd mutual-review-mcp
pip install -e .[dev]
pytest
```

## Claude Desktop 設定

`%APPDATA%/Claude/claude_desktop_config.json` (macOS は `~/Library/Application Support/Claude/claude_desktop_config.json`) に:

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

完全な例は [examples/claude_desktop_config.json](examples/claude_desktop_config.json) を参照。

## Claude Code 設定

```bash
claude mcp add mutual-review -- uvx mutual-review-mcp
```

または `.mcp.json` を手書き:

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

## ツール一覧

### `review_file`

ファイルをディスクから読んで両モデルでレビュー。

| 引数 | 型 | 必須 | 説明 |
|---|---|---|---|
| `path` | string | yes | レビュー対象ファイルの絶対パス |
| `language` | string | no | 言語ヒント。省略時は拡張子から自動推定 |
| `context` | string | no | コードの背景情報 |
| `synthesize` | boolean | no | 統合レポート生成 (default: true) |

呼び出し例:
```
review_file(path="/repo/src/auth.py", context="OAuth2 callback handler")
```

### `review_code`

コードスニペットを直接渡してレビュー。

| 引数 | 型 | 必須 | 説明 |
|---|---|---|---|
| `code` | string | yes | レビュー対象コード |
| `language` | string | no | 言語ヒント |
| `filename` | string | no | 文脈用ファイル名 |
| `context` | string | no | 背景情報 |
| `synthesize` | boolean | no | 統合レポート生成 (default: true) |

### `review_diff`

unified diff 文字列を直接渡してレビュー。v0.1 では git 実行は行わない。
呼び出し側で `git diff` の出力を取得して渡す:

```bash
git diff HEAD~1 | mutual-review --diff -
```

| 引数 | 型 | 必須 | 説明 |
|---|---|---|---|
| `diff` | string | yes | unified diff テキスト |
| `context` | string | no | 背景情報 |
| `synthesize` | boolean | no | 統合レポート生成 (default: true) |

> v0.2 で `review_diff_git(repo_path, ref)` を追加予定。詳細は [docs/ROADMAP.md](docs/ROADMAP.md)。

## CLI

MCP を経由せず直接実行する CLI も同梱:

```bash
# ファイルレビュー (拡張子から言語自動推定)
mutual-review path/to/foo.py

# スニペット
mutual-review --code "def foo(): pass" --language python

# 標準入力から diff
git diff HEAD~1 | mutual-review --diff -

# 統合レポートを省略
mutual-review path/to/foo.py --no-synth
```

## 動作のしくみ

```
              [ Code / File / Diff ]
                       |
            +----------+----------+
            |                     |
            v                     v
   +-----------------+   +-----------------+
   | Claude reviewer |   |  GPT reviewer   |   (並列実行)
   +-----------------+   +-----------------+
            |                     |
            +----------+----------+
                       |
                       v
              +------------------+
              | Claude synthesizer|   (両レビューを統合)
              +------------------+
                       |
                       v
                 [ Final Report ]
```

統合レポートには以下が含まれます:
1. 両モデルが合意した指摘 (高優先度)
2. 各モデル固有の発見
3. 優先順位付きアクションアイテム
4. 総合判定 (Ready / Needs Minor Work / Needs Major Work)

## コスト目安

`multi_agent.py` (520 行・約 7,000 文字) を 1 ファイルレビュー (統合あり) した実測値:

| モデル構成 | 合計トークン (in/out) | 1ファイルあたり |
|---|---|---|
| `claude-haiku-4-5` + `gpt-4o-mini` | 16,130 / 4,489 | **約 $0.025 (約 ¥4)** |
| `claude-sonnet-4-6` + `gpt-4o`     | 16,161 / 4,204 | **約 $0.105 (約 ¥16)** |

> 1 USD = 155 円換算・2026-05 時点。価格は [reviewer.py の `PRICING`](src/mutual_review_mcp/reviewer.py) で管理しています。
>
> `--no-synth` で 3 回中 1 回 (統合呼び出し) を省略でき、Sonnet/gpt-4o 構成で約 30% コスト削減できます。

モデル変更は環境変数で:

```bash
MUTUAL_REVIEW_CLAUDE_MODEL=claude-haiku-4-5-20251001
MUTUAL_REVIEW_GPT_MODEL=gpt-4o-mini
```

## 環境変数一覧

| 変数 | デフォルト | 説明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | (必須) Anthropic API キー |
| `OPENAI_API_KEY` | — | (必須) OpenAI API キー |
| `MUTUAL_REVIEW_CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude モデル名 |
| `MUTUAL_REVIEW_GPT_MODEL` | `gpt-4o` | GPT モデル名 |
| `ENABLE_COST_TRACKING` | `0` | `1`/`true` でコスト追跡ログ出力 |
| `COST_LOG_PATH` | OS依存 (XDG 準拠) | コストログの出力先 (`usage.jsonl`) |
| `MUTUAL_REVIEW_CONFIG` | OS依存 | JSON 設定ファイルパス (APIキーフォールバック) |

## 設定ファイル (オプション)

環境変数の代わりに JSON 設定ファイルから API キーを読むこともできます。

デフォルトパス:
- Windows: `%APPDATA%\mutual-review-mcp\config.json`
- macOS: `~/Library/Application Support/mutual-review-mcp/config.json`
- Linux: `~/.config/mutual-review-mcp/config.json`

内容:
```json
{
  "anthropic_api_key": "sk-ant-...",
  "openai_api_key": "sk-..."
}
```

## エラーメッセージ

エラーメッセージは日英併記です:

```
ANTHROPIC_API_KEY が設定されていません / ANTHROPIC_API_KEY is not set. ...
Anthropic API への接続に失敗しました: ... / Failed to call Anthropic API: ...
```

## ライセンス

[MIT](LICENSE)

## 関連

- 英語版 README: [README.en.md](README.en.md)
- ロードマップ: [docs/ROADMAP.md](docs/ROADMAP.md)
- MCP 仕様: https://spec.modelcontextprotocol.io/
