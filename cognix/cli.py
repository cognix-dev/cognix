"""
CLI Interface for Cognix
Handles command parsing and interactive chat interface
"""


import os
import sys
import cmd
import shlex
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import tempfile


from cognix.config import Config
from cognix.memory import Memory
from cognix.context import FileContext
from cognix.llm import LLMManager, CodeAssistant
from cognix.diff_engine import DiffEngine, DiffType
from cognix.session import SessionManager
from cognix.utils import (
    print_table, print_diff_highlighted, confirm_action, get_user_input,
    open_in_editor, format_file_size, format_duration, truncate_text,
    create_temp_file, cleanup_temp_files, ProgressBar
)
from cognix.prompt_templates import prompt_manager
from cognix.error_handling import ErrorHandler, safe_execute, CognixError
from cognix import __version__  # バージョン情報を取得するため

class CognixCLI(cmd.Cmd):
    """Interactive CLI for Cognix"""
  
    prompt = "cognix> "
    
    def __init__(self, config: Config, auto_mode: bool = False):

        """Initialize CLI"""
        super().__init__()
        
        self.config = config
        self.auto_mode = auto_mode
        
        self.memory = Memory()
        
        project_root = self._find_reasonable_project_root()
        
        self.context = FileContext(root_dir=project_root)
        
        self.is_first_run = self._check_first_run()
        
        # プロバイダーの利用可能性チェック
        available_providers = self.config.get_available_providers()
        if not available_providers:
            print("❌ APIキーが設定されていません")
            print("OPENAI_API_KEYまたはANTHROPIC_API_KEYを設定してください")
            sys.exit(1)
        
        # 利用可能なモデルに自動切り替え
        current_model = self.config.get("model")
        available_models = self.config.get_available_models_for_providers()
        
        if current_model not in available_models:
            default_model = self.config.get_default_model()
            if default_model:
                print(f"モデル '{current_model}' が利用できません。'{default_model}' に切り替えます。")
                self.config.set("model", default_model)
            else:
                print("❌ 利用可能なモデルがありません")
                sys.exit(1)

        self.llm_manager = LLMManager(config.get_effective_config())
        
        self.code_assistant = CodeAssistant(self.llm_manager)
        
        self.diff_engine = DiffEngine()
        
        self.session_manager = SessionManager()
        
        self.error_handler = ErrorHandler(debug_mode=config.get('debug_mode', False))
        
        # Generate dynamic intro
        self.intro = self._generate_terminal_logo()
        
        # Workflow state
        self.workflow_state = {
            "think_result": None,
            "plan_result": None,
            "current_goal": None
        }
        
        self.temp_files: List[str] = []
        self.current_session_id = None
        
        # Load project config if available
        project_root = self.context.root_dir
        if project_root:
            self.config.load_project_config(str(project_root))


    def _find_reasonable_project_root(self) -> str:
        """Find a reasonable project root directory"""
        current = Path.cwd()
        
        # C:\ 直下の場合は、ユーザーのホームディレクトリを使用
        if str(current).upper() in ["C:\\", "C:/"]:
            return str(Path.home())
        
        # プロジェクトの指標となるファイル/ディレクトリを探す
        project_indicators = ['.git', 'setup.py', 'requirements.txt', 'pyproject.toml', 
                            '.cognix.json', 'package.json', 'Cargo.toml', '.env']
        
        # 現在のディレクトリから上に向かってプロジェクトルートを探す
        for parent in [current] + list(current.parents):
            # C:\ まで上がってしまった場合は停止
            if str(parent).upper() in ["C:\\", "C:/"]:
                break
                
            if any((parent / indicator).exists() for indicator in project_indicators):
                return str(parent)
        
        # プロジェクトルートが見つからない場合
        if str(current).upper() not in ["C:\\", "C:/"]:
            return str(current)
        else:
            return str(Path.home())

    def _check_first_run(self) -> bool:
        """Check if this is the first time running the application"""
        config_dir = Path.home() / ".cognix"
        first_run_marker = config_dir / ".first_run_complete"
        
        if not first_run_marker.exists():
            return True
        return False
    
    def _mark_first_run_complete(self):
        """Mark first run as complete"""
        config_dir = Path.home() / ".cognix"
        first_run_marker = config_dir / ".first_run_complete"
        first_run_marker.touch()    

    def _generate_terminal_logo(self) -> str:
        """Generate terminal-style logo with dynamic information"""
        try:
            # Safe attribute access with defaults
            current_model = "Unknown"
            if hasattr(self, 'llm_manager') and self.llm_manager:
                current_model = getattr(self.llm_manager, 'current_model', 'Unknown')
            
            # Session information with safe access
            session_status = "new session"
            if hasattr(self, 'session_manager') and self.session_manager:
                try:
                    if hasattr(self.session_manager, 'has_autosave') and self.session_manager.has_autosave():
                        session_status = "auto-saved"
                except:
                    pass
            
            # Memory information with safe access
            memory_persistent = "persistent" if hasattr(self, 'memory') and self.memory else "disabled"
            
            # Backup status with safe access
            backup_enabled = "enabled"
            if hasattr(self, 'config') and self.config:
                backup_enabled = "enabled" if self.config.get("auto_backup", True) else "disabled"
            
            # Check color support
            use_colors = self._check_color_support()
            
            if use_colors:
                # Color codes
                CYAN = "\033[36m"
                GREEN = "\033[32m"
                BLUE = "\033[1;94m"
                YELLOW = "\033[33m"
                GRAY = "\033[90m"
                RESET = "\033[0m"
                BOLD = "\033[1m"
            else:
                # No colors
                CYAN = GREEN = BLUE = YELLOW = GRAY = RESET = BOLD = ""
            
            # Truncate long model names to fit layout
            if len(current_model) > 16:
                current_model = current_model[:13] + "..."
            
            # Cyber-style logo without borders
            logo = f"""{CYAN}Cognix v0.1.0{RESET} {GRAY}// Augmented AI Development Partner for CLI{RESET}

{GREEN}█▀▀ █▀█ █▀▀ █▄░█ █ ▀▄▀
█▄▄ █▄█ █▄█ █░▀█ █ █░█{RESET}

{GRAY}Status:{RESET}
{GREEN}Model:{RESET} {current_model}
{GREEN}Session:{RESET} {session_status}
{GREEN}Memory:{RESET} {memory_persistent}

{GRAY}Core mechanism:{RESET}
Multi-Model Support | Persistent Sessions | Long-Term Memory  
Full-Pipeline Development | Seamless Terminal Experience

{GREEN}>{RESET} {CYAN}/help{RESET}           - Show all commands
{GREEN}>{RESET} {CYAN}/think "goal"{RESET}   - Start AI analysis  
{GREEN}>{RESET} {CYAN}/edit file.py{RESET}   - AI-assisted editing

{GRAY}Made by Individual Developer | MIT License{RESET}"""
            
            return logo
            
        except Exception as e:
            # Fallback to simple logo if anything goes wrong
            return """Cognix v0.1.0 // Augmented AI Development Partner for CLI

█▀▀ █▀█ █▀▀ █▄░█ █ ▀▄▀
█▄▄ █▄█ █▄█ █░▀█ █ █░█

Multi-Model Support | Persistent Sessions | Long-Term Memory  
Full-Pipeline Development | Seamless Terminal Experience

> /help           - Show all commands
> /think "goal"   - Start AI analysis
> /edit file.py   - AI-assisted editing

Made by Individual Developer | MIT License"""

    def _check_color_support(self) -> bool:
        """Check if terminal supports color"""
        try:
            import sys
            return (
                hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
                os.getenv('TERM') != 'dumb' and
                os.getenv('NO_COLOR') is None and
                os.getenv('ANSI_COLORS_DISABLED') is None
            )
        except:
            return False

    def _show_setup_guide(self):
        """Show setup guide for first-time users"""
        print("\n" + "🎉 Welcome to Cognix!")
        print("=" * 50)
        print("Let's get you set up quickly:")
        print()
        print("1. You need an API key from OpenAI or Anthropic")
        print("   • OpenAI: https://platform.openai.com/api-keys")
        print("   • Anthropic: https://console.anthropic.com/")
        print()
        print("2. Create a .env file in this directory:")
        
        env_path = Path.cwd() / ".env"
        print(f"   File location: {env_path}")
        print()
        print("3. Add your API key to the .env file:")
        print("   ANTHROPIC_API_KEY=your_key_here")
        print("   # or")
        print("   OPENAI_API_KEY=your_key_here")
        print()
        
        # Offer to create .env file
        try:
            create_env = input("Would you like me to create a .env file template? [y/N]: ").strip().lower()
            if create_env in ['y', 'yes']:
                self._create_env_template()
        except (KeyboardInterrupt, EOFError):
            print("\nSkipping .env file creation.")
        
        print("\n4. Restart the application after adding your API key")
        print("=" * 50)
    
    def _create_env_template(self):
        """Create .env template file"""
        env_path = Path.cwd() / ".env"
        
        if env_path.exists():
            print(f"✅ .env file already exists at {env_path}")
            return
        
        template_content = """# Cognix - API Keys
# Add your actual API keys below (remove the # and add your real keys)

# Anthropic API Key (for Claude models)
# Get from: https://console.anthropic.com/
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# OpenAI API Key (for GPT models)  
# Get from: https://platform.openai.com/api-keys
# OPENAI_API_KEY=your_openai_api_key_here

# Optional settings
# DEFAULT_MODEL=claude-3-opus
# DEFAULT_TEMPERATURE=0.7
"""
        
        try:
            env_path.write_text(template_content)
            print(f"✅ Created .env template at {env_path}")
            print("   Edit this file and uncomment/add your API key")
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
    
    def _check_session_restoration(self):
        """Check for autosave and offer to restore"""
        if not self.session_manager.has_autosave():
            return
        
        autosave_info = self.session_manager.get_autosave_info()
        if not autosave_info:
            return
        
        print("\n📋 Previous session found!")
        print(f"   Last updated: {autosave_info['last_updated']}")
        print(f"   Entries: {autosave_info['entries']}")
        print(f"   Model: {autosave_info['model']}")
        print(f"   Directory: {autosave_info['directory']}")
        print()
        
        try:
            restore = input("Would you like to restore the previous session? [y/N]: ").strip().lower()
            if restore in ['y', 'yes']:
                if self.session_manager.resume_session("autosave"):
                    print("✅ Session restored successfully!")
                    
                    # 🔧 ワークフロー状態復元を追加（ここが抜けていた！）
                    if (self.session_manager.current_session and 
                        self.session_manager.current_session.workflow_state):
                        self.workflow_state = self.session_manager.current_session.workflow_state
                        print("🔄 Workflow state restored!")
                        
                        # ワークフロー状態を表示
                        if self.workflow_state.get("current_goal"):
                            print(f"   Goal: {self.workflow_state['current_goal']}")
                            think_done = "✅" if self.workflow_state.get("think_result") else "⏳"
                            plan_done = "✅" if self.workflow_state.get("plan_result") else "⏳"
                            print(f"   Progress: {think_done} Think → {plan_done} Plan → ⏳ Write")
                    
                    self._display_session_summary()
                else:
                    print("❌ Failed to restore session")
            else:
                # Ask if they want to keep the autosave
                keep = input("Keep the autosave for later? [Y/n]: ").strip().lower()
                if keep not in ['n', 'no']:
                    print("   (Autosave preserved - use '/resume autosave' to restore later)")
                else:
                    self.session_manager.clear_current_session()
                    print("   (Autosave cleared)")
        except (KeyboardInterrupt, EOFError):
            print("\n   (Skipping session restoration)")
    
    def _display_session_summary(self):
        """Display current session summary"""
        stats = self.session_manager.get_session_stats()
        if not stats:
            return
        
        print(f"\n📊 Session Summary:")
        print(f"   Entries: {stats['total_entries']}")
        print(f"   Current model: {stats['current_model']}")
        
        if 'models_used' in stats:
            models = ', '.join([f"{model}({count})" for model, count in stats['models_used'].items()])
            print(f"   Models used: {models}")
        
        if 'unique_files' in stats:
            print(f"   Files touched: {stats['unique_files']}")
    
    def _confirm_action(self, message: str, auto_apply: bool = None) -> bool:
        """Confirm action with user, respecting auto mode"""
        if auto_apply is None:
            auto_apply = self.auto_mode
        
        if auto_apply:
            print(f"{message} (auto-applied)")
            return True
        
        return confirm_action(message)
    
    def _extract_function_from_code(self, code: str, function_name: str) -> Optional[str]:
        """Extract specific function from code using AST parsing for robustness"""
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    # Get the source lines for this function
                    lines = code.split('\n')
                    start_line = node.lineno - 1  # AST is 1-indexed
                    
                    # Calculate end line by looking at the next function/class or end of file
                    end_line = len(lines)
                    for next_node in ast.walk(tree):
                        if (isinstance(next_node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) 
                            and next_node.lineno > node.lineno):
                            end_line = min(end_line, next_node.lineno - 1)
                    
                    # Extract function lines including proper indentation
                    func_lines = []
                    base_indent = None
                    
                    for i in range(start_line, end_line):
                        if i >= len(lines):
                            break
                            
                        line = lines[i]
                        
                        # Skip empty lines after function definition
                        if not line.strip() and not func_lines and i > start_line:
                            continue
                            
                        # Determine base indentation from function definition
                        if base_indent is None and line.strip():
                            base_indent = len(line) - len(line.lstrip())
                        
                        # Check if we've moved to a different indentation level (end of function)
                        if (line.strip() and base_indent is not None and 
                            len(line) - len(line.lstrip()) <= base_indent and 
                            i > start_line and not line.lstrip().startswith(('@', 'def ', 'async def '))):
                            break
                        
                        func_lines.append(line)
                    
                    return '\n'.join(func_lines)
            
            return None
            
        except SyntaxError:
            # Fallback to regex-based extraction for malformed code
            return self._extract_function_regex(code, function_name)

    def _detect_constraints(self, goal: str) -> dict:
            """ユーザーの制約指示を自動検出"""
            import re
            
            constraints = {
                "is_brief": False,
                "word_limit": None,
                "bullet_limit": None,
                "sentence_limit": None,
                "format_type": None
            }
            
            goal_lower = goal.lower()
            
            # 簡潔性キーワード検出
            brief_keywords = [
                "brief", "concise", "short", "quick", "simple", "summary",
                "簡潔", "短く", "簡単", "要点", "簡単に", "まとめ"
            ]
            
            if any(keyword in goal_lower for keyword in brief_keywords):
                constraints["is_brief"] = True
            
            # 数値制限検出
            word_match = re.search(r'(\d+)\s*words?', goal_lower)
            if word_match:
                constraints["word_limit"] = int(word_match.group(1))
                constraints["is_brief"] = True
            
            bullet_match = re.search(r'(\d+)\s*bullet\s*points?', goal_lower)
            if bullet_match:
                constraints["bullet_limit"] = int(bullet_match.group(1))
                constraints["is_brief"] = True
            
            sentence_match = re.search(r'(\d+)\s*sentences?', goal_lower)
            if sentence_match:
                constraints["sentence_limit"] = int(sentence_match.group(1))
                constraints["is_brief"] = True
            
            # 特殊フォーマット検出
            if "haiku" in goal_lower:
                constraints["format_type"] = "haiku"
                constraints["is_brief"] = True
            elif "twitter" in goal_lower or "tweet" in goal_lower:
                constraints["format_type"] = "twitter"
                constraints["word_limit"] = 25
                constraints["is_brief"] = True
            elif "elevator pitch" in goal_lower:
                constraints["format_type"] = "elevator_pitch"
                constraints["sentence_limit"] = 3
                constraints["is_brief"] = True
            
            return constraints

    def _generate_constraint_prompt(self, goal: str, constraints: dict) -> tuple:
        """制約に基づいて最適なプロンプトを生成"""
        
        # 簡潔性が要求されている場合
        if constraints["is_brief"]:
            
            # 制約付きシステムプロンプト
            system_prompt = """You are a concise technical analyst. 
CRITICAL: User has requested specific constraints. You MUST follow them exactly.
- If word limit specified: Do not exceed it under any circumstances
- If bullet points specified: Use exactly that number, no more
- If format specified: Follow the format precisely
- Keep analysis practical and actionable
- No verbose explanations or unnecessary details"""
            
            # 制約別プロンプト生成
            if constraints["bullet_limit"]:
                prompt = f"""Analyze this goal in exactly {constraints['bullet_limit']} bullet points (no more, no less):
Goal: {goal}

Format: • Point 1 • Point 2 • Point 3 (example for 3 points)
Each point should be 1-2 sentences maximum."""
                
            elif constraints["word_limit"]:
                prompt = f"""Analyze this goal in exactly {constraints['word_limit']} words or less:
Goal: {goal}

STRICT LIMIT: {constraints['word_limit']} words maximum. Count carefully."""
                
            elif constraints["sentence_limit"]:
                prompt = f"""Analyze this goal in exactly {constraints['sentence_limit']} sentences:
Goal: {goal}

Each sentence should cover a key aspect. Be direct and actionable."""
                
            elif constraints["format_type"] == "haiku":
                prompt = f"""Analyze this goal as a haiku (5-7-5 syllables):
Goal: {goal}

Format:
Line 1 (5 syllables): Problem/Goal
Line 2 (7 syllables): Solution approach  
Line 3 (5 syllables): Expected result"""
                
            elif constraints["format_type"] == "twitter":
                prompt = f"""Analyze this goal in Twitter format (under 280 characters):
Goal: {goal}

Use: Problem → Solution → Result (with emojis for clarity)"""
                
            else:
                # 一般的な簡潔プロンプト
                prompt = f"""Provide a brief analysis of this goal (3 key points maximum):
Goal: {goal}

Focus on: 1) What needs to be built 2) Key challenges 3) Success approach
Keep each point to 1-2 sentences."""
            
            return prompt, system_prompt
        
        # 制約なしの場合は従来のプロンプトを使用
        else:
            try:
                prompt_data = prompt_manager.render_prompt(
                    "problem_analysis",
                    {"goal": goal}
                )
                return prompt_data["prompt"], prompt_data["system_prompt"]
            except:
                # フォールバック
                return f"Analyze this goal: {goal}", "You are a helpful technical analyst."

    def _generate_write_constraint_prompt(self, goal: str, analysis: str, plan: str, constraints: dict, target_language: str = "python", target_file: str = None) -> tuple:
        """writeコマンド用の制約プロンプト生成"""
        
        # 制約付きシステムプロンプト
        system_prompt = f"""You are a concise code generator.
    CRITICAL: User has requested specific constraints. You MUST follow them exactly.
    - If word limit specified: Keep code comments and documentation within limit
    - If bullet points specified: Organize code into exactly that many sections/functions
    - Generate clean, functional {target_language} code
    - Focus on core functionality, minimal boilerplate
    - No verbose explanations in code comments"""
        
        # 制約別プロンプト生成
        if constraints["bullet_limit"]:
            prompt = f"""Generate {target_language} code with exactly {constraints['bullet_limit']} main sections/functions:

    Goal: {goal}
    Analysis: {analysis}
    Plan: {plan}

    Target file: {target_file or 'main file'}
    Language: {target_language}

    Structure: Organize into exactly {constraints['bullet_limit']} clear sections.
    Each section should be functional and well-defined."""
            
        elif constraints["word_limit"]:
            prompt = f"""Generate {target_language} code with minimal comments (under {constraints['word_limit']} words total in comments):

    Goal: {goal}
    Analysis: {analysis}  
    Plan: {plan}

    Target file: {target_file or 'main file'}
    Language: {target_language}

    STRICT LIMIT: Keep all comments and documentation under {constraints['word_limit']} words."""
            
        elif constraints["sentence_limit"]:
            prompt = f"""Generate {target_language} code with exactly {constraints['sentence_limit']} main functions:

    Goal: {goal}
    Analysis: {analysis}
    Plan: {plan}

    Target file: {target_file or 'main file'}
    Language: {target_language}

    Structure: Create exactly {constraints['sentence_limit']} main functions, each handling a key aspect."""
            
        else:
            # 一般的な簡潔コード生成
            prompt = f"""Generate clean, minimal {target_language} code (focus on core functionality):

    Goal: {goal}
    Analysis: {analysis}
    Plan: {plan}

    Target file: {target_file or 'main file'}
    Language: {target_language}

    Requirements: Core functionality only, minimal comments, clean structure."""
        
        return prompt, system_prompt

    def _generate_plan_constraint_prompt(self, goal: str, analysis: str, constraints: dict) -> tuple:
            """planコマンド用の制約プロンプト生成"""
            
            # 制約付きシステムプロンプト
            system_prompt = """You are a concise implementation planner.
    CRITICAL: User has requested specific constraints. You MUST follow them exactly.
    - If word limit specified: Do not exceed it under any circumstances  
    - If bullet points specified: Use exactly that number, no more
    - Focus on actionable steps and concrete deliverables
    - No verbose explanations or unnecessary details"""
            
            # 制約別プロンプト生成
            if constraints["bullet_limit"]:
                prompt = f"""Create an implementation plan in exactly {constraints['bullet_limit']} bullet points:

    Goal: {goal}
    Analysis: {analysis}

    Format: • Step 1 • Step 2 • Step 3 (example for 3 points)
    Each point should be actionable and specific."""
                
            elif constraints["word_limit"]:
                prompt = f"""Create an implementation plan in {constraints['word_limit']} words or less:

    Goal: {goal} 
    Analysis: {analysis}

    STRICT LIMIT: {constraints['word_limit']} words maximum."""
                
            elif constraints["sentence_limit"]:
                prompt = f"""Create an implementation plan in exactly {constraints['sentence_limit']} sentences:

    Goal: {goal}
    Analysis: {analysis}

    Each sentence should be actionable and specific."""
                
            else:
                # 一般的な簡潔プラン
                prompt = f"""Create a brief implementation plan (3 key steps maximum):

    Goal: {goal}
    Analysis: {analysis}

    Focus on: 1) Setup & core logic 2) UI implementation 3) Testing & deployment
    Keep each step to 1-2 sentences."""
            
            return prompt, system_prompt

    def _display_with_typewriter(self, text: str, prefix: str = ""):
        """タイプライター効果でテキストを表示
        
        Args:
            text (str): 表示するテキスト
            prefix (str): テキストの前に表示するプレフィックス（例: "Claude: "）
        """
        if not self.config.get("typewriter_effect", False):
            # タイプライター効果が無効の場合は通常表示
            if prefix:
                print(f"{prefix}{text}")
            else:
                print(text)
            return
        
        # タイプライター効果の設定を取得
        speed = self.config.get("typewriter_speed", 0.03)
        chunk_size = self.config.get("typewriter_chunk_size", 1)
        
        import time
        
        # プレフィックスを即座に表示
        if prefix:
            print(prefix, end="", flush=True)
        
        # テキストを chunk_size 単位で段階的に表示
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            print(chunk, end="", flush=True)
            time.sleep(speed)
        
        print()  # 最後に改行

    def _stream_with_typewriter(self, stream_generator, prefix: str = ""):
        """ストリーミング応答にタイプライター効果を適用
        
        Args:
            stream_generator: LLMからのストリーミング応答ジェネレータ
            prefix (str): テキストの前に表示するプレフィックス
            
        Returns:
            str: 完全な応答テキスト
        """
        # ストリーミング応答にタイプライター効果を適用するか確認
        apply_to_streaming = self.config.get("typewriter_apply_to_streaming", True)
        typewriter_enabled = self.config.get("typewriter_effect", False)
        
        if not typewriter_enabled or not apply_to_streaming:
            # タイプライター効果無効時は通常のストリーミング表示
            if prefix:
                print(prefix, end=" ", flush=True)
            
            response_parts = []
            for chunk in stream_generator:
                print(chunk, end="", flush=True)
                response_parts.append(chunk)
            print()
            return "".join(response_parts)
        
        # タイプライター効果付きストリーミング
        speed = self.config.get("typewriter_speed", 0.03)
        
        import time
        
        # プレフィックスを即座に表示
        if prefix:
            print(prefix, end=" ", flush=True)
        
        response_parts = []
        for chunk in stream_generator:
            # チャンク内の各文字を段階的に表示
            for char in chunk:
                print(char, end="", flush=True)
                time.sleep(speed)
            response_parts.append(chunk)
        
        print()
        return "".join(response_parts)


    def _display_command_result(self, content: str, command_type: str = "result"):
        """コマンド結果をタイプライター効果で表示
        
        Args:
            content (str): 表示する内容
            command_type (str): コマンドの種類（think, plan, write等）
        """
        # コマンド結果にタイプライター効果を適用するか確認
        apply_to_commands = self.config.get("typewriter_apply_to_commands", True)
        typewriter_enabled = self.config.get("typewriter_effect", False)
        
        if not typewriter_enabled or not apply_to_commands:
            # タイプライター効果無効時は通常表示
            print(content)
            return
        
        # コマンド種別に応じたプレフィックス（オプション）
        prefixes = {
            "think": "💭 Analysis Result:\n",
            "plan": "📋 Implementation Plan:\n", 
            "write": "✍️  Generated Implementation:\n",
            "review": "📊 Code Review:\n"
        }
        
        prefix = prefixes.get(command_type, "")
        
        if prefix:
            # プレフィックスは即座に表示
            print(prefix, end="", flush=True)
            # 少し間を置く
            import time
            time.sleep(0.5)
        
        # メインコンテンツをタイプライター効果で表示
        self._display_with_typewriter(content, "")


    # 設定変更時の便利メソッド（オプション）
    def _toggle_typewriter_effect(self):
        """タイプライター効果のオン/オフを切り替える便利メソッド"""
        current = self.config.get("typewriter_effect", False)
        new_value = not current
        self.config.set("typewriter_effect", new_value)
        
        status = "enabled" if new_value else "disabled"
        print(f"🎭 Typewriter effect {status}")
        
        if new_value:
            speed = self.config.get("typewriter_speed", 0.03)
            print(f"   Speed: {speed}s per character")
            print(f"   💡 Use '/config set typewriter_speed 0.01' to make it faster")
            print(f"   💡 Use '/config set typewriter_speed 0.05' to make it slower")

    def _extract_function_regex(self, code: str, function_name: str) -> Optional[str]:
        """Fallback function extraction using regex (less robust)"""
        lines = code.split('\n')
        func_lines = []
        in_function = False
        base_indent = None
        
        for i, line in enumerate(lines):
            # Look for function definition
            if re.match(rf'^\s*(async\s+)?def\s+{re.escape(function_name)}\s*\(', line):
                in_function = True
                base_indent = len(line) - len(line.lstrip())
                func_lines.append(line)
                continue
            
            if in_function:
                # Empty line
                if not line.strip():
                    func_lines.append(line)
                    continue
                
                # Check indentation
                current_indent = len(line) - len(line.lstrip())
                
                # If we're back to the base level or less, function has ended
                if current_indent <= base_indent and not line.lstrip().startswith(('@', '#')):
                    break
                
                func_lines.append(line)
        
        return '\n'.join(func_lines) if func_lines else None
    
    def _replace_function_in_code(self, original_code: str, function_name: str, new_function: str) -> str:
        """Replace specific function in code with new implementation"""
        try:
            tree = ast.parse(original_code)
            lines = original_code.split('\n')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    start_line = node.lineno - 1
                    
                    # Find end line more precisely
                    end_line = len(lines)
                    for next_node in ast.walk(tree):
                        if (isinstance(next_node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) 
                            and next_node.lineno > node.lineno):
                            end_line = min(end_line, next_node.lineno - 1)
                    
                    # Find actual end by checking indentation
                    base_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
                    actual_end = start_line + 1
                    
                    for i in range(start_line + 1, end_line):
                        if i >= len(lines):
                            break
                        line = lines[i]
                        if line.strip():
                            current_indent = len(line) - len(line.lstrip())
                            if current_indent <= base_indent and not line.lstrip().startswith(('@', '#')):
                                break
                        actual_end = i + 1
                    
                    # Replace the function
                    new_lines = lines[:start_line] + new_function.split('\n') + lines[actual_end:]
                    return '\n'.join(new_lines)
            
            # Function not found, return original
            return original_code
            
        except SyntaxError:
            # Fallback to regex replacement
            return self._replace_function_regex(original_code, function_name, new_function)
    
    def _replace_function_regex(self, original_code: str, function_name: str, new_function: str) -> str:
        """Fallback function replacement using regex"""
        lines = original_code.split('\n')
        new_lines = []
        skip_lines = False
        base_indent = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for function definition
            if re.match(rf'^\s*(async\s+)?def\s+{re.escape(function_name)}\s*\(', line):
                base_indent = len(line) - len(line.lstrip())
                # Add the new function
                new_lines.extend(new_function.split('\n'))
                skip_lines = True
            elif skip_lines:
                # Skip lines until we're back to base indentation
                if line.strip():
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= base_indent and not line.lstrip().startswith(('@', '#')):
                        skip_lines = False
                        new_lines.append(line)
            else:
                new_lines.append(line)
            
            i += 1
        
        return '\n'.join(new_lines)
    
    def run(self):
        """Start the CLI"""
        try:
            # 起動時に画面をクリア
            import os
            if os.name == 'nt':  # Windows
                os.system('cls')
            else:  # Linux/Mac
                os.system('clear')
            
            # ロゴを一番上から表示
            print(self.intro)
            print()  # 空行を追加
            
            # その後でセッション復元チェック
            self._check_session_restoration()
            
            # cmdloopを開始（introは空にする）
            original_intro = self.intro
            self.intro = ""  # cmdloopでのintro表示を無効化
            
            self.cmdloop()
            
            # 元に戻す
            self.intro = original_intro
            
        except KeyboardInterrupt:
            print("\n\n✨ Session saved! See you again! 👋")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        cleanup_temp_files(self.temp_files)
    
    def default(self, line: str):
        """Handle regular chat input"""
        # より厳密な空入力チェック
        if not line or not line.strip():
            return  # 何もしない - 重要：早期リターン
        
        line = line.strip()
        
        # Check if it's a slash command
        if line.startswith('/'):
            self.handle_slash_command(line)
            return
        
        # Regular chat interaction
        self.handle_chat(line)

    def emptyline(self):
        """Override emptyline to prevent any action on empty input"""
        return  # 何もしない
    
    def handle_slash_command(self, command: str):
        """Handle slash commands"""
        parts = shlex.split(command[1:])  # Remove leading /
        
        if not parts:
            return
        
        cmd_name = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Map slash commands to methods
        command_map = {
            'edit': self.cmd_edit,
            'fix': self.cmd_fix,
            'review': self.cmd_review,
            'status': self.cmd_status,
            'init': self.cmd_init,
            'config': self.cmd_config,
            'reset': self.cmd_reset,
            'help': self.cmd_help,
            'memory': self.cmd_memory,
            'diff': self.cmd_diff,
            'apply': self.cmd_apply,
            'backup': self.cmd_backup,
            'model': self.cmd_model,
            'export': self.cmd_export,
            'import': self.cmd_import,
            'save-session': self.cmd_save_session,
            'resume': self.cmd_resume,
            'list-sessions': self.cmd_list_sessions,
            'session-info': self.cmd_session_info,
            'delete-session': self.cmd_delete_session,
            'export-session': self.cmd_export_session,
            'think': self.cmd_think,
            'plan': self.cmd_plan,
            'write': self.cmd_write,
            'workflow-status': self.cmd_workflow_status,
            'clear-workflow': self.cmd_clear_workflow
        }
        
        if cmd_name in command_map:
            def execute_command():
                command_map[cmd_name](args)
            
            safe_execute(
                execute_command,
                error_handler=self.error_handler,
                context=f"command execution: /{cmd_name}"
            )
        else:
            print(f"Unknown command: /{cmd_name}")
            print("Type '/help' for available commands.")

    def handle_chat(self, user_input: str):
        """Handle regular chat interaction"""
        try:
            # 複数行チャット入力のサポート
            if user_input.strip().upper() == "MULTI":
                print("💬 Multi-line chat mode")
                user_input = self.get_multiline_input(
                    "Enter your question or message:",
                    allow_empty=False
                )
                if not user_input:
                    return
            
            print("Thinking...")
            
            # Generate context
            context = self.context.generate_context_for_prompt(user_input)
            
            # Get conversation history
            conversation_history = self.memory.get_conversation_context(limit=5)
            
            # Build enhanced system prompt with session awareness
            base_system_prompt = self.config.get_system_prompt("default")
            
            # セッション復元時の自動コンテキスト追加
            session_context = ""
            if self.session_manager.get_session_stats():
                stats = self.session_manager.get_session_stats()
                if stats.get('total_entries', 0) > 0:
                    session_context = f"""

    IMPORTANT COGNIX SESSION CONTEXT:
    - You are operating in Cognix, which has advanced session management
    - This session has been restored with {stats['total_entries']} previous interactions
    - All conversation history and context from previous sessions is available to you
    - When users reference past conversations, you can naturally access them from your memory
    - Do NOT say information "won't be preserved" - in Cognix, it IS preserved across sessions
    - Respond naturally as if this is one continuous conversation"""
            
            enhanced_system_prompt = base_system_prompt + session_context
            
            # Generate response
            if self.config.get("stream_responses", True):
                # ストリーミング応答をタイプライター効果で表示
                stream_gen = self.llm_manager.stream_response(
                    prompt=user_input,
                    context=context,
                    conversation_history=conversation_history,
                    system_prompt=enhanced_system_prompt
                )
                response_content = self._stream_with_typewriter(stream_gen, "Claude:")
                
            else:
                response = self.llm_manager.generate_response(
                    prompt=user_input,
                    context=context,
                    conversation_history=conversation_history,
                    system_prompt=enhanced_system_prompt
                )
                response_content = response.content
                # 非ストリーミング応答もタイプライター効果で表示
                self._display_with_typewriter(response_content, "Claude: ")
            
            # Store in memory
            self.memory.add_entry(
                user_prompt=user_input,
                claude_reply=response_content,
                model_used=self.llm_manager.current_model
            )
            
            # Store in session
            self.session_manager.add_entry(
                user_input=user_input,
                ai_response=response_content,
                model_used=self.llm_manager.current_model,
                command_type="chat"
            )
            
            # Show token usage if enabled
            if self.config.get("show_token_usage", False) and not self.config.get("stream_responses", True):
                usage = response.usage
                print(f"Tokens: {usage['total_entries']} ({usage['prompt_tokens']} + {usage['completion_tokens']})")
            
        except Exception as e:
            self.error_handler.handle_error(e, "chat interaction")    

    def get_multiline_input(self, prompt: str, allow_empty: bool = False) -> str:
        """複数行入力を適切に処理する統一関数"""
        print(f"\n{prompt}")
        print("💡 Input tips:")
        print("  • Type 'END' on a new line to finish")
        print("  • Press Ctrl+D (Unix) or Ctrl+Z (Windows) to finish")
        print("  • Press Ctrl+C to cancel")
        print()
        
        lines = []
        try:
            while True:
                try:
                    line = input()
                    if line.strip() == 'END':
                        break
                    lines.append(line)
                except EOFError:
                    # Ctrl+D (Unix) or Ctrl+Z (Windows)
                    break
        except KeyboardInterrupt:
            print("\n❌ Input cancelled")
            return ""
        
        content = '\n'.join(lines).strip()
        
        if not content and not allow_empty:
            print("❌ Empty input not allowed. Please try again.")
            return self.get_multiline_input(prompt, allow_empty)
        
        return content

    def get_input_with_options(self, prompt: str, allow_empty: bool = False) -> str:
        """単行または複数行入力を選択できる関数"""
        print(f"\n{prompt}")
        print("📝 Input options:")
        print("  • Type directly for single line")
        print("  • Press ENTER for multi-line mode")
        print("  • Type 'MULTI' for multi-line mode")
        
        first_input = input("➤ ").strip()
        
        if first_input == "" or first_input.upper() == "MULTI":
            # Multi-line mode
            return self.get_multiline_input("Enter your content:", allow_empty)
        else:
            # Single line input
            return first_input
    
    def cmd_edit(self, args: List[str]):
        """Edit a file with AI assistance"""
        if not args:
            print("Usage: /edit <file_path> [--auto]")
            return
        
        # Validate file path input
        try:
            from .error_handling import validate_file_path
            file_path = args[0]
            # Basic validation - more detailed validation happens later
            if not file_path or file_path.strip() == "":
                print("❌ File path cannot be empty")
                return
        except Exception as e:
            self.error_handler.handle_error(e, "file path validation")
            return
        
        # Parse arguments
        file_path = args[0]
        auto_apply = self.auto_mode
        
        # Check for --auto flag
        if "--auto" in args[1:]:
            auto_apply = True
        
        full_path = Path.cwd() / file_path
        
        if not full_path.exists():
            create_confirm = input(f"File '{file_path}' doesn't exist. Create it? [y/N] ").strip().lower()
            if create_confirm != 'y':
                print("❌ File editing cancelled")
                return
            
            # Create empty file
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.touch()
        
        try:
            # Read current content
            original_content = full_path.read_text(encoding='utf-8')
            
            print(f"\n📝 Editing: {file_path}")
            print(f"📊 Size: {format_file_size(len(original_content.encode()))}")
            
            # 修正: 複数行入力対応
            edit_request = self.get_input_with_options(
                "What changes would you like to make?", 
                allow_empty=False
            )
            
            if not edit_request:
                print("❌ No changes specified")
                return

            print("\n🤖 Generating suggestions...")
            
            # Generate suggestions
            language = self.context.get_file_language(full_path)
            context = self.context.generate_context_for_prompt(edit_request, max_context_size=4000)
            
            suggestion = self.code_assistant.generate_diff_suggestion(
                original_content,
                edit_request,
                language=language,
                context=context
            )
            
            print(f"\n💡 Suggestion:")
            print(suggestion)
            
            # Apply confirmation
            apply_confirm = input("\nApply these changes? [y/N] ").strip().lower()
            if apply_confirm != 'y':
                print("❌ Changes discarded")
                return

            # 修正: 複数行コンテンツ入力対応
            new_content = self.get_input_with_options(
                "Paste the new content:",
                allow_empty=False
            )

            if not new_content:
                print("❌ No content provided")
                return

            # Show diff preview
            diff_result = self.diff_engine.preview_changes(str(full_path), new_content)
            
            if diff_result.diff_content:
                print("\n📋 Changes preview:")
                print_diff_highlighted(diff_result.diff_content)
                
                print(f"\nChanges: +{diff_result.line_changes['added']} -{diff_result.line_changes['removed']} ~{diff_result.line_changes['modified']} lines")
            
            final_confirm = input("\n💾 Save changes? [y/N] ").strip().lower()
            if final_confirm != 'y':
                print("❌ Changes discarded")
                return

            # Apply changes
            patch_result = self.diff_engine.apply_content_replacement(
                str(full_path),
                new_content,
                create_backup=self.config.get("auto_backup", True)
            )
            
            if patch_result.success:
                print(f"✅ File saved: {file_path}")
                if patch_result.backup_path:
                    print(f"💾 Backup: {patch_result.backup_path}")
                
                # Store in memory
                self.memory.add_entry(
                    user_prompt=f"Edit {file_path}: {edit_request}",
                    claude_reply=suggestion,
                    model_used=self.llm_manager.current_model,
                    file_path=file_path,
                    file_before=original_content,
                    file_after=new_content
                )
                
                # Store in session
                self.session_manager.add_entry(
                    user_input=f"Edit {file_path}: {edit_request}",
                    ai_response=suggestion,
                    model_used=self.llm_manager.current_model,
                    command_type="edit",
                    target_files=[file_path],
                    metadata={
                        "file_size_before": len(original_content),
                        "file_size_after": len(new_content),
                        "backup_created": patch_result.backup_path is not None
                    }
                )
                
            else:
                print(f"❌ Failed to save file: {patch_result.error}")
                
        except Exception as e:
            print(f"❌ Error editing file: {e}")
    
    def cmd_fix(self, args: List[str]):
        """Fix/modify a file directly with AI"""
        if not args:
            print("Usage: /fix <file_path> [--function <function_name>] [--auto]")
            return
        
        # Validate inputs
        try:
            from .error_handling import validate_file_path, validate_function_name
            file_path = args[0]
            if not file_path or file_path.strip() == "":
                print("❌ File path cannot be empty")
                return
        except Exception as e:
            self.error_handler.handle_error(e, "input validation")
            return
        
        # Parse arguments
        file_path = args[0]
        function_name = None
        auto_apply = self.auto_mode
        
        # Simple argument parsing with validation
        i = 1
        while i < len(args):
            if args[i] == "--function" and i + 1 < len(args):
                try:
                    function_name = validate_function_name(args[i + 1])
                except Exception as e:
                    self.error_handler.handle_error(e, "function name validation")
                    return
                i += 2
            elif args[i] == "--auto":
                auto_apply = True
                i += 1
            else:
                i += 1
        
        full_path = Path.cwd() / file_path
        
        if not full_path.exists():
            if not self._confirm_action(f"File '{file_path}' does not exist. Create it?", auto_apply):
                return
            full_path.touch()
        
        try:
            print(f"Fixing: {file_path}")
            
            # Read current content
            original_content = full_path.read_text(encoding='utf-8')
            print(f"Size: {format_file_size(len(original_content.encode('utf-8')))}")
            
            if not original_content.strip():
                print("File is empty. Nothing to fix.")
                return
            
            # Prepare content for fixing
            if function_name:
                # Extract specific function using robust AST-based method
                content_to_fix = self._extract_function_from_code(original_content, function_name)
                
                if not content_to_fix:
                    print(f"Function '{function_name}' not found in {file_path}")
                    return
                
                context_info = f"Function '{function_name}' from {file_path}"
            else:
                content_to_fix = original_content
                context_info = f"File: {file_path}"
            
            # Generate fix prompt using template
            language = self.context.get_file_language(full_path) if full_path else "python"
            
            try:
                prompt_data = prompt_manager.render_prompt(
                    "code_fix",
                    {
                        "content_type": "function" if function_name else "file",
                        "context_info": context_info,
                        "code_content": content_to_fix,
                        "language": language
                    }
                )
                
                if not prompt_data:
                    raise CognixError("Failed to generate fix prompt template")
                
                fix_prompt = prompt_data["prompt"]
                system_prompt = prompt_data["system_prompt"]
                
            except Exception as e:
                self.error_handler.handle_error(e, "prompt generation")
                return
            
            print("Analyzing and fixing code...")
            
            # Get AI response
            response = self.llm_manager.generate_response(
                prompt=fix_prompt,
                system_prompt=system_prompt
            )
            
            fixed_code = response.content.strip()
            
            # Remove markdown code blocks if present
            if fixed_code.startswith('```'):
                lines = fixed_code.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                fixed_code = '\n'.join(lines)
            
            print(f"\nFixed code preview:")
            print("=" * 50)
            preview_text = fixed_code[:500] + ("..." if len(fixed_code) > 500 else "")
            self._display_with_typewriter(preview_text, "")
            print("=" * 50)
            
            # Apply fix
            if function_name:
                # Replace function using robust AST-based method
                new_content = self._replace_function_in_code(original_content, function_name, fixed_code)
            else:
                new_content = fixed_code
            
            # Confirm and apply changes
            if self._confirm_action("Apply the fix?", auto_apply):
                # Create backup if enabled
                if self.config.get("auto_backup", True):
                    backup_result = self.diff_engine.create_backup(str(full_path))
                    if backup_result.success and backup_result.backup_path:
                        print(f"Backup created: {backup_result.backup_path}")
                
                # Apply the fix
                patch_result = self.diff_engine.apply_content_replacement(
                    file_path=str(full_path),
                    new_content=new_content,
                    create_backup=False  # Already created above
                )
                
                if patch_result.success:
                    print(f"✅ File fixed: {file_path}")
                    
                    # Store in memory
                    self.memory.add_entry(
                        user_prompt=f"Fix {file_path}" + (f" (function: {function_name})" if function_name else ""),
                        claude_reply=f"Fixed code:\n{fixed_code}",
                        model_used=self.llm_manager.current_model,
                        file_path=file_path,
                        file_before=original_content,
                        file_after=new_content
                    )
                    
                    # Store in session
                    self.session_manager.add_entry(
                        user_input=f"Fix {file_path}" + (f" (function: {function_name})" if function_name else ""),
                        ai_response=f"Fixed code:\n{fixed_code}",
                        model_used=self.llm_manager.current_model,
                        command_type="fix",
                        target_files=[file_path],
                        metadata={
                            "function_name": function_name,
                            "file_size_before": len(original_content),
                            "file_size_after": len(new_content),
                            "auto_applied": auto_apply
                        }
                    )
                    
                else:
                    print(f"❌ Failed to apply fix: {patch_result.error}")
            else:
                print("Fix cancelled")
            
        except Exception as e:
            print(f"Error fixing file: {e}")
    
    def cmd_review(self, args: List[str]):
        """Review and analyze a directory"""
        if args:
            target_dir = Path(args[0])
        else:
            target_dir = self.context.root_dir
        
        if not target_dir.exists():
            print(f"Directory not found: {target_dir}")
            return
        
        print(f"Reviewing: {target_dir}")
        
        # Create file context for target directory
        review_context = FileContext(str(target_dir))
        summary = review_context.get_project_summary()
        
        print(f"\nProject Summary:")
        print(f"  Files: {summary['total_files']}")
        print(f"  Size: {format_file_size(summary['total_size_bytes'])}")
        print(f"  Lines: {summary['total_lines']:,}")
        
        if summary['languages']:
            print(f"  Languages: {', '.join(summary['languages'].keys())}")
        
        # Generate AI review using template
        print("\nGenerating review...")
        
        context_text = review_context.generate_context_for_prompt("review this project", max_context_size=8000)
        
        try:
            prompt_data = prompt_manager.render_prompt(
                "code_review",
                {
                    "content_type": "project",
                    "context_info": f"Project: {target_dir}\nFiles: {summary['total_files']}\nSize: {format_file_size(summary['total_size_bytes'])}",
                    "code_content": context_text,
                    "language": ", ".join(summary['languages'].keys()) if summary['languages'] else "mixed"
                }
            )
            
            if not prompt_data:
                raise CognixError("Failed to generate review prompt template")
            
            review_prompt = prompt_data["prompt"]
            system_prompt = prompt_data["system_prompt"]
            
        except Exception as e:
            self.error_handler.handle_error(e, "review prompt generation")
            return
        
        try:
            response = self.llm_manager.generate_response(
                prompt=review_prompt,
                system_prompt=system_prompt
            )
            
            print()  # 空行
            self._display_command_result(response.content, "review")
            
            # Store in memory
            self.memory.add_entry(
                user_prompt=f"Review directory: {target_dir}",
                claude_reply=response.content,
                model_used=self.llm_manager.current_model,
                metadata={"directory": str(target_dir), "summary": summary}
            )
            
            # Store in session
            self.session_manager.add_entry(
                user_input=f"Review directory: {target_dir}",
                ai_response=response.content,
                model_used=self.llm_manager.current_model,
                command_type="review",
                target_files=[str(target_dir)],
                metadata={
                    "directory": str(target_dir),
                    "total_files": summary['total_files'],
                    "total_size": summary['total_size_bytes'],
                    "languages": list(summary['languages'].keys()) if summary['languages'] else []
                }
            )
            
        except Exception as e:
            print(f"Error generating review: {e}")
    
    def cmd_status(self, args: List[str]):
        """Show current status"""
        print("Cognix Status")
        print("=" * 30)
        
        # Configuration
        print(f"Model: {self.llm_manager.current_model}")
        print(f"Temperature: {self.config.get('temperature')}")
        print(f"Max Tokens: {self.config.get('max_tokens')}")
        
        # Project info
        print(f"\nProject: {self.context.root_dir}")
        summary = self.context.get_project_summary()
        print(f"Files: {summary['total_files']}")
        print(f"Size: {format_file_size(summary['total_size_bytes'])}")
        
        # Memory stats
        memory_stats = self.memory.get_memory_stats()
        print(f"\nMemory: {memory_stats['total_entries']} entries")
        print(f"Files tracked: {memory_stats['unique_files']}")
        
        # Available models
        available_models = self.llm_manager.get_available_models()
        print(f"\nAvailable models: {', '.join(available_models)}")
    
    def cmd_init(self, args: List[str]):
        """Create CLAUDE.md in current directory"""
        claude_file = self.context.root_dir / "CLAUDE.md"
        
        if claude_file.exists():
            overwrite = confirm_action("CLAUDE.md already exists. Overwrite?", default=False)
            if not overwrite:
                return
        
        # Generate CLAUDE.md content
        summary = self.context.get_project_summary()
        
        claude_content = f"""# Cognix Project Configuration

goal: "AI-assisted development for this project"
model: "{self.llm_manager.current_model}"
tone: "professional, helpful, focused on code quality"
project_type: "software development"

## Project Overview
- Files: {summary['total_files']}
- Languages: {', '.join(summary['languages'].keys()) if summary['languages'] else 'mixed'}
- Size: {format_file_size(summary['total_size_bytes'])}

## Excluded Directories
excluded_dirs: {json.dumps(list(self.config.get_exclude_patterns()[:10]))}

## Common Prompts
prompts:
  - "Review this code for potential improvements"
  - "Explain what this function does"
  - "Generate unit tests for this module"
  - "Refactor this code to be more maintainable"
  - "Find potential bugs or security issues"
  - "Optimize this code for performance"
  - "Add proper error handling"
  - "Improve code documentation"
"""
        
        try:
            claude_file.write_text(claude_content, encoding='utf-8')
            print(f"Created CLAUDE.md in {self.context.root_dir}")
            
            # Reload context to pick up new config
            self.context.load_claude_config()
            
        except Exception as e:
            print(f"Error creating CLAUDE.md: {e}")
    
    # cli.py の cmd_config() メソッドを以下で完全に置き換えてください

    def cmd_config(self, args: List[str]):
        """Show or edit configuration"""
        if not args:
            # Show current config
            config_summary = self.config.get_config_summary()
            
            print("⚙️ Configuration")
            print("=" * 30)
            
            for key, value in config_summary.items():
                if key == "validation_issues" and value:
                    print(f"⚠️ Issues: {', '.join(value)}")
                else:
                    print(f"{key}: {value}")
            
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "edit":
            # Open config file in editor
            config_path = str(self.config.config_path)
            if open_in_editor(config_path):
                print(f"Opened config: {config_path}")
                
                # Reload config
                self.config.load_config()
                print("Configuration reloaded")
            else:
                print(f"Failed to open editor for: {config_path}")
        
        elif subcommand == "set" and len(args) >= 3:
            key, value = args[1], args[2]
            
            # Try to parse value as JSON for complex types
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = value
            
            self.config.set(key, parsed_value)
            print(f"Set {key} = {parsed_value}")
        
        elif subcommand == "get" and len(args) >= 2:
            key = args[1]
            value = self.config.get(key)
            print(f"{key} = {value}")
        
        elif subcommand == "typewriter" and len(args) >= 2:
            action = args[1].lower()
            
            if action == "on":
                self.config.set("typewriter_effect", True)
                speed = self.config.get("typewriter_speed", 0.03)
                print(f"🎭 Typewriter effect enabled (speed: {speed}s)")
                
            elif action == "off":
                self.config.set("typewriter_effect", False)
                print("🎭 Typewriter effect disabled")
                
            elif action == "toggle":
                self._toggle_typewriter_effect()
                
            elif action == "speed" and len(args) >= 3:
                try:
                    speed = float(args[2])
                    if 0.005 <= speed <= 0.2:
                        self.config.set("typewriter_speed", speed)
                        print(f"🎭 Typewriter speed set to {speed}s")
                    else:
                        print("❌ Speed must be between 0.005 and 0.2")
                except ValueError:
                    print("❌ Invalid speed value")
            
            else:
                print("Usage:")
                print("  /config typewriter on       - Enable typewriter effect")
                print("  /config typewriter off      - Disable typewriter effect") 
                print("  /config typewriter toggle   - Toggle typewriter effect")
                print("  /config typewriter speed X  - Set speed (0.005-0.2)")
        
        else:
            print("Usage:")
            print("  /config              - Show current configuration")
            print("  /config edit         - Edit configuration file")
            print("  /config set key val  - Set configuration value")
            print("  /config get key      - Get configuration value")
            print("  /config typewriter   - Typewriter effect settings")
    
    def cmd_reset(self, args: List[str]):
        """Reset memory and start fresh"""
        if confirm_action("Clear all memory? This cannot be undone.", default=False):
            self.memory.clear_memory()
            self.session_manager.clear_current_session()
            self.workflow_state = {"think_result": None, "plan_result": None, "current_goal": None}
            print("✅ Everything reset to initial state")
    
    def cmd_help(self, args: List[str]):
        """Show help information"""
        print("""
🚀 Cognix Commands:

File Operations:
  /edit <file>         - Edit a file with AI assistance
  /fix <file> [--function <name>] [--auto] - Fix/modify file directly
  /review [dir]        - Review and analyze directory
  /diff <file1> <file2> - Show diff between files
  /apply <patch_file>  - Apply patch to files

Workflow Commands:
  /think <goal>        - Analyze problem with AI (Step 1)
  /plan                - Create implementation plan (Step 2)
  /write [--file <path>] [--step <name>] - Generate code (Step 3)
  /workflow-status     - Show current workflow progress
  /clear-workflow      - Clear workflow state

Memory & Context:
  /status              - Show current status
  /memory [search]     - Show/search memory entries
  /reset               - Clear all memory

Session Management:
  /save-session <name> - Save current session with name
  /resume <name>       - Resume named session
  /list-sessions       - List all saved sessions
  /session-info        - Show current session info
  /delete-session <name> - Delete a saved session
  /export-session <name> <path> [format] - Export session

Configuration:
  /config              - Show configuration
  /config edit         - Edit configuration
  /init                - Create CLAUDE.md file

Model & Export:
  /model [name]        - Switch model or show current
  /export <format>     - Export memory/config
  /import <file>       - Import memory/config
  /backup              - Manage backups

General:
  /help                - Show this help
  help                 - Show built-in commands

💡 Multi-line Input Tips:
- Type 'MULTI' in chat for multi-line questions
- Use ENTER in prompts to switch to multi-line mode
- Type 'END' on a new line to finish multi-line input
- Use Ctrl+D (Unix) or Ctrl+Z (Windows) to finish input

🎭 Demo & Presentation:
- Use '/config typewriter on' for smooth AI response display
- Use '/config typewriter speed 0.02' for faster demos
- Use '/config typewriter off' to return to instant display

💡 Tips:
- Just type your question or request to chat with Claude
- Use /edit to modify files with AI assistance
- Use /review to get AI feedback on your code
- Memory is automatically saved between sessions
""")
    
    def cmd_memory(self, args: List[str]):
        """Show or search memory entries"""
        if args and args[0]:
            # Search memory
            query = " ".join(args)
            entries = self.memory.search_entries(query)
            print(f"🔍 Found {len(entries)} entries for '{query}':")
        else:
            # Show recent entries
            entries = self.memory.get_entries(limit=10)
            print("📝 Recent memory entries:")
        
        if not entries:
            print("No entries found.")
            return
        
        # Display entries
        rows = []
        for entry in entries:
            rows.append([
                entry.id[:8],
                entry.timestamp[:19].replace('T', ' '),
                truncate_text(entry.user_prompt, 40),
                entry.model_used,
                entry.file_path or "-"
            ])
        
        print_table(
            ["ID", "Time", "Prompt", "Model", "File"],
            rows
        )
        
        # Show details for a specific entry
        if len(entries) == 1:
            entry = entries[0]
            print(f"\n📋 Entry Details:")
            print(f"User: {entry.user_prompt}")
            print(f"Claude: {truncate_text(entry.claude_reply, 200)}")
    
    def cmd_diff(self, args: List[str]):
        """Show diff between files"""
        if len(args) < 2:
            print("Usage: /diff <file1> <file2>")
            return
        
        file1, file2 = args[0], args[1]
        
        diff_result = self.diff_engine.generate_file_diff(file1, file2)
        
        if diff_result.error:
            print(f"❌ Error: {diff_result.error}")
            return
        
        if not diff_result.diff_content.strip():
            print("ℹ️ Files are identical")
            return
        
        print(f"📊 Diff: {file1} → {file2}")
        print_diff_highlighted(diff_result.diff_content)
        
        changes = diff_result.line_changes
        print(f"\nSummary: +{changes['added']} -{changes['removed']} ~{changes['modified']} lines")
    
    def cmd_apply(self, args: List[str]):
        """Apply patch to files"""
        if not args:
            print("Usage: /apply <patch_file>")
            return
        
        patch_file = args[0]
        
        if not Path(patch_file).exists():
            print(f"❌ Patch file not found: {patch_file}")
            return
        
        try:
            with open(patch_file, 'r', encoding='utf-8') as f:
                patch_content = f.read()
            
            print(f"📥 Applying patch: {patch_file}")
            
            # 修正: 複数行入力対応
            target_file = self.get_input_with_options(
                "Target file:", 
                allow_empty=False
            )
            if not target_file:
                return
            
            result = self.diff_engine.apply_patch(
                target_file,
                patch_content,
                create_backup=self.config.get("auto_backup", True),
                dry_run=False
            )
            
            if result.success:
                print(f"✅ Patch applied to {target_file}")
                if result.backup_path:
                    print(f"💾 Backup: {result.backup_path}")
            else:
                print(f"❌ Failed to apply patch: {result.error}")
        
        except Exception as e:
            print(f"❌ Error applying patch: {e}")
    
    def cmd_backup(self, args: List[str]):
        """Manage backups"""
        if not args:
            # List backups
            backups = self.diff_engine.list_backups()
            
            if not backups:
                print("📦 No backups found")
                return
            
            print(f"📦 Available backups ({len(backups)}):")
            
            rows = []
            for backup in backups[:20]:  # Show last 20
                rows.append([
                    backup["name"],
                    format_file_size(backup["size"]),
                    backup["created"][:19].replace('T', ' ')
                ])
            
            print_table(["Name", "Size", "Created"], rows)
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "cleanup":
            days = int(args[1]) if len(args) > 1 else 7
            removed = self.diff_engine.cleanup_old_backups(days)
            print(f"🧹 Removed {removed} old backups (older than {days} days)")
        
        elif subcommand == "restore" and len(args) >= 3:
            backup_path, target_path = args[1], args[2]
            
            result = self.diff_engine.restore_from_backup(backup_path, target_path)
            
            if result.success:
                print(f"✅ Restored {target_path} from backup")
            else:
                print(f"❌ Failed to restore: {result.error}")
        
        else:
            print("Usage:")
            print("  /backup                    - List backups")
            print("  /backup cleanup [days]     - Clean old backups")
            print("  /backup restore <backup> <target> - Restore from backup")

    def _handle_model_unavailable_error(self, model_name: str, error: Exception):
        """モデル利用不可エラーを役立つ提案とともに処理"""
        available_providers = self.config.get_available_providers()
        available_models = self.config.get_available_models_for_providers()
        
        print(f"モデル '{model_name}' は利用できません")
        
        if not available_providers:
            print("APIプロバイダーが設定されていません")
            print("OPENAI_API_KEYまたはANTHROPIC_API_KEYを設定してください")
            return
        
        if "anthropic" in str(error).lower() and "anthropic" not in available_providers:
            print()
            print("これはClaudeモデルですが、Anthropic APIキーが設定されていません")
            print("Claudeモデルを使用するには:")
            print("  1. .envファイルにANTHROPIC_API_KEY=your_key_hereを追加")
            print("  2. またはコマンドで: export ANTHROPIC_API_KEY=your_key_here")
        
        elif "openai" in str(error).lower() and "openai" not in available_providers:
            print()
            print("これはGPTモデルですが、OpenAI APIキーが設定されていません")
            print("GPTモデルを使用するには:")
            print("  1. .envファイルにOPENAI_API_KEY=your_key_hereを追加")
            print("  2. またはコマンドで: export OPENAI_API_KEY=your_key_here")
        
        if available_models:
            print()
            print("現在のAPIキーで利用可能なモデル:")
            for model in available_models[:5]:
                provider = "Claude" if "claude" in model else "GPT" if "gpt" in model else "不明"
                print(f"  • {model} ({provider})")
            
            if len(available_models) > 5:
                print(f"  ... その他{len(available_models) - 5}個")
            
            print()
            print(f"試してください: /model {available_models[0]}")

    # cmd_model メソッドを置き換え
    def cmd_model(self, args: List[str]):
        """Switch model or show current with better error handling"""
        if not args:
            current = self.llm_manager.current_model
            available_models = self.config.get_available_models_for_providers()
            available_providers = self.config.get_available_providers()
            
            print(f"現在のモデル: {current}")
            print(f"利用可能プロバイダー: {', '.join(available_providers) if available_providers else 'なし'}")
            
            if available_models:
                print(f"利用可能なモデル ({len(available_models)}個):")
                by_provider = {}
                for model in available_models:
                    provider = "anthropic" if "claude" in model else "openai" if "gpt" in model else "other"
                    if provider not in by_provider:
                        by_provider[provider] = []
                    by_provider[provider].append(model)
                
                for provider, models in by_provider.items():
                    print(f"  {provider.upper()} ({len(models)}個のモデル):")
                    for model in models:
                        marker = " ← 現在使用中" if model == current else ""
                        print(f"    • {model}{marker}")
            else:
                print("利用可能なモデルがありません - APIキーの設定を確認してください")
            
            return
        
        # Switch to specified model
        model_name = args[0]
        available_models = self.config.get_available_models_for_providers()
        
        if not available_models:
            print("利用可能なモデルがありません")
            print("OPENAI_API_KEYまたはANTHROPIC_API_KEYを設定してください")
            return
        
        # Check for exact match
        if model_name in available_models:
            target_model = model_name
        else:
            # Try partial matching
            partial_matches = [m for m in available_models if model_name.lower() in m.lower()]
            
            if len(partial_matches) == 1:
                target_model = partial_matches[0]
                print(f"部分一致を使用: {model_name} → {target_model}")
            elif len(partial_matches) > 1:
                print(f"'{model_name}'に対して複数の一致:")
                for match in partial_matches:
                    print(f"  • {match}")
                print("より具体的に指定してください")
                return
            else:
                print(f"モデル '{model_name}' が見つかりません")
                print("利用可能なモデル:")
                for model in available_models[:5]:
                    print(f"  • {model}")
                return
        
        try:
            # Switch model
            self.llm_manager.set_model(target_model)
            print(f"切り替えました: {target_model}")
            
            # Update config
            self.config.set("model", target_model)
            
        except Exception as e:
            self._handle_model_unavailable_error(target_model, e)   
    
    def cmd_export(self, args: List[str]):
        """Export memory or configuration"""
        if not args:
            print("Usage: /export <memory|config> [file]")
            return
        
        export_type = args[0].lower()
        export_file = args[1] if len(args) > 1 else None
        
        if export_type == "memory":
            if not export_file:
                export_file = f"claude_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            try:
                self.memory.export_memory(export_file, format="json")
                print(f"✅ Memory exported to: {export_file}")
            except Exception as e:
                print(f"❌ Export failed: {e}")
        
        elif export_type == "config":
            if not export_file:
                export_file = f"claude_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            try:
                self.config.export_config(export_file)
                print(f"✅ Configuration exported to: {export_file}")
            except Exception as e:
                print(f"❌ Export failed: {e}")
        
        else:
            print("❌ Unknown export type. Use 'memory' or 'config'")
    
    def cmd_import(self, args: List[str]):
        """Import memory or configuration"""
        if len(args) < 2:
            print("Usage: /import <memory|config> <file>")
            return
        
        import_type, import_file = args[0].lower(), args[1]
        
        if not Path(import_file).exists():
            print(f"❌ File not found: {import_file}")
            return
        
        if import_type == "memory":
            try:
                count = self.memory.import_memory(import_file)
                print(f"✅ Imported {count} memory entries from: {import_file}")
            except Exception as e:
                print(f"❌ Import failed: {e}")
        
        elif import_type == "config":
            try:
                self.config.import_config(import_file, merge=True)
                print(f"✅ Configuration imported from: {import_file}")
                
                # Reinitialize LLM manager with new config
                self.llm_manager = LLMManager(self.config.get_effective_config())
                self.code_assistant = CodeAssistant(self.llm_manager)
                
            except Exception as e:
                print(f"❌ Import failed: {e}")
        
        else:
            print("❌ Unknown import type. Use 'memory' or 'config'")
    
    def do_exit(self, args):
        """Exit the application"""
        print("\n✨ Session saved! See you again! 👋")
        return True
    
    def do_quit(self, args):
        """Exit the application"""
        print("\n✨ Session saved! See you again! 👋")
        return True
    
    def do_EOF(self, args):
        """Handle Ctrl+D"""
        print("\n✨ Session saved! See you again! 👋")
        return True
    
    def cmd_save_session(self, args: List[str]):
        """Save current session with name"""
        if not args:
            print("Usage: /save-session <name>")
            return
        
        # Validate session name
        try:
            from .error_handling import validate_session_name
            session_name = " ".join(args)
            session_name = validate_session_name(session_name)
            
            if self.session_manager.save_session(session_name):
                print(f"✅ Session saved as: {session_name}")
            else:
                print(f"❌ Failed to save session: {session_name}")
                
        except Exception as e:
            self.error_handler.handle_error(e, "session name validation")
    
    # cli.py の cmd_resume メソッドを以下に置き換え

    def cmd_resume(self, args: List[str]):
        """Resume named session"""
        if not args:
            print("Usage: /resume <name>")
            print("Available sessions:")
            self.cmd_list_sessions([])
            return
        
        session_name = " ".join(args)
        if self.session_manager.resume_session(session_name):
            print(f"✅ Resumed session: {session_name}")
            
            # ワークフロー状態を復元（新機能）
            if (self.session_manager.current_session and 
                self.session_manager.current_session.workflow_state):
                self.workflow_state = self.session_manager.current_session.workflow_state
                print("🔄 Workflow state restored!")
                
                # ワークフロー状態を表示
                if self.workflow_state.get("current_goal"):
                    print(f"   Goal: {self.workflow_state['current_goal']}")
                    think_done = "✅" if self.workflow_state.get("think_result") else "⏳"
                    plan_done = "✅" if self.workflow_state.get("plan_result") else "⏳"
                    print(f"   Progress: {think_done} Think → {plan_done} Plan → ⏳ Write")
            
            self._display_session_summary()
        else:
            print(f"❌ Failed to resume session: {session_name}")
    
    def cmd_list_sessions(self, args: List[str]):
        """List all saved sessions"""
        sessions = self.session_manager.list_sessions()
        
        if not sessions:
            print("📋 No saved sessions found")
            return
        
        print("📋 Available sessions:")
        print()
        
        # Sort sessions by last updated
        sorted_sessions = sorted(
            sessions.items(),
            key=lambda x: x[1]['last_updated'],
            reverse=True
        )
        
        for name, info in sorted_sessions:
            status = "🔄 (autosave)" if name == "autosave" else "💾"
            print(f"{status} {name}")
            print(f"   Created: {info['created_at'][:19]}")
            print(f"   Updated: {info['last_updated'][:19]}")
            print(f"   Entries: {info['entries']}")
            print(f"   Model: {info['model']}")
            print(f"   Directory: {info['directory']}")
            print()
    
    def cmd_session_info(self, args: List[str]):
        """Show current session information"""
        stats = self.session_manager.get_session_stats()
        
        if not stats:
            print("📋 No active session")
            return
        
        print("📊 Current Session Info:")
        print(f"   Session ID: {stats['session_id']}")
        print(f"   Created: {stats['created_at'][:19]}")
        print(f"   Updated: {stats['last_updated'][:19]}")
        print(f"   Entries: {stats['total_entries']}")
        print(f"   Current model: {stats['current_model']}")
        print(f"   Directory: {stats['current_directory']}")
        
        if 'models_used' in stats and stats['models_used']:
            print("\n   Models used:")
            for model, count in stats['models_used'].items():
                print(f"     {model}: {count} times")
        
        if 'command_types' in stats and stats['command_types']:
            print("\n   Commands used:")
            for cmd, count in stats['command_types'].items():
                print(f"     {cmd}: {count} times")
        
        if 'unique_files' in stats and stats['unique_files'] > 0:
            print(f"\n   Files touched: {stats['unique_files']}")
            if 'files_touched' in stats:
                for file in stats['files_touched'][:5]:  # Show first 5 files
                    print(f"     {file}")
                if len(stats['files_touched']) > 5:
                    print(f"     ... and {len(stats['files_touched']) - 5} more")
    
    def cmd_delete_session(self, args: List[str]):
        """Delete a saved session"""
        if not args:
            print("Usage: /delete-session <name>")
            return
        
        session_name = " ".join(args)
        
        if session_name == "autosave":
            confirm = input("Are you sure you want to delete the autosave? [y/N]: ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("Cancelled")
                return
        
        if self.session_manager.delete_session(session_name):
            print(f"✅ Session deleted: {session_name}")
        else:
            print(f"❌ Failed to delete session: {session_name}")
    
    def cmd_export_session(self, args: List[str]):
        """Export session to file"""
        if len(args) < 2:
            print("Usage: /export-session <session_name> <export_path> [format]")
            print("Formats: json (default), markdown")
            return
        
        session_name = args[0]
        export_path = args[1]
        format_type = args[2] if len(args) > 2 else "json"
        
        if self.session_manager.export_session(session_name, export_path, format_type):
            print(f"✅ Session exported to: {export_path}")
        else:
            print(f"❌ Failed to export session: {session_name}")
    
    def cmd_think(self, args: List[str]):
        """Analyze problem with AI (Step 1 of think→plan→write workflow)"""
        
        # Validate goal input
        if args:
            # コマンドライン引数から取得
            goal = " ".join(args).strip()
        else:
            # 修正: 複数行入力対応
            goal = self.get_input_with_options(
                "What would you like me to think about?",
                allow_empty=False
            )
        
        if not goal or len(goal) < 5:
            print("❌ Goal description must be at least 5 characters long")
            return
        
        if len(goal) > 2000:  # 複数行対応で制限を緩和
            print("❌ Goal description is too long (max 2000 characters)")
            return
        
        # 🔧 新機能: 制約検出
        constraints = self._detect_constraints(goal)
        
        # 制約が検出された場合、ユーザーに確認
        if constraints["is_brief"]:
            constraint_info = []
            if constraints["word_limit"]:
                constraint_info.append(f"{constraints['word_limit']} words max")
            if constraints["bullet_limit"]:
                constraint_info.append(f"{constraints['bullet_limit']} bullet points")
            if constraints["sentence_limit"]:
                constraint_info.append(f"{constraints['sentence_limit']} sentences")
            if constraints["format_type"]:
                constraint_info.append(f"{constraints['format_type']} format")
            
            if constraint_info:
                print(f"🎯 Detected constraints: {', '.join(constraint_info)}")
        
        self.workflow_state["current_goal"] = goal
        
        print(f"🤔 Thinking about: {goal}")
        print("=" * 50)
        
        # 🔧 新機能: 制約に基づくプロンプト生成
        try:
            think_prompt, system_prompt = self._generate_constraint_prompt(goal, constraints)
        except Exception as e:
            self.error_handler.handle_error(e, "constraint-based prompt generation")
            return
        
        try:
            response = self.llm_manager.generate_response(
                prompt=think_prompt,
                system_prompt=system_prompt
            )
            
            self._display_command_result(response.content, "think")
            
            # 制約検証（オプション）
            if constraints["word_limit"]:
                word_count = len(response.content.split())
                if word_count > constraints["word_limit"] * 1.2:  # 20%余裕
                    print(f"⚠️ Response may exceed word limit ({word_count} words)")
            
            # Store result for next step
            self.workflow_state["think_result"] = response.content
            
            # Store in memory and session
            self.memory.add_entry(
                user_prompt=f"Think: {goal}",
                claude_reply=response.content,
                model_used=self.llm_manager.current_model,
                metadata={
                    "workflow_step": "think", 
                    "goal": goal,
                    "constraints": constraints
                }
            )
            
            self.session_manager.add_entry(
                user_input=f"Think: {goal}",
                ai_response=response.content,
                model_used=self.llm_manager.current_model,
                command_type="think",
                metadata={
                    "workflow_step": "think",
                    "goal": goal,
                    "constraints": constraints
                },
                workflow_state=self.workflow_state.copy()  # ← 追加
            )
            
            print(f"\n✅ Analysis complete! Next step: /plan")
            
        except Exception as e:
            print(f"Error during thinking: {e}")
    
    def cmd_plan(self, args: List[str]):
        """Create implementation plan (Step 2 of think→plan→write workflow)"""
        if not self.workflow_state["think_result"]:
            print("❌ No analysis found. Please run /think <goal> first.")
            return
        
        goal = self.workflow_state["current_goal"]
        think_result = self.workflow_state["think_result"]
        
        # 🔧 新機能: goalから制約を再検出
        constraints = self._detect_constraints(goal)
        
        # 制約が検出された場合、ユーザーに確認
        if constraints["is_brief"]:
            constraint_info = []
            if constraints["word_limit"]:
                constraint_info.append(f"{constraints['word_limit']} words max")
            if constraints["bullet_limit"]:
                constraint_info.append(f"{constraints['bullet_limit']} bullet points")
            if constraints["sentence_limit"]:
                constraint_info.append(f"{constraints['sentence_limit']} sentences")
            if constraints["format_type"]:
                constraint_info.append(f"{constraints['format_type']} format")
            
            if constraint_info:
                print(f"🎯 Applying constraints to plan: {', '.join(constraint_info)}")
        
        print(f"📋 Planning implementation for: {goal}")
        print("=" * 50)
        
        # 🔧 新機能: 制約に基づくプロンプト生成（planバージョン）
        try:
            if constraints["is_brief"]:
                plan_prompt, system_prompt = self._generate_plan_constraint_prompt(goal, think_result, constraints)
            else:
                # 従来のプロンプトテンプレートを使用
                prompt_data = prompt_manager.render_prompt(
                    "implementation_plan",
                    {
                        "goal": goal,
                        "analysis": think_result
                    }
                )
                
                if not prompt_data:
                    raise CognixError("Failed to generate plan prompt template")
                
                plan_prompt = prompt_data["prompt"]
                system_prompt = prompt_data["system_prompt"]
                
        except Exception as e:
            self.error_handler.handle_error(e, "plan prompt generation")
            return
        
        try:
            response = self.llm_manager.generate_response(
                prompt=plan_prompt,
                system_prompt=system_prompt
            )
            
            self._display_command_result(response.content, "plan")
            
            # Store result for next step
            self.workflow_state["plan_result"] = response.content
            
            # Store in memory and session
            self.memory.add_entry(
                user_prompt=f"Plan: {goal}",
                claude_reply=response.content,
                model_used=self.llm_manager.current_model,
                metadata={
                    "workflow_step": "plan", 
                    "goal": goal,
                    "constraints": constraints
                }
            )
            
            self.session_manager.add_entry(
                user_input=f"Plan: {goal}",
                ai_response=response.content,
                model_used=self.llm_manager.current_model,
                command_type="plan",
                metadata={
                    "workflow_step": "plan",
                    "goal": goal,
                    "has_analysis": True,
                    "constraints": constraints
                },
                workflow_state=self.workflow_state.copy()  # ← 追加
            )
            
            print(f"\n✅ Plan created! Next step: /write")
            
        except Exception as e:
            print(f"Error during planning: {e}")
        
    def cmd_write(self, args: List[str]):
            """Generate code from plan (Step 3 of think→plan→write workflow)"""
            if not self.workflow_state["plan_result"]:
                print("❌ No implementation plan found. Please run /think and /plan first.")
                return
            
            # Parse arguments for specific step or file
            target_step = None
            target_file = None
            auto_apply = self.auto_mode
            
            i = 0
            while i < len(args):
                if args[i] == "--step" and i + 1 < len(args):
                    target_step = args[i + 1]
                    i += 2
                elif args[i] == "--file" and i + 1 < len(args):
                    target_file = args[i + 1]
                    i += 2
                elif args[i] == "--auto":
                    auto_apply = True
                    i += 1
                else:
                    i += 1
            
            goal = self.workflow_state["current_goal"]
            think_result = self.workflow_state["think_result"]
            plan_result = self.workflow_state["plan_result"]
            
            # 🔧 新機能: goalから制約を再検出
            constraints = self._detect_constraints(goal)
            
            # 制約が検出された場合、ユーザーに確認
            if constraints["is_brief"]:
                constraint_info = []
                if constraints["word_limit"]:
                    constraint_info.append(f"{constraints['word_limit']} words max")
                if constraints["bullet_limit"]:
                    constraint_info.append(f"{constraints['bullet_limit']} sections")
                if constraints["sentence_limit"]:
                    constraint_info.append(f"{constraints['sentence_limit']} functions")
                if constraints["format_type"]:
                    constraint_info.append(f"{constraints['format_type']} format")
                
                if constraint_info:
                    print(f"🎯 Applying constraints to code: {', '.join(constraint_info)}")
            
            print(f"✍️  Writing implementation for: {goal}")
            if target_step:
                print(f"   Focused on step: {target_step}")
            if target_file:
                print(f"   Target file: {target_file}")
            print("=" * 50)
            
            # ファイル拡張子から言語を推定
            target_language = "python"  # デフォルト
            if target_file:
                file_extension = Path(target_file).suffix.lower()
                language_map = {
                    '.js': 'javascript',
                    '.ts': 'typescript', 
                    '.py': 'python',
                    '.java': 'java',
                    '.cpp': 'cpp',
                    '.c': 'c',
                    '.cs': 'csharp',
                    '.go': 'go',
                    '.rs': 'rust',
                    '.php': 'php',
                    '.rb': 'ruby',
                    '.swift': 'swift',
                    '.kt': 'kotlin'
                }
                target_language = language_map.get(file_extension, 'python')
                print(f"   Target language: {target_language} (from {file_extension})")
            
            # 🔧 新機能: 制約に基づくプロンプト生成
            try:
                if constraints["is_brief"]:
                    write_prompt, system_prompt = self._generate_write_constraint_prompt(
                        goal, think_result, plan_result, constraints, target_language, target_file
                    )
                else:
                    # 従来のプロンプトテンプレートを使用
                    additional_context = ""
                    if target_step:
                        additional_context += f"\nFocus specifically on implementing: {target_step}"
                    if target_file:
                        additional_context += f"\nGenerate code for file: {target_file}"
                        additional_context += f"\nIMPORTANT: Write the code in {target_language} programming language only."
                        additional_context += f"\nThe file extension is {Path(target_file).suffix}, so use {target_language} syntax and conventions."
                    
                    prompt_data = prompt_manager.render_prompt(
                        "code_generation",
                        {
                            "goal": goal,
                            "analysis": think_result,
                            "plan": plan_result,
                            "additional_context": additional_context,
                            "target_language": target_language,
                            "target_file": target_file
                        }
                    )
                    
                    if not prompt_data:
                        raise CognixError("Failed to generate code generation prompt template")
                    
                    write_prompt = prompt_data["prompt"]
                    system_prompt = prompt_data["system_prompt"]
                    
                    # システムプロンプトにも言語指定を追加
                    if target_file:
                        system_prompt += f"\n\nIMPORTANT: You must generate code in {target_language} programming language only. "
                        system_prompt += f"The user specified {target_file} which requires {target_language} code. "
                        system_prompt += f"Do not use any other programming language."
                
            except Exception as e:
                self.error_handler.handle_error(e, "write prompt generation")
                return
            
            try:
                response = self.llm_manager.generate_response(
                    prompt=write_prompt,
                    system_prompt=system_prompt
                )
                
                self._display_command_result(response.content, "write")
                
                # Store in memory and session
                self.memory.add_entry(
                    user_prompt=f"Write: {goal}" + (f" (step: {target_step})" if target_step else "") + (f" (file: {target_file})" if target_file else ""),
                    claude_reply=response.content,
                    model_used=self.llm_manager.current_model,
                    metadata={
                        "workflow_step": "write",
                        "goal": goal,
                        "target_step": target_step,
                        "target_file": target_file,
                        "target_language": target_language,
                        "constraints": constraints
                    }
                )
                
                self.session_manager.add_entry(
                    user_input=f"Write: {goal}" + (f" (step: {target_step})" if target_step else "") + (f" (file: {target_file})" if target_file else ""),
                    ai_response=response.content,
                    model_used=self.llm_manager.current_model,
                    command_type="write",
                    target_files=[target_file] if target_file else [],
                    metadata={
                        "workflow_step": "write",
                        "goal": goal,
                        "target_step": target_step,
                        "target_file": target_file,
                        "target_language": target_language,
                        "has_analysis": True,
                        "has_plan": True,
                        "constraints": constraints
                    },
                    workflow_state=self.workflow_state.copy()  # ← 追加
                )
                
                # Ask if user wants to save code to files
                if target_file and self._confirm_action(f"Save generated code to {target_file}?", auto_apply):
                    try:
                        # Extract code from response (simple implementation)
                        code_content = response.content
                        
                        # Try to extract code blocks
                        if "```" in code_content:
                            lines = code_content.split('\n')
                            in_code_block = False
                            code_lines = []
                            
                            for line in lines:
                                if line.strip().startswith('```'):
                                    in_code_block = not in_code_block
                                    continue
                                if in_code_block:
                                    code_lines.append(line)
                            
                            if code_lines:
                                code_content = '\n'.join(code_lines)
                        
                        # Save to file
                        file_path = Path.cwd() / target_file
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Create backup if file exists
                        if file_path.exists() and self.config.get("auto_backup", True):
                            backup_result = self.diff_engine.create_backup(str(file_path))
                            if backup_result.success and backup_result.backup_path:
                                print(f"Backup created: {backup_result.backup_path}")
                        
                        file_path.write_text(code_content, encoding='utf-8')
                        print(f"✅ Code saved to: {target_file}")
                        
                    except Exception as e:
                        print(f"❌ Failed to save code: {e}")
                
                print(f"\n✅ Implementation complete!")
                print("   You can run /think again with a new goal to start a new workflow.")
                
            except Exception as e:
                print(f"Error during writing: {e}")
        
    def cmd_workflow_status(self, args: List[str]):
        """Show current workflow status"""
        print("🔄 Workflow Status:")
        print("=" * 30)
        
        if self.workflow_state["current_goal"]:
            print(f"Current Goal: {self.workflow_state['current_goal']}")
        else:
            print("No active workflow")
            return
        
        steps = [
            ("Think", self.workflow_state["think_result"]),
            ("Plan", self.workflow_state["plan_result"]),
            ("Write", None)  # Write doesn't store state
        ]
        
        for i, (step_name, result) in enumerate(steps, 1):
            if result is not None:
                print(f"  ✅ {i}. {step_name} - Complete")
            else:
                print(f"  ⏳ {i}. {step_name} - Pending")
        
        if all(result is not None for _, result in steps[:2]):
            print("\n💡 Ready for /write - Generate implementation")
        elif self.workflow_state["think_result"]:
            print("\n💡 Next step: /plan - Create implementation plan")
        else:
            print("\n💡 Start with: /think <your_goal>")
    
    def cmd_clear_workflow(self, args: List[str]):
        """Clear current workflow state"""
        if self.workflow_state["current_goal"]:
            if self._confirm_action("Clear current workflow state?"):
                # 1. メモリ内のワークフロー状態をクリア
                self.workflow_state = {
                    "think_result": None,
                    "plan_result": None,
                    "current_goal": None
                }
                
                # 2. セッションからもワークフロー状態を完全削除
                if self.session_manager.current_session:
                    self.session_manager.current_session.workflow_state = None
                    
                    # 3. 強制的に即座に保存
                    try:
                        self.session_manager.autosave()
                        print("✅ Workflow state cleared and saved")
                    except Exception as e:
                        print(f"⚠️ Workflow cleared but save failed: {e}")
                        # 手動でファイルを強制更新
                        try:
                            self.session_manager._save_session_to_file(
                                self.session_manager.current_session, 
                                self.session_manager.autosave_path
                            )
                            print("🔧 Forced manual save completed")
                        except Exception as manual_e:
                            print(f"❌ Manual save also failed: {manual_e}")
                else:
                    print("✅ Workflow state cleared")
            else:
                print("Workflow state preserved")
        else:
            print("No active workflow to clear")

# cognix/cli.py の最後に以下のエントリーポイントを追加

def main():
    """
    Main entry point for the cognix CLI command.
    """
    import sys
    try:
        # Configオブジェクトを作成（デフォルト設定で）
        from cognix.config import Config
        config = Config()
        
        # CLIインスタンスを作成
        cli = CognixCLI(config)
        
        # 引数がある場合は直接コマンド実行、なければ対話モード
        if len(sys.argv) > 1:
            # コマンドライン引数を処理
            command_line = ' '.join(sys.argv[1:])
            cli.onecmd(command_line)
        else:
            # 対話モードで起動
            cli.cmdloop()
            
    except KeyboardInterrupt:
        print("\n🔸 Cognix interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Cognix error: {e}")
        # デバッグ情報表示
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()