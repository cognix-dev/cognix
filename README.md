# Cognix

<div align="center">

<div style="background-color: #1e1e1e; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #333;">
<pre style="color: #00d962; font-family: 'Courier New', monospace; font-weight: bold; margin: 0; font-size: 16px; background-color: #1e1e1e;">
█▀▀ █▀█ █▀▀ █▄░█ █ ▀▄▀
█▄▄ █▄█ █▄█ █░▀█ █ █░█
</pre>
</div>

**Cognix — Augmented AI Development Partner for CLI**  
Persistent Sessions, Long-Term Memory, Multi-Model Support, and Full-Pipeline Development — All in One Terminal.  
Build smarter, faster, and without context loss — directly from your terminal.

[![Version](https://img.shields.io/badge/version-0.1.0--beta-blue.svg)](https://github.com/cognix-dev/cognix)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Demo](https://img.shields.io/badge/demo-12_seconds-brightgreen.svg)](https://github.com/cognix-dev/cognix#-see-it-in-action)

[Quick Start](#-quick-start) • [Demo](#-see-it-in-action) • [Features](#-key-features) • [Commands](#-commands)

</div>

---

## 🎯 **12-Second Magic**

Cognix is the **only AI coding Partner** that:
- 💾 **Session Restoration**: Resume interrupted work completely
- ⚡ **Structured Workflow**: Think → Plan → Write
- 🎨 **Practical Results**: Generate beautiful GUI apps instantly
- 🧠 **Persistent Memory**: Remember entire projects across sessions

**"Once you have an idea, it's already complete."**

---

## 🎬 See It In Action

https://github.com/cognix-dev/cognix/assets/226239127/478856788-94577806-5a80-4deb-ae58-c699c43efd3c

*12-second demo: Session restoration → /write → Beautiful neon green clock app*

### Quick Demo (12 seconds)
```bash
# 0-1 seconds: Start Cognix
cognix

# 1-3 seconds: Session restoration
Would you like to restore the previous session? [y/N]: y
✅ Session restored successfully!
🔄 Workflow state restored!
   Goal: Brief: big bright green clock popup window bold digits
   Progress: ✅ Think → ✅ Plan → ⏳ Write

# 3-8 seconds: Code generation
cognix> /write --file clock.py
✨ Writing implementation for: Brief: big bright green clock popup window bold digits
   Target file: clock.py
   Target language: python (from .py)

# 8-10 seconds: Beautiful neon green clock appears
Save generated code to clock.py? [y/N] y
✅ Code saved to: clock.py
```

**What you just saw:**
1. 💾 **Workflow Restoration**: AI remembers your thinking process across sessions
2. ⚡ **Instant Code Generation**: From plan to working GUI in seconds  
3. 🎨 **Beautiful Results**: Functional neon green digital clock with #00FF00 perfection
4. 🚀 **Complete Pipeline**: Think → Plan → Write → Deploy in one session

### Try It Yourself
```bash
# Step 1: Start your thinking
cognix> /think "Brief: bright green digital clock GUI"

# Step 2: Plan implementation  
cognix> /plan

# Step 3: Generate code
cognix> /write --file my_clock.py

# Step 4: Exit and run
cognix> exit
python my_clock.py  # → Beautiful clock appears!
```

---

## 🚀 Quick Start

### Installation
```bash
pip install cognix
```

### Setup (2 minutes)
```bash
# 1. Get your API key from Anthropic or OpenAI
# https://console.anthropic.com/ or https://platform.openai.com/

# 2. Create .env file
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
echo "OPENAI_API_KEY=your_api_key_here" >> .env

# 3. Start Cognix
cognix
```

### Your First Workflow (30 seconds)
```bash
cognix> /think "Create a REST API for user authentication"
# 🤔 AI analyzes your requirements...

cognix> /plan
# 📋 AI creates detailed implementation plan...

cognix> /write --file auth_api.py
# ✍️ AI generates production-ready code...
```

**That's it!** Your API is ready to use.

---

## 📋 Commands

### Core Workflow
| Command | Description | Example |
|---------|-------------|---------|
| `/think "<goal>"` | AI analyzes your problem | `/think "API rate limiting"` |
| `/plan` | Creates implementation strategy | `/plan` |
| `/write [--file path]` | Generates production code | `/write --file api.py` |

### Help & Information
| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show all commands | `/help` |
| `/model` | Show current model & options | `/model` |
| `/workflow-status` | Check current progress | `/workflow-status` |

### AI Model Management
| Command | Description | Example |
|---------|-------------|---------|
| `/model <name>` | Switch AI models instantly | `/model gpt-5` |

### File Operations
| Command | Description | Example |
|---------|-------------|---------|
| `/edit <file>` | AI-assisted editing | `/edit src/main.py` |
| `/fix <file>` | Auto-fix bugs | `/fix api.py --function auth` |
| `/review [dir]` | Code analysis | `/review src/` |

### Session Management
| Command | Description | Example |
|---------|-------------|---------|
| `/save-session <name>` | Save your work | `/save-session "auth-system"` |
| `/resume <name>` | Resume previous work | `/resume "auth-system"` |

### Workflow Control
| Command | Description | Example |
|---------|-------------|---------|
| `/clear-workflow` | Start fresh | `/clear-workflow` |

---

## 🌟 Key Features

### 🔄 **Multi-AI Powerhouse**
```bash
cognix> /think "Build a todo app"
# Using Claude-4: Detailed, enterprise-focused analysis

cognix> /model gpt-5
✅ Switched to: gpt-5

cognix> /think "Build a todo app"  
# Using GPT-5: Creative, modern, action-oriented approach
```

**Compare results instantly. Choose the best AI for each task.**

### 🧠 **True Session Persistence**
```bash
# Yesterday
cognix> /think "E-commerce platform architecture"
cognix> /plan
# Work interrupted...

# Today
cognix
🔄 Workflow state restored!
Goal: E-commerce platform architecture  
Progress: ✅ Think → ✅ Plan → ⏳ Write

cognix> /write --file platform.py
# Continue exactly where you left off!
```

### ⚡ **Lightning-Fast Development**
```bash
# Generate production-ready GUI apps in seconds
cognix> /think "Brief: neon green clock GUI"
cognix> /plan  
cognix> /write --file clock.py
# → Beautiful tkinter app with #00FF00 fluorescent green digits!
```

**Perfect for rapid prototyping and instant visual results.**

### ⚡ **Intelligent Context Awareness**
- 📁 **Auto-scans** your project structure
- 🧠 **Remembers** all previous conversations  
- 🎯 **Adapts** suggestions to your codebase
- 🔄 **Maintains** context across sessions

---

## 💡 Real Usage Examples

### **Scenario 1: Feature Development**
```bash
cognix> /think "Add OAuth2 authentication to my Express.js API"

💭 Analysis Result:
**1) What needs to be built:** OAuth2 flow with JWT tokens, middleware for route protection, 
and integration with popular providers (Google, GitHub, etc.)
**2) Key challenges:** Token validation, refresh logic, and secure session management
**3) Success approach:** Use passport.js ecosystem, implement proper error handling, 
and add comprehensive testing for auth flows

cognix> /plan

📋 Implementation Plan:
- Setup & core logic: Install passport, passport-jwt, configure strategies for Google/GitHub OAuth2...
- Security implementation: JWT signing/validation, refresh token rotation, rate limiting...
- Testing & deployment: Unit tests for auth middleware, integration tests for OAuth flows...

cognix> /write --file auth/oauth.js
# Generates complete OAuth2 implementation
```

### **Scenario 2: AI Model Comparison**
```bash
# Claude-4 approach (detailed, enterprise-focused)
cognix> /think "Database caching strategy"
→ Comprehensive analysis with Redis, Memcached comparison, 
  enterprise concerns, compliance considerations

# Switch to GPT-5 for creative alternatives  
cognix> /model gpt-5
cognix> /think "Database caching strategy"  
→ Modern approach with edge caching, CDN integration,
  serverless caching solutions

# Choose the best elements from both!
```

### **Scenario 3: Session Restoration**
```bash
# After weekend break
cognix
📋 Previous session found!
   Last updated: 2025-08-09T18:42:57
   Entries: 15
   Model: claude-sonnet-4-20250514

Would you like to restore the previous session? [y/N]: y
✅ Session restored successfully!
🔄 Workflow state restored!
   Goal: Microservices architecture design
   Progress: ✅ Think → ✅ Plan → ⏳ Write

# Continue immediately where you left off
cognix> /write --file services/user-service.py
```

### **Scenario 4: Rapid GUI Prototyping**
```bash
# 12-second workflow for visual applications
cognix> /think "Brief: desktop calculator with dark theme"
cognix> /plan
cognix> /write --file calculator.py

# Result: Complete GUI calculator ready to use
python calculator.py  # → Professional calculator app launches
```

---

## 🎯 Supported AI Models

### **Claude 4 Series** (Anthropic)
- `claude-opus-4-20250514` - Most capable, complex reasoning
- `claude-sonnet-4-20250514` - Balanced performance & speed

### **GPT-5 Series** (OpenAI)  
- `gpt-5` - Latest model, highly creative
- `gpt-5-mini` - Fast responses, cost-effective

### **Legacy Support**
- `claude-3-5-sonnet-20241022`
- `claude-3-7-sonnet-20250219`

**Switch between any model instantly:** `/model gpt-5`

---

## ⚙️ Configuration & Customization

### Default Config (`~/.cognix/config.json`)
```json
{
  "model": "claude-sonnet-4-20250514",
  "temperature": 0.7,
  "max_tokens": 4000,
  "auto_backup": true,
  "stream_responses": true,
  "typewriter_effect": false
}
```

### Environment Variables
```bash
# API Keys (Required)
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Optional settings  
COGNIX_DEBUG=true
DEFAULT_MODEL=gpt-5
COGNIX_AUTO_SAVE=true
```

### System Requirements
- **Python**: 3.8 or higher
- **OS**: Windows 10+, macOS 10.15+, Linux
- **Memory**: 512MB minimum recommended
- **Internet**: Required for API connections

---

## 🏆 Why Choose Cognix?

### **vs. GitHub Copilot**
| Feature | Cognix | Copilot |
|---------|--------|---------|
| Multi-AI Support | ✅ GPT-5 + Claude-4 | ❌ OpenAI only |
| Session Persistence | ✅ Full project memory | ❌ No memory |
| Workflow Structure | ✅ Think→Plan→Write | ❌ Code completion only |
| CLI Integration | ✅ Native terminal | ❌ Editor-dependent |

### **vs. ChatGPT/Claude Web**
| Feature | Cognix | Web Interfaces |
|---------|--------|----------------|
| Development Integration | ✅ Direct file operations | ❌ Copy-paste workflow |
| Project Context | ✅ Full codebase awareness | ❌ Limited context |
| AI Model Switching | ✅ Instant switching | ❌ Separate applications |
| Session Management | ✅ Auto-save everything | ❌ Manual management |

### **vs. Other AI Coding Tools**
- 🧠 **Memory Persistence**: Only Cognix remembers everything across sessions
- 🔄 **Multi-AI**: Compare approaches from different models instantly  
- ⚡ **Structured Workflow**: Think→Plan→Write methodology
- 🎯 **State Restoration**: Resume work exactly where you left off

---

## 🚀 Project-Specific Examples

### **Web Development**
```bash
cognix> /think "Full-stack blog platform with Next.js"
cognix> /plan
cognix> /write --file blog-platform.js
```

### **Data Science**
```bash
cognix> /think "Analyze customer churn with machine learning"
cognix> /plan  
cognix> /write --file churn_analysis.py
```

### **DevOps**
```bash
cognix> /think "Docker containerization for my Python app"
cognix> /plan
cognix> /write --file Dockerfile
```

### **Mobile Development**
```bash
cognix> /think "React Native app with offline sync"
cognix> /plan
cognix> /write --file OfflineSync.js
```

---

## 🛠️ Advanced Features

### **Constraint Detection**
```bash
cognix> /think "Todo app - brief"
🎯 Detected constraints: brief format
💭 Analysis Result:
**1) What needs to be built:** Basic CRUD operations...
**2) Key challenges:** Data persistence and user experience...  
**3) Success approach:** Start with MVP featuring essential functions...
```

### **Intelligent File Operations**
```bash
# Edit with AI assistance
cognix> /edit src/api.py
📝 Editing: src/api.py
What changes would you like to make? Add rate limiting

🤖 Generating suggestions...
💡 Suggestion: I'll add Express rate limiting middleware...

# Auto-fix specific functions
cognix> /fix utils.py --function calculate_total
🔧 Analyzing function: calculate_total
✅ Fixed: Added null checking and proper error handling
```

### **Project-Aware Conversations**
```bash
cognix> How can I improve the performance of my React components?

# AI automatically analyzes your React project structure
🧠 Analyzing your React project...
📁 Found: 15 components, 3 hooks, 2 contexts

💡 Specific recommendations for your codebase:
1. UserProfile.jsx: Consider React.memo for expensive renders
2. DataTable.jsx: Implement virtualization for large datasets  
3. Global state: Your Redux store could benefit from RTK Query
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### **Development Setup**
```bash
git clone https://github.com/cognix-ai/cognix.git
cd cognix
pip install -e ".[dev]"
```

### **Running Tests**
```bash
pytest tests/
```

### **Code Style**
```bash
black src/
flake8 src/
```

### **Contribution Guidelines**
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/cognix-ai/cognix/issues)
- 💡 **Feature Proposals**: [GitHub Discussions](https://github.com/cognix-ai/cognix/discussions)
- 🔀 **Pull Requests**: [Contributing Guide](CONTRIBUTING.md)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🌟 Roadmap

### **v0.2.0** - Memory Management & Code Enhancement
- [ ] 📝 Individual memory entry deletion
- [ ] 🗂️ Automatic memory archiving
- [ ] 📊 Memory size management and cleanup
- [ ] 🎨 AI code enhancement (/refactor, /lint)
- [ ] ⚡ Improved streaming output

### **v0.3.0** - Advanced Development Features
- [ ] 🎯 Target file/function specification (@filename, #function)
- [ ] 🏃 File execution capabilities (/run)
- [ ] 📱 Browser-based GUI (beta)
- [ ] 🔍 Advanced code analysis features

### **v0.4.0** - Team Collaboration
- [ ] 👥 Shared sessions between team members
- [ ] 📋 Code review workflows
- [ ] 🔗 Basic GitHub/GitLab integration

### **v0.5.0** - Enterprise
- [ ] 🏢 Self-hosted deployment options
- [ ] 🔒 Advanced security features
- [ ] 📊 Usage analytics and metrics

---

## 💬 Support & Community

### **Need Help?**
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/cognix-ai/cognix/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/cognix-ai/cognix/discussions)  
- 📧 **Email**: support@cognix.dev
- 💬 **Discord**: [Join our community](https://discord.gg/cognix)

### **Stay Updated**
- 📰 **Blog**: [cognix.dev/blog](https://cognix.dev/blog)
- 🐦 **Twitter**: [@CognixAI](https://twitter.com/CognixAI)
- 📺 **YouTube**: [Cognix Tutorials](https://youtube.com/@CognixAI)

---

<div align="center">

**🧠 Cognix - Where AI meets intelligent development workflows**

Made with ❤️ by [Individual Developer](https://github.com/cognix-ai)

[⭐ Star on GitHub](https://github.com/cognix-ai/cognix) • [📖 Documentation](https://docs.cognix.dev) • [🚀 Get Started](#-quick-start)

---

**"Once you have an idea, it's already complete with Cognix."**

</div>
