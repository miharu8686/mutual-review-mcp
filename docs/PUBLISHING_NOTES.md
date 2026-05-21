# PyPI 初回公開でハマったこと (Windows 11 + Python 3.11)

`mutual-review-mcp` を PyPI に公開する過程で 4 つの落とし穴に遭遇しました。
いずれも Windows 環境固有の問題で、Linux / macOS ではまず起きません。
公開作業を Windows でやる人向けの覚え書きです。

各セクションは独立して読めるようにしています。

---

## 1. `.pypirc` の UTF-8 BOM で twine が起動できない

### 症状

```
$ python -m twine upload --repository testpypi dist/*
...
  File "configparser.py", line 1037, in _read
    for lineno, line in enumerate(fp, start=1):
UnicodeDecodeError: 'cp932' codec can't decode byte 0xef in position 0: illegal multibyte sequence
```

### 発生条件

PowerShell の以下のコマンドで `.pypirc` を作成すると BOM 付き UTF-16 LE になり、
さらに何らかのエディタで UTF-8 として開き直して保存すると BOM 付き UTF-8 が残ります。

```powershell
"[pypi]`nusername = __token__`n..." | Out-File -Encoding utf8 ~/.pypirc
```

`Out-File -Encoding utf8` は Windows PowerShell 5.1 では **BOM 付き UTF-8 を出力します**
(Pwsh 7 でも互換のため BOM 付きがデフォルト)。

### 原因

`twine` は内部で `configparser.RawConfigParser.read_file()` を使って `.pypirc` を読みますが、
このメソッドはファイルを **OS のデフォルトエンコーディングで開きます**。
Windows 日本語環境のデフォルトは `cp932` (Shift_JIS) なので、UTF-8 BOM (`EF BB BF`)
を解釈できずに `UnicodeDecodeError` で死にます。

`configparser` は Python 3.11 の時点では `encoding` パラメータを明示すれば UTF-8 を
受け付けるのですが、twine 側は明示していません。

### 対処

BOM を除去します。Python ワンライナーが手っ取り早い:

```bash
python -c "
import os
p = os.path.expanduser('~/.pypirc')
data = open(p, 'rb').read()
if data.startswith(b'\xef\xbb\xbf'):
    open(p, 'wb').write(data[3:])
    print('BOM removed')
"
```

### 予防

PowerShell で `.pypirc` を書くときは:

- **Pwsh 7+**: `Set-Content -Encoding utf8NoBOM`
- **PowerShell 5.1**: `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))`

VS Code でエンコーディングを確認するなら、右下のステータスバーに表示される
"UTF-8 with BOM" が要注意。クリックして "Save with Encoding" → "UTF-8" を選択。

### 参考

