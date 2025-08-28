"""
Configuration Manager for Cognix
Handles loading, saving, and managing configuration settings
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

try:
    from dotenv import load_dotenv, find_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None
    find_dotenv = None


@dataclass
class ModelConfig:
    """Configuration for LLM models"""
    name: str
    provider: str  # "openai" or "anthropic"
    temperature: float = 0.7
    max_tokens: int = 4000
    context_window: int = 32000

class Config:
    """Configuration manager"""

    DEFAULT_CONFIG = {
        "version": "0.1.0",
        "model": "claude-sonnet-4-20250514",  # 更新: 正確なClaude 4モデル名
        "temperature": 0.7,
        "max_tokens": 4000,
        "context_lines": 3,
        "auto_backup": True,
        "memory_limit": 100,
        "memory_cleanup_days": 30,
        "backup_cleanup_days": 7,
        "stream_responses": True,
        "show_token_usage": False,
        # 🎭 タイプライター効果設定を追加 (ここから)
        "typewriter_effect": False,                    # タイプライター効果のオン/オフ
        "typewriter_speed": 0.01,                     # 文字間の遅延時間（秒）
        "typewriter_chunk_size": 1,                   # 一度に表示する文字数
        "typewriter_apply_to_streaming": True,        # ストリーミング応答にも適用するか
        "typewriter_apply_to_commands": True,         # Think/Plan/Write コマンドにも適用するか
        # （ここまで）
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
            # Anthropic Claude 4 models (最新・実際に動作する)
            "claude-opus-4-20250514": {
                "name": "claude-opus-4-20250514",
                "provider": "anthropic",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000
            },
            "claude-sonnet-4-20250514": {
                "name": "claude-sonnet-4-20250514", 
                "provider": "anthropic",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000
            },
            
            # Anthropic Claude 3.7 models (実在確認済み)
            "claude-3-7-sonnet-20250219": {
                "name": "claude-3-7-sonnet-20250219",
                "provider": "anthropic",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000
            },
            
            # Anthropic Claude 3.5 models (まだ利用可能)
            "claude-3-5-sonnet-20241022": {
                "name": "claude-3-5-sonnet-20241022",
                "provider": "anthropic",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000
            },
            
            # OpenAI models
            "gpt-4": {
                "name": "gpt-4",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 32000
            },
            "gpt-4-turbo": {
                "name": "gpt-4-turbo",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 128000
            },
            "gpt-4-turbo-preview": {
                "name": "gpt-4-turbo-preview",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 128000
            },
            "gpt-3.5-turbo": {
                "name": "gpt-3.5-turbo",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 16000
            },
            "gpt-4o": {
                "name": "gpt-4o",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 128000
            },
            "gpt-4o-mini": {
                "name": "gpt-4o-mini",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 128000
            },
            # OpenAI GPT-5 models (2025年8月リリース)
            "gpt-5": {
                "name": "gpt-5",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000  # GPT-5は大きなコンテキストウィンドウを持つ
            },
            "gpt-5-mini": {
                "name": "gpt-5-mini",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 128000
            },
            "gpt-5-nano": {
                "name": "gpt-5-nano",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 64000
            },
            # エイリアス (Config側でも定義して検証エラーを回避)
            "claude-opus-4": {
                "name": "claude-opus-4",
                "provider": "anthropic",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000
            },
            "claude-sonnet-4": {
                "name": "claude-sonnet-4",
                "provider": "anthropic",
                "temperature": 0.7,
                "max_tokens": 4000,
                "context_window": 200000
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
            
            "test": "You are a testing specialist in Cognix with session memory. Generate comprehensive test cases and improve test coverage."
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
        """Load environment variables from .env file with priority handling"""
        if not DOTENV_AVAILABLE:
            return
        
        env_files_loaded = []
        
        # Method 1: Use find_dotenv to automatically discover .env files
        try:
            dotenv_path = find_dotenv(usecwd=True)
            if dotenv_path:
                load_dotenv(dotenv_path, override=True)
                env_files_loaded.append(dotenv_path)
        except Exception:
            pass  # fallback to manual search
        
        # Method 2: Manual search in specific locations (fallback)
        if not env_files_loaded:
            env_paths = [
                # 1. Cognixパッケージのルートディレクトリ (最優先)
                Path(__file__).parent.parent / ".env",
                # 2. ユーザーのCognix設定フォルダ
                Path.home() / ".cognix" / ".env",
                # 3. 現在のプロジェクト作業ディレクトリ (最後)
                Path.cwd() / ".env",
            ]
            
            for env_path in env_paths:
                if env_path.exists():
                    try:
                        load_dotenv(env_path, override=True)
                        env_files_loaded.append(str(env_path))
                        break
                    except Exception:
                        continue
        
        # Debug information (only in debug mode)
        if self._is_debug_mode():
            if env_files_loaded:
                print(f"Debug: Loaded .env from: {env_files_loaded[0]}")
                # Check if API keys are now available
                for key in ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY']:
                    value = os.getenv(key)
                    if value:
                        print(f"Debug: {key} loaded (length: {len(value)})")
                    else:
                        print(f"Debug: {key} not found")
            else:
                print("Debug: No .env files found or loaded")
                print(f"Debug: Searched paths: {[str(Path.cwd() / '.env'), str(Path.home() / '.cognix' / '.env')]}")
        
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
        """Get configuration value"""
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
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
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check required fields
        required_fields = ["model", "temperature", "max_tokens"]
        for field in required_fields:
            if not self.has_key(field):
                issues.append(f"Missing required field: {field}")
        
        # Validate model exists
        model = self.get("model")
        if model and model not in self.get_available_models():
            issues.append(f"Unknown model: {model}")
        
        # Validate temperature range
        temperature = self.get("temperature")
        if temperature is not None and not (0 <= temperature <= 2):
            issues.append("Temperature must be between 0 and 2")
        
        # Validate max_tokens
        max_tokens = self.get("max_tokens")
        if max_tokens is not None and (max_tokens < 1 or max_tokens > 100000):
            issues.append("max_tokens must be between 1 and 100000")
        
        # Check API keys with helpful messages
        api_key_issues = self._validate_api_keys()
        issues.extend(api_key_issues)
        
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
            if provider in available_providers:
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
        
        # フォールバック用の優先順位
        preferred_models = [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022", 
            "gpt-4o",
            "gpt-4",
            "gpt-3.5-turbo"
        ]
        
        for preferred in preferred_models:
            if preferred in available_models:
                return preferred
        
        # 優先モデルが利用できない場合は最初に利用可能なものを返す
        return available_models[0]

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