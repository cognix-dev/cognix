# 🤖 Cognix

> AI development assistant with persistent memory. Solves the problem of AI tools forgetting context across sessions.

[![PyPI version](https://badge.fury.io/py/cognix.svg)](https://badge.fury.io/py/cognix)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 **Problem**

Current AI tools lose context every session, forcing developers to:
- Re-explain their codebase repeatedly
- Lose conversation history
- Start from scratch each time
- Waste time on context setup

## 💡 **Solution**

Cognix provides **persistent memory** for AI interactions:
- **Session persistence** across restarts
- **Multi-AI switching** (GPT-5 ↔ Claude-4)
- **Structured workflows** (/think → /plan → /write)
- **CLI-native** for developer speed

## 🚀 **Quick Start**

```bash
# Install
pip install cognix

# Initialize
cognix init

# Start coding with persistent context
cognix chat "Help me build a REST API"
```

## ⭐ **Key Features**

- **🧠 Persistent Memory**: Never lose context again
- **🔄 Multi-AI Support**: Switch between models seamlessly  
- **⚡ CLI-First**: Designed for terminal workflows
- **📁 Project-Aware**: Understands your codebase structure
- **🔗 Workflow Integration**: Connects thinking, planning, and execution

## 🛠️ **Installation**

### Prerequisites
- Python 3.8+
- OpenAI API key
- Claude API key (optional)

### Install via pip
```bash
pip install cognix
```

### Install from source
```bash
git clone https://github.com/cognix-dev/cognix.git
cd cognix
pip install -e .
```

## 📖 **Usage**

### Basic Commands
```bash
# Initialize project
cognix init

# Start interactive session
cognix chat

# Run structured workflow
cognix think "How to optimize this database query?"
cognix plan
cognix write
```

### Configuration
```bash
# Set API keys
cognix config set openai_key YOUR_KEY
cognix config set claude_key YOUR_KEY

# Switch AI models
cognix config set model gpt-4
cognix config set model claude-3
```

## 🏗️ **Project Structure**

```
cognix/
├── src/
│   ├── cognix/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── memory.py
│   │   ├── ai_client.py
│   │   └── workflows.py
│   └── tests/
├── docs/
├── examples/
├── README.md
├── setup.py
├── pyproject.toml
└── LICENSE
```

## 🤝 **Contributing**

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
```bash
git clone https://github.com/cognix-dev/cognix.git
cd cognix
pip install -e ".[dev]"
pytest
```

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🗺️ **Roadmap**

- [x] Core CLI framework
- [x] Basic memory persistence
- [ ] Multi-AI switching
- [ ] Structured workflows
- [ ] Project-aware context
- [ ] Plugin system
- [ ] Web interface

## 📞 **Support**

- **Issues**: [GitHub Issues](https://github.com/cognix-dev/cognix/issues)
- **Discussions**: [GitHub Discussions](https://github.com/cognix-dev/cognix/discussions)
- **Twitter**: [@cognix_dev](https://twitter.com/cognix_dev)

## 🎉 **Status**

**Pre-launch** - Launching August 28, 2025

Target: Developers frustrated with current AI tools that lose context.

---

**Built with ❤️ for developers who value persistent context in AI interactions.**
