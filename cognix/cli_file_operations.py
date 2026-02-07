"""
CLI ファイル操作モジュール

このモジュールは、ファイル編集、レビュー、比較などの機能を提供します。
具体的には以下の機能を含みます：

1. AI支援ファイル編集 (edit)
2. コードレビューと分析 (review)
3. ファイル修正 (fix)
"""

import os
import sys
import re
import difflib
from typing import Dict, List, Set, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime

# 必須依存
from cognix.cli_shared import CLIModuleBase
from cognix.prompt_templates import prompt_manager
from cognix.logger import err_console

class FileOperationsModule(CLIModuleBase):
    """ファイル操作機能モジュール
    
    ファイルの編集、レビュー、比較などの機能を提供します。
    """
    
    def __init__(self):
        """基本初期化 - 引数なし
        
        依存オブジェクトはset_dependenciesで後から設定します
        """
        # 親クラスの初期化 - 引数なしで呼び出し
        super().__init__()
        
        # このモジュール固有の初期化
        # (依存オブジェクトに依存しない初期化のみ)
    
    def cmd_edit(self, args):
        """AI-assisted file editing
        
        Args:
            args: コマンド引数（ファイル名）
        """
        try:
            # ファイル名の取得
            if args:
                filename = args.strip() if isinstance(args, str) else " ".join(args).strip()
            else:
                filename = self.get_input_with_options(
                    "Enter file path to edit",
                    allow_empty=False
                )
                if not filename:
                    err_console.print("Operation cancelled.")
                    return
            
            # ファイルの存在確認
            file_path = Path(filename)
            if not file_path.exists():
                # 新規ファイル作成の確認
                create_new = self._confirm_action(f"File {filename} does not exist. Create new file?")
                if not create_new:
                    err_console.print("Operation cancelled.")
                    return
                
                # 新規ファイルの場合は空内容で開始
                current_content = ""
                err_console.print(f"Creating new file: {filename}")
            else:
                # 既存ファイルの読み込み
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='shift_jis') as f:
                        current_content = f.read()
                err_console.print(f"Editing file: {filename}")
            
            # 編集指示の取得
            instruction = self.get_multiline_input(
                "Enter your editing instructions",
                allow_empty=False
            )
            if not instruction:
                err_console.print("Operation cancelled.")
                return
            
            err_console.print(f"● Generating edit for {filename}...")
            
            # コンテキスト生成
            context = self.context.generate_context_for_prompt(
                user_prompt=f"Edit {filename}: {instruction}",
                max_context_size=8000
            )
            
            # プロンプト生成
            prompt = prompt_manager.get_prompt("edit_file").format(
                filename=filename,
                current_content=current_content,
                instruction=instruction
            )
            
            # LLM応答生成
            if hasattr(self, 'llm_manager') and self.llm_manager:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    context=context,
                    system_prompt=prompt_manager.get_prompt("edit_system")
                )
                response_content = response.content if hasattr(response, 'content') else str(response)
            else:
                response_content = "Error: LLM Manager not available"
                err_console.print(response_content)
                return
            
            # 編集結果の表示
            model_prefix = self._get_model_prefix()
            self._display_with_typewriter(response_content, model_prefix)
            
            # 編集の適用確認
            apply_edit = self._confirm_action(f"\nApply this edit to {filename}?")
            if apply_edit:
                # ファイル保存
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(response_content)
                
                err_console.print(f"✅ Changes saved to {filename}")
            else:
                err_console.print("Changes not applied.")
            
            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt=f"/edit {filename}\n{instruction}",
                    claude_reply=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={"command": "edit", "filename": filename}
                )
            
            # セッションに保存
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input=f"/edit {filename}\n{instruction}",
                    ai_response=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="edit",
                    metadata={"filename": filename}
                )
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "edit command")
            else:
                err_console.print(f"Error in edit command: {e}")
    
    def cmd_fix(self, args):
        """Fix/modify code
        
        Args:
            args: コマンド引数（ファイル名）
        """
        try:
            # ファイル名の取得
            if args:
                filename = args.strip() if isinstance(args, str) else " ".join(args).strip()
            else:
                filename = self.get_input_with_options(
                    "Enter file path to fix",
                    allow_empty=False
                )
                if not filename:
                    err_console.print("Operation cancelled.")
                    return
            
            # ファイルの存在確認
            file_path = Path(filename)
            if not file_path.exists():
                err_console.print(f"Error: File {filename} does not exist.")
                return
            
            # ファイルの読み込み
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='shift_jis') as f:
                    current_content = f.read()
            
            err_console.print(f"● Analyzing {filename} for issues...")
            
            # コンテキスト生成
            context = self.context.generate_context_for_prompt(
                user_prompt=f"Fix issues in {filename}",
                max_context_size=8000
            )
            
            # プロンプト生成
            prompt = prompt_manager.get_prompt("fix_file").format(
                filename=filename,
                current_content=current_content
            )
            
            # LLM応答生成
            if hasattr(self, 'llm_manager') and self.llm_manager:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    context=context,
                    system_prompt=prompt_manager.get_prompt("fix_system")
                )
                response_content = response.content if hasattr(response, 'content') else str(response)
            else:
                response_content = "Error: LLM Manager not available"
                err_console.print(response_content)
                return
            
            # 修正結果の表示
            model_prefix = self._get_model_prefix()
            self._display_with_typewriter(response_content, model_prefix)
            
            # 修正の適用確認
            apply_fix = self._confirm_action(f"\nApply this fix to {filename}?")

            if apply_fix:
                # ファイル保存
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(response_content)
                    
                    err_console.print(f"✅ Fixes saved to {filename}")
            else:
                err_console.print("Fixes not applied.")
            
            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt=f"/fix {filename}",
                    claude_reply=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={"command": "fix", "filename": filename}
                )
            
            # セッションに保存
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input=f"/fix {filename}",
                    ai_response=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="fix",
                    metadata={"filename": filename}
                )
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "fix command")
            else:
                err_console.print(f"Error in fix command: {e}")
    
    def cmd_review(self, args):
        """Code review
        
        Args:
            args: Command arguments (file name or directory)
        """
        try:
            # ファイル/ディレクトリ名の取得
            if args:
                target = args.strip() if isinstance(args, str) else " ".join(args).strip()
            else:
                target = self.get_input_with_options(
                    "Enter file or directory path to review",
                    allow_empty=False
                )
                if not target:
                    err_console.print("Operation cancelled.")
                    return
            
            # パスの存在確認
            target_path = Path(target)
            if not target_path.exists():
                err_console.print(f"Error: Path {target} does not exist.")
                return
            
            # ファイルリストの生成
            if target_path.is_file():
                files_to_review = [target_path]
                err_console.print(f"● Reviewing file: {target}")
            else:
                # ディレクトリ内の全ファイルを取得（サブディレクトリも含む）
                files_to_review = list(target_path.glob("**/*"))
                # フィルタリング（一般的なコードファイルのみ）
                code_extensions = ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp', '.html', '.css']
                files_to_review = [f for f in files_to_review if f.is_file() and f.suffix in code_extensions]
                err_console.print(f"● Reviewing {len(files_to_review)} files in directory: {target}")
            
            # ファイルが多すぎる場合は警告
            if len(files_to_review) > 10:
                confirm_large = self._confirm_action(
                    f"Found {len(files_to_review)} files to review. This may take a while. Continue?")
                if not confirm_large:
                    err_console.print("Operation cancelled.")
                    return
            
            # コンテキスト生成
            context = self.context.generate_context_for_prompt(
                user_prompt=f"Review code in {target}",
                max_context_size=8000
            )
            
            # ファイル内容の収集（最初の10ファイルのみ）
            file_contents = []
            for i, file_path in enumerate(files_to_review[:10]):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 相対パス取得を試みる
                    try:
                        relative_path = file_path.relative_to(self.context.root_dir)
                        display_path = str(relative_path)
                    except (ValueError, AttributeError):
                        # relative_to()が失敗した場合はファイル名のみ、またはフルパス
                        display_path = file_path.name if hasattr(file_path, 'name') else str(file_path)
                    
                    file_contents.append(f"File: {display_path}\n```\n{content}\n```\n")
                except Exception as e:
                    err_console.print(f"Warning: Could not read file {file_path}: {e}")

            
            # プロンプト生成
            prompt = prompt_manager.get_prompt("review_code").format(
                target=target,
                files_count=len(files_to_review),
                files_content="\n\n".join(file_contents)
            )
            
            err_console.print(f"● Analyzing code...")
            
            # LLM応答生成
            if hasattr(self, 'llm_manager') and self.llm_manager:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    context=context,
                    system_prompt=prompt_manager.get_prompt("review_system")
                )
                response_content = response.content if hasattr(response, 'content') else str(response)
            else:
                response_content = "Error: LLM Manager not available"
                err_console.print(response_content)
                return
            
            # レビュー結果の表示
            model_prefix = self._get_model_prefix()
            self._display_with_typewriter(response_content, model_prefix)
            
            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt=f"/review {target}",
                    claude_reply=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={"command": "review", "target": target}
                )
            
            # セッションに保存
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input=f"/review {target}",
                    ai_response=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="review",
                    metadata={"target": target}
                )
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "review command")
            else:
                err_console.print(f"Error in review command: {e}")
    
    # 以下はヘルパーメソッド
    
    def _extract_function_from_code(self, code, function_name):
        """コードから関数を抽出する
        
        Args:
            code: ソースコード
            function_name: 関数名
            
        Returns:
            抽出された関数のコード、見つからない場合はNone
        """
        try:
            # まず正規表現による抽出を試みる
            result = self._extract_function_regex(code, function_name)
            if result:
                return result
            
            # 正規表現で見つからない場合は、行ベースの解析を試みる
            lines = code.splitlines()
            in_function = False
            function_code = []
            indent_level = 0
            
            # 言語の判定（簡易版）
            if code.strip().startswith("<?php"):
                pattern = r"function\s+{0}\s*\(".format(function_name)
            else:  # デフォルトはPythonとして扱う
                pattern = r"def\s+{0}\s*\(".format(function_name)
            
            for line in lines:
                if not in_function:
                    # 関数定義行を探す
                    if re.search(pattern, line):
                        in_function = True
                        indent_level = len(line) - len(line.lstrip())
                        function_code.append(line)
                else:
                    # 関数終了を判定
                    if (line.strip() and 
                        len(line) - len(line.lstrip()) <= indent_level and 
                        not line.strip().startswith("#")):
                        break
                    
                    function_code.append(line)
            
            if function_code:
                return "\n".join(function_code)
            
            return None
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "extract function")
            else:
                err_console.print(f"Error extracting function: {e}")
            return None
    
    def _extract_function_regex(self, code, function_name):
        """正規表現を使ってコードから関数を抽出する
        
        Args:
            code: ソースコード
            function_name: 関数名
            
        Returns:
            抽出された関数のコード、見つからない場合はNone
        """
        try:
            # Python関数のパターン
            python_pattern = r"(def\s+{0}\s*\([^)]*\):(?:\s*(?:#.*)?(?:\n|$))(?:(?:\s+.*(?:\n|$))*)*)".format(
                re.escape(function_name))
            # JavaScript関数のパターン
            js_pattern = r"((?:async\s+)?function\s+{0}\s*\([^)]*\)\s*{{(?:[^{{}}]*(?:{{[^{{}}]*}})*)*}})".format(
                re.escape(function_name))
            # JavaScript Arrow関数のパターン
            arrow_pattern = r"((?:const|let|var)\s+{0}\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*(?:{{(?:[^{{}}]*(?:{{[^{{}}]*}})*)*}}|[^;]*);?)".format(
                re.escape(function_name))
            
            # 各パターンで検索
            for pattern in [python_pattern, js_pattern, arrow_pattern]:
                matches = re.search(pattern, code, re.DOTALL)
                if matches:
                    return matches.group(1)
            
            return None
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "regex extract function")
            else:
                err_console.print(f"Error in regex function extraction: {e}")
            return None
    
    def _replace_function_in_code(self, original_code, function_name, new_function):
        """コード内の関数を置き換える
        
        Args:
            original_code: 元のソースコード
            function_name: 置き換える関数名
            new_function: 新しい関数のコード
            
        Returns:
            置き換え後のコード
        """
        try:
            # まず正規表現による置換を試みる
            result = self._replace_function_regex(original_code, function_name, new_function)
            if result != original_code:  # 置換が行われた
                return result
            
            # 正規表現での置換に失敗した場合は、行ベースの解析で置換を試みる
            lines = original_code.splitlines()
            result_lines = []
            in_function = False
            skip_lines = 0
            indent_level = 0
            
            # 言語の判定（簡易版）
            if original_code.strip().startswith("<?php"):
                pattern = r"function\s+{0}\s*\(".format(function_name)
            else:  # デフォルトはPythonとして扱う
                pattern = r"def\s+{0}\s*\(".format(function_name)
            
            for i, line in enumerate(lines):
                if skip_lines > 0:
                    skip_lines -= 1
                    continue
                
                if not in_function:
                    # 関数定義行を探す
                    if re.search(pattern, line):
                        in_function = True
                        indent_level = len(line) - len(line.lstrip())
                        result_lines.append(new_function)
                        
                        # 関数終了行を探して、その行までスキップ
                        for j, next_line in enumerate(lines[i+1:], start=1):
                            if (next_line.strip() and 
                                len(next_line) - len(next_line.lstrip()) <= indent_level and 
                                not next_line.strip().startswith("#")):
                                skip_lines = j - 1
                                break
                    else:
                        result_lines.append(line)
                else:
                    # 関数終了を判定
                    if (line.strip() and 
                        len(line) - len(line.lstrip()) <= indent_level and 
                        not line.strip().startswith("#")):
                        in_function = False
                        result_lines.append(line)
                    # 関数内はスキップ
            
            return "\n".join(result_lines)
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "replace function")
            else:
                err_console.print(f"Error replacing function: {e}")
            return original_code
    
    def _replace_function_regex(self, original_code, function_name, new_function):
        """正規表現を使ってコード内の関数を置き換える
        
        Args:
            original_code: 元のソースコード
            function_name: 置き換える関数名
            new_function: 新しい関数のコード
            
        Returns:
            置き換え後のコード
        """
        try:
            # Python関数のパターン
            python_pattern = r"def\s+{0}\s*\([^)]*\):(?:\s*(?:#.*)?(?:\n|$))(?:(?:\s+.*(?:\n|$))*)*)".format(
                re.escape(function_name))
            # JavaScript関数のパターン
            js_pattern = r"(?:async\s+)?function\s+{0}\s*\([^)]*\)\s*{{(?:[^{{}}]*(?:{{[^{{}}]*}})*)*}}".format(
                re.escape(function_name))
            # JavaScript Arrow関数のパターン
            arrow_pattern = r"(?:const|let|var)\s+{0}\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*(?:{{(?:[^{{}}]*(?:{{[^{{}}]*}})*)*}}|[^;]*);?".format(
                re.escape(function_name))
            
            # 各パターンで置換を試みる
            for pattern in [python_pattern, js_pattern, arrow_pattern]:
                modified_code = re.sub(pattern, new_function, original_code, flags=re.DOTALL)
                if modified_code != original_code:
                    return modified_code
            
            return original_code
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "regex replace function")
            else:
                err_console.print(f"Error in regex function replacement: {e}")
            return original_code