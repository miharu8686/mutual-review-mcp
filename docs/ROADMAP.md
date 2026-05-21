# Roadmap

## v0.1.0 (current)

- `review_file(path, language=None, context=None, synthesize=True)`
- `review_code(code, language=None, filename=None, context=None, synthesize=True)`
- `review_diff(diff, context=None, synthesize=True)` — diff 文字列を直接受け取る
- CLI: `mutual-review` (path / --code / --diff)
- MCP server: `mutual-review-mcp`
- 言語自動推定 (拡張子ベース)
- コスト追跡 (環境変数 `ENABLE_COST_TRACKING=1` で有効化)

## v0.2 (planned)

- `review_diff_git(repo_path, ref="HEAD~1", context=None, synthesize=True)`
  - リポジトリパスと git ref を直接受け取り、内部で `git diff` を実行する
  - 現状 v0.1 では呼び出し側で `git diff` 出力を取得して `review_diff` に渡す前提
- Model override per tool call (parameter `model`)
- Additional reviewers (e.g. Gemini, local models via OpenAI-compatible endpoints)
- Configurable review prompts (custom system message per language)

## v0.3 (ideas)

- Streaming output (partial review results as they arrive)
- Caching: skip re-review if the file hash hasn't changed
- Severity scoring & machine-readable JSON output mode
- GitHub Action integration example
