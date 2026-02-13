# Cognix データ配置統一仕様書

**作成日**: 2026-02-12
**目的**: データファイル配置ルールの統一と仕様バグの修正
**対象バージョン**: v0.2.1 → v0.2.2

---

## 1. 設計思想

### 1.1 基本原則

Cognix のデータ配置は **2層構造** とする。

| 層 | 配置場所 | 内容 | 例 |
|---|---|---|---|
| **グローバル** | `~/.cognix/` | ユーザー固有の設定・データ。どのディレクトリで実行しても共有される | APIキー、config、memory、sessions |
| **プロジェクト固有** | `<project>/.cognix.json` 等 | 特定プロジェクトにのみ適用される設定 | プロジェクト固有ルール |

### 1.2 ルール

1. **APIキー・認証情報は必ずグローバル層に置く**（誤ってgitコミットするリスクを排除）
2. **グローバル層はフラット構造** とする（ファイル数が少ないためサブフォルダ不要）
3. **複数ファイルが蓄積されるものだけフォルダ**にする（sessions, backups, logs, temp, impact_analysis）
4. **カレントディレクトリに設定ファイルを作成しない**（`.cognix.json` と `sample_spec_tetris.md` を除く）
5. **パッケージ内のデータファイルに `.template` 拡張子を付けない**（変数展開処理を行わないため）

---

## 2. あるべきディレクトリ構造

### 2.1 ユーザー側（`~/.cognix/`）

```
~/.cognix/
├── .env                            # APIキー・認証情報
├── config.json                     # グローバル設定
├── memory.json                     # 会話・プロジェクトメモリ
├── repository_data.json            # リポジトリ解析キャッシュ
├── ui-knowledge.json               # UIコンポーネント知識
├── app_patterns.json               # アプリパターン定義
├── default_file_reference_rules.md # ファイル参照ルール
├── sessions/                       # 保存された作業セッション
├── backups/                        # 自動バックアップ
├── logs/                           # デバッグログ
├── temp/                           # 一時ファイル
└── impact_analysis/                # コード影響分析結果
```

### 2.2 プロジェクト側（カレントディレクトリ）

```
<project>/
├── .cognix.json                    # プロジェクト固有設定（任意）
└── .cognix/
    └── file_reference_rules.md     # プロジェクト固有ルール（任意）
```

### 2.3 パッケージ内（ソースコード側）

```
cognix/
├── data/
│   ├── .env.example
│   ├── ui-knowledge.json
│   ├── app_patterns.json
│   ├── default_file_reference_rules.md
│   └── sample_spec_tetris.md
├── config.py
├── cli_main.py
├── ... (その他の.pyファイル)
```

---

## 3. 現状からの変更一覧

### 3.1 .env ファイルの作成先変更

| 項目 | 現状 | 変更後 |
|---|---|---|
| 初回ウィザード作成先 | `Path.cwd() / ".env"` | `Path.home() / ".cognix" / ".env"` |
| テンプレート作成先 | `Path.cwd() / ".env"` | `Path.home() / ".cognix" / ".env"` |
| ヘルプ表示の案内先 | `Path.cwd() / ".env"` | `Path.home() / ".cognix" / ".env"` |

**対象ファイル・行番号:**

| ファイル | 行 | 内容 |
|---|---|---|
| `cli_main.py` | L627 | `env_path = Path.cwd() / ".env"` → `env_path = Path.home() / ".cognix" / ".env"` |
| `cli_utilities.py` | L578, L600 | 同上 |
| `llm.py` | L732 | 同上（ヘルプ表示の案内） |

### 3.2 .env ファイルの読み込みロジック簡素化

| 項目 | 現状 | 変更後 |
|---|---|---|
| 読み込み優先順位 | 3箇所フォールバック（パッケージルート → ~/.cognix → cwd） | `~/.cognix/.env` のみ |
| `COGNIX_PROJECT=true` チェック | あり | 廃止（`~/.cognix/.env` は常にCognixのもの） |

**対象ファイル:**

| ファイル | 行 | 内容 |
|---|---|---|
| `config.py` | L275-329 | `_is_cognix_env_file()` 廃止、`_load_dotenv()` 簡素化 |

