# Installation Guide

## Quick Install (pip)

```bash
pipx install cognix
```

or

```bash
pip install cognix
```

For details, see [README](README.md).

---

## Windows Binary (cognix.exe)

### Download

Download `cognix.exe` from [GitHub Releases](https://github.com/cognix-dev/cognix/releases).

### Setup

1. **Place the binary** in a folder of your choice (e.g., `C:\Tools\Cognix\`).

2. **Add to PATH** (optional, for use from any directory):
   ```powershell
   # Add to user PATH (restart terminal after running)
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Tools\Cognix", "User")
   ```

3. **Verify installation**:
   ```powershell
   cognix.exe --version
   # Expected: Cognix 0.2.0
   ```

### First Launch

The first startup takes approximately 30-60 seconds. This is because the onefile binary extracts its contents to a local cache directory (`%LOCALAPPDATA%\Cognix\0.2.0`). Subsequent launches use the cache and start much faster.

```powershell
cognix.exe
```

---

## API Key Configuration

At least one API key is required. Create a `.env` file in your working directory:

### Anthropic Claude (Default)
```bash
ANTHROPIC_API_KEY=sk-ant-your_key_here
```
Get your key at: https://console.anthropic.com/

### OpenAI
```bash
OPENAI_API_KEY=sk-your_key_here
```
Get your key at: https://platform.openai.com/

### OpenRouter (Multiple models with one key)
```bash
OPENAI_API_KEY=sk-or-v1-your_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```
Get your key at: https://openrouter.ai/keys

### Verification

```powershell
cognix
# Should display the COGNIX logo and [Sonnet 4.5] cognix> prompt
```

---

## Troubleshooting

### No LLM providers available

**Cause**: No API key found.

**Solution**: Ensure `.env` exists in your current working directory with at least one valid API key. Cognix checks for `.env` in: (1) current directory, (2) `~/.cognix/` directory.

### Provider anthropic not available

**Cause**: `ANTHROPIC_API_KEY` is missing or invalid.

**Solution**: Verify your key:
```powershell
# Check if the key is set
echo $env:ANTHROPIC_API_KEY

# Or check .env file
type .env
```

### cognix.exe is slow on first launch

**Cause**: Normal behavior for onefile binary. The executable extracts to `%LOCALAPPDATA%\Cognix\0.2.0` on first run.

**Solution**: Wait 30-60 seconds. Subsequent launches will be fast.

### cognix.exe is not recognized

**Cause**: The binary is not in your PATH.

**Solution**: Either add the folder to PATH (see Setup step 2) or run with the full path:
```powershell
C:\Tools\Cognix\cognix.exe
```

### 402 Insufficient credits (OpenRouter)

**Cause**: OpenRouter account has no credits.

**Solution**: Add credits at https://openrouter.ai/settings/credits or use free models:
```bash
cognix> /model google/gemini-2.0-flash-exp:free
```

### 429 Rate limited

**Cause**: Too many API requests in a short period.

**Solution**: Wait a few minutes and retry, or switch to a different model:
```bash
cognix> /model
```

### Japanese characters not displaying correctly (Windows)

**Cause**: PowerShell default encoding may not support UTF-8.

**Solution**:
```powershell
# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

### Session restore errors

**Cause**: Corrupted session files or permission issues.

**Solution**: Check the sessions directory:
```powershell
ls ~/.cognix/sessions/
```
If needed, delete the corrupted session file and restart Cognix.

---

## System Requirements

- **OS**: Windows 10 or later
- **Python**: 3.9+ (for pip install only; not required for binary)
- **Memory**: 512 MB minimum
- **Disk**: ~100 MB (binary + cache)
- **Internet**: Required for LLM API calls

---

## Uninstall

### pip
```bash
pipx uninstall cognix
```

### Binary
1. Delete `cognix.exe`
2. Delete cache: `%LOCALAPPDATA%\Cognix\`
3. Delete config (optional): `~/.cognix/`
