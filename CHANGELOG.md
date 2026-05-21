# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.1] - 2026-05-22

### Fixed
- `pyproject.toml`: project URLs を正しい GitHub URL (`miharu8686/mutual-review-mcp`) に修正。
  0.1.0 のリリースでは placeholder の `your-org` が残っており、PyPI ページの
  Project links が無効なリンクになっていた。

### Added
- `[project.urls]` に `Repository` / `Changelog` エントリを追加。
- `CHANGELOG.md` (このファイル)。
- `docs/PUBLISHING_NOTES.md`: 初回 PyPI 公開時にハマった Windows 固有の問題と対処法。

## [0.1.0] - 2026-05-22

### Added
- 初回リリース。
- MCP stdio server with 3 tools: `review_file`, `review_code`, `review_diff`。
- Claude × GPT-4o による相互コードレビュー + 統合レポート生成。
- スタンドアロン CLI `mutual-review` (path / `--code` / `--diff` モード)。
- ファイル拡張子からの言語自動推定 (`.py` → python など 30 種)。
- API キーは環境変数 / OS-default の JSON 設定ファイルから読み込み。
- バイリンガル (日本語 / 英語) README、実測コスト目安を掲載。
- オプションのコスト追跡 (`ENABLE_COST_TRACKING=1`)。
- 12 unit tests (拡張子推定 / コスト計算 / バイリンガルエラー / 入力検証)。
