"""
CLI メインコントローラーモジュール - 堅牢化修正版

このモジュールは、CLIのメイン制御とコマンド振り分け機能を提供します。
初期化エラーハンドリングを強化し、AttributeErrorによるクラッシュを防ぎます。
"""

import os
import sys
import cmd
import traceback
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path

# 必須依存
from cognix.config import Config
from cognix.memory import Memory
from cognix.context import FileContext
from cognix.llm import LLMManager
from cognix.llm import CodeAssistant
from cognix.diff_engine import DiffEngine
from cognix.session import SessionManager
from cognix.error_handling import ErrorHandler, safe_execute
from cognix.run import RunCommand
from cognix.ui import StatusIndicator, show_startup_animation, tips_help_line

from cognix.logger import err_console

from cognix.theme_zen import GREEN, RESET  # Cognix統一色
from rich.text import Text  # ANSIカラーコード表示用
# 共有基盤
from cognix.cli_shared import CLISharedState

class CognixCLI(cmd.Cmd):
    """Cognix コマンドラインインターフェース
    
    メイン制御とコマンド振り分けを担当します。
    """
    
    def __init__(self, config: Config, auto_mode: bool = False):
        """CLIの初期化
        
        引数:
            config: 設定オブジェクト
            auto_mode: 自動モードフラグ
        """
        super().__init__()
        self.config = config
        
        # ===== APIキーに基づくモデル自動切り替え =====
        self.config.validate_config()
        
        self.auto_mode = auto_mode
        self._multiline_buffer = []
        self._empty_line_count = 0
        self._original_prompt = "cognix> "
        
        # ===== 1. 最初に共有状態を初期化 =====
        self.shared_state = CLISharedState()
        
        # 複数行入力状態の初期化
        self._multiline_buffer = []
        self._empty_line_count = 0
        self._original_prompt = "cognix> "
        
        # プロンプト設定
        self.prompt = self._original_prompt
        
        # 複数行入力モードフラグ
        self.multiline_mode = False
        self.multiline_buffer = []
        self._triple_quote_mode = False  # """モード用フラグ
        
        # /make """用の複数行入力フラグ
        self._make_multiline_mode = False
        self._make_buffer = []
        
        # 初回実行フラグを最初に設定（エラーが起きても属性は存在するように）
        self.is_first_run = False

        # ========================================
        # ⭐ 安全対策: モジュール変数とエラー情報の事前初期化
        # 初期化中にエラーが起きても AttributeError にならないようにする
        # ========================================
        self.chat_workflow = None
        self.file_operations = None
        self.repository = None
        self.utilities = None
        self.run_command = None
        self.command_map = {}  # ⭐ ここで空辞書として定義しておく
        self.init_error = None  # 初期化エラーを保持する変数
        
        try:
            # ========================================
            # ⭐ 必須依存の初期化 - EnhancedMemory優先（フェーズ3-タスク2）
            # ========================================
            
            # 1. EnhancedMemoryの優先使用
            try:
                from cognix.enhanced_memory import EnhancedMemory
                self.memory = EnhancedMemory()
                
                # リポジトリ機能を有効化
                if hasattr(self.memory, 'enable_repository_features'):
                    self.memory.enable_repository_features()
                
                # デバッグ情報（開発時のみ）
                if config.get('debug_mode', False):
                    err_console.print("✅ EnhancedMemory initialized successfully")
                    
            except ImportError as e:
                # フォールバック: 通常のMemoryを使用
                from cognix.memory import Memory
                self.memory = Memory()
                
                if config.get('debug_mode', False):
                    err_console.print(StatusIndicator.warning("EnhancedMemory not available, using standard Memory"))
                    err_console.print(f"   Reason: {e}")
                    
            except Exception as e:
                # その他のエラー: 通常のMemoryにフォールバック
                from cognix.memory import Memory
                self.memory = Memory()
                
                if config.get('debug_mode', False):
                    err_console.print(StatusIndicator.warning("EnhancedMemory initialization failed, using standard Memory"))
                    err_console.print(f"   Error: {e}")
            
            # 2. プロジェクトルートの検出
            project_root = self._find_reasonable_project_root()
            self.context = FileContext(root_dir=project_root)
            
            # 3. LLM関連の初期化
            self.llm_manager = LLMManager(config.get_effective_config())
            
            # 4. CodeAssistant初期化 - 正しい引数のみを渡す
            try:
                # 正しい引数のみで初期化
                self.code_assistant = CodeAssistant(self.llm_manager)
            except TypeError as e:
                err_console.print(f"Error initializing CodeAssistant: {e}")
                # パラメータを確認
                import inspect
                signature = inspect.signature(CodeAssistant.__init__)
                err_console.print(f"CodeAssistant constructor expects: {signature}")
                raise
            
            # その他のコンポーネント初期化
            self.diff_engine = DiffEngine()
            self.session_manager = SessionManager()
            self.error_handler = ErrorHandler(debug_mode=config.get('debug_mode', False))
            
            # ===== 重要: RunCommandの初期化 =====
            self.run_command = RunCommand(self)
            
            # オプション依存の初期化
            self._initialize_optional_dependencies()
            
            # 機能モジュールの初期化
            self._initialize_modules()
            
            # 初回実行チェックを試みる
            try:
                self.is_first_run = self._check_first_run_fallback()
            except:
                pass
                
        except Exception as e:
            # エラーをキャプチャし、init_errorに保存（run()で表示するため）
            import traceback
            self.init_error = traceback.format_exc()
            
            # 開発者向けデバッグ出力（念のためここでも出す）
            # err_console.print(f"Initialization Error caught: {e}")
        finally:
            # ⭐ 成功しても失敗しても、必ずコマンドマップを構築する
            # これにより、初期化に失敗しても help や exit コマンドが動作する
            self._build_command_map()
        
        # Phase 2: プロンプトにモデル名を表示
        self.prompt = self._get_prompt_with_model()
        
        # Phase 3: readline統合（コマンド履歴・Tab補完）
        self._setup_readline()

        # 初期プロンプトを統一（_original_prompt もモデル入りで保持）
        model_label = self.config.get('model', None)
        if model_label:
            # configから動的に表示名を取得
            display_name = self.config.get_model_display_name(model_label)
            self._original_prompt = f"[{display_name}] cognix> "
        else:
            self._original_prompt = "cognix> "
        self.prompt = self._original_prompt

    def _get_prompt_with_model(self) -> str:
        """モデル名を含むプロンプトを生成"""
        try:
            model = self.config.get('model', 'unknown')
            # configから動的に表示名を取得
            display_name = self.config.get_model_display_name(model)
            model_prefix = f"[{display_name}] "
            return f"{model_prefix}cognix> "
        except Exception:
            return "cognix> "

    def _setup_readline(self):
            """readlineの設定とコマンド履歴機能の初期化"""
            try:
                import readline
                import atexit
                from pathlib import Path
                
                config_dir = Path.home() / ".cognix"
                config_dir.mkdir(parents=True, exist_ok=True)
                histfile = config_dir / ".cognix_history"
                
                try:
                    readline.read_history_file(str(histfile))
                except FileNotFoundError:
                    pass
                
                readline.set_history_length(1000)
                if histfile.exists():
                    histfile.chmod(0o600)
                atexit.register(readline.write_history_file, str(histfile))
                
                readline.parse_and_bind("tab: complete")
                readline.set_completer(self._get_command_completer())
                
            except ImportError:
                if self.config.get('debug_mode', False):
                    err_console.print("Note: readline not available")
            except Exception as e:
                if self.config.get('debug_mode', False):
                    err_console.print(f"Warning: readline setup failed: {e}")

    def _get_command_completer(self):
            """Tab補完用のcompleter関数を返す"""
            def completer(text, state):
                if text.startswith('/'):
                    commands = ['/' + cmd for cmd in self.command_map.keys()]
                    matches = [cmd for cmd in commands if cmd.startswith(text)]
                    if state < len(matches):
                        return matches[state]
                return None
            return completer

    def _find_reasonable_project_root(self):
        """プロジェクトルートの検出"""
        current_dir = Path.cwd()
        markers = ['.git', 'setup.py', 'pyproject.toml', 'requirements.txt', 'package.json']
        
        for _ in range(10):
            for marker in markers:
                if (current_dir / marker).exists():
                    return str(current_dir)
            parent = current_dir.parent
            if parent == current_dir:
                break
            current_dir = parent
        return str(Path.cwd())
    
    def _initialize_optional_dependencies(self):
        """条件付き依存の安全な初期化"""
        
        # 1. 関連ファインダー
        try:
            from cognix.related_finder import BasicRelatedFinder
            self.related_finder = BasicRelatedFinder(self.context)
        except ImportError:
            self.related_finder = None
        
        # 2. RepositoryAnalyzer (ImpactAnalyzerより先)
        try:
            from cognix.repository_analyzer import RepositoryAnalyzer
            self.repository_analyzer = RepositoryAnalyzer(
                enhanced_memory=self.memory,
                context=self.context,
                related_finder=self.related_finder
            )
        except ImportError:
            self.repository_analyzer = None
        except Exception as e:
            err_console.print(f"Warning: RepositoryAnalyzer init failed: {e}")
            self.repository_analyzer = None
            
        # 3. ImpactAnalyzer
        try:
            from cognix.impact_analyzer import ImpactAnalyzer
            self.impact_analyzer = ImpactAnalyzer(
                context_manager=self.context,
                config=self.config,
                repository_analyzer=getattr(self, 'repository_analyzer', None)
            )
        except ImportError:
            self.impact_analyzer = None
        except Exception as e:
            err_console.print(f"Warning: ImpactAnalyzer init failed: {e}")
            self.impact_analyzer = None
            
        # 4. SafeEditor
        try:
            from cognix.safe_editor import SafeEditor
            self.safe_editor = SafeEditor(
                memory_manager=self.memory,
                diff_engine=self.diff_engine,
                impact_analyzer=self.impact_analyzer,
                repository_manager=None
            )
        except ImportError:
            self.safe_editor = None
        except Exception as e:
            err_console.print(f"Warning: SafeEditor init failed: {e}")
            self.safe_editor = None

        # リポジトリ初期スキャン
        if self.repository_analyzer:
            try:
                # リポジトリデータが空の場合のみスキャン
                if not getattr(self.repository_analyzer.memory, 'repository_data', None):
                    # 同期的に簡易スキャン
                    list(self.repository_analyzer.analyze_project_incrementally(max_files=500))
            except Exception:
                pass # スキャン失敗は無視（起動を優先）
    
    def _initialize_modules(self):
        """機能モジュールの初期化"""
        # 1) Chat workflow
        try:
            from cognix.cli_chat_workflow import ChatWorkflowModule
            self.chat_workflow = ChatWorkflowModule()
            self.chat_workflow.set_dependencies(self)
        except Exception as e:
            self.chat_workflow = None
            err_console.print(f"Warning: ChatWorkflowModule init failed: {e}")

        # 2) File operations
        try:
            from cognix.cli_file_operations import FileOperationsModule
            self.file_operations = FileOperationsModule()
            self.file_operations.set_dependencies(self)
        except Exception as e:
            self.file_operations = None
            err_console.print(f"Warning: FileOperationsModule init failed: {e}")

        # 3) Repository
        try:
            from cognix.cli_repository import RepositoryModule
            self.repository = RepositoryModule()
            self.repository.set_dependencies(self)
        except Exception as e:
            self.repository = None
            err_console.print(f"Warning: RepositoryModule init failed: {e}")

        # 4) Utilities
        try:
            from cognix.cli_utilities import UtilitiesModule
            self.utilities = UtilitiesModule()
            self.utilities.set_dependencies(self)
        except Exception as e:
            self.utilities = None
            err_console.print(f"Warning: UtilitiesModule init failed: {e}")
    
    def _build_command_map(self):
        """コマンドマップの構築"""
        # 基本コマンド
        self.command_map = {
            'help': self.cmd_help,
            'exit': self.do_exit,
            'quit': self.do_quit,
        }
        
        # runコマンド
        self.command_map['run'] = self.cmd_run

        # ラッパー（モジュール未ロードでもコマンド自体は定義する）
        self.command_map.update({
            'semi-auto': self.cmd_semi_auto,
            'make': self.cmd_make,
        })

        # Chat
        if self.chat_workflow:
            self.command_map.update({
                'think': self.chat_workflow.cmd_think,
                'plan': self.chat_workflow.cmd_plan,
                'write': self.chat_workflow.cmd_write,
                'workflow-status': self.chat_workflow.cmd_workflow_status,
                'clear-workflow': self.chat_workflow.cmd_clear_workflow,
                'semi-auto': self.chat_workflow.cmd_semi_auto,
                'make': self.chat_workflow.cmd_semi_auto,
            })
        
        # File ops
        if self.file_operations:
            self.command_map.update({
                'edit': self.file_operations.cmd_edit,
                'fix': self.file_operations.cmd_fix,
                'review': self.file_operations.cmd_review,
            })
        
        # Repository
        if self.repository:
            self.command_map.update({
                'repo-status': self.repository.cmd_repo_status,
                'repository-status': self.repository.cmd_repo_status,
                'repo-init': self.repository.cmd_repo_init,
                'repo-search': self.repository.cmd_repo_search,
                'repo-analyze': self.repository.cmd_repo_analyze,
                'repo-stats': self.repository.cmd_repo_stats,
                'repo-info': self.repository.cmd_repo_info,
                'repo-clean': self.repository.cmd_repo_clean,
                'repo-similar': self.repository.cmd_repo_similar,
                'repo-deps': self.repository.cmd_repo_deps,
            })
        
        # Utilities
        if self.utilities:
            self.command_map.update({
                'status': self.utilities.cmd_status,
                'model': self.utilities.cmd_model,
            })
    
    def cmd_run(self, args):
        """Run command
        
        Args:
            args: Command arguments (script or command to execute)
        """
        if getattr(self, 'run_command', None):
            try:
                arg_list = args.split() if args else []
                self.run_command.execute(arg_list)
            except Exception as e:
                if getattr(self, 'error_handler', None):
                    self.error_handler.handle_error(e, "run command execution")
                else:
                    err_console.print(f"Error executing run command: {e}")
        else:
            err_console.print("Run command is not available")
    
    def _check_first_run_fallback(self) -> bool:
        from pathlib import Path
        config_dir = Path.home() / ".cognix"
        first_run_marker = config_dir / ".first_run_complete"
        return not first_run_marker.exists()
    
    def _check_first_run(self) -> bool:
        if getattr(self, 'utilities', None) and hasattr(self.utilities, '_check_first_run'):
            return self.utilities._check_first_run()
        return self._check_first_run_fallback()
    
    def _mark_first_run_complete(self):
        if getattr(self, 'utilities', None) and hasattr(self.utilities, '_mark_first_run_complete'):
            self.utilities._mark_first_run_complete()
        else:
            from pathlib import Path
            config_dir = Path.home() / ".cognix"
            config_dir.mkdir(parents=True, exist_ok=True)
            first_run_marker = config_dir / ".first_run_complete"
            first_run_marker.touch()
    
    def _show_setup_guide(self):
        if getattr(self, 'utilities', None) and hasattr(self.utilities, '_show_setup_guide'):
            self.utilities._show_setup_guide()
        else:
            err_console.print("\n" + "="*60)
            err_console.print("   Welcome to Cognix - Setup Guide")
            err_console.print("="*60)
            # ... (簡易表示)
    
    def run(self):
        """CLIメインループの実行"""
        try:
            # 起動時に画面をクリア
            import os
            if os.name == 'nt': os.system('cls')
            else: os.system('clear')
            
            # ===== ⭐ エラーレポート表示 ⭐ =====
            # 画面クリア後にエラーを表示することで、ユーザーに問題を通知する
            if self.init_error:
                from rich.panel import Panel
                # APIキー未設定エラーの場合はインタラクティブセットアップを実行
                if "No LLM providers available" in self.init_error:
                    self._run_api_key_setup()
                    return
                else:
                    # その他のエラーはTraceback含めて表示
                    err_console.print(Panel(
                        f"[bold red]Startup Initialization Failed[/bold red]\n\n{self.init_error}",
                        title="System Error",
                        border_style="red"
                    ))
                    err_console.print("[yellow]Some features may be unavailable.[/yellow]\n")

            # 初回実行チェック
            if self.is_first_run:
                if self.utilities is not None:
                    self.utilities._show_setup_guide()
                    self.utilities._mark_first_run_complete()
                else:
                    err_console.print("\nFirst run detected (utilities unavailable).")
                return
            
            # 起動アニメーション
            try:
                show_startup_animation(config=self.config if hasattr(self, 'config') else None)
            except Exception:
                if getattr(self, 'utilities', None) and hasattr(self.utilities, "_generate_terminal_logo"):
                    err_console.print(self.utilities._generate_terminal_logo())
                else:
                    err_console.print("Cognix CLI initialized")

            err_console.print()

            from rich.text import Text
            err_console.print(Text.from_ansi(tips_help_line()))

            if getattr(self, 'utilities', None):
                self.utilities._check_session_restoration()            
                        
            original_intro = self.intro if hasattr(self, 'intro') else ""
            self.intro = ""
            
            self.cmdloop()
            
            self.intro = original_intro
            
        except KeyboardInterrupt:
            err_console.print(Text.from_ansi(f"\n{GREEN}Session saved! See you again!{RESET}\n\n"))
        except Exception as e:
            if getattr(self, 'error_handler', None):
                self.error_handler.handle_error(e, "CLI main loop")
            else:
                err_console.print(f"Critical error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        # 変数チェックをしてからクリーンアップ
        if hasattr(self, 'shared_state') and self.shared_state:
            temp_files = getattr(self.shared_state, 'temp_files', [])
            if temp_files:
                err_console.print("Cleaning up resources...")
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file): os.remove(temp_file)
                    except: pass
        
        if getattr(self, 'session_manager', None):
            try:
                if hasattr(self.session_manager, 'autosave'):
                    self.session_manager.autosave()
            except: pass
    
    def _run_api_key_setup(self):
        """インタラクティブなAPIキーセットアップを実行"""
        from pathlib import Path
        
        # GRAYのみローカル定義（theme_zen.pyに存在しないため）
        GRAY = "\033[90m"
        
        rule_line = "─" * 50
        
        print()
        print(f"{GREEN}Welcome to Cognix!{RESET}")
        print(f"{GREEN}{rule_line}{RESET}")
        print()
        print(f"{GREEN}API Key Setup{RESET}")
        print()
        print(f"{GREEN}Choose your AI provider:{RESET}")
        print("  [1] Anthropic (Claude) - Recommended")
        print("  [2] OpenAI (GPT)")
        print("  [3] Anthropic (Claude) & OpenAI (GPT)")
        print("  [4] OpenRouter (Multiple models)")
        print()
        
        # プロバイダー選択
        try:
            choice = input("Enter choice (1/2/3/4): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSetup cancelled.")
            return
        
        if choice == "1":
            provider = "anthropic"
            key_names = ["ANTHROPIC_API_KEY"]
            key_urls = ["https://console.anthropic.com/"]
        elif choice == "2":
            provider = "openai"
            key_names = ["OPENAI_API_KEY"]
            key_urls = ["https://platform.openai.com/api-keys"]
        elif choice == "3":
            provider = "both"
            key_names = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
            key_urls = ["https://console.anthropic.com/", "https://platform.openai.com/api-keys"]
        elif choice == "4":
            provider = "openrouter"
            key_names = ["OPENAI_API_KEY"]
            key_urls = ["https://openrouter.ai/keys"]
        else:
            print(f"\n{GRAY}Invalid choice. Setup cancelled.{RESET}")
            return
        
        # APIキー入力
        api_keys = {}
        for i, key_name in enumerate(key_names):
            print()
            print(f"{GRAY}Get your API key at:{RESET} {key_urls[i]}")
            print()
            
            try:
                api_key = input(f"Enter your {key_name}: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\nSetup cancelled.")
                return
            
            if not api_key:
                print(f"\n{GRAY}No API key entered. Setup cancelled.{RESET}")
                return
            
            api_keys[key_name] = api_key
        
        # .envファイル作成
        env_path = Path.cwd() / ".env"
        
        try:
            env_content = "# Cognix Configuration\nCOGNIX_PROJECT=true\n\n"
            
            if provider == "openrouter":
                env_content += f"# OpenRouter\n{key_names[0]}={api_keys[key_names[0]]}\nOPENAI_BASE_URL=https://openrouter.ai/api/v1\n"
            elif provider == "both":
                env_content += f"# Anthropic\nANTHROPIC_API_KEY={api_keys['ANTHROPIC_API_KEY']}\n\n"
                env_content += f"# OpenAI\nOPENAI_API_KEY={api_keys['OPENAI_API_KEY']}\n"
            else:
                env_content += f"# {provider.capitalize()}\n{key_names[0]}={api_keys[key_names[0]]}\n"
            
            env_path.write_text(env_content, encoding="utf-8")
            
            print()
            print(f"{GREEN}✓ .env created successfully{RESET}")
            
            # sample_spec_tetris.mdをカレントディレクトリにコピー（サイレント）
            try:
                import shutil
                package_dir = Path(__file__).parent
                sample_spec_src = package_dir / "data" / "templates" / "sample_spec_tetris.md"
                sample_spec_dst = Path.cwd() / "sample_spec_tetris.md"
                
                if sample_spec_src.exists() and not sample_spec_dst.exists():
                    shutil.copy2(sample_spec_src, sample_spec_dst)
            except Exception:
                pass  # サンプルファイルのコピー失敗は無視
            
            print()
            print(f"Run {GREEN}cognix{RESET} to start.")
            print()
            
        except Exception as e:
            print(f"\n{GRAY}Error creating .env file: {e}{RESET}")
            print(f"\n{GRAY}Please create .env manually:{RESET}")
            for key_name, api_key in api_keys.items():
                print(f"  {key_name}={api_key}")
            if provider == "openrouter":
                print("  OPENAI_BASE_URL=https://openrouter.ai/api/v1")
    
    # ... (default, handle_slash_command, _handle_multiline_input, _reset_multiline_state, emptyline, do_exit, do_quit, cmd_make 等はそのまま) ...
    def default(self, line):
        # /make """モード中の入力処理
        if self._make_multiline_mode:
            self._handle_make_multiline_input(line)
            return
        
        if line.startswith('/'):
            # /make """ または /semi-auto """ の検出
            stripped = line.strip()
            if stripped.startswith('/make """') or stripped.startswith('/semi-auto """'):
                self._start_make_multiline(stripped)
                return
            
            cmd_parts = line[1:].strip().split(maxsplit=1)
            cmd_name = cmd_parts[0]
            args = cmd_parts[1] if len(cmd_parts) > 1 else ""
            self.handle_slash_command(cmd_name, args)
            self._reset_multiline_state() 
        else:
            self._handle_multiline_input(line)
    
    def handle_slash_command(self, cmd_name, args):
        if cmd_name in self.command_map:
            try:
                self.command_map[cmd_name](args)
            except Exception as e:
                if hasattr(self, 'error_handler') and self.error_handler:
                    self.error_handler.handle_error(e, f"command execution: /{cmd_name}")
                else:
                    err_console.print(f"Error executing command /{cmd_name}: {e}")
        else:
            err_console.print(f"Unknown command: /{cmd_name}")
            err_console.print("Type '/help' for available commands.")

    def _handle_multiline_input(self, line):
        # 簡易実装（元コード同様）
        if line.strip().startswith('"""'):
            if not self._triple_quote_mode:
                self._triple_quote_mode = True
                self._multiline_buffer = []
                content = line.strip()[3:].strip()
                if content:
                    if content.endswith('"""'):
                        self._multiline_buffer.append(content[:-3].strip())
                        full = '\n'.join(self._multiline_buffer)
                        if self.chat_workflow: self.chat_workflow.handle_chat(full)
                        self._reset_multiline_state()
                        return
                    else:
                        self._multiline_buffer.append(content)
                self.prompt = "... "
                return
        
        if self._triple_quote_mode:
            if line.strip().endswith('"""'):
                content = line.strip()[:-3]
                if content: self._multiline_buffer.append(content)
                full = '\n'.join(self._multiline_buffer)
                if self.chat_workflow: self.chat_workflow.handle_chat(full)
                else: err_console.print("Chat unavailable")
                self._reset_multiline_state()
            else:
                self._multiline_buffer.append(line)
                self.prompt = "... "
            return
            
        if line.strip():
            if self.chat_workflow: self.chat_workflow.handle_chat(line)
            else: err_console.print("Chat unavailable")
        self._reset_multiline_state()

    def _reset_multiline_state(self):
        self._multiline_buffer = []
        self._empty_line_count = 0
        self._triple_quote_mode = False
        # /make """モードのリセット
        self._make_multiline_mode = False
        self._make_buffer = []
        # プロンプト復帰ロジック（簡略化）
        self.prompt = self._get_prompt_with_model()

    def _start_make_multiline(self, line):
        """
        /make triple-quote または /semi-auto triple-quote で複数行入力モードを開始
        
        Args:
            line: 入力行（例: '/make triple-quote内容' または '/make triple-quote'）
        """
        self._make_multiline_mode = True
        self._make_buffer = []
        
        # /make """ または /semi-auto """ の後の内容を取得
        if '"""' in line:
            # """の後の内容を取得
            after_quote = line.split('"""', 1)[1] if '"""' in line else ""
            
            # 同一行で閉じている場合（例: /make """goal"""）
            if after_quote.endswith('"""'):
                goal = after_quote[:-3].strip()
                if goal:
                    self.cmd_make(goal)
                self._reset_multiline_state()
                return
            
            # 内容があれば追加
            if after_quote.strip():
                self._make_buffer.append(after_quote)
        
        self.prompt = "> "
        err_console.print('[dim]Enter Multiline goal (end with """)[/dim]')

    def _handle_make_multiline_input(self, line):
        """
        /make triple-quote モード中の入力を処理
        
        Args:
            line: 入力行
        """
        # """で終了する場合
        if line.rstrip().endswith('"""'):
            content = line.rstrip()[:-3]
            if content:
                self._make_buffer.append(content)
            
            # goalを結合して実行
            goal = '\n'.join(self._make_buffer).strip()
            
            if goal:
                self.cmd_make(goal)
            else:
                err_console.print("[yellow]Goal is empty. Operation cancelled.[/yellow]")
            
            self._reset_multiline_state()
        else:
            # バッファに追加
            self._make_buffer.append(line)

    def emptyline(self):
        # /make triple-quote モード中は空行もバッファに追加
        if self._make_multiline_mode:
            self._make_buffer.append('')
            return
        self._handle_multiline_input('')

    def do_exit(self, args):
        """Exit the CLI application

        Args:
            args: Not used
        """        
        err_console.print(Text.from_ansi(f"{GREEN}Session saved! See you again!{RESET}\n\n"))
        return True
    
    def do_quit(self, args):
        return self.do_exit(args)

    def cmd_make(self, args):
        if getattr(self, "chat_workflow", None) and hasattr(self.chat_workflow, "cmd_semi_auto"):
            return self.chat_workflow.cmd_semi_auto(args)
        else:
            from cognix.logger import err_console
            err_console.print("Chat workflow is not available (module not initialized)")

    def cmd_semi_auto(self, args):
        return self.cmd_make(args)
    
    def cmd_help(self, args):
        if getattr(self, 'utilities', None) and hasattr(self.utilities, 'cmd_help'):
            self.utilities.cmd_help(args)
        else:
            err_console.print("Available commands (Fallback): /help, /exit, /quit")
    
    def postcmd(self, stop, line):
        # /make """モード中はプロンプトを維持
        if self._make_multiline_mode:
            self.prompt = "> "
        else:
            self.prompt = self._get_prompt_with_model()
        return stop