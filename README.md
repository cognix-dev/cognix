# Cognix

Autonomous code generation powered by flow engineering.

[![Version](https://img.shields.io/badge/version-0.2.1-blue.svg)](https://github.com/cognix-dev/cognix)
[![License](https://img.shields.io/badge/license-Apache_2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)

---

## Quick Start

### 1. Install and run

```bash
pipx install cognix
cognix
```

### 2. First-time setup

When you run Cognix for the first time, an interactive wizard will help you set up your API key:

- Choose your AI provider (Anthropic, OpenAI, or OpenRouter)
- Enter your API key
- The wizard creates a `.env` file automatically

### 3. Generate code

Try the included sample first (use `@` to specify a file):

```bash
cognix> /make @sample_spec_tetris.md
```

Or describe what you want to build:

```bash
cognix> /make "landing page with HTML and CSS"
```

A sample specification file `sample_spec_tetris.md` is included in the repository. Use it as a reference for writing your own specifications.

### 4. Available commands

Type `/help` in the CLI to see all available commands.

---

## API Key Setup

### Automatic setup (recommended)

Just run `cognix` and follow the interactive wizard.

### Manual setup

Create a `.env` file in your project directory:

**Anthropic Claude (default):**
```bash
ANTHROPIC_API_KEY=sk-ant-your_key_here
```
Get your key at: https://console.anthropic.com/

Supported models: Sonnet 4.5 (default), Opus 4.5

**OpenAI:**
```bash
OPENAI_API_KEY=sk-your_key_here
```
Get your key at: https://platform.openai.com/api-keys

Supported models: GPT-5.2, GPT-5.2 Codex

**OpenRouter:**
```bash
OPENAI_API_KEY=sk-or-v1-your_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```
Get your key at: https://openrouter.ai/keys

### Switch models

```bash
cognix> /model
```

---

## MCP Server Integration

Use Cognix from Claude Desktop, Cursor, VSCode, or any MCP-compatible tool.

Add to `claude_desktop_config.json`:

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

## Data Storage

Cognix stores data in `~/.cognix/`:

```
~/.cognix/
├── config.json            # Your settings
├── memory.json            # Conversation & project memory
├── repository_data.json   # Repository analysis cache
├── ui-knowledge.json      # UI component knowledge
├── sessions/              # Saved work sessions
├── knowledge/             # App pattern definitions
├── rules/                 # File reference rules
├── backups/               # Automatic backups
└── impact_analysis/       # Code impact analysis results
```

**Privacy:** No telemetry. API calls only go to your configured LLM provider.

---

## System Requirements

- **OS:** Windows 10+, macOS 10.15+, or Linux
- **Python:** 3.9 or higher
- **Internet:** Required for LLM API access

---

## Links

- **Documentation:** [github.com/cognix-dev/cognix](https://github.com/cognix-dev/cognix)
- **Report Issues:** [GitHub Issues](https://github.com/cognix-dev/cognix/issues)
- **Discussions:** [GitHub Discussions](https://github.com/cognix-dev/cognix/discussions)

---

## License

Apache-2.0 License - see [LICENSE](LICENSE) file for details
