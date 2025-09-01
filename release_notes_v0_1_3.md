# Cognix v0.1.3 Release Notes

**Released**: [Date]

## 🚀 New Features

### OpenRouter Integration
- **Multiple AI models with single API key** - Access Google Gemini, Microsoft Phi, Meta Llama, and many more models through OpenRouter
- **Free model support** - Use powerful models like `google/gemini-2.0-flash-exp:free` at no cost
- **Seamless provider switching** - Switch between OpenRouter, OpenAI, and Anthropic without configuration changes

### Enhanced Error Handling
- **Smart error recovery** - Automatic fallback suggestions for common API issues
- **User-friendly error messages** - Clear guidance for 402 (insufficient credits), 429 (rate limited), and 401 (invalid key) errors
- **Provider-specific troubleshooting** - Contextual help based on your current API configuration

## 🔧 Improvements

### Model Management
- **Improved model detection** - Better automatic detection of available models based on configured API keys
- **Enhanced model switching** - More reliable switching between different providers and models
- **Provider identification** - Clear display of which provider is currently active (Direct vs OpenRouter)

### User Experience
- **Better setup guidance** - Clearer documentation for API key configuration
- **Improved error context** - More helpful error messages with specific next steps
- **Configuration validation** - Automatic detection and resolution of common setup issues

## 🐛 Bug Fixes

- Fixed model availability detection when switching providers
- Resolved OpenRouter API key handling in multi-provider setups  
- Corrected provider display information for OpenRouter models
- Fixed model switching behavior when OPENAI_BASE_URL is set

## 📚 Documentation Updates

- Added comprehensive OpenRouter setup guide
- Updated .env.example with recommended configuration patterns
- Enhanced troubleshooting section with provider-specific solutions
- Added free model discovery guide

## 🔄 Migration Guide

### For Existing Users
Your existing configuration will continue to work without changes. To take advantage of OpenRouter features:

1. **Optional OpenRouter setup**:
   ```bash
   OPENAI_API_KEY=sk-or-v1-your_openrouter_key
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   ```

2. **Access free models**:
   ```bash
   cognix> /model google/gemini-2.0-flash-exp:free
   ```

### Configuration Patterns
- **Anthropic only**: Set `ANTHROPIC_API_KEY`
- **OpenAI only**: Set `OPENAI_API_KEY` 
- **OpenRouter**: Set `OPENAI_API_KEY` (with OpenRouter key) + `OPENAI_BASE_URL`
- **Mixed setup**: Any combination of the above

## 🎯 What's Coming Next

### v0.2.0 Preview
- Memory management improvements
- Enhanced code analysis features  
- Performance optimizations
- Additional model providers

## 📋 Technical Details

### API Compatibility
- Maintains backward compatibility with existing configurations
- Supports all previous model names and aliases
- No breaking changes to CLI commands or session format

### Provider Support
- **Anthropic**: Claude 4 series, Claude 3.7, Claude 3.5
- **OpenAI**: GPT-4o series, GPT-4, GPT-3.5-turbo
- **OpenRouter**: 100+ models from multiple providers including free options

### System Requirements
- Python 3.8+
- Internet connection for API access
- At least one configured API provider

## 🙏 Acknowledgments

Thanks to the community for feedback on multi-provider support and error handling improvements. Special recognition for users who reported model switching issues that led to this enhanced implementation.

---

**Install or upgrade**: `pip install --upgrade cognix`

**Get started**: https://github.com/cognix-dev/cognix#quick-start

**Report issues**: https://github.com/cognix-dev/cognix/issues