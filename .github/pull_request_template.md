# Pull Request

## 📝 Description

### Summary
<!-- Provide a brief description of what this PR does -->

### Related Issues
<!-- Link to related issues using "Fixes #123" or "Relates to #123" -->
- Fixes #
- Relates to #

### Type of Change
<!-- Mark with an `x` all that apply -->
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🧪 Test coverage improvement
- [ ] 🏗️ Build/CI changes

## 🎯 Areas Affected

### Core Components
<!-- Mark with an `x` all that apply -->
- [ ] 🧠 Memory system (session persistence, restoration)
- [ ] 🔄 Workflow engine (Think→Plan→Write)
- [ ] 🤖 AI integrations (Anthropic/OpenAI providers)
- [ ] 💻 CLI interface and commands
- [ ] 📁 File operations (/write, /edit, /fix, /review)
- [ ] ⚙️ Configuration and setup
- [ ] 🔍 Project detection and analysis
- [ ] 🌐 Multi-model switching
- [ ] 📊 Error handling and logging

### Compatibility
<!-- Mark with an `x` all that apply -->
- [ ] 🐍 Python version compatibility (3.8+)
- [ ] 💻 Cross-platform (Windows/macOS/Linux)
- [ ] 🤖 AI provider compatibility (Claude/GPT)
- [ ] 📦 Package dependencies

## 🧪 Testing

### Test Coverage
<!-- Mark with an `x` all that apply -->
- [ ] ✅ Unit tests added/updated
- [ ] 🔗 Integration tests added/updated
- [ ] 🤖 AI integration tests (with mocks)
- [ ] 💻 CLI interface tests
- [ ] 🧠 Memory persistence tests
- [ ] 📁 File operation tests
- [ ] 🌐 Cross-platform testing completed

### Manual Testing
<!-- Describe your manual testing process -->
```bash
# Example commands tested:
cognix> /think "your test case"
cognix> /plan
cognix> /write --file test.py

# Results:
# - Expected behavior: [describe]
# - Actual behavior: [describe]
# - Session restoration: [tested/not applicable]
```

### AI Model Testing
<!-- If applicable, describe testing with AI models -->
- [ ] 🤖 Tested with Claude models
- [ ] 🤖 Tested with OpenAI models
- [ ] 🔄 Tested model switching functionality
- [ ] 💾 Tested session persistence across model changes

## 🔄 Changes Made

### Code Changes
<!-- Provide more detailed description of the changes -->

### New Files
<!-- List any new files added -->
- `path/to/new/file.py` - Description of purpose

### Modified Files
<!-- List modified files and what was changed -->
- `path/to/existing/file.py` - Description of changes

### Removed Files
<!-- List any files removed -->
- `path/to/removed/file.py` - Reason for removal

## 📸 Screenshots/Recordings

### Before/After (if UI changes)
<!-- Add screenshots or recordings if applicable -->

### CLI Output Examples
<!-- Show example CLI interactions if relevant -->
```bash
# Example of new/changed behavior:
$ cognix your-new-command
Output example here...
```

## 🔧 Configuration Changes

### New Configuration Options
<!-- List any new config options -->
```json
{
  "new_option": "default_value",
  "description": "What this option does"
}
```

### Environment Variables
<!-- List any new environment variables -->
- `NEW_ENV_VAR` - Description of purpose

### Breaking Configuration Changes
<!-- Warn about any breaking config changes -->
- [ ] ⚠️ This PR includes breaking configuration changes
- [ ] 📝 Migration guide provided in description/documentation

## 📚 Documentation

### Documentation Updates
<!-- Mark with an `x` all that apply -->
- [ ] 📖 README.md updated
- [ ] 📝 CONTRIBUTING.md updated
- [ ] 💬 Inline code documentation added/updated
- [ ] 📋 Command help text updated
- [ ] 🌍 Japanese documentation updated (if applicable)

### New Documentation Needed
<!-- List any documentation that should be created -->
- [ ] Usage examples for new features
- [ ] API documentation updates
- [ ] Configuration guide updates

## 🚀 Deployment Considerations

### Version Impact
<!-- Mark with an `x` one that applies -->
- [ ] 🔧 Patch version (bug fixes, small improvements)
- [ ] ✨ Minor version (new features, backwards compatible)
- [ ] 💥 Major version (breaking changes)

### Migration Requirements
<!-- If this is a breaking change -->
- [ ] 📋 Migration guide provided
- [ ] 🔄 Automatic migration script included
- [ ] ⚠️ User action required after update

### Performance Impact
<!-- Describe any performance implications -->
- [ ] ⚡ Performance improvement
- [ ] 📊 No significant performance impact
- [ ] ⚠️ Potential performance impact (explain below)

## ✅ Pre-submission Checklist

### Code Quality
- [ ] 🔍 Code follows project style guidelines (Black, Flake8)
- [ ] 📝 Code is well-documented with docstrings
- [ ] 🧪 All tests pass locally
- [ ] 🚫 No breaking changes (or breaking changes are documented)
- [ ] 🔒 No sensitive information (API keys, credentials) included

### Testing
- [ ] ✅ Added tests for new functionality
- [ ] 🔄 Existing tests still pass
- [ ] 🤖 AI integrations work with mock responses
- [ ] 💻 CLI commands work as expected
- [ ] 💾 Session persistence works correctly (if applicable)

### Documentation
- [ ] 📖 Documentation updated for new features
- [ ] 💬 Code comments explain complex logic
- [ ] 📋 Commit messages follow conventional commit format
- [ ] 🌍 Considered impact on non-English users

### Compatibility
- [ ] 🐍 Compatible with Python 3.8+
- [ ] 💻 Tested on multiple platforms (or marked as platform-specific)
- [ ] 📦 Dependencies are minimal and justified
- [ ] 🤖 Works with all supported AI providers

## 🤝 Reviewer Notes

### Areas for Special Attention
<!-- Highlight areas where you want careful review -->
- [ ] 🧠 Memory/session logic
- [ ] 🔒 Security implications
- [ ] ⚡ Performance considerations
- [ ] 🌐 Cross-platform compatibility
- [ ] 🤖 AI provider integration

### Questions for Reviewers
<!-- Any specific questions or concerns -->

### Additional Context
<!-- Any other information that might help reviewers -->

---

## 🎯 Definition of Done

This PR is ready for merge when:
- [ ] All automated tests pass
- [ ] Code review is approved
- [ ] Documentation is updated
- [ ] No breaking changes (or properly communicated)
- [ ] Changelog entry added (for significant changes)

---

**Thank you for contributing to Cognix! 🎉**

*Remember: Small, focused PRs are easier to review and merge. Consider breaking large changes into multiple PRs when possible.*
