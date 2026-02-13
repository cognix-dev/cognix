"""
CLI ユーティリティモジュール

このモジュールは、様々なユーティリティコマンドと補助機能を提供します。
具体的には以下の機能を含みます：

1. 状態表示 (status)
2. モデル切り替え (model)
3. ヘルプ表示 (help)
4. その他のユーティリティコマンド
"""

import os
import sys
import json
import shutil
import platform
from typing import Dict, List, Set, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime

# 必須依存
from cognix.cli_shared import CLIModuleBase
from cognix.prompt_templates import prompt_manager
from cognix.ui import StatusIndicator  # Phase 1: UI改善
from cognix.logger import err_console
from cognix.theme_zen import GREEN, RESET  # ANSI色コード
from rich.text import Text  # ANSIエスケープシーケンス表示用

# Phase 5: 相対時間表示関数
try:
    from cognix.session import format_relative_time, format_duration
except ImportError:
    # フォールバック: 関数が見つからない場合は単純な文字列を返す
    def format_relative_time(timestamp_str):
        return str(timestamp_str)
    def format_duration(seconds):
        return f"{int(seconds)}s"

class UtilitiesModule(CLIModuleBase):
    """ユーティリティ機能モジュール
    
    状態表示、モデル切り替え、ヘルプ表示などの機能を提供します。
    """
    
    def __init__(self):
        """基本初期化 - 引数なし
        
        依存オブジェクトはset_dependenciesで後から設定します
        """
        # 親クラスの初期化 - 引数なしで呼び出し
        super().__init__()
        
        # このモジュール固有の初期化
        # (依存オブジェクトに依存しない初期化のみ)
    
    def cmd_status(self, args):
        """Display current status
        
        Args:
            args: Command arguments (optional)
        """
        try:
            # 詳細レベルの取得
            verbose = False
            if args:
                args_str = args.strip() if isinstance(args, str) else " ".join(args).strip()
                if args_str == "-v" or args_str == "--verbose":
                    verbose = True
            
            # 基本的なシステム情報
            err_console.print("\n📊 System Status:")
            err_console.print(f"Python: {sys.version.split()[0]}")
            err_console.print(f"Platform: {platform.platform()}")
            err_console.print(f"Working Directory: {os.getcwd()}")
            
            # Cognixの状態
            err_console.print("\n📋 Cognix Status:")
            
            if hasattr(self.config, 'config_path'):
                err_console.print(f"Config File: {self.config.config_path}")
            elif hasattr(self.config, 'config_file'):
                err_console.print(f"Config File: {self.config.config_file}")
            else:
                # フォールバック: 標準的な設定ファイルパスを表示
                config_path = Path.home() / ".cognix" / "config.json"
                err_console.print(f"Config File: {config_path}")
            
            if hasattr(self, 'llm_manager') and self.llm_manager:
                err_console.print(f"Current Model: {self.llm_manager.current_model}")
                err_console.print(f"Available Models: {', '.join(self.llm_manager.get_available_models())}")
            
            if hasattr(self, 'context') and self.context:
                err_console.print(f"Project Root: {self.context.root_dir}")
            
            # 詳細情報(verboseモード時のみ)
            if verbose:
                err_console.print("\n🔍 Detailed Information:")
                
                if hasattr(self, 'memory') and self.memory:
                    err_console.print(f"Memory Entries: {len(self.memory.get_entries(100))}")
                
                if hasattr(self, 'session_manager') and self.session_manager:
                    stats = self.session_manager.get_session_stats()
                    if stats:
                        err_console.print(f"Session Entries: {stats.get('total_entries', 0)}")
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "status command")
            else:
                err_console.print(f"Error in status command: {e}")
    
    def cmd_model(self, args):
        """Switch or display model
        
        Args:
            args: Model name or options
        """
        try:
            if not hasattr(self, 'llm_manager') or not self.llm_manager:
                err_console.print("Error: LLM Manager not available")
                return
            
            # 引数がない場合は現在のモデルを表示
            if not args or (isinstance(args, list) and len(args) == 0):
                current = self.llm_manager.current_model
                
                # 現在のモデルの情報を取得
                if hasattr(self, 'config') and self.config:
                    current_display = self.config.get_model_display_name(current)
                    models_info = self.config.get("models", {})
                    current_provider = models_info.get(current, {}).get("provider", "unknown")
                    
                    # provider別にグループ化
                    models_by_provider = self.config.get_models_by_provider_with_display()
                    
                    # 新しいフォーマットで表示
                    err_console.print(Text.from_ansi(f"\n{GREEN}Current Model:{RESET}"))
                    err_console.print(f"    {current_provider}: {current_display}")
                    err_console.print(Text.from_ansi(f"\n{GREEN}Available Models:{RESET}"))
                    
                    for provider in sorted(models_by_provider.keys()):
                        models = models_by_provider[provider]
                        display_names = [display_name for _, display_name in models]
                        models_str = ', '.join(display_names)
                        err_console.print(f"    {provider}: {models_str}")
                    
                    # プロンプトとの間に空行を追加
                    err_console.print()
                else:
                    # フォールバック: 従来の表示
                    available = self.llm_manager.get_available_models()
                    err_console.print(f"\nCurrent Model: {current}")
                    err_console.print(f"Available Models: {', '.join(available)}")
                    err_console.print()  # プロンプトとの間に空行を追加
                
                return
            
            # 引数を文字列化
            model_name = args.strip() if isinstance(args, str) else " ".join(args).strip()
            
            # モデル名を解決（短縮名または完全名を受け付ける）
            if hasattr(self, 'config') and self.config:
                resolved_name = self.config.resolve_model_name(model_name)
                if not resolved_name:
                    err_console.print(f"Error: Model '{model_name}' not found")
                    err_console.print("Use '/model' to see available models")
                    return
                model_name = resolved_name
            
            # モデルの切り替え
            try:
                self.llm_manager.set_model(model_name)
                
                # 表示名を取得
                if hasattr(self, 'config') and self.config:
                    display_name = self.config.get_model_display_name(model_name)
                    err_console.print(f"✓ Switched to model: {display_name}")
                    err_console.print()
                else:
                    err_console.print(f"✓ Switched to model: {model_name}")
                    err_console.print()
                
                # 設定に保存
                if hasattr(self, 'config') and self.config:
                    self.config.set('model', model_name)
                
                # Phase 2: プロンプトを更新
                if hasattr(self, '_cli_instance') and hasattr(self._cli_instance, '_get_prompt_with_model'):
                    self._cli_instance.prompt = self._cli_instance._get_prompt_with_model()
                    
            except Exception as e:
                err_console.print(StatusIndicator.error(f"Failed to switch model: {e}"))
                err_console.print(f"Available models: {', '.join(self.llm_manager.get_available_models())}")

                
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "model command")
            else:
                err_console.print(f"Error in model command: {e}")
    
    def cmd_help(self, args):
        """Display help information
        
        Args:
            args: Specific command name (optional)
        """
        try:
            # コマンドマップの取得
            command_map = {}
            if hasattr(self, '_cli_instance') and hasattr(self._cli_instance, 'command_map'):
                command_map = self._cli_instance.command_map
            
            # --allオプションのチェック
            show_all = False
            if args:
                args_str = args.strip() if isinstance(args, str) else " ".join(args).strip()
                if args_str == '--all':
                    show_all = True
                else:
                    # 特定のコマンドのヘルプ
                    self._show_command_help(args_str, command_map)
                    return
            
            # 全コマンドの一覧表示
            err_console.print("\nAvailable commands:")
            
            # ========================================
            # ⭐ デフォルト表示: 12個（よく使うコマンドのみ）
            # --all表示: 22個（全コマンド）
            # ========================================
            
            # AI driven development コマンド
            # デフォルト: /make, /review のみ
            # --all: 全コマンド表示
            workflow_default = [
                'make',             # 最重要（自動実装）
                'review',           # コードレビュー
            ]
            workflow_advanced = [
                'think',            # ワークフローStep 1（実験的）
                'plan',             # ワークフローStep 2（実験的）
                'write',            # ワークフローStep 3（実験的）
                'workflow-status',  # ワークフロー状態確認
                'clear-workflow',   # ワークフロークリア
                'fix',              # Fix/modify code（実験的）
                'edit',             # AI編集（実験的）
            ]
            
            # Repositoryコマンド
            repo_commands_default = [
                'repo-init',        # リポジトリ初期化
                'repo-stats',       # 統計情報（最重要）
            ]
            repo_commands_advanced = [
                'repo-status',      # 状態確認
                'repo-search',      # ファイル検索
                'repo-analyze',     # プロジェクト分析
                'repo-info',        # ファイル詳細情報
                'repo-clean',       # データクリア
                'repo-similar',     # 類似ファイル検索
                'repo-deps',        # 依存関係表示
            ]
            
            # 表示するコマンドを決定
            workflow_cmds = workflow_default + workflow_advanced if show_all else workflow_default
            repo_commands = repo_commands_default + repo_commands_advanced if show_all else repo_commands_default
            
            categories = {
                "AI driven development": workflow_cmds,
                "Repository": repo_commands,
                "Execution": [
                    'run'               # スクリプト実行
                ],
                "Utility": [
                    'status',
                    'model',
                    #'help',
                    #'usage',  # Phase 2: Token usage statistics
                    'exit',
                ],
            }
            
            # 各カテゴリの表示
            for category, commands in categories.items():
                err_console.print(f"\n{category}:")
                for cmd in commands:
                    if cmd in command_map:
                        doc = command_map[cmd].__doc__ or "No description"
                        # 最初の行のみ表示
                        short_doc = doc.split('\n')[0].strip()
                        err_console.print(f"  [bright_green]/{cmd}[/bright_green]{' ' * (18 - len(cmd))} - {short_doc}")
                    else:
                        err_console.print(f"  [bright_green]/{cmd}[/bright_green]{' ' * (18 - len(cmd))} - Not available")
            
            err_console.print(Text.from_ansi(f"\nFor more information on a specific command, type: {GREEN}/help <command>{RESET}"))
            
            # --allオプションの説明（デフォルト表示時のみ）
            if not show_all:
                err_console.print(Text.from_ansi(f"For all commands including advanced options, type: {GREEN}/help --all{RESET}"))
                err_console.print()
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "help command")
            else:
                err_console.print(f"Error in help command: {e}")
                # フォールバック：基本的なヘルプ
                self._show_basic_help()

    def cmd_usage(self, args):
            """Display token usage and session statistics
            
            Args:
                args: Command arguments (optional)
            
            Phase 2: /usageコマンド実装
            """
            try:
                # SessionManagerから統計を取得
                if not hasattr(self, 'session_manager') or not self.session_manager:
                    err_console.print(StatusIndicator.error("Session manager is not available."))
                    return
                
                # 統計情報を取得
                stats = self.session_manager.get_token_statistics()
                
                # ui.pyの表示関数を使用
                from cognix.ui import print_usage_statistics
                print_usage_statistics(stats)
                
            except Exception as e:
                if hasattr(self, 'error_handler') and self.error_handler:
                    self.error_handler.handle_error(e, "usage command")
                else:
                    err_console.print(StatusIndicator.error(f"An error occurred: {e}"))

    def cmd_clear(self, args):
        """Clear screen
        
        Args:
            args: Command arguments (unused)
        """
        try:
            # OSに応じたクリアコマンドの実行
            if platform.system() == "Windows":
                os.system("cls")
            else:
                os.system("clear")
            
            err_console.print("Screen cleared.")
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "clear command")
            else:
                err_console.print(f"Error in clear command: {e}")
    
    def cmd_memory(self, args):
        """Display memory contents
        
        Args:
            args: Command arguments (optional)
        """
        try:
            # メモリの取得
            if not hasattr(self, 'memory') or not self.memory:
                err_console.print("Error: Memory not available")
                return
            
            # 表示件数の取得
            limit = 5  # デフォルト
            if args:
                args_str = args.strip() if isinstance(args, str) else " ".join(args).strip()
                try:
                    if args_str.isdigit():
                        limit = int(args_str)
                except ValueError:
                    pass
            
            # メモリエントリの取得
            entries = self.memory.get_entries(limit)
            
            if not entries:
                err_console.print("No memory entries found.")
                return
            
            err_console.print(f"\n📋 Recent Memory Entries (last {len(entries)}):")
            
            for i, entry in enumerate(entries, 1):
                # エントリの基本情報
                timestamp = getattr(entry, 'timestamp', 'Unknown')
                user_prompt = getattr(entry, 'user_prompt', 'Unknown')
                model = getattr(entry, 'model_used', 'Unknown')
                
                # 短い要約の表示
                prompt_summary = user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt
                err_console.print(f"\n{i}. {timestamp}")
                err_console.print(f"   Model: {model}")
                err_console.print(f"   Prompt: {prompt_summary}")
                
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "memory command")
            else:
                err_console.print(f"Error in memory command: {e}")
    
    # =====================
    # ヘルパーメソッド群
    # =====================
    
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
        
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            first_run_marker.touch()
        except Exception as e:
            err_console.print(f"Warning: Could not mark first run as complete: {e}")

    def _generate_terminal_logo(self) -> str:
        """Generate terminal-style logo with dynamic information"""
        try:
            # Safe attribute access with defaults
            current_model = "Unknown"
            if hasattr(self, 'llm_manager') and self.llm_manager:
                current_model = getattr(self.llm_manager, 'current_model', 'Unknown')
            
            # ===== 修正: セッション状態の正確な判定 =====
            session_status = "new session"
            if hasattr(self, 'session_manager') and self.session_manager:
                try:
                    # 1. 現在のセッションがある場合（復元済み）
                    if hasattr(self.session_manager, 'current_session') and self.session_manager.current_session:
                        if hasattr(self.session_manager.current_session, 'name'):
                            session_name = self.session_manager.current_session.name
                            if session_name == "autosave":
                                session_status = "restored"
                            else:
                                session_status = f"restored ({session_name})"
                        else:
                            session_status = "restored"
                    # 2. オートセーブが利用可能（未復元）
                    elif hasattr(self.session_manager, 'has_autosave') and self.session_manager.has_autosave():
                        session_status = "auto-saved available"
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
            
            # バージョンを動的に取得
            try:
                from cognix import __version__
                version = __version__
            except:
                version = "0.2.2"
                
            # Box-style logo
            logo = f"""{CYAN}Cognix v{version}{RESET} // Augmented AI Development Partner for CLI{RESET}

{GREEN}┌───┬───┬───┬───┬───┬───┐
│ C │ O │ G │ N │ I │ X │
└───┴───┴───┴───┴───┴───┘{RESET}

{GRAY}Status:{RESET}
{GREEN}Model:{RESET} {current_model}
{GREEN}Session:{RESET} {session_status}
{GREEN}Memory:{RESET} {memory_persistent}

{GRAY}Core mechanism:{RESET}
Multi-Model Support | Persistent Sessions | Long-Term Memory  
Full-Pipeline Development | Seamless Terminal Experience

{GRAY}Made by Individual Developer | MIT License{RESET}"""
            
            return logo
            
        except Exception as e:
            # Fallback to simple logo if anything goes wrong
            return """Cognix v0.2.2 // Augmented AI Development Partner for CLI

┌───┬───┬───┬───┬───┬───┐
│ C │ O │ G │ N │ I │ X │
└───┴───┴───┴───┴───┴───┘

Multi-Model Support | Persistent Sessions | Long-Term Memory  
Full-Pipeline Development | Seamless Terminal Experience

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
        err_console.print("\n" + "🎉 Welcome to Cognix!")
        err_console.print("=" * 50)
        err_console.print("Let's get you set up quickly:")
        err_console.print()
        err_console.print("1. You need an API key from OpenAI or Anthropic")
        err_console.print("   • OpenAI: https://platform.openai.com/api-keys")
        err_console.print("   • Anthropic: https://console.anthropic.com/")
        err_console.print()
        err_console.print("2. Create a .env file:")
        
        env_path = Path.home() / ".cognix" / ".env"
        err_console.print(f"   File location: {env_path}")
        err_console.print()
        err_console.print("3. Add your API key to the .env file:")
        err_console.print("   ANTHROPIC_API_KEY=your_key_here")
        err_console.print("   # or")
        err_console.print("   OPENAI_API_KEY=your_key_here")
        err_console.print()
        
        # Offer to create .env file
        try:
            create_env = input("Would you like me to create a .env file template? [y/N]: ").strip().lower()
            if create_env in ['y', 'yes']:
                self._create_env_template()
        except (KeyboardInterrupt, EOFError):
            err_console.print("\nSkipping .env file creation.")
        
        err_console.print("\n4. Restart the application after adding your API key")
        err_console.print("=" * 50)
    
    def _create_env_template(self):
        """Create .env template file"""
        cognix_dir = Path.home() / ".cognix"
        cognix_dir.mkdir(parents=True, exist_ok=True)
        env_path = cognix_dir / ".env"
        
        if env_path.exists():
            err_console.print(f"✅ .env file already exists at {env_path}")
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
            err_console.print(f"✅ Created .env template at {env_path}")
            err_console.print("   Edit this file and uncomment/add your API key")
        except Exception as e:
            err_console.print(StatusIndicator.error(f"Failed to create .env file: {e}"))
    
    def _check_session_restoration(self):
        """Check for autosave and offer to restore (Phase 5: Table化)"""
        if not hasattr(self, 'session_manager') or not self.session_manager:
            return
            
        if not self.session_manager.has_autosave():
            return
        
        autosave_info = self.session_manager.get_autosave_info()
        if not autosave_info:
            return
        
        # Zen HUD: 最小表示に置換
        from cognix.ui_zen_integration import rule

        err_console.print(Text.from_ansi(f"\n☰  {GREEN}Previous Session{RESET}"))
        # 相対/絶対時間の準備は現行ロジックを流用
        relative_time = format_relative_time(autosave_info['last_updated'])
        absolute_time = autosave_info['last_updated'].split('T')[0] + ' ' + autosave_info['last_updated'].split('T')[1].split('.')[0]

        # 白色で表示（Richマークアップ使用・ラベル18文字幅（先頭4スペース含めて22文字）統一）
        err_console.print(f"[white]    {'Last Updated':<18}{absolute_time}[/white]")
        err_console.print(f"[white]    {'Entries':<18}{autosave_info['entries']} conversations[/white]")
        err_console.print(f"[white]    {'Model':<18}{autosave_info['model']}[/white]")
        err_console.print(f"[white]    {'Directory':<18}{autosave_info['directory']}[/white]")

        # 追加の統計があれば行追加（既存 stats 利用）
        stats = self.session_manager.get_session_stats()
        if stats:
            total_tokens = stats.get('total_tokens', 0)
            if total_tokens > 0:
                cost = stats.get('estimated_cost', 0.0)
                err_console.print(f"  Token Usage    {total_tokens:,} (~${cost:.2f})")
            duration = stats.get('total_duration', 0.0)
            if duration > 0:
                err_console.print(f"  Total Duration {format_duration(duration)}")

        # rule()はANSIコードを返すのでprint()で直接出力
        print("\n" + rule())

        try:
            restore = input("Would you like to restore the previous session? [y/N]: ").strip().lower()
            if restore in ['y', 'yes']:
                if self.session_manager.resume_session("autosave"):
                    # Phase 5: 成功メッセージをバナー表示（ANSI GREEN + Text.from_ansi()）
                    err_console.print(Text.from_ansi(f"{GREEN}✓ Session restored successfully!{RESET}"))
                    err_console.print()  # 改行追加
                    
                    # ワークフロー状態復元を追加
                    if (self.session_manager.current_session and 
                        self.session_manager.current_session.workflow_state):
                        if hasattr(self, 'shared_state') and self.shared_state:
                            self.shared_state.workflow_state = self.session_manager.current_session.workflow_state
                            err_console.print("▭ Workflow state restored!")
                            
                            # ワークフロー状態を表示
                            workflow_state = self.shared_state.workflow_state
                            if workflow_state and workflow_state.get("current_goal"):
                                err_console.print(f"   Goal: {workflow_state['current_goal']}")
                                think_done = "✅" if workflow_state.get("think_result") else "⏳"
                                plan_done = "✅" if workflow_state.get("plan_result") else "⏳"
                                err_console.print(f"   Progress: {think_done} Think → {plan_done} Plan → ⏳ Write")
                    
                    self._display_session_summary()
                else:
                    err_console.print(StatusIndicator.error("Failed to restore session"))
            else:
                # Ask if they want to keep the autosave
                keep = input("Keep the autosave for later? [Y/n]: ").strip().lower()
                if keep not in ['n', 'no']:
                    err_console.print("   (Autosave preserved - use '/resume autosave' to restore later)")
                else:
                    self.session_manager.clear_current_session()
                    err_console.print("   (Autosave cleared)")
        except (KeyboardInterrupt, EOFError):
            err_console.print("\n   (Skipping session restoration)")
    
    def _display_session_summary(self):
        """Display current session summary"""
        # ✅ Session Summary表示を無効化（ユーザー要望）
        # シンプルな復元成功メッセージのみで十分
        pass
    
    def _show_command_help(self, cmd_name: str, command_map: dict):
        """特定のコマンドの詳細ヘルプを表示
        
        Args:
            cmd_name: コマンド名
            command_map: コマンドマップ
        """
        # /make コマンドの場合は詳細ヘルプを表示
        if cmd_name == 'make':
            self._show_make_detailed_help()
            return
        
        if cmd_name in command_map:
            func = command_map[cmd_name]
            doc = func.__doc__ or "No documentation available"
            err_console.print(f"\nCommand: [bright_green]/{cmd_name}[/bright_green]")
            err_console.print(f"{doc}", highlight=False)
        else:
            err_console.print(f"\nCommand '[bright_green]/{cmd_name}[/bright_green]' not found")
            err_console.print("Use '[bright_green]/help[/bright_green]' to see all available commands")
    
    def _show_make_detailed_help(self):
        """Display detailed help for /make command"""
        
        err_console.print()
        # Command header (standard format)
        err_console.print("Command: [bright_green]/make[/bright_green]")
        err_console.print("Automatic implementation with AI assistance")
        err_console.print()
        
        # Args
        err_console.print("Args:")
        err_console.print("    args: Implementation goal (required)")
        err_console.print()
        
        # Tips (compact format)
        err_console.print("Tips:")
        err_console.print("  [white]/make[/white] [bright_green]@[/bright_green][white]spec.md[/white]               [dim]:[/dim] load spec file")
        err_console.print("  [white]/make[/white] [bright_green]\"\"\"[/bright_green][white]multi-line goal[/white][bright_green]\"\"\"[/bright_green]  [dim]:[/dim] multiline input")
        err_console.print("  [white]/make[/white] [white]\"...[/white] [bright_green]KEEP[/bright_green] [white]x.[/white] [bright_green]ONLY[/bright_green] [white]y.\"[/white]  [dim]:[/dim] constraint keywords")
        err_console.print()
        
        # Powered by
        err_console.print("Powered by:")
        err_console.print("  [dim]•[/dim] AlphaCodium Pipeline [dim]—[/dim] splits complex tasks into 3 phases")
        err_console.print("  [dim]•[/dim] 6 Analysis Engines [dim]—[/dim] integrates AST, dependency, impact, and quality")
        err_console.print("  [dim]•[/dim] LLM Structure Detection [dim]—[/dim] dynamically understands project structure")
        err_console.print("  [dim]•[/dim] 3-Layer Quality Gate [dim]—[/dim] lint, review, and consistency checks")
        err_console.print("  [dim]•[/dim] Auto-Rollback [dim]—[/dim] automatic recovery on failure")
        err_console.print("  [dim]•[/dim] Auto-Completion [dim]—[/dim] detects and generates missing files")
        err_console.print()
    
    def _show_basic_help(self):
        """基本的なヘルプを表示(フォールバック)"""
        err_console.print("\nBasic Commands:")
        err_console.print("  [bright_green]/help[/bright_green]           - Show this help")
        err_console.print("  [bright_green]/status[/bright_green]         - Show system status")
        err_console.print("  [bright_green]/model[/bright_green] <name>   - Switch model")
        err_console.print("  [bright_green]/exit[/bright_green]           - Exit application")
        err_console.print("  [bright_green]/quit[/bright_green]           - Exit application")