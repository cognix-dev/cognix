# Cognix

フローエンジニアリングによる自律型コード生成。

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/cognix-dev/cognix)
[![License](https://img.shields.io/badge/license-Apache_2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)

---

## Installation

```bash
pipx install cognix
```

または `pip install cognix`。Python 3.9以上が必要です。

Windowsバイナリのインストールは [INSTALL_JA.md](INSTALL_JA.md) を参照してください。

---

## クイックスタート

```bash
# APIキー設定
echo "ANTHROPIC_API_KEY=your_key" > .env

# 実行
cognix

# 仕様書ファイルからコード生成（サンプル同梱）
cognix> /make @sample_spec_tetris.md

# または自由記述で
cognix> /make "landing page with HTML and CSS"
```

サンプル仕様書 `sample_spec_tetris.md` がリポジトリに同梱されています。独自の仕様書を書く際の参考にしてください。

利用可能なコマンドはCLI内で `/help` と入力すると確認できます。

`ruff` によるLintingはデフォルトで含まれています。追加のLinter（`flake8`、`pylint`）はインストール済みであれば自動検出されます。

### Windowsバイナリ

[Releases](https://github.com/cognix-dev/cognix/releases) から `cognix.exe` をダウンロード。Python不要。

---

## モデル設定

### Anthropic Claude（デフォルト）

```bash
ANTHROPIC_API_KEY=sk-ant-your_key
# サポート: Sonnet 4.5（デフォルト）、Opus 4.5
```

### OpenAI

```bash
OPENAI_API_KEY=sk-your_key
# サポート: GPT-5.2、GPT-5.2 Codex
```

### OpenRouter

```bash
OPENAI_API_KEY=sk-or-v1-your_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

### モデル切り替え

```bash
cognix> /model
```

---

## MCPサーバー統合

Claude Desktop、Cursor、VSCode、その他MCP互換ツールからCognixを使用可能。

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

```
~/.cognix/
├── config.json            # 設定
├── memory.json            # 会話・プロジェクトメモリ
├── repository_data.json   # リポジトリ解析データ
├── ui-knowledge.json      # UIナレッジベース
├── sessions/              # セッション保存
├── knowledge/             # アプリパターン定義
├── rules/                 # ファイル参照ルール
├── backups/               # 自動バックアップ
└── impact_analysis/       # 影響分析結果
```

テレメトリなし。設定されたLLMプロバイダーへのAPI呼び出しのみ。

---

## リンク

**GitHub**: [github.com/cognix-dev/cognix](https://github.com/cognix-dev/cognix)
**課題**: [GitHub Issues](https://github.com/cognix-dev/cognix/issues)
**ディスカッション**: [GitHub Discussions](https://github.com/cognix-dev/cognix/discussions)

---

## ライセンス

Apache-2.0ライセンス - [LICENSE](LICENSE) ファイル参照