- [configparser — Python docs](https://docs.python.org/3/library/configparser.html)
- [PEP 263 / BOM の扱い](https://peps.python.org/pep-0263/)

---

## 2. Windows コマンドプロンプトで twine の進捗バーが crash

### 症状

```
$ python -m twine upload dist/*
Uploading distributions to https://upload.pypi.org/legacy/
...
  File "rich/_win32_console.py", line 402, in write_text
    self.write(text)
UnicodeEncodeError: 'cp932' codec can't encode character '•' in position 0: illegal multibyte sequence
```

upload は成功している可能性もあるが、進捗バー描画のクラッシュで twine が異常終了する
ことがあります (実際は upload 完了後に死ぬパターンが多い)。

### 発生条件

- Windows 11 の標準コマンドプロンプト or Git Bash (cp932 端末)
- twine 6.x (rich を進捗バー描画に使う版)
- 端末側の active code page が 932

`chcp` で確認:
```
> chcp
Active code page: 932
```

### 原因

twine 6.x は [rich](https://github.com/Textualize/rich) を使って進捗バーを描画します。
rich はデフォルトで `•` (U+2022 BULLET) などの Unicode 文字を使いますが、
cp932 はこの文字を含まないため `UnicodeEncodeError` で死にます。

Python のデフォルト stdout エンコーディングが cp932 になっているのが根本原因。

### 対処

2 つを組み合わせる:

```bash
PYTHONIOENCODING=utf-8 python -m twine upload --disable-progress-bar dist/*
```

- `PYTHONIOENCODING=utf-8`: Python 自体の stdout/stderr エンコーディングを UTF-8 に固定。
  これだけでも進捗バーは生き残ることがあるが、Windows Console API が UTF-8 に
  対応していない領域があり完璧ではない。
- `--disable-progress-bar`: twine 側で rich の進捗バーを使わない安全策。

予防的に、Windows の "Beta: Use Unicode UTF-8 for worldwide language support" を
有効にすると `chcp 65001` がデフォルトになり、この種の問題は激減します
(設定 → 時刻と言語 → 言語と地域 → 管理用の言語の設定 → システム ロケールの変更)。

### 参考

- [Rich docs: legacy_windows](https://rich.readthedocs.io/en/stable/console.html#legacy-windows)
- [Python: PYTHONIOENCODING](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONIOENCODING)
- [twine issue tracker](https://github.com/pypa/twine/issues)

---

## 3. CWD shadowing でインストールしたパッケージが import されない

### 症状

TestPyPI からインストールしたパッケージの動作確認をしようとして、
開発元ディレクトリで以下を実行:

```
$ cd C:\Claude\jurika
$ python -c "from mutual_review_mcp.server import main_sync"
ModuleNotFoundError: No module named 'mutual_review_mcp.server';
'mutual_review_mcp' is not a package
```

`pip install` 自体は成功しているのに、import すると別のものが拾われる。

### 発生条件

開発元のディレクトリ (今回の例だと `C:\Claude\jurika`) に、
パッケージ化前の旧スクリプト `mutual_review_mcp.py` が単一ファイルとして
残っている状態で、そのディレクトリを CWD として `python` を起動した場合。

### 原因

Python の import システムは `sys.path` を順に走査します。
`python` をスクリプトファイル無しで起動した場合、`sys.path[0]` は **CWD** になります。
これは site-packages よりも前に来るため、CWD にある同名モジュール (この場合は
旧の `.py` 1 ファイル) が site-packages のパッケージ (`__init__.py` 付きの
ディレクトリ) を完全に隠してしまいます。

旧の `.py` ファイルには `server` というサブモジュールが存在しないため、
`from mutual_review_mcp.server import ...` が失敗します。

### 対処

検証は **別のディレクトリ** から実行:

```bash
cd /tmp     # または cd %TEMP% など、無関係なディレクトリ
python -c "from mutual_review_mcp.server import main_sync; print('OK')"
```

CI で動作確認するときも、checkout したリポジトリ外から実行するように。

### 予防

旧コードと同名のパッケージを公開する場合は、開発元の旧ファイルを移動・改名するか、
検証用の clean venv は必ずプロジェクト外で起動する習慣をつける。

### 参考

- [Python: The import system](https://docs.python.org/3/reference/import.html)
- [sys.path initialization](https://docs.python.org/3/library/sys_path_init.html)

---

## 4. `uvx` が見つからない (uv 未インストール)

### 症状

```
$ uvx mutual-review-mcp
bash: uvx: command not found
```

README の "uvx 推奨" 通りに動かしたいユーザーが踏みがち。

### 発生条件

`uv` (Rust 製の Python パッケージマネージャ) が未インストール。
`uvx` は `uv` パッケージに同梱されるサブコマンドで、別売りではない。

### 対処

```bash
pip install uv
# その後:
uvx --version   # 動作確認
uvx mutual-review-mcp   # PyPI から取得して実行
```

または公式のスタンドアロンインストーラー:

```powershell
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### なぜ uvx が便利なのか

- インストール不要で実行できる (ephemeral)
- 依存関係を裏で隔離してくれる (システム Python を汚さない)
- 起動が速い (内部キャッシュが効く)

MCP server を Claude Desktop / Claude Code から呼ぶ場合、
`uvx mutual-review-mcp` を `command` に指定するだけで動くので、
ユーザーは pip install すら不要。これが README で推す理由。

### 参考

- [uv 公式ドキュメント](https://docs.astral.sh/uv/)
- [uv: install](https://docs.astral.sh/uv/getting-started/installation/)

---

## まとめ

| # | 問題 | キーワード | 対処コマンド |
|---|---|---|---|
| 1 | `.pypirc` の BOM | `UnicodeDecodeError: 'cp932'` | BOM 3 バイト除去 |
| 2 | twine 進捗バー文字化け | `'•'` `cp932 encode` | `PYTHONIOENCODING=utf-8 --disable-progress-bar` |
| 3 | CWD shadowing | `'X' is not a package` | 別ディレクトリから実行 |
| 4 | uvx 未インストール | `uvx: command not found` | `pip install uv` |

Linux / macOS だと 1〜3 はそもそも起きません。Windows での Python 開発は
"端末エンコーディング" と "パス優先度" の 2 大ハマりポイントを意識しておくと、
こういう作業がスムーズに進みます。