### 3.3 memory.json の保存先変更

| 項目 | 現状 | 変更後 |
|---|---|---|
| 保存先 | `<プロジェクトルート>/.cognix/memory.json` | `~/.cognix/memory.json` |

**対象ファイル:**

| ファイル | 行 | 内容 |
|---|---|---|
| `memory.py` | L48-53 | `_find_project_root()` を使用 → `Path.home() / ".cognix"` に固定 |

**注意**: `_find_project_root()` メソッドは memory.py 以外から使われていないことを修正時に確認すること。

### 3.4 backups の統一

| 項目 | 現状 | 変更後 |
|---|---|---|
| `diff_engine.py` | `~/.cognix/backups/` | `~/.cognix/backups/`（変更なし） |
| `safe_editor.py` | `Path.cwd() / ".cognix" / "backups"` | `Path.home() / ".cognix" / "backups"` |
| `semi_auto_engine.py` | `workspace_path / ".cognix_backups"` | `Path.home() / ".cognix" / "backups"` |

**対象ファイル:**

| ファイル | 行 | 内容 |
|---|---|---|
| `safe_editor.py` | L146 | `Path.cwd() / ".cognix" / "backups"` → `Path.home() / ".cognix" / "backups"` |
| `semi_auto_engine.py` | L3620 | `workspace_path / ".cognix_backups"` → `Path.home() / ".cognix" / "backups"` |

### 3.5 temp の統一

| 項目 | 現状 | 変更後 |
|---|---|---|
| `semi_auto_engine.py` | `workspace_path / ".cognix_temp"` | `Path.home() / ".cognix" / "temp"` |

**対象ファイル:**

| ファイル | 行 | 内容 |
|---|---|---|
| `semi_auto_engine.py` | L3624 | `workspace_path / ".cognix_temp"` → `Path.home() / ".cognix" / "temp"` |

### 3.6 logs の移動

| 項目 | 現状 | 変更後 |
|---|---|---|
| `logger.py` | `Path.cwd() / ".cognix"` | `Path.home() / ".cognix" / "logs"` |

**対象ファイル:**

| ファイル | 行 | 内容 |
|---|---|---|
| `logger.py` | L57 | `Path.cwd() / ".cognix"` → `Path.home() / ".cognix" / "logs"` |

### 3.7 デフォルトファイル配置先のフラット化

| 項目 | 現状 | 変更後 |
|---|---|---|
| ui-knowledge.json | `~/.cognix/knowledge/ui-knowledge.json` | `~/.cognix/ui-knowledge.json` |
| app_patterns.json | `~/.cognix/knowledge/app_patterns.json` | `~/.cognix/app_patterns.json` |
| default_file_reference_rules.md | `~/.cognix/rules/default_file_reference_rules.md` | `~/.cognix/default_file_reference_rules.md` |

**対象ファイル:**

| ファイル | 行 | 内容 |
|---|---|---|
| `config.py` | L373-381 | ディレクトリ作成・コピー先パスの変更 |
| `semi_auto_engine.py` | L3079-3084 | default_file_reference_rules.md の読み込みパス |
| `semi_auto_engine.py` | L3405-3410 | app_patterns.json の読み込みパス |
| `semi_auto_engine.py` | L11790-11801 | ui-knowledge.json の読み込みパス |
| `file_detection.py` | L318-337 | app_patterns.json の読み込みパス |

### 3.8 パッケージ内テンプレート構造の変更

| 項目 | 現状 | 変更後 |
|---|---|---|
| ディレクトリ | `data/templates/` | `data/` |
| ファイル拡張子 | `.json.template`, `.md.template` | `.json`, `.md`（拡張子そのまま） |
| サブフォルダ | `knowledge/`, `rules/` | なし（フラット） |

**対象ファイル:**

