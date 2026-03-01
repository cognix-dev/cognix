"""
CLI リポジトリ分析モジュール

このモジュールは、リポジトリ分析と管理機能を提供します。
具体的には以下の機能を含みます：

1. リポジトリ状態の分析 (repo-status)
2. リポジトリ初期化 (repo-init)
3. 依存関係分析 (repo-deps)
"""

import os
import sys
import json
from typing import Dict, List, Set, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime

# 必須依存
from cognix.cli_shared import CLIModuleBase
from cognix.prompt_templates import prompt_manager
from cognix.ui import StatusIndicator  # Phase 1: UI改善
from cognix.logger import err_console

class RepositoryModule(CLIModuleBase):
    """リポジトリ分析機能モジュール
    
    リポジトリの分析、依存関係の検出、初期化などの機能を提供します。
    """
    
    def __init__(self):
        """基本初期化 - 引数なし
        
        依存オブジェクトはset_dependenciesで後から設定します
        """
        # 親クラスの初期化 - 引数なしで呼び出し
        super().__init__()
        
        # このモジュール固有の初期化
        # (依存オブジェクトに依存しない初期化のみ)
    
    def cmd_repo_status(self, args):
        """Display repository status
        
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
            
            err_console.print("📊 Analyzing repository structure...")
            
            # リポジトリルートの確認
            repo_root = self.context.root_dir if hasattr(self, 'context') and self.context else Path.cwd()
            err_console.print(f"Repository root: {repo_root}")
            
            # 基本的なリポジトリ情報の収集
            repo_info = self._collect_repo_info(repo_root, verbose)
            
            # コンテキスト生成
            context = ""
            if hasattr(self, 'context') and self.context:
                context = self.context.generate_context_for_prompt(num_files=10)
            
            # プロンプト生成
            prompt = prompt_manager.get_prompt("repo_status").format(
                repo_root=str(repo_root),
                repo_info=json.dumps(repo_info, indent=2)
            )
            
            # LLM応答生成
            if hasattr(self, 'llm_manager') and self.llm_manager:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    context=context,
                    system_prompt=prompt_manager.get_prompt("repo_status_system")
                )
                response_content = response.content if hasattr(response, 'content') else str(response)
            else:
                response_content = "Error: LLM Manager not available"
                err_console.print(response_content)
                return
            
            # 結果の表示
            model_prefix = self._get_model_prefix()
            self._display_with_typewriter(response_content, model_prefix)
            
            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt=f"/repo-status{' -v' if verbose else ''}",
                    claude_reply=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={"command": "repo-status", "verbose": verbose}
                )
            
            # セッションに保存
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input=f"/repo-status{' -v' if verbose else ''}",
                    ai_response=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="repo-status",
                    metadata={"verbose": verbose},
                    tokens_used=getattr(response, 'usage', None),
                )
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "repo-status command")
            else:
                err_console.print(f"Error in repo-status command: {e}")
    
    def cmd_repo_init(self, args):
        """Initialize repository
        
        Args:
            args: Command arguments (project name or directory)
        """
        try:
            # プロジェクト名/ディレクトリの取得
            if args:
                project_dir = args.strip() if isinstance(args, str) else " ".join(args).strip()
            else:
                project_dir = self.get_input_with_options(
                    "Enter project directory to initialize",
                    allow_empty=False
                )
                if not project_dir:
                    err_console.print("Operation cancelled.")
                    return
            
            # プロジェクトタイプの取得
            project_type = self.get_input_with_options(
                "Enter project type (python, javascript, etc.)",
                allow_empty=False
            )
            if not project_type:
                err_console.print("Operation cancelled.")
                return
            
            # プロジェクト説明の取得
            project_description = self.get_multiline_input(
                "Enter project description",
                allow_empty=True
            )
            
            err_console.print(f"🚀 Initializing {project_type} project in {project_dir}...")
            
            # プロンプト生成
            prompt = prompt_manager.get_prompt("repo_init").format(
                project_dir=project_dir,
                project_type=project_type,
                project_description=project_description
            )
            
            # LLM応答生成
            if hasattr(self, 'llm_manager') and self.llm_manager:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    system_prompt=prompt_manager.get_prompt("repo_init_system")
                )
                response_content = response.content if hasattr(response, 'content') else str(response)
            else:
                response_content = "Error: LLM Manager not available"
                err_console.print(response_content)
                return
            
            # 結果の表示
            model_prefix = self._get_model_prefix()
            self._display_with_typewriter(response_content, model_prefix)
            
            # 初期化の実lines確認
            confirm_init = self._confirm_action(f"\nCreate these files in {project_dir}?")
            if not confirm_init:
                err_console.print("Operation cancelled.")
                return
            
            # プロジェクト初期化の実lines
            self._execute_repo_init(project_dir, response_content)
            
            # 拡張メモリに保存（初期化した場合のみ）
            try:
                from cognix.enhanced_memory import EnhancedMemory
                
                if hasattr(self, 'memory') and isinstance(self.memory, EnhancedMemory):
                    self.memory.add_project_info(
                        project_dir=project_dir,
                        project_type=project_type,
                        description=project_description
                    )
            except ImportError:
                pass
            
            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt=f"/repo-init {project_dir}",
                    claude_reply=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={
                        "command": "repo-init",
                        "project_dir": project_dir,
                        "project_type": project_type
                    }
                )
            
            # セッションに保存
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input=f"/repo-init {project_dir}",
                    ai_response=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="repo-init",
                    metadata={
                        "project_dir": project_dir,
                        "project_type": project_type
                    },
                    tokens_used=getattr(response, 'usage', None),
                )
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "repo-init command")
            else:
                err_console.print(f"Error in repo-init command: {e}")
    
    def cmd_repo_deps(self, args):
        """Analyze repository dependencies
        
        Args:
            args: Command arguments (optional)
        """
        try:
            # リポジトリマネージャーのインポート
            try:
                from cognix.repository_manager import RepositoryManager
            except ImportError:
                err_console.print("Error: RepositoryManager not available")
                err_console.print("Please install the required dependencies.")
                return
            
            err_console.print("🔍 Analyzing repository dependencies...")
            
            # リポジトリマネージャーの初期化
            repo_root = self.context.root_dir if hasattr(self, 'context') and self.context else Path.cwd()
            repo_manager = RepositoryManager(repo_root)
            
            # 依存関係の収集
            dependencies = repo_manager.analyze_dependencies()
            
            # コンテキスト生成
            context = ""
            if hasattr(self, 'context') and self.context:
                context = self.context.generate_context_for_prompt(num_files=5)
            
            # プロンプト生成
            prompt = prompt_manager.get_prompt("repo_deps").format(
                repo_root=str(repo_root),
                dependencies=json.dumps(dependencies, indent=2)
            )
            
            # LLM応答生成
            if hasattr(self, 'llm_manager') and self.llm_manager:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    context=context,
                    system_prompt=prompt_manager.get_prompt("repo_deps_system")
                )
                response_content = response.content if hasattr(response, 'content') else str(response)
            else:
                response_content = "Error: LLM Manager not available"
                err_console.print(response_content)
                return
            
            # 結果の表示
            model_prefix = self._get_model_prefix()
            self._display_with_typewriter(response_content, model_prefix)
            
            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt="/repo-deps",
                    claude_reply=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={"command": "repo-deps"}
                )
            
            # セッションに保存
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input="/repo-deps",
                    ai_response=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="repo-deps",
                    metadata={},
                    tokens_used=getattr(response, 'usage', None),
                )
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "repo-deps command")
            else:
                err_console.print(f"Error in repo-deps command: {e}")
    
    # 以下はヘルパーメソッド
    
    def _collect_repo_info(self, repo_root: Path, verbose: bool = False) -> Dict[str, Any]:
        """リポジトリ情報の収集
        
        Args:
            repo_root: リポジトリルートディレクトリ
            verbose: 詳細情報を含めるかどうか
            
        Returns:
            収集したリポジトリ情報
        """
        repo_info = {
            "root": str(repo_root),
            "files": {},
            "metadata": {}
        }
        
        # リポジトリメタデータの検出
        metadata_files = [
            "package.json",
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "composer.json",
            "Gemfile",
            "build.gradle",
            "pom.xml",
            "Cargo.toml",
            ".gitignore"
        ]
        
        for metadata_file in metadata_files:
            metadata_path = repo_root / metadata_file
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        content = f.read()
                    repo_info["metadata"][metadata_file] = content
                except Exception:
                    repo_info["metadata"][metadata_file] = "Error reading file"
        
        # files統計情報の収集
        file_extensions = {}
        directory_structure = []
        
        # files拡張子統計とディレクトリ構造の収集
        for root, dirs, files in os.walk(repo_root):
            # .gitディレクトリの除外
            if ".git" in dirs:
                dirs.remove(".git")
            
            # node_modulesディレクトリの除外
            if "node_modules" in dirs:
                dirs.remove("node_modules")
            
            # 相対パスに変換
            rel_path = os.path.relpath(root, repo_root)
            if rel_path != ".":
                directory_structure.append(rel_path)
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext:
                    if ext not in file_extensions:
                        file_extensions[ext] = 0
                    file_extensions[ext] += 1
        
        repo_info["files"]["extensions"] = file_extensions
        repo_info["directories"] = directory_structure[:20]  # 最初の20ディレクトリのみ
        
        # 詳細情報（verboseモード時のみ）
        if verbose:
            # 言語検出（簡易版）
            languages = self._detect_languages(file_extensions)
            repo_info["languages"] = languages
            
            # そのmoreの詳細情報
            # ...追加の情報収集ロジックがあればここに実装...
        
        return repo_info
    
    def _detect_languages(self, file_extensions: Dict[str, int]) -> Dict[str, int]:
        """files拡張子から言語を検出
        
        Args:
            file_extensions: files拡張子の統計
            
        Returns:
            言語の統計
        """
        languages = {}
        extension_to_language = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React/JSX",
            ".tsx": "React/TSX",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".sass": "Sass",
            ".less": "Less",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".h": "C/C++ Header",
            ".cs": "C#",
            ".go": "Go",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".rs": "Rust",
            ".scala": "Scala"
        }
        
        for ext, count in file_extensions.items():
            if ext in extension_to_language:
                lang = extension_to_language[ext]
                if lang not in languages:
                    languages[lang] = 0
                languages[lang] += count
        
        return languages
    
    def _execute_repo_init(self, project_dir: str, ai_response: str):
        """リポジトリ初期化の実lines
        
        Args:
            project_dir: プロジェクトディレクトリ
            ai_response: AI応答内容
        """
        # プロジェクトディレクトリの作成
        project_path = Path(project_dir)
        project_path.mkdir(parents=True, exist_ok=True)
        
        # 応答からfilesの抽出と作成
        file_pattern = r"```(?:[a-zA-Z0-9_\-\.]+)?\n([\s\S]+?)\n```\s*\n([a-zA-Z0-9_\-\.\/\\]+)"
        file_matches = re.finditer(file_pattern, ai_response)
        
        files_created = []
        
        for match in file_matches:
            content = match.group(1)
            filename = match.group(2).strip()
            
            if filename:
                file_path = project_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                files_created.append(str(file_path))
        
        # 別のパターンでも試す
        alt_pattern = r"([a-zA-Z0-9_\-\.\/\\]+)\n```(?:[a-zA-Z0-9_\-\.]+)?\n([\s\S]+?)\n```"
        alt_matches = re.finditer(alt_pattern, ai_response)
        
        for match in alt_matches:
            filename = match.group(1).strip()
            content = match.group(2)
            
            if filename and filename not in files_created:
                file_path = project_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                files_created.append(str(file_path))
        
        # 結果の表示
        if files_created:
            err_console.print("\n✅ Created the following files:")
            for file in files_created:
                err_console.print(f"  {file}")
        else:
            err_console.print("\nNo files were created. Please check the response format.")

    def cmd_repo_search(self, args):
        """Search repository files
        
        Usage:
            /repo-search main.py
            /repo-search --function calculate
            /repo-search --class UserModel
            /repo-search --content "import requests"
        
        Args:
            args: Command arguments
        """
        # ヘルプ表示
        if not args or (isinstance(args, str) and args.strip() in ["--help", "-h"]):
            err_console.print("📖 /repo-search - Repository file search")
            err_console.print("Usage:")
            err_console.print("  /repo-search main.py              # Search by file name")
            err_console.print("  /repo-search --function calculate  # Search by function name")
            err_console.print("  /repo-search --class UserModel     # Search by class name")
            err_console.print("  /repo-search --content import      # Search by content")
            return
        
        try:
            # 引数の解析
            if isinstance(args, str):
                args_list = args.split()
            elif isinstance(args, list):
                args_list = args
            else:
                args_list = []
            
            if not args_list:
                err_console.print(StatusIndicator.error("Please specify your search query."))
                return
            
            # デフォルト設定
            search_type = "name"
            query = args_list[0]
            
            # 検索タイプの解析
            if "--function" in args_list:
                search_type = "function"
                func_index = args_list.index("--function")
                if func_index + 1 < len(args_list):
                    query = args_list[func_index + 1]
            elif "--class" in args_list:
                search_type = "class"
                class_index = args_list.index("--class")
                if class_index + 1 < len(args_list):
                    query = args_list[class_index + 1]
            elif "--content" in args_list:
                search_type = "content"
                content_index = args_list.index("--content")
                if content_index + 1 < len(args_list):
                    query = args_list[content_index + 1]
            
            # RepositoryManagerのインポートと初期化
            try:
                from cognix.repository_manager import RepositoryManager
                from pathlib import Path
            except ImportError:
                err_console.print(StatusIndicator.error("RepositoryManager is not available."))
                err_console.print("💡 Please install the required dependencies")
                return
            
            repo_manager = RepositoryManager(self.memory, Path.cwd())
            
            # 既存データのロード
            if not repo_manager._load_repository_data():
                err_console.print(StatusIndicator.error("Repository data not found."))
                err_console.print("💡 `/repo-init`to initialize")
                return
            
            # 検索実lines
            results = repo_manager.search_files(query, search_type)
            
            if not results:
                err_console.print(StatusIndicator.error(f"No files matching '{query}' found."))
                return
            
            # 結果表示
            err_console.print(f"🔍 Search results: '{query}' ({search_type})")
            err_console.print(f"📁 {len(results)}files found\n")
            
            for i, repo_file in enumerate(results[:10], 1):  # 最大10items表示
                err_console.print(f"{i}. {repo_file.file_path}")
                err_console.print(f"   Language: {repo_file.language}")
                err_console.print(f"   Size: {repo_file.file_size:,} bytes")
                err_console.print(f"   Lines: {repo_file.line_count:,} lines")
                err_console.print(f"   Confidence: {repo_file.confidence_score:.2f}")
                
                # 検索タイプに応じた追加情報
                if search_type == "function" and repo_file.functions:
                    matching_funcs = [f for f in repo_file.functions if query.lower() in f["name"].lower()]
                    if matching_funcs:
                        func_names = [f['name'] for f in matching_funcs[:3]]
                        err_console.print(f"   Matching functions: {', '.join(func_names)}")
                
                if search_type == "class" and repo_file.classes:
                    matching_classes = [c for c in repo_file.classes if query.lower() in c["name"].lower()]
                    if matching_classes:
                        class_names = [c['name'] for c in matching_classes[:3]]
                        err_console.print(f"   Matching classes: {', '.join(class_names)}")
                
                err_console.print()
            
            if len(results) > 10:
                err_console.print(f"... more {len(results) - 10}items")
        
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "repo-search command")
            else:
                err_console.print(StatusIndicator.error(f"Error during search: {e}"))

    def cmd_repo_analyze(self, args):
        """Execute project analysis
        
        Usage:
            /repo-analyze       # Incremental analysis (recommended)
            /repo-analyze --full # Full analysis
        
        Args:
            args: Command arguments
        """
        # ヘルプ表示
        if isinstance(args, str) and args.strip() in ["--help", "-h"]:
            err_console.print("📖 /repo-analyze - Execute project analysis")
            err_console.print("Usage:")
            err_console.print("  /repo-analyze       # Incremental analysis (recommended)")
            err_console.print("  /repo-analyze --full # Full analysis")
            return
        
        err_console.print("📄 Analyzing project...")
        
        try:
            # 引数の解析
            if isinstance(args, str):
                args_list = args.split()
            elif isinstance(args, list):
                args_list = args
            else:
                args_list = []
            
            # インクリメンタル分析の判定
            incremental = "--full" not in args_list
            
            # RepositoryManagerのインポートと初期化
            try:
                from cognix.repository_manager import RepositoryManager
                from pathlib import Path
            except ImportError:
                err_console.print(StatusIndicator.error("RepositoryManager is not available."))
                err_console.print("💡 Please install the required dependencies")
                return
            
            repo_manager = RepositoryManager(self.memory, Path.cwd())
            
            # Execute project analysis
            result = repo_manager.analyze_project(incremental)
            
            # 結果表示
            err_console.print("✅ Project analysis completed")
            err_console.print(f"📁 Total files: {result['total_files']}")
            err_console.print(f"✅ Analyzed: {result['analyzed_files']}")
            err_console.print(f"⏭️ Skipped: {result['skipped_files']}")
            
            # 言語別統計
            if result["languages"]:
                err_console.print("\n📊 Files by language:")
                for lang, count in sorted(result["languages"].items()):
                    err_console.print(f"   {lang}: {count}files")
            
            # Key files
            if result["key_files"]:
                err_console.print(f"\n🔑 Key files ({len(result['key_files'])}files):")
                for key_file in result["key_files"][:5]:
                    err_console.print(f"   • {key_file}")
                if len(result["key_files"]) > 5:
                    err_console.print(f"   ... more {len(result['key_files']) - 5}files")
            
            # 潜在的な問題
            if result["potential_issues"]:
                err_console.print(StatusIndicator.warning(f"Potential issues ({len(result['potential_issues'])} found):"))
                for issue in result["potential_issues"][:3]:
                    err_console.print(f"   • {issue}")
                if len(result["potential_issues"]) > 3:
                    err_console.print(f"   ... more {len(result['potential_issues']) - 3}items")
            
            # データ保存
            repo_manager._save_repository_data()
            err_console.print("\n💾 Analysis results saved")
        
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "repo-analyze command")
            else:
                err_console.print(StatusIndicator.error(f"Error during analysis: {e}"))

    def cmd_repo_info(self, args):
        """Display detailed file information
        
        Usage:
            /repo-info src/main.py
        
        Args:
            args: Command arguments (file paths)
        """
        # ヘルプ表示または引数なし
        if not args or (isinstance(args, str) and args.strip() in ["--help", "-h"]):
            err_console.print("📖 /repo-info - Display detailed file information")
            err_console.print("Usage:")
            err_console.print("  /repo-info src/main.py  # Display detailed file information")
            return
        
        try:
            # 引数の解析
            if isinstance(args, str):
                file_path = args.strip()
            elif isinstance(args, list):
                file_path = args[0] if args else ""
            else:
                file_path = ""
            
            if not file_path:
                err_console.print(StatusIndicator.error("Please specify a file path."))
                return
            
            # RepositoryManagerのインポートと初期化
            try:
                from cognix.repository_manager import RepositoryManager
                from pathlib import Path
            except ImportError:
                err_console.print(StatusIndicator.error("RepositoryManager is not available."))
                return
            
            repo_manager = RepositoryManager(self.memory, Path.cwd())
            
            # 既存データのロード
            if not repo_manager._load_repository_data():
                err_console.print(StatusIndicator.error("Repository data not found."))
                err_console.print("💡 `/repo-init`to initialize")
                return
            
            # files情報取得
            repo_file = repo_manager.get_file_info(file_path)
            
            if not repo_file:
                err_console.print(StatusIndicator.error(f"File '{file_path}' information not found."))
                return
            
            # 詳細情報表示
            err_console.print(f"📄 File information: {file_path}")
            err_console.print("=" * 60)
            
            # 基本情報
            err_console.print(f"\n【Basic Information】")
            err_console.print(f"  Language: {repo_file.language}")
            err_console.print(f"  Size: {repo_file.file_size:,} bytes")
            err_console.print(f"  Lines: {repo_file.line_count:,} lines")
            err_console.print(f"  Confidence score: {repo_file.confidence_score:.2f}")
            err_console.print(f"  Last updated: {repo_file.last_modified}")
            err_console.print(f"  Last analyzed: {repo_file.last_analyzed}")
            
            # インポート/依存関係
            if repo_file.imports:
                err_console.print(f"\n【Imports】 ({len(repo_file.imports)}items)")
                for imp in repo_file.imports[:10]:
                    err_console.print(f"  • {imp}")
                if len(repo_file.imports) > 10:
                    err_console.print(f"  ... more {len(repo_file.imports) - 10}items")
            
            # エクスポート
            if repo_file.exports:
                err_console.print(f"\n【Exports】 ({len(repo_file.exports)}items)")
                for exp in repo_file.exports[:10]:
                    err_console.print(f"  • {exp}")
                if len(repo_file.exports) > 10:
                    err_console.print(f"  ... more {len(repo_file.exports) - 10}items")
            
            # 関数
            if repo_file.functions:
                err_console.print(f"\n【Functions】 ({len(repo_file.functions)}items)")
                for func in repo_file.functions[:10]:
                    func_name = func.get('name', 'unknown')
                    args = func.get('args', [])
                    args_str = f"({', '.join(args)})" if args else "()"
                    err_console.print(f"  • {func_name}{args_str}")
                if len(repo_file.functions) > 10:
                    err_console.print(f"  ... more {len(repo_file.functions) - 10}items")
            
            # クラス
            if repo_file.classes:
                err_console.print(f"\n【Classes】 ({len(repo_file.classes)}items)")
                for cls in repo_file.classes[:10]:
                    cls_name = cls.get('name', 'unknown')
                    methods = cls.get('methods', [])
                    methods_str = f" ({len(methods)} methods)" if methods else ""
                    err_console.print(f"  • {cls_name}{methods_str}")
                if len(repo_file.classes) > 10:
                    err_console.print(f"  ... more {len(repo_file.classes) - 10}items")
            
            # 関連files
            relationships = repo_manager.get_file_relationships(file_path)
            if relationships["imports"]:
                err_console.print(f"\n【Imports To】 ({len(relationships['imports'])}items)")
                for rel_file in relationships["imports"][:5]:
                    err_console.print(f"  • {rel_file}")
                if len(relationships["imports"]) > 5:
                    err_console.print(f"  ... more {len(relationships['imports']) - 5}items")
            
            if relationships["imported_by"]:
                err_console.print(f"\n【Imported By】 ({len(relationships['imported_by'])}items)")
                for rel_file in relationships["imported_by"][:5]:
                    err_console.print(f"  • {rel_file}")
                if len(relationships["imported_by"]) > 5:
                    err_console.print(f"  ... more {len(relationships['imported_by']) - 5}items")
        
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "repo-info command")
            else:
                err_console.print(StatusIndicator.error(f"An error occurred: {e}"))

    def cmd_repo_clean(self, args):
        """Clear repository data
        
        Usage:
            /repo-clean --confirm  # Clear data
        
        Args:
            args: Command arguments
        """
        # ヘルプ表示
        if isinstance(args, str) and args.strip() in ["--help", "-h"]:
            err_console.print("📖 /repo-clean - Clear repository data")
            err_console.print("Usage:")
            err_console.print("  /repo-clean --confirm  # Clear data")
            return
        
        try:
            # 引数の解析
            if isinstance(args, str):
                args_list = args.split()
            elif isinstance(args, list):
                args_list = args
            else:
                args_list = []
            
            # 確認なしの場合は警告表示
            if "--confirm" not in args_list:
                err_console.print(StatusIndicator.warning("This operation will delete all repository analysis data."))
                err_console.print("To execute, --confirm option")
                err_console.print("Example: /repo-clean --confirm")
                return
            
            # EnhancedMemoryの確認
            if not hasattr(self.memory, 'clear_repository_data'):
                err_console.print(StatusIndicator.error("Repository feature is not available."))
                err_console.print("💡 Please verify EnhancedMemory is enabled")
                return
            
            # データクリア実lines
            if self.memory.clear_repository_data():
                err_console.print("✅ Repository data successfully cleared")
                err_console.print("💡 To use again, run `/repo-init` to initialize")
            else:
                err_console.print(StatusIndicator.error("Failed to clear repository data."))
        
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "repo-clean command")
            else:
                err_console.print(StatusIndicator.error(f"An error occurred: {e}"))

    def cmd_repo_similar(self, args):
        """Find similar files
        
        Usage:
            /repo-similar src/main.py
            /repo-similar src/main.py --threshold 0.8
        
        Args:
            args: Command arguments
        """
        # ヘルプ表示または引数なし
        if not args or (isinstance(args, str) and args.strip() in ["--help", "-h"]):
            err_console.print("📖 /repo-similar - Similar file search")
            err_console.print("Usage:")
            err_console.print("  /repo-similar src/main.py           # Search for similar files")
            err_console.print("  /repo-similar src/main.py --threshold 0.8  # Specify threshold")
            return
        
        try:
            # 引数の解析
            if isinstance(args, str):
                args_list = args.split()
            elif isinstance(args, list):
                args_list = args
            else:
                args_list = []
            
            if not args_list:
                err_console.print(StatusIndicator.error("Please specify a file path."))
                return
            
            file_path = args_list[0]
            threshold = 0.7  # デフォルト閾値
            
            # 閾値の解析
            if "--threshold" in args_list:
                threshold_index = args_list.index("--threshold")
                if threshold_index + 1 < len(args_list):
                    try:
                        threshold = float(args_list[threshold_index + 1])
                        threshold = max(0.0, min(1.0, threshold))  # 0-1の範囲に制限
                    except ValueError:
                        err_console.print(StatusIndicator.warning("Please specify threshold as a number between 0.0 and 1.0."))
                        return
            
            # RepositoryManagerのインポートと初期化
            try:
                from cognix.repository_manager import RepositoryManager
                from pathlib import Path
            except ImportError:
                err_console.print(StatusIndicator.error("RepositoryManager is not available."))
                return
            
            repo_manager = RepositoryManager(self.memory, Path.cwd())
            
            # 既存データのロード
            if not repo_manager._load_repository_data():
                err_console.print(StatusIndicator.error("Repository data not found."))
                err_console.print("💡 `/repo-init`to initialize")
                return
            
            # Find similar files
            similar_files = repo_manager.find_similar_files(file_path, threshold)
            
            if not similar_files:
                err_console.print(StatusIndicator.error(f"No similar files found for '{file_path}' (threshold: {threshold:.2f})"))
                return
            
            # 結果表示
            err_console.print(f"🔍 Similar files: {file_path} (threshold: {threshold:.2f})")
            err_console.print(f"📁 {len(similar_files)}files found\n")
            
            for i, (similar_path, similarity) in enumerate(similar_files[:10], 1):
                repo_file = repo_manager.get_file_info(similar_path)
                err_console.print(f"{i}. {similar_path}")
                err_console.print(f"   Similarity: {similarity:.3f}")
                if repo_file:
                    err_console.print(f"   Language: {repo_file.language}")
                    err_console.print(f"   Functions: {len(repo_file.functions)}items")
                    err_console.print(f"   Classes: {len(repo_file.classes)}items")
                err_console.print()
            
            if len(similar_files) > 10:
                err_console.print(f"... more {len(similar_files) - 10}items")
        
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "repo-similar command")
            else:
                err_console.print(StatusIndicator.error(f"An error occurred: {e}"))

    def cmd_repo_stats(self, args):
        """Display repository status
        
        Usage:
            /repo-stats
        
        Args:
            args: Command arguments
        """
        # ヘルプ表示
        if isinstance(args, str) and args.strip() in ["--help", "-h"]:
            err_console.print("📖 /repo-stats - Display Repository Statistics")
            err_console.print("Usage:")
            err_console.print("  /repo-stats  # Display statistics")
            return
        
        try:
            # RepositoryManagerのインポートと初期化
            try:
                from cognix.repository_manager import RepositoryManager
                from pathlib import Path
            except ImportError:
                err_console.print(StatusIndicator.error("RepositoryManager is not available."))
                return
            
            repo_manager = RepositoryManager(self.memory, Path.cwd())
            
            # 既存データのロード
            if not repo_manager._load_repository_data():
                err_console.print(StatusIndicator.error("Repository data not found."))
                err_console.print("💡 `/repo-init`to initialize")
                return
            
            # サマリー取得
            summary = repo_manager.get_project_summary()
            
            if not summary or summary.get('total_files', 0) == 0:
                err_console.print(StatusIndicator.error("Statistics are not available."))
                return
            
            # 統計情報表示
            err_console.print("📊 Repository Statistics")
            err_console.print("=" * 60)
            
            # 基本統計
            err_console.print(f"\n【Basic Statistics】")
            err_console.print(f"  Total files: {summary.get('total_files', 0):,}files")
            err_console.print(f"  Total size: {summary.get('total_size_bytes', 0):,} bytes")
            err_console.print(f"  Total lines: {summary.get('total_lines', 0):,} lines")
            err_console.print(f"  Average confidence: {summary.get('avg_confidence', 0):.2f}")
            
            # 言語別統計
            languages = summary.get('languages', {})
            if languages:
                err_console.print(f"\n【Language Statistics】")
                total_files = sum(languages.values())
                for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / total_files) * 100 if total_files > 0 else 0
                    err_console.print(f"  {lang}: {count}files ({percentage:.1f}%)")
            
            # 言語別詳細統計
            if hasattr(repo_manager, 'repository_data') and repo_manager.repository_data:
                err_console.print(f"\n【Details by Language】")
                
                lang_stats = {}
                for repo_file in repo_manager.repository_data.values():
                    lang = repo_file.language
                    if lang not in lang_stats:
                        lang_stats[lang] = {
                            'files': [],
                            'total_size': 0,
                            'total_lines': 0,
                            'total_funcs': 0,
                            'total_classes': 0
                        }
                    
                    lang_stats[lang]['files'].append(repo_file)
                    lang_stats[lang]['total_size'] += repo_file.file_size
                    lang_stats[lang]['total_lines'] += repo_file.line_count
                    lang_stats[lang]['total_funcs'] += len(repo_file.functions)
                    lang_stats[lang]['total_classes'] += len(repo_file.classes)
                
                for lang, stats in sorted(lang_stats.items(), key=lambda x: len(x[1]['files']), reverse=True):
                    lang_files = stats['files']
                    total_size = stats['total_size']
                    total_lines = stats['total_lines']
                    total_funcs = stats['total_funcs']
                    total_classes = stats['total_classes']
                    avg_size = total_size / len(lang_files) if lang_files else 0
                    
                    err_console.print(f"\n   {lang}:")
                    err_console.print(f"     Files count: {len(lang_files)}")
                    err_console.print(f"     Total size: {total_size:,} bytes")
                    err_console.print(f"     Total lines: {total_lines:,}")
                    err_console.print(f"     Average size: {avg_size:.0f} bytes")
                    err_console.print(f"     Functions: {total_funcs}items")
                    err_console.print(f"     Classes: {total_classes}items")
            
            # 最終更新時刻
            err_console.print(f"\n⏰ Last updated: {summary.get('last_updated', 'N/A')}")
        
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "repo-stats command")
            else:
                err_console.print(StatusIndicator.error(f"An error occurred: {e}"))