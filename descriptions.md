# Cognix — Description Variants v6 (Final)

Tagline: Not speed — quality. Not flash — reliability.
日本語: 速さではなく品質。派手さではなく堅実さ。

訴求軸: AI生成コードの品質危機（66%/45%）に対する堅実な解答
出典: Stack Overflow 2025, byteiota.com
想定競合: Aider, Cursor, Copilot（速さ・派手さ訴求）

---

## English

### Short (100 chars)
Not speed — quality. Not flash — reliability. AI code generation that actually works. Apache-2.0, CLI.

### Medium (300 chars)
45% of developers spend more time fixing AI code than writing it themselves. Cognix takes a different approach: multi-stage generation that validates each phase before moving on. Not speed — quality. Not flash — reliability. CLI, Claude/GPT/OpenRouter, Apache-2.0. `pip install cognix`.

### Long (1000 chars)
Every AI coding tool promises speed. The 2025 Stack Overflow survey tells a different story: 66% of developers say "almost right" code is their #1 frustration, and 45% spend more time debugging AI output than writing it themselves.

Cognix is built on a different principle. Not speed — quality. Not flash — reliability. Instead of generating everything in one shot, it builds in validated phases — data models, then logic, then environment — catching broken imports and missing configs between stages, not after you've wasted 30 minutes.

Type `/make "FastAPI with JWT auth"` and get working source files, .env templates, and docs. This isn't autocomplete or pair programming — if Cognix generates it, it should run.

Supports Claude, GPT, and 100+ models via OpenRouter. Adapts depth to complexity — simple tasks stay fast, complex ones get thorough multi-stage treatment.

No IDE lock-in, no subscription, no telemetry. Apache-2.0 licensed, all data local.

`pip install cognix` — the fastest code is code you don't have to debug.

---

## 日本語

### Short（100文字）
速さではなく品質。派手さではなく堅実さ。実際に動くコードを生成するAI CLIツール。Apache-2.0、オープンソース。

### Medium（300文字）
開発者の45%がAI生成コードの修正に自分で書くより時間がかかっています。Cognixは違うアプローチを取ります。多段階生成で各フェーズを検証してから次へ進む。速さではなく品質。派手さではなく堅実さ。CLI、Claude/GPT/OpenRouter対応、Apache-2.0。`pip install cognix`。

### Long（1000文字）
すべてのAIコーディングツールが「速さ」を約束します。しかしStack Overflow 2025調査では、開発者の66%が「惜しいけど動かないコード」を最大のフラストレーションに挙げ、45%がAI出力のデバッグに自分で書くより時間がかかると回答しました。

Cognixは異なる原則で作られています。速さではなく品質。派手さではなく堅実さ。コードを一度に吐き出すのではなく、データモデル→ロジック→環境設定のフェーズに分割し、各段階で検証してから次に進みます。壊れたimportや不足する設定は、あなたが30分無駄にする前にフェーズ間で検出されます。

`/make "JWT認証付きFastAPI"`と入力すれば、動作するソースコード、.envテンプレート、ドキュメントが出力されます。オートコンプリートでもペアプログラミングでもありません。Cognixが生成したコードは、動くべきです。

Claude、GPT、OpenRouter経由100以上のモデルに対応。タスクの複雑度に応じて処理深度を自動調整。シンプルなタスクは速く、複雑なタスクは徹底的に。

IDE縛りなし、サブスクなし、テレメトリなし。Apache-2.0ライセンス、データはすべてローカル。

`pip install cognix` — 最も速いコードは、デバッグ不要なコードだから。
