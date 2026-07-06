# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-07-06

品質・配布基盤リリース(新ツールの追加なし。ROADMAP の v0.2 機能候補は次リリース以降)。

### Added
- **起動時 fail-fast**: API キー未解決の場合、MCP サーバー(`mutual-review-mcp`)と
  CLI(`mutual-review`)は起動直後に設定方法の案内付きエラー(日英併記)を出して
  終了コード 2 で停止する(従来は最初のツール呼び出しまでエラーが出なかった)。
  `config.validate_keys()` を公開 API に追加。
- テストスイート大幅拡充: 12 → **79 テスト**。設定優先順位(環境変数 > 設定ファイル > エラー)の
  全分岐・MCP ツールのスキーマとディスパッチ・CLI・コスト追跡・API エラー経路を、
  全て API モックで検証(実キー・課金不要)。カバレッジ **96%**(pytest-cov 計測)。
- CI: GitHub Actions(`.github/workflows/test.yml`)で push / PR ごとに
  Python 3.11 / 3.12 マトリクスの pytest + ruff を実行。シークレット不要構成。
- 設定テンプレート: `.env.example` / `config.example.json` を同梱。
- `pyproject.toml` に pytest / ruff / coverage 設定を集約。dev 依存に
  `pytest-cov` / `ruff` を追加。

### Changed
- README(日英)を更新: キー設定手順(環境変数 / 設定ファイル)・fail-fast 挙動・
  開発(テスト / lint / CI)手順を追記。
- sdist から内部作業文書を除外(`[tool.hatch.build.targets.sdist]`)。

### Security
- ソースツリー・git 全履歴に実 API キー・個人パスが無いことを監査して確認
  (ヒットはドキュメントの `sk-ant-...` プレースホルダのみ)。

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
