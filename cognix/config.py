"""
Configuration Manager for Cognix
Handles loading, saving, and managing configuration settings
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None


@dataclass
class ModelConfig:
    """Configuration for LLM models"""
    name: str
    provider: str  # "OpenAI" or "ANTHROPIC"
    temperature: float = 0.7
    max_tokens: int = 4000
    context_window: int = 32000

class Config:
    """Configuration manager"""

    DEFAULT_CONFIG = {
        "version": "0.2.2",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.7,
        "max_tokens": 4000,
        "context_lines": 3,
        "auto_backup": True,
        "memory_limit": 100,
        "memory_cleanup_days": 30,
        "backup_cleanup_days": 7,
        "stream_responses": True,
        "show_token_usage": False,
        "semi_auto_enabled": True,
        "semi_auto_max_impact_score": 0.8,
        "semi_auto_multi_agent_depth": 3,
        "semi_auto_cost_optimization": True,
        "semi_auto_require_confirmation": True,
        "semi_auto_backup_always": True,
        "semi_auto_quality_threshold": 0.7,
        "semi_auto_max_files_per_operation": 5,
        "typewriter_effect": False,
        "typewriter_speed": 0.01,
        "typewriter_chunk_size": 1,
        "typewriter_apply_to_streaming": True,
        "typewriter_apply_to_commands": True,
        "editor": os.getenv("EDITOR", "nano"),
        "diff_context_lines": 3,
        "exclude_patterns": [
            ".git", ".svn", ".hg", ".bzr",
            "node_modules", "__pycache__", ".pytest_cache",
            "venv", "env", ".venv", ".env",
            "build", "dist", "target",
            ".idea", ".vscode", ".vs",
            "*.pyc", "*.pyo", "*.pyd",
            "*.class", "*.jar", "*.war",
            "*.o", "*.so", "*.dll", "*.dylib",
            "*.exe", "*.bin",
            "*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp",
            "*.mp3", "*.mp4", "*.avi", "*.mov",
            "*.zip", "*.tar", "*.gz", "*.rar",
            ".DS_Store", "Thumbs.db"
        ],
        "file_size_limit": 1048576,
        "supported_languages": [
            "python", "javascript", "typescript", "java", "c", "cpp",
            "csharp", "go", "rust", "ruby", "php", "swift", "kotlin",
            "scala", "bash", "html", "css", "json", "yaml", "sql"
        ],
        "models": {
            "claude-sonnet-4-5-20250929": {
                "name": "claude-sonnet-4-5-20250929",
                "provider": "Anthropic",
                "display_name": "Sonnet 4.5",
                "aliases": ["claude-sonnet-4.5", "sonnet-4.5", "sonnet4.5", "sonnet"],
                "priority": 1,
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000
            },
            "claude-opus-4-6": {
                "name": "claude-opus-4-6",
                "provider": "Anthropic",
                "display_name": "Opus 4.6",
                "aliases": ["claude-opus-4.6", "opus-4.6", "opus4.6", "opus"],
                "priority": 2,
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000
            },
            "claude-opus-4-5-20251101": {
                "name": "claude-opus-4-5-20251101",
                "provider": "Anthropic",
                "display_name": "Opus 4.5",
                "aliases": ["claude-opus-4.5", "opus-4.5", "opus4.5"],
                "priority": 3,
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000
            },
            "gpt-5.2": {
                "name": "gpt-5.2",
                "provider": "OpenAI",
                "display_name": "GPT-5.2",
                "aliases": ["gpt5.2"],
                "priority": 4,
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 400000
            },
            "gpt-5.2-codex": {
                "name": "gpt-5.2-codex",
                "provider": "OpenAI",
                "display_name": "GPT-5.2 Codex",
                "aliases": ["codex", "gpt-5.2-code"],
                "priority": 5,
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 400000
            }
        },
        "system_prompts": {
            "default": """You are Claude Code, an AI assistant helping with software development through Cognix.

    COGNIX CAPABILITIES:
    - Advanced session management with persistent memory across restarts
    - Conversation history is automatically preserved and restored
    - You can naturally reference previous interactions and context
    - Users can restore sessions, making past conversations available to you

    When users mention previous conversations or ask if you remember something, check your conversation history - you likely have access to that information through Cognix's session restoration feature.

    You are knowledgeable, helpful, and provide precise code suggestions.""",
            
            "review": "You are an expert code reviewer in Cognix with session memory. Analyze code for quality, performance, security, and best practices.",
            
            "refactor": "You are a refactoring specialist in Cognix with session memory. Improve code structure while maintaining functionality.",
            
            "debug": "You are a debugging expert in Cognix with session memory. Help identify and fix issues in code.",
            
            "test": "You are a testing specialist in Cognix with session memory. Generate comprehensive test cases and improve test coverage.",
            
            "aider_code_generation": """Act as an expert software developer.
    Always use best practices when coding.
    Respect and use existing conventions, libraries, etc that are already present in the code base.

    CRITICAL OUTPUT FORMAT RULES (HIGHEST PRIORITY):
    1. ALWAYS respond in PLAIN MARKDOWN format
    2. NEVER use JSON, YAML, or any structured data format for code
    3. NEVER wrap code in JSON strings
    4. NEVER use escaped quotes (\") or escaped newlines (\\n) in code
    5. NEVER add explanatory text outside code blocks

    Code format requirements:
    ```language filename.ext
    # actual code here (no escaping, no JSON)
    ```

    FORBIDDEN (will cause errors):
    {
    "files": [{"path": "main.py", "content": "..."}]  ❌ NEVER
    }

    REQUIRED (correct format):
    ```python main.py
    def hello():
        print("Hello")
    ```  ✅ ALWAYS

    If you need to create multiple files, use multiple code blocks:

    ```python main.py
    # main file code
    ```

    ```python utils.py
    # utils file code
    ```

    REMEMBER: The user's system CANNOT parse JSON code responses. Plain markdown ONLY.

    When modifying existing files, prefer the SEARCH/REPLACE format:

    filename.ext
    <<<<<<< SEARCH
    # old code to find
    =======
    # new code to replace with
    >>>>>>> REPLACE

    This ensures precise, conflict-free updates.

    COGNIX CAPABILITIES:
    - Advanced session management with persistent memory across restarts
    - Conversation history is automatically preserved and restored
    - You can naturally reference previous interactions and context
    - Users can restore sessions, making past conversations available to you"""
        },
        "python_compatibility": {
            "description": "Python version compatibility rules for requirements.txt generation",
            "rules": {
                "3.13": {
                    "sqlalchemy": {
                        "min_version": "2.0.25",
                        "recommended": "2.0.36",
                        "reason": "SQLAlchemy < 2.0.25 is incompatible with Python 3.13 typing changes"
                    },
                    "flask-sqlalchemy": {
                        "min_version": "3.1.1",
                        "recommended": "3.1.1",
                        "reason": "Requires SQLAlchemy >= 2.0.25 for Python 3.13"
                    },
                    "marshmallow": {
                        "min_version": "3.21.0",
                        "recommended": "3.23.0",
                        "reason": "Earlier versions may have typing issues with Python 3.13"
                    },
                    "werkzeug": {
                        "min_version": "3.0.1",
                        "recommended": "3.1.0",
                        "reason": "Python 3.13 compatibility improvements"
                    }
                },
                "3.12": {
                    "sqlalchemy": {
                        "min_version": "2.0.20",
                        "recommended": "2.0.36",
                        "reason": "SQLAlchemy < 2.0.20 may have issues with Python 3.12"
                    }
                },
                "3.11": {},
                "3.10": {},
                "3.9": {}
            },
            "always_use_latest": [
                "flask",
                "flask-cors",
                "python-dotenv",
                "pytest"
            ]
        }
    }

    def __init__(self, config_path: str = None):
        """Initialize configuration"""
        # Load .env file if available
        self._load_dotenv()
        
        if config_path is None:
            config_dir = Path.home() / ".cognix"
            config_dir.mkdir(exist_ok=True)
            config_path = config_dir / "config.json"
        
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # ==========================================
        # 初回実行時: デフォルト設定ファイルを配置
        # ==========================================
        self._ensure_default_config_files()
        
        self.data: Dict[str, Any] = {}
        self.load_config()
    
    def _is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return (
            os.getenv('COGNIX_DEBUG') == 'true' or
            os.getenv('DEBUG') == 'true' or
            os.getenv('COGNIX_VERBOSE') == 'true'
        )

    def _load_dotenv(self):
        """Load environment variables from ~/.cognix/.env"""
        if not DOTENV_AVAILABLE:
            return
        
        env_path = Path.home() / ".cognix" / ".env"
        
        if env_path.exists():
            load_dotenv(env_path)
            return
        
        # Debug information (only in debug mode)
        if self._is_debug_mode():
            print(f"Debug: No .env file found at {env_path}")
        
    def _ensure_default_config_files(self):
        """
        初回実行時にデフォルト設定ファイルをユーザーディレクトリに配置
        
        パッケージ同梱のデフォルトファイルを ~/.cognix/ にコピーして、
        完璧な初回体験を提供します。
        
        配置されるファイル:
        - ~/.cognix/ui-knowledge.json
        - ~/.cognix/app_patterns.json
        - ~/.cognix/default_file_reference_rules.md
        """
        import shutil
        
        user_cognix_dir = Path.home() / ".cognix"
        
        # パッケージ内のデフォルトファイルディレクトリを探す
        data_dir = None
        
        try:
            package_dir = Path(__file__).parent  # cognix/ ディレクトリ
            data_candidates = [
                package_dir / "data",           # 通常のインストール
                package_dir.parent / "cognix" / "data",  # 開発環境
            ]
            
            for candidate in data_candidates:
                if candidate.exists():
                    data_dir = candidate
                    break
        except Exception:
            pass
        
        # デフォルトファイルディレクトリが見つからない場合は処理をスキップ
        if not data_dir or not data_dir.exists():
            return
        
        # コピーするファイルのマッピング
        # {ソースファイル名: 配置先パス}
        files_to_copy = {
            "ui-knowledge.json": user_cognix_dir / "ui-knowledge.json",
            "app_patterns.json": user_cognix_dir / "app_patterns.json",
            "default_file_reference_rules.md": user_cognix_dir / "default_file_reference_rules.md",
        }
        
        # ファイルをコピー（存在しない場合のみ）
        copied_count = 0
        for src_rel, dst in files_to_copy.items():
            src = data_dir / src_rel
            
            # ソースファイルが存在し、配置先がまだ存在しない場合のみコピー
            if src.exists() and not dst.exists():
                try:
                    shutil.copy2(src, dst)
                    copied_count += 1
                except Exception as e:
                    # エラーが発生しても処理は継続（完璧な初回体験を目指すが、失敗しても動作する）
                    pass
        
        # デバッグモードの場合、コピー結果を表示
        if self._is_debug_mode() and copied_count > 0:
            print(f"Debug: Copied {copied_count} default config files to {user_cognix_dir}")
    
    def reload_dotenv(self):
        """Force reload .env file - useful for debugging"""
        self._load_dotenv()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Merge with defaults
                self.data = self._merge_config(self.DEFAULT_CONFIG, loaded_config)
            else:
                # Use defaults and save
                self.data = self.DEFAULT_CONFIG.copy()
                self.save_config()
                
        except Exception as e:
            print(f"Warning: Failed to load config: {e}")
            self.data = self.DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with environment variable fallback"""
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # 環境変数もチェック（特定のキーに限定）
                if key.upper() == "OPENAI_BASE_URL":
                    env_value = os.getenv("OPENAI_BASE_URL")
                    if env_value is not None:
                        return env_value
                return default
        
        return value
    
    def set(self, key: str, value: Any, save: bool = True):
        """Set configuration value"""
        keys = key.split('.')
        data = self.data
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        
        # Set the value
        data[keys[-1]] = value
        
        if save:
            self.save_config()
    
    def remove(self, key: str, save: bool = True):
        """Remove configuration value"""
        keys = key.split('.')
        data = self.data
        
        # Navigate to the parent of the target key
        try:
            for k in keys[:-1]:
                data = data[k]
            
            if keys[-1] in data:
                del data[keys[-1]]
                
                if save:
                    self.save_config()
                return True
                    
        except (KeyError, TypeError):
            pass
        
        return False
    
    def has_key(self, key: str) -> bool:
        """Check if configuration key exists"""
        return self.get(key) is not None
    
    def get_model_config(self, model_name: str = None) -> Optional[Dict[str, Any]]:
        """Get model configuration"""
        if model_name is None:
            model_name = self.get("model")
        
        models = self.get("models", {})
        return models.get(model_name)
    
    def add_model(
        self,
        model_id: str,
        name: str,
        provider: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        context_window: int = 32000
    ):
        """Add new model configuration"""
        model_config = {
            "name": name,
            "provider": provider,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "context_window": context_window
        }
        
        self.set(f"models.{model_id}", model_config)
    
    def remove_model(self, model_id: str):
        """Remove model configuration"""
        return self.remove(f"models.{model_id}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        models = self.get("models", {})
        return list(models.keys())
    
    def get_model_display_name(self, full_name: str) -> str:
        """Get display name for model (動的取得版)
        
        Args:
            full_name: Full model name (e.g., 'claude-sonnet-4-5-20250929')
        
        Returns:
            Display name (e.g., 'Sonnet 4.5') or original name if not found
        """
        # None/空文字チェック
        if not full_name:
            return full_name or "Unknown"
        
        models = self.get("models", {})
        model_config = models.get(full_name, {})
        return model_config.get("display_name", full_name)
    
    def get_model_provider(self, model_name: str) -> Optional[str]:
        """Get provider for model
        
        Args:
            model_name: Full model name
        
        Returns:
            Provider name (lowercase) or None if not found
        """
        # None/空文字チェック
        if not model_name:
            return None
        
        models = self.get("models", {})
        model_config = models.get(model_name, {})
        provider = model_config.get("provider", None)
        return provider.lower() if provider else None
    
    def get_model_aliases(self, model_name: str) -> List[str]:
        """Get aliases for model
        
        Args:
            model_name: Full model name
        
        Returns:
            List of aliases or empty list
        """
        models = self.get("models", {})
        model_config = models.get(model_name, {})
        return model_config.get("aliases", [])
    
    def is_valid_model(self, name: str) -> bool:
        """Check if model name or alias is valid
        
        Args:
            name: Model name or alias to check
        
        Returns:
            True if valid, False otherwise
        """
        return self.resolve_model_name(name) is not None
    
    def resolve_model_name(self, name: str) -> Optional[str]:
        """Resolve model name from alias, display name or full name
        
        Args:
            name: Alias, display name (e.g., 'Sonnet 4.5') or full name
        
        Returns:
            Full model name or None if not found
        """
        # None/空文字チェック
        if not name:
            return None
        
        models = self.get("models", {})
        name_lower = name.lower()
        
        # 完全名として存在するか確認
        if name in models:
            return name
        
        # 大文字小文字を無視して完全名を検索
        for model_name in models.keys():
            if model_name.lower() == name_lower:
                return model_name
        
        # aliasから検索
        for model_name, model_config in models.items():
            aliases = model_config.get("aliases", [])
            if name_lower in [a.lower() for a in aliases]:
                return model_name
        
        # display_nameから検索
        for model_name, model_config in models.items():
            display = model_config.get("display_name", "")
            if display.lower() == name_lower:
                return model_name
        
        return None
    
    def get_models_by_provider_with_display(self) -> Dict[str, List[Tuple[str, str]]]:
        """Get models grouped by provider with display names
        
        Returns:
            Dict[str, List[Tuple[str, str]]]: 
            {"Anthropic": [("claude-sonnet-4-5-20250929", "Sonnet 4.5"), ...]}
        
        Note:
            Only models with explicit display_name are shown (officially supported models).
            Models without display_name (e.g., auto-detected or legacy) are excluded.
        """
        models = self.get("models", {})
        grouped = {}
        
        # priorityでソートしてからグループ化
        sorted_models = sorted(
            models.items(),
            key=lambda x: x[1].get("priority", 999)
        )
        
        for model_name, model_info in sorted_models:
            # display_nameがないモデルはスキップ（公式サポートモデルのみ表示）
            if "display_name" not in model_info:
                continue
            
            # providerがない場合はスキップ
            provider = model_info.get("provider")
            if not provider:
                continue
            
            display_name = model_info.get("display_name")
            
            if provider not in grouped:
                grouped[provider] = []
            grouped[provider].append((model_name, display_name))
        
        return grouped
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider with enhanced debugging"""
        # First check config file
        api_key = self.get(f"api_keys.{provider}")
        
        if api_key:
            return api_key
        
        # Then check environment variables
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY"
        }
        
        env_var = env_var_map.get(provider)
        if env_var:
            api_key = os.getenv(env_var)
            
            # Debug information (only in debug mode)
            if self._is_debug_mode():
                if api_key:
                    print(f"Debug: Found {env_var} (length: {len(api_key)}, starts with: {api_key[:10]}...)")
                else:
                    print(f"Debug: {env_var} not found in environment")
                    # Also try to reload .env and check again
                    print("Debug: Attempting to reload .env...")
                    self._load_dotenv()
                    api_key = os.getenv(env_var)
                    if api_key:
                        print(f"Debug: Found {env_var} after reload (length: {len(api_key)})")
                    else:
                        print(f"Debug: Still no {env_var} after reload")
            
            return api_key
        
        return None
    
    def set_api_key(self, provider: str, api_key: str):
        """Set API key for provider"""
        self.set(f"api_keys.{provider}", api_key)
    
    def get_system_prompt(self, prompt_type: str = "default") -> str:
        """Get system prompt by type"""
        prompts = self.get("system_prompts", {})
        return prompts.get(prompt_type, prompts.get("default", ""))
    
    def set_system_prompt(self, prompt_type: str, prompt: str):
        """Set system prompt"""
        self.set(f"system_prompts.{prompt_type}", prompt)
    
    def get_exclude_patterns(self) -> List[str]:
        """Get file exclude patterns"""
        return self.get("exclude_patterns", [])
    
    def add_exclude_pattern(self, pattern: str):
        """Add exclude pattern"""
        patterns = self.get_exclude_patterns()
        if pattern not in patterns:
            patterns.append(pattern)
            self.set("exclude_patterns", patterns)
    
    def remove_exclude_pattern(self, pattern: str):
        """Remove exclude pattern"""
        patterns = self.get_exclude_patterns()
        if pattern in patterns:
            patterns.remove(pattern)
            self.set("exclude_patterns", patterns)
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.data = self.DEFAULT_CONFIG.copy()
        self.save_config()
    
    def export_config(self, export_path: str):
        """Export configuration to file"""
        export_file = Path(export_path)
        
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def import_config(self, import_path: str, merge: bool = True):
        """Import configuration from file"""
        import_file = Path(import_path)
        
        if not import_file.exists():
            raise FileNotFoundError(f"Config file not found: {import_path}")
        
        with open(import_file, 'r', encoding='utf-8') as f:
            imported_config = json.load(f)
        
        if merge:
            self.data = self._merge_config(self.data, imported_config)
        else:
            self.data = imported_config
        
        self.save_config()
    
    def validate_config(self) -> List[str]:
        """設定を検証し、問題のリストを返す - OpenRouter対応版"""
        issues = []
        
        # APIキーを最初に確認
        available_providers = self.get_available_providers()
        
        if not available_providers:
            issues.append("有効なAPIキーが見つかりません")
            issues.append("OPENAI_API_KEYまたはANTHROPIC_API_KEYを設定してください")
            return issues
        
        # OpenRouter設定の検証を追加
        openrouter_issues = self._validate_openrouter_config()
        issues.extend(openrouter_issues)
        
        # 現在のモデルが利用可能かを確認
        model = self.get("model")
        available_models = self.get_available_models_for_providers()
        
        if model and model not in available_models:
            # ** OpenRouter特別処理を追加 **
            if os.getenv("OPENAI_BASE_URL") and "/" in model:
                # OpenRouterモデルの場合は検証をスキップ
                pass
            else:
                default_model = self.get_default_model()
                if default_model:
                    issues.append(f"モデル '{model}' は現在のAPIキーでは利用できません")
                    issues.append(f"自動切り替えします: {default_model}")
                    # 自動修正
                    self.set("model", default_model, save=True)
                else:
                    issues.append(f"モデル '{model}' が利用できず、フォールバックも見つかりません")
        
        # 必須フィールドの確認
        required_fields = ["model", "temperature", "max_tokens"]
        for field in required_fields:
            if not self.has_key(field):
                issues.append(f"必須フィールドが不足: {field}")
        
        # 温度範囲の確認
        temperature = self.get("temperature")
        if temperature is not None and not (0 <= temperature <= 2):
            issues.append("温度は0から2の間である必要があります")
        
        # max_tokensの確認
        max_tokens = self.get("max_tokens")
        if max_tokens is not None and (max_tokens < 1 or max_tokens > 100000):
            issues.append("max_tokensは1から100000の間である必要があります")
        
        return issues

    def _validate_openrouter_config(self) -> List[str]:
        """OpenRouter設定の検証（新規メソッド）"""
        issues = []
        
        base_url = os.getenv("OPENAI_BASE_URL")
        openai_key = self.get_api_key("openai")
        
        if base_url and not openai_key:
            issues.append("OPENAI_BASE_URLが設定されていますが、OPENAI_API_KEYがありません")
        
        if base_url and not base_url.startswith(("http://", "https://")):
            issues.append("OPENAI_BASE_URLの形式が正しくありません")
        
        return issues
    
    def _validate_api_keys(self) -> List[str]:
        """Validate API keys with helpful error messages"""
        issues = []
        
        openai_key = self.get_api_key("openai")
        anthropic_key = self.get_api_key("anthropic")
        
        if not openai_key and not anthropic_key:
            issues.append("No API keys found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY")
            issues.append("You can:")
            issues.append("  • Create a .env file with your API keys")
            issues.append("  • Set environment variables")
            issues.append("  • Add keys to your shell profile")
        
        # Check if keys look valid (basic format check)
        if openai_key and not openai_key.startswith(('sk-', 'sk_')):
            issues.append("OpenAI API key format looks incorrect (should start with 'sk-')")
        
        if anthropic_key and not anthropic_key.startswith('sk-ant-'):
            issues.append("Anthropic API key format looks incorrect (should start with 'sk-ant-')")
        
        return issues
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            "config_path": str(self.config_path),
            "current_model": self.get("model"),
            "available_models": self.get_available_models(),
            "temperature": self.get("temperature"),
            "max_tokens": self.get("max_tokens"),
            "auto_backup": self.get("auto_backup"),
            "stream_responses": self.get("stream_responses"),
            "memory_limit": self.get("memory_limit"),
            "exclude_patterns_count": len(self.get_exclude_patterns()),
            "has_openai_key": bool(self.get_api_key("openai")),
            "has_anthropic_key": bool(self.get_api_key("anthropic")),
            "validation_issues": self.validate_config()
        }
    
    def _merge_config(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def create_project_config(self, project_dir: str, config_data: Dict[str, Any] = None):
        """Create project-specific configuration"""
        project_path = Path(project_dir) / ".cognix.json"
        
        if config_data is None:
            config_data = {
                "model": self.get("model"),
                "temperature": self.get("temperature"),
                "max_tokens": self.get("max_tokens"),
                "exclude_patterns": [],
                "custom_prompts": {},
                "project_specific": True
            }
        
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        return str(project_path)
    
    def load_project_config(self, project_dir: str):
        """Load project-specific configuration"""
        project_config_path = Path(project_dir) / ".cognix.json"
        
        if project_config_path.exists():
            try:
                with open(project_config_path, 'r', encoding='utf-8') as f:
                    project_config = json.load(f)
                
                # Merge project config with base config
                self.data = self._merge_config(self.data, project_config)
                
                return True
            except Exception as e:
                print(f"Warning: Failed to load project config: {e}")
        
        return False
    
    def get_effective_config(self) -> Dict[str, Any]:
        """Get the effective configuration (with environment variables)"""
        config = self.data.copy()
        
        # Add environment-based API keys
        for provider in ["openai", "anthropic"]:
            api_key = self.get_api_key(provider)
            if api_key:
                if "api_keys" not in config:
                    config["api_keys"] = {}
                config["api_keys"][provider] = "***HIDDEN***"
        
        return config

    # config.pyのConfigクラスに以下のメソッドを追加

    def get_available_providers(self) -> List[str]:
        """利用可能なAPIキーを持つプロバイダーのリストを取得"""
        available = []
        
        providers_to_check = ["openai", "anthropic"]
        
        for provider in providers_to_check:
            api_key = self.get_api_key(provider)
            if api_key and len(api_key.strip()) > 10:
                available.append(provider)
        
        return available

    def get_available_models_for_providers(self) -> List[str]:
        """利用可能なプロバイダーに基づいて実際に使用可能なモデルのリストを取得"""
        available_providers = self.get_available_providers()
        available_models = []
        
        all_models = self.get("models", {})
        
        for model_id, model_config in all_models.items():
            provider = model_config.get("provider")
            if provider and provider.lower() in available_providers:
                available_models.append(model_id)
        
        return available_models

    def get_default_model(self) -> Optional[str]:
        """設定されたプロバイダーに基づいて最適なデフォルトモデルを取得"""
        available_models = self.get_available_models_for_providers()
        
        if not available_models:
            return None
        
        # 設定の現在のデフォルト
        current_default = self.get("model")
        if current_default in available_models:
            return current_default
        
        # priorityから動的にフォールバック順序を生成
        preferred_models = self.get_preferred_models()
        
        for preferred in preferred_models:
            if preferred in available_models:
                return preferred
        
        # 優先モデルが利用できない場合は最初に利用可能なものを返す
        return available_models[0]
    
    def get_preferred_models(self) -> List[str]:
        """Get preferred models sorted by priority
        
        Returns:
            List of model names sorted by priority (lowest first)
        """
        models = self.get("models", {})
        sorted_models = sorted(
            models.items(),
            key=lambda x: x[1].get("priority", 999)
        )
        return [name for name, _ in sorted_models]

    def validate_config(self) -> List[str]:
        """設定を検証し、問題のリストを返す - 改良版"""
        issues = []
        
        # APIキーを最初に確認
        available_providers = self.get_available_providers()
        
        if not available_providers:
            issues.append("有効なAPIキーが見つかりません")
            issues.append("OPENAI_API_KEYまたはANTHROPIC_API_KEYを設定してください")
            return issues
        
        # 現在のモデルが利用可能かを確認
        model = self.get("model")
        available_models = self.get_available_models_for_providers()
        
        if model and model not in available_models:
            default_model = self.get_default_model()
            if default_model:
                issues.append(f"モデル '{model}' は現在のAPIキーでは利用できません")
                issues.append(f"自動切り替えします: {default_model}")
                # 自動修正
                self.set("model", default_model, save=True)
            else:
                issues.append(f"モデル '{model}' が利用できず、フォールバックも見つかりません")
        
        # 必須フィールドの確認
        required_fields = ["model", "temperature", "max_tokens"]
        for field in required_fields:
            if not self.has_key(field):
                issues.append(f"必須フィールドが不足: {field}")
        
        # 温度範囲の確認
        temperature = self.get("temperature")
        if temperature is not None and not (0 <= temperature <= 2):
            issues.append("温度は0から2の間である必要があります")
        
        # max_tokensの確認
        max_tokens = self.get("max_tokens")
        if max_tokens is not None and (max_tokens < 1 or max_tokens > 100000):
            issues.append("max_tokensは1から100000の間である必要があります")
        
        return issues