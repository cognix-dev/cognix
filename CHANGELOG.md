# Changelog

All notable changes to Cognix will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
pip install cognix-dev
```