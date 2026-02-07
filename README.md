# Cognix

Autonomous code generation powered by flow engineering.

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/cognix-dev/cognix)
[![License](https://img.shields.io/badge/license-Apache_2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)

---

## Installation

```bash
pipx install cognix
```

or `pip install cognix`. Requires Python 3.9+.

For Windows binary installation, see [INSTALL.md](INSTALL.md).

---

## Quick Start

```bash
# Setup API key
echo "ANTHROPIC_API_KEY=your_key" > .env

# Run
cognix

# Generate code from a spec file (sample included)
cognix> /make @sample_spec_tetris.md

# Or describe what you want
cognix> /make "landing page with HTML and CSS"
```

A sample spec file `sample_spec_tetris.md` is included in the repository. Use it as a reference for writing your own specs.

For available commands, type `/help` in the CLI.

Linting with `ruff` is included by default. Additional linters (`flake8`, `pylint`) are auto-detected if installed.

### Windows binary

Download `cognix.exe` from [Releases](https://github.com/cognix-dev/cognix/releases). No Python installation required.

---

## Model Configuration

### Anthropic Claude (Default)

```bash
ANTHROPIC_API_KEY=sk-ant-your_key
# Supports: Sonnet 4.5 (default), Opus 4.5
```

### OpenAI

```bash
OPENAI_API_KEY=sk-your_key
# Supports: GPT-5.2, GPT-5.2 Codex
```

### OpenRouter

```bash
OPENAI_API_KEY=sk-or-v1-your_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

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

```
~/.cognix/
├── config.json            # Settings
├── memory.json            # Conversation & project memory
├── repository_data.json   # Repository analysis data
├── ui-knowledge.json      # UI knowledge base
├── sessions/              # Saved sessions
├── knowledge/             # App pattern definitions
├── rules/                 # File reference rules
├── backups/               # Automatic backups
└── impact_analysis/       # Impact analysis results
```

No telemetry. API calls only to configured LLM provider.

---

## Links

**GitHub**: [github.com/cognix-dev/cognix](https://github.com/cognix-dev/cognix)
**Issues**: [GitHub Issues](https://github.com/cognix-dev/cognix/issues)
**Discussions**: [GitHub Discussions](https://github.com/cognix-dev/cognix/discussions)

---

## License

Apache-2.0 License - see [LICENSE](LICENSE) file
