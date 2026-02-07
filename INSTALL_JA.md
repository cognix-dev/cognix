# Windowsバイナリ インストールガイド

pip/pipxでのインストールは [README_JA.md](README_JA.md#installation) を参照してください。

---

## ダウンロード

[GitHub Releases](https://github.com/cognix-dev/cognix/releases) から `cognix.exe` をダウンロード。Pythonのインストールは不要です。

---

## セットアップ

1. **バイナリを任意のフォルダに配置**（例: `C:\Tools\Cognix\`）

2. **PATHに追加**（任意。どのディレクトリからでも実行可能にする場合）:
   ```powershell
   # ユーザーPATHに追加（実行後ターミナルを再起動）
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Tools\Cognix", "User")
   ```

3. **インストール確認**:
   ```powershell
   cognix.exe --version
   # 期待される出力: Cognix 0.2.0
   ```

### 初回起動について

初回起動には約30〜60秒かかります。onefileバイナリがローカルキャッシュディレクトリ（`%LOCALAPPDATA%\Cognix\0.2.0`）に内容を展開するためです。2回目以降はキャッシュが使用され、高速に起動します。

```powershell
cognix.exe
```

---

## APIキー設定

少なくとも1つのAPIキーが必要です。作業ディレクトリに `.env` ファイルを作成してください:

### Anthropic Claude（デフォルト）
```bash
ANTHROPIC_API_KEY=sk-ant-your_key_here
```
キーの取得: https://console.anthropic.com/

### OpenAI
```bash
OPENAI_API_KEY=sk-your_key_here
```
キーの取得: https://platform.openai.com/

### OpenRouter（1つのキーで複数モデル利用可能）
```bash
OPENAI_API_KEY=sk-or-v1-your_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```
キーの取得: https://openrouter.ai/keys

### 動作確認

```powershell
cognix
# COGNIXロゴと [Sonnet 4.5] cognix> プロンプトが表示されればOK
```

---

## トラブルシューティング

### No LLM providers available

**原因**: APIキーが見つからない。

**解決策**: 現在の作業ディレクトリに有効なAPIキーを含む `.env` ファイルが存在することを確認。Cognixは以下の順で `.env` を検索します: (1) カレントディレクトリ、(2) `~/.cognix/` ディレクトリ。

### Provider anthropic not available

**原因**: `ANTHROPIC_API_KEY` が未設定または無効。

**解決策**: キーを確認:
```powershell
# キーが設定されているか確認
echo $env:ANTHROPIC_API_KEY

# または.envファイルを確認
type .env
```

### cognix.exe の初回起動が遅い

**原因**: onefileバイナリの正常な動作。初回実行時に `%LOCALAPPDATA%\Cognix\0.2.0` に展開されます。

**解決策**: 30〜60秒お待ちください。2回目以降は高速に起動します。

### cognix.exe が認識されない

**原因**: バイナリがPATHに含まれていない。

**解決策**: PATHにフォルダを追加するか（セットアップ手順2参照）、フルパスで実行:
```powershell
C:\Tools\Cognix\cognix.exe
```

### 402 Insufficient credits (OpenRouter)

**原因**: OpenRouterアカウントにクレジットがない。

**解決策**: https://openrouter.ai/settings/credits でクレジットを追加するか、無料モデルを使用:
```bash
cognix> /model google/gemini-2.0-flash-exp:free
```

### 429 Rate limited

**原因**: 短時間に多数のAPIリクエストを送信。

**解決策**: 数分待ってからリトライするか、別のモデルに切り替え:
```bash
cognix> /model
```

### 日本語が正しく表示されない (Windows)

**原因**: PowerShellのデフォルトエンコーディングがUTF-8をサポートしていない場合がある。

**解決策**:
```powershell
# UTF-8エンコーディングを設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

### セッション復元エラー

**原因**: セッションファイルの破損またはパーミッションの問題。

**解決策**: セッションディレクトリを確認:
```powershell
ls ~/.cognix/sessions/
```
必要に応じて破損したセッションファイルを削除し、Cognixを再起動してください。

---

## システム要件

- **OS**: Windows 10以降
- **メモリ**: 512 MB以上
- **ディスク**: 約100 MB（バイナリ＋キャッシュ）
- **インターネット**: LLM API呼び出しに必要

---

## アンインストール

1. `cognix.exe` を削除
2. キャッシュを削除: `%LOCALAPPDATA%\Cognix\`
3. 設定を削除（任意）: `~/.cognix/`
