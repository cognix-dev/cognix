# Changelog

All notable changes to Cognix will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-08-22

### Added
- 🎉 **Initial Release** - AI-powered CLI development assistant
- 🧠 **Multi-AI Support** - Claude 4 and GPT-5 integration
- 💾 **Session Persistence** - Conversation history across restarts
- ⚡ **Structured Workflow** - Think → Plan → Write methodology
- 🔧 **26 CLI Commands** - Complete development toolkit

#### Core AI Features
- `/think` - AI analysis and problem understanding
- `/plan` - Development planning and strategy
- `/write` - Code generation and file creation
- `/model` - AI model switching and information

#### Session Management
- `/save_session` - Save development sessions
- `/resume` - Restore previous sessions
- `/list_sessions` - Session management
- `/session_info` - Current session details
- `/memory` - Session memory and context

#### File Operations
- `/edit` - AI-assisted code editing
- `/review` - Comprehensive code review
- `/diff` - Code comparison and analysis
- `/fix` - Bug detection and fixing

#### Configuration & Status
- `/config` - Configuration management
- `/status` - System and project status
- `/help` - Interactive help system
- `/init` - Project initialization

#### Advanced Features
- `/workflow_status` - Development progress tracking
- `/backup` - Session and code backup
- `/export` - Session export functionality
- `/import` - Session import capabilities

### Technical Improvements
- ✅ **Complete Multi-AI Environment** - Both Anthropic and OpenAI dependencies
- ✅ **Optimized Default Settings** - Claude-first configuration
- ✅ **Robust Error Handling** - Comprehensive error management
- ✅ **Cross-Platform Compatibility** - Windows, macOS, Linux support

### Dependencies
- `anthropic>=0.25.0` - Claude AI integration
- `openai>=1.0.0` - GPT AI integration
- `click>=8.1.0` - CLI framework
- `colorama>=0.4.6` - Terminal colors
- `pydantic>=2.5.0` - Data validation
- `python-dotenv>=1.0.0` - Environment management
- `rich>=13.7.0` - Rich terminal output

### Requirements
- Python 3.8 or higher
- Internet connection for AI API access
- API keys for Anthropic Claude and/or OpenAI GPT

### Installation
```bash
pip install cognix-dev