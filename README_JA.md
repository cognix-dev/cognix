# Cognix

フローエンジニアリングによる自律型コード生成。

[![Version](https://img.shields.io/badge/version-0.2.2-blue.svg)](https://github.com/cognix-dev/cognix)
[![License](https://img.shields.io/badge/license-Apache_2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)

---

## クイックスタート

### 1. インストールと起動

```bash
pipx install cognix
cognix
```

### 2. 初回セットアップ

Cognixを初めて起動すると、対話式ウィザードがAPIキーの設定をサポートします:

- AIプロバイダーを選択（Anthropic、OpenAI、またはOpenRouter）
- APIキーを入力
- ウィザードが自動的に `~/.cognix/.env` ファイルを作成

### 3. コード生成

まず同梱のサンプルを試してみましょう（`@`でファイル指定）:

```bash
cognix> /make @sample_spec_tetris.md
```

または、作りたいものを自由に記述:

```bash
cognix> /make "landing page with HTML and CSS"
```

サンプル仕様書 `sample_spec_tetris.md` がリポジトリに同梱されています。独自の仕様書を書く際の参考にしてください。

### 4. 利用可能なコマンド

CLI内で `/help` と入力すると、すべてのコマンドが表示されます。

---

## APIキー設定

### 自動設定（推奨）

`cognix` を実行して、対話式ウィザードに従うだけです。

### 手動設定

`~/.cognix/.env` ファイルを編集（Windowsの場合: `C:\Users\<ユーザー名>\.cognix\.env`）:

**Anthropic Claude（デフォルト）:**
```bash
ANTHROPIC_API_KEY=sk-ant-your_key_here
```
キーの取得: https://console.anthropic.com/

サポートモデル: Sonnet 4.5（デフォルト）、Opus 4.6、Opus 4.5

**OpenAI:**
```bash
OPENAI_API_KEY=sk-your_key_here
```
キーの取得: https://platform.openai.com/api-keys

サポートモデル: GPT-5.2、GPT-5.2 Codex

**OpenRouter:**
```bash
OPENAI_API_KEY=sk-or-v1-your_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```
キーの取得: https://openrouter.ai/keys

### モデル切り替え

```bash
cognix> /model
```

---

## MCPサーバー統合

Claude Desktop、Cursor、VSCode、その他MCP互換ツールからCognixを使用できます。

`claude_desktop_config.json` に追加:

```json
{
  "mcpServers": {
    "cognix": {
      "command": "cognix-mcp"
    }
  }
}
```

---

## データストレージ

Cognixは `~/.cognix/` にデータを保存します:

```
~/.cognix/
├── .env                            # APIキー・認証情報
├── config.json                     # 設定
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

**プライバシー:** テレメトリなし。API呼び出しは設定されたLLMプロバイダーのみに送信されます。

---

## システム要件

- **OS:** Windows 10以降、macOS 10.15以降、またはLinux
- **Python:** 3.9以上
- **インターネット:** LLM APIアクセスに必要

---

## リンク

- **ドキュメント:** [github.com/cognix-dev/cognix](https://github.com/cognix-dev/cognix)
- **問題報告:** [GitHub Issues](https://github.com/cognix-dev/cognix/issues)
- **ディスカッション:** [GitHub Discussions](https://github.com/cognix-dev/cognix/discussions)

---

## ライセンス

Apache-2.0ライセンス - 詳細は [LICENSE](LICENSE) ファイルを参照
