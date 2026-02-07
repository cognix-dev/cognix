# Changelog

All notable changes to Cognix will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-04

### Added
- **Multi-Stage Code Generation** - AlphaCodium-based three-phase approach (Foundation, Application, Environment) with 2.3x accuracy improvement over single-stage generation.
- **Complexity-Adaptive Processing** - Automatic three-tier assessment (simple/medium/complex) that adjusts prompt templates, token limits, and processing depth.
- **Multi-File Generation** - Automatic detection and generation when multiple files are explicitly requested by the user.
- **Zen HUD Design System** - Minimal, clean terminal UI with consistent Cognix green (#78af00) coloring, replacing basic Rich output.
- **StepHUD Progress Indicators** - Real-time timer display and step-by-step progress during code generation (⟳ running, · pending, ✓ complete).
- **MCP Server Integration** - Model Context Protocol support for use with Claude Desktop, Cursor, VSCode, and other MCP-compatible tools via `cognix-mcp` entry point.
- **Linter Integration** - Auto-detection support for flake8, ruff, pylint (Python); eslint, htmlhint, stylelint (JavaScript/CSS); TypeScript compiler. Install via `pip install cognix[lint-python]`.
- **Quality Assessment System** - Multi-layer validation including syntax checking, import dependency analysis, cross-file consistency, and semantic code evaluation.
- **`/make` Command** - New primary command for AI-powered automatic implementation, replacing the Think→Plan→Write workflow.
- **`/repo-init` and `/repo-stats` Commands** - Repository initialization and statistics display.
- **`/run` Command** - Execute commands directly from within Cognix.
- **Diff Engine and Diff Viewer** - Visual comparison of code changes before application.
- **Impact Analyzer** - Assessment of modification effects across the codebase.
- **Repository Analyzer** - Persistent understanding across sessions with dependency graphs and file integrity validation.
- **Enhanced Memory System** - Long-term project knowledge retention across sessions.
- **Semi-Automated Implementation Engine** - Staged confirmation workflow with Enter×2 to send pattern.
- **Automatic File Backup** - Timestamped copies created before file modifications.
- **File Detection Module** - Intelligent file type and structure recognition.
- **Reference Parser** - Cross-file dependency extraction and resolution.
- **Related File Finder** - Contextually connected file identification within repositories.
- **Requirement Validator** - Implementation completeness verification against specifications.
- **Safe Editor** - File modifications with rollback capability.
- **Stylecode Extractor** - Consistent code style pattern analysis and maintenance.
- **`build.py`** - Nuitka binary build automation script (check/standalone/onefile/clean modes).
- **`.env.example`** - API key configuration template.

### Changed
- **Command Architecture Overhaul** - Replaced Think→Plan→Write workflow (`/think`, `/plan`, `/write`) with `/make`-centered generation approach.
- **UI Completely Redesigned** - Startup display with animated COGNIX box logo, version indicator, and "Made by Individual Developer" credit line.
- **Model Display Simplified** - From full identifier (e.g., `claude-sonnet-4-5-20250929`) to friendly name (e.g., `Sonnet 4.5`).
- **LLM Provider Support Updated** - Now supports Anthropic Claude (Sonnet 4.5, Opus 4.5), OpenAI (GPT-5.2, GPT-5.2 Codex), and OpenRouter.
- **Icon Updates** - Starting icon `🤖` → `⚙`, Goal icon `📄` → `📋`.
- **Progress Bars** - Unified to Cognix green color scheme.
- **Spinner Symbols** - Standardized to `⟳` (running), `·` (pending), `✓` (complete).
- **Tips/Help Line** - Moved to ANSI escape code rendering for proper color display.
- **Backup Display** - Changed from folder path to individual file listing with timestamps.
- **`pyproject.toml`** - Updated with MCP dependency, new entry points, optional linter dependencies, and version bump to 0.2.0.
- **README** - Rewritten with "flow engineering" tagline, unified `pipx install cognix` recommendation, and comprehensive feature documentation (English and Japanese versions).
- **LICENSE** - Updated copyright year to 2025-2026.
- **Python Requirement** - Changed from 3.8+ to 3.9+.
- **Dependencies** - Removed `click` from core dependencies; added `mcp` for MCP server support.

### Removed
- **`/think` Command** - Replaced by complexity analysis within `/make`.
- **`/plan` Command** - Replaced by automatic implementation planning within `/make`.
- **`/write` Command** - Replaced by code generation within `/make`.
- **`/edit` Command** - AI-assisted editing now handled through `/make` workflow.
- **`/fix` Command** - Bug fixing now integrated into `/make` and `/review`.
- **`/apply` Command** - Patch application now automatic within generation workflow.
- **`/clear-workflow` Command** - Workflow state management redesigned.
- **`/save-session` / `/resume` / `/list_sessions` / `/session_info` Commands** - Session management redesigned with automatic persistence.
- **`/memory` Command** - Memory management now automatic.
- **`/backup` Command** - Backup management now automatic with timestamped copies.
- **`/workflow-status` Command** - Replaced by `/status`.
- **`/import` / `/export` Commands** - Session import/export removed.

### Fixed
- HUD display duplication where Code Generation HUD appeared twice.
- SyntaxWarning from invalid escape sequences in string literals.
- `[RUNNING]` status display color corrected to cyan.
- NameError in `[v] View details` action during code review workflow.
- New file display truncation (50-line limit removed for full content display).
- Double-reject issue in confirmation workflow resolved with return value-based detection.
- Panel padding adjusted from `(1,2)` to `(0,1)` for consistent spacing.
- Backup display empty lines corrected with proper formatting.
- 90-second cooldown logic for logo animation removed (replaced with `COGNIX_SKIP_LOGO_ANIM=1` environment variable).

## [0.1.5] - 2025-09-05

### Fixed
- Critical syntax error fix improving startup reliability.
- Reference notation (`@file`) resilience for partial file failures.
- Improved error messages and recovery for file reference issues.

### Improved
- Cross-model compatibility (Claude Sonnet 4 & GPT-4o verified).
- System prompt construction optimization.

## [0.1.4] - 2025-09-04

### Improved
- **Reference Notation Resilience** - Enhanced handling of partial file reference failures
  - Processing continues when some referenced files are found and others are missing
  - Clear reporting of which specific files could not be located
  - Graceful degradation instead of complete failure
- **Error Handling Enhancement** - More user-friendly error messages and recovery
  - Detailed feedback for file reference issues
  - Improved system prompt construction optimization
- **Cross-Model Compatibility** - Consistent behavior across different AI models
  - Verified functionality with Claude Sonnet 4 and GPT-4o
  - Standardized error handling across model providers

### Fixed
- Reference notation (`@file1.py @file2.py`) now continues processing when partial files are missing
- System prompt construction optimized for better reliability
- Improved error message clarity for file reference failures

### Technical
- Enhanced file resolution logic in reference notation processing
- Optimized error propagation and user feedback mechanisms
- Comprehensive testing across multiple AI model providers

## [0.1.3] - 2025-09-01

### Added
- **OpenRouter Integration** - Support for multiple AI models through single API key
  - Access to 100+ models including Google Gemini, Microsoft Phi, Meta Llama
  - Free model support (e.g., `google/gemini-2.0-flash-exp:free`)
  - OpenRouter-specific configuration via `OPENAI_BASE_URL`
- **Enhanced Error Handling** - Intelligent error recovery with contextual guidance
  - 402 error (insufficient credits) with upgrade/free model suggestions
  - 429 error (rate limited) with wait time and alternative model recommendations
  - 401 error (invalid API key) with provider-specific troubleshooting
- **Multi-Provider Architecture** - Seamless switching between API providers
  - Direct OpenAI API support alongside OpenRouter
  - Dual API key configuration support
  - Provider identification in model switching display

### Changed
- **Model Management Improvements**
  - Enhanced `/model` command with provider identification
  - Better model availability detection based on configured API keys
  - Improved model switching reliability across different providers
- **Configuration System Updates**
  - Updated `.env.example` with clear provider option patterns
  - Enhanced API key validation and provider detection
  - Improved configuration error messages and recovery suggestions
- **Documentation Enhancements**
  - Comprehensive OpenRouter setup guide in README
  - Updated troubleshooting section with provider-specific solutions
  - Enhanced API key configuration instructions

### Fixed
- Model switching behavior when `OPENAI_BASE_URL` is configured
- Provider detection logic for mixed API configurations
- Model availability validation in multi-provider setups
- Error message consistency across different API providers

### Technical
- Refactored `LLMManager` class for better provider abstraction
- Enhanced error handling in `OpenAIProvider` and `AnthropicProvider`
- Improved model normalization for OpenRouter format handling
- Added provider-specific parameter handling for different model APIs

## [0.1.2] - 2025-08-29

### Fixed
- OpenAI model recognition issue - "Unknown model: gpt-4o" error
- Model provider dictionary synchronization between llm.py and config.py
- Removed non-existent GPT-5 model references

### Added
- Support for gpt-4o and gpt-4o-mini models
- Support for GPT-4.1 model series (gpt-4.1, gpt-4.1-mini, gpt-4.1-nano)
- OpenAI model aliases (gpt4o → gpt-4o, gpt-4-omni → gpt-4o)
- Experimental model auto-detection capability (via COGNIX_AUTO_DETECT_MODELS env var)

### Changed
- Updated default model list to reflect actual available models
- Improved model validation and fallback logic

## [0.1.1] - 2025-08-28

### Added
- Session persistence improvements
- Enhanced error handling

## [0.1.0] - 2025-08-22

### Added
- 🎉 **Initial Release** - AI-powered CLI development assistant
- 🧠 **Multi-AI Support** - Claude 4 and GPT-4 integration
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
pip install cognix
```

[0.2.0]: https://github.com/cognix-dev/cognix/compare/v0.1.5...v0.2.0
[0.1.5]: https://github.com/cognix-dev/cognix/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/cognix-dev/cognix/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/cognix-dev/cognix/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/cognix-dev/cognix/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/cognix-dev/cognix/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/cognix-dev/cognix/releases/tag/v0.1.0