| ファイル | 変更内容 |
|---|---|
| `data/templates/` | ディレクトリごと廃止 |
| `data/ui-knowledge.json` | `data/templates/ui-knowledge.json.template` からリネーム・移動 |
| `data/app_patterns.json` | `data/templates/knowledge/app_patterns.json.template` からリネーム・移動 |
| `data/default_file_reference_rules.md` | `data/templates/rules/default_file_reference_rules.md.template` からリネーム・移動 |
| `data/sample_spec_tetris.md` | `data/templates/sample_spec_tetris.md` から移動 |
| `data/.env.example` | 変更なし（既に `data/` 直下） |
| `config.py` | L349-366 | テンプレートディレクトリ探索パスの変更 |
| `pyproject.toml` | package-data セクション | `"data/*"` に簡素化 |

### 3.9 README_JA.md の修正

修正箇所:
- 「初回セットアップ」セクション: `.env` の作成先を `~/.cognix/.env` に変更
- 「APIキー設定 > 手動設定」セクション: 「プロジェクトディレクトリに作成されている `.env`」を `~/.cognix/.env` に変更
- 「データストレージ」セクション: フラット化後の構造に更新

---

## 4. 修正対象ファイル一覧（まとめ）

| # | ファイル | 修正内容 |
|---|---|---|
| 1 | `cli_main.py` | .env 作成先を `~/.cognix/.env` に変更 |
| 2 | `cli_utilities.py` | .env テンプレート作成先・案内先を `~/.cognix/.env` に変更 |
| 3 | `llm.py` | ヘルプ表示の .env 案内先を変更 |
| 4 | `config.py` | .env 読み込みロジック簡素化、デフォルトファイル配置パスのフラット化、テンプレートディレクトリパス変更 |
| 5 | `memory.py` | 保存先を `~/.cognix/` に変更 |
| 6 | `safe_editor.py` | バックアップ先を `~/.cognix/backups` に変更 |
| 7 | `semi_auto_engine.py` | バックアップ・temp・knowledge/rules 読み込みパスの変更 |
| 8 | `file_detection.py` | app_patterns.json 読み込みパスの変更 |
| 9 | `logger.py` | ログ出力先を `~/.cognix/logs` に変更 |
| 10 | `pyproject.toml` | package-data セクションの簡素化 |
| 11 | `README_JA.md` | データ配置構造の記載を更新 |
| 12 | `data/.env.example` | 内容変更なし、配置はそのまま |
| 13 | `data/templates/` 配下 | `data/` 直下に移動・リネーム、`templates/` ディレクトリ削除 |

合計: **ソースコード 9ファイル + ドキュメント 1ファイル + パッケージ設定 1ファイル + データファイル移動**

---

## 5. 影響しない箇所（変更不要）

| ファイル | 理由 |
|---|---|
| `session.py` L60 | 既に `Path.home() / ".cognix"` を使用。変更不要 |
| `diff_engine.py` L53 | 既に `~/.cognix/backups` を使用。変更不要 |
| `impact_analyzer.py` L77 | 既に `~/.cognix/impact_analysis` をフォールバックで使用。変更不要 |
| `.cognix.json`（プロジェクト設定） | プロジェクト固有設定として `<project>/.cognix.json` のまま。設計思想通り |
| `<project>/.cognix/file_reference_rules.md` | プロジェクト固有ルールとして現状維持。設計思想通り |

---

## 6. 後方互換性

### 6.1 既存ユーザーへの影響

| 影響 | 対応 |
|---|---|
| カレントディレクトリの `.env` が読み込まれなくなる | 初回起動時にマイグレーション案内を表示（手動で `~/.cognix/.env` にコピーを促す） |
| `<project>/.cognix/memory.json` が読み込まれなくなる | 既存データは残るが新規は `~/.cognix/memory.json` に作成される |
| `~/.cognix/knowledge/`, `~/.cognix/rules/` が使われなくなる | 旧パスにファイルがあれば読み込むフォールバックを一定期間残すか、マイグレーション処理を入れる |

### 6.2 マイグレーション方針

v0.2.2 の初回起動時に以下を実行する案：

1. `Path.cwd() / ".env"` に `COGNIX_PROJECT=true` を含む `.env` が存在する場合、`~/.cognix/.env` へのコピーを提案
2. `~/.cognix/knowledge/` や `~/.cognix/rules/` にファイルがある場合、`~/.cognix/` 直下への移動を提案
3. いずれも自動実行ではなくユーザー確認を経て実行

---

以上。
