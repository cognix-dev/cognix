"""
CLI チャット処理とワークフロー管理モジュール

このモジュールは、チャット処理とワークフロー管理機能を提供します。
具体的には以下の機能を含みます：

1. チャット対話処理 (handle_chat)
2. ワークフロー管理 (think, plan, write)
3. セミオート実装機能
"""

import os
import sys
import json
import time
from typing import Dict, List, Set, Any, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path

# 必須依存
from cognix.cli_shared import CLIModuleBase
from cognix.reference_parser import ReferenceParser
from cognix.prompt_templates import prompt_manager
from cognix.ui import StatusIndicator, Icon, FileIconMapper, get_risk_icon  # Phase 1: UI improvements

# Zen Step HUD（任意・存在しなければ無効）
try:
    from cognix.progress_zen import StepHUD
except Exception:
    StepHUD = None

from cognix.logger import console, err_console, logger  # stdout/stderr separation + debug log
from rich.text import Text
from cognix.theme_zen import GREEN, CYAN, YELLOW, MAGENTA, RESET  # ANSI color codes

class ChatWorkflowModule(CLIModuleBase):
    """チャット処理とワークフロー管理機能モジュール
    
    メインのチャット対話処理とワークフロー管理（think, plan, write）を担当します。
    また、セミオート実装機能も提供します。
    """
    
    def __init__(self):
        """基本初期化 - 引数なし
        
        依存オブジェクトはset_dependenciesで後から設定します
        """
        # 親クラスの初期化 - 引数なしで呼び出し
        super().__init__()
        
        # このモジュール固有の初期化
        # (依存オブジェクトに依存しない初期化のみ)
    
    def set_dependencies(self, cli):
        """CLI から依存オブジェクトを注入する
        
        ベースクラスで共通依存をセットし、
        追加で repository_analyzer / impact_analyzer / related_finder も明示的にコピー
        """
        # まずベース実装で config, memory, context, llm_manager などをコピー
        super().set_dependencies(cli)
        
        # 追加依存を明示的にコピー
        self.repository_analyzer = getattr(cli, 'repository_analyzer', None)
        self.impact_analyzer = getattr(cli, 'impact_analyzer', None)
        self.related_finder = getattr(cli, 'related_finder', None)
        self.session_manager = getattr(cli, 'session_manager', None)  # セッション管理
    
    def handle_chat(self, user_input: str):
        """チャット入力を処理する
        
        Args:
            user_input: ユーザー入力テキスト
        """
        try:
            # 複数行チャット入力のサポート
            if user_input.strip().upper() == "MULTI":
                err_console.print("💬 Multi-line chat mode")
                user_input = self.get_multiline_input(
                    "Enter your question or message:",
                    allow_empty=False
                )
                if not user_input:
                    return

            err_console.print("Thinking...")

            # 参照記法の解析を追加
            reference_parser = ReferenceParser(self.context)
            parsed_refs = reference_parser.parse(user_input)

            # 変数を事前に初期化（重要：参照記法がない場合でも定義）
            has_errors = False
            has_valid_content = False
            error_messages = []

            # 参照記法が見つかった場合の処理
            if parsed_refs.has_references:
                err_console.print("\n🔎 Processing references...")
                
                # ファイル参照をチェック
                for file_ref in parsed_refs.files:
                    if not file_ref.exists:
                        error_messages.append(f"❌ File not found: {file_ref.filename}")
                        has_errors = True
                    else:
                        has_valid_content = True
                
                # 関数参照をチェック
                for func_ref in parsed_refs.functions:
                    if not func_ref.found:
                        error_messages.append(f"❌ Function not found: #{func_ref.function_name}")
                        has_errors = True
                    else:
                        has_valid_content = True
                                
                # エラーメッセージを表示（ただし処理は継続）
                if error_messages:
                    for error_msg in error_messages:
                        err_console.print(error_msg)
                
                # 有効なコンテンツがある場合は処理を継続
                if has_valid_content:
                    if parsed_refs.context_text:
                        err_console.print(parsed_refs.context_text)
                        err_console.print()
                elif has_errors and not has_valid_content:
                    # 全ての参照が失敗した場合のみ中断
                    err_console.print("\nAll references failed. Please check your reference syntax.")
                    return

            # コンテキスト生成（修正：正しいシグネチャで呼び出し）
            base_context = self.context.generate_context_for_prompt(user_input)
            
            # 参照記法のコンテキストを結合（有効なコンテンツがある場合のみ）
            enhanced_context = base_context
            if parsed_refs.has_references and parsed_refs.context_text:
                enhanced_context = f"{base_context}\n\n=== Referenced Content ===\n{parsed_refs.context_text}"

            # 会話履歴の管理（修正：正しいメソッド名で呼び出し）
            conversation_history = []
            if hasattr(self, 'memory') and self.memory:
                conversation_history = self.memory.get_conversation_context(5)
                
            # システムプロンプトの強化
            base_system_prompt = self.config.get_system_prompt("default") if hasattr(self, 'config') else ""

            # 参照コンテキスト（ユーザー提供のファイル内容）
            reference_context = ""
            if parsed_refs.has_references and has_valid_content:
                reference_context = f"""CRITICAL: The user has provided specific file content below using reference notation.
The following content is the ACTUAL file content from the user's project:
{parsed_refs.context_text}
You MUST base your analysis on this exact content shown above. 
Do NOT make assumptions about what the file might contain based on its name.
The content displayed above is the current, real state of the user's files."""

            # セッションコンテキスト
            session_context = ""
            if hasattr(self, 'session_manager') and self.session_manager:
                stats = self.session_manager.get_session_stats()
                if stats and stats.get('total_entries', 0) > 0:
                    session_context = f"""

IMPORTANT COGNIX SESSION CONTEXT:
- You are operating in Cognix, which has advanced session management
- This session has been restored with {stats['total_entries']} previous interactions
- All conversation history and context from previous sessions is available to you
- When users reference past conversations, you can naturally access them from your memory
- Do NOT say information "won't be preserved" - in Cognix, it IS preserved across sessions
- Respond naturally as if this is one continuous conversation"""

            # システムプロンプトの構築（参照コンテキストを最優先配置）
            if reference_context:
                enhanced_system_prompt = reference_context + "\n\n" + base_system_prompt + session_context
            else:
                enhanced_system_prompt = base_system_prompt + session_context

            # LLM応答生成
            _last_usage = None  # トークン使用量（ストリーミング時はNone）
            if hasattr(self, 'llm_manager') and self.llm_manager:
                if self.config.get("stream_responses", True):
                    # ストリーミング応答
                    stream_gen = self.llm_manager.stream_response(
                        prompt=user_input,
                        context=enhanced_context,
                        system_prompt=enhanced_system_prompt,
                        conversation_history=conversation_history
                    )

                    model_prefix = self._get_model_prefix()
                    full_response = self._stream_with_typewriter(stream_gen, model_prefix)
                else:
                    # 通常応答
                    response = self.llm_manager.generate_response(
                        prompt=user_input,
                        context=enhanced_context,
                        system_prompt=enhanced_system_prompt,
                        conversation_history=conversation_history
                    )
                    full_response = response.content if hasattr(response, 'content') else str(response)
                    _last_usage = getattr(response, 'usage', None)

                    model_prefix = self._get_model_prefix()
                    self._display_with_typewriter(full_response, model_prefix)
            else:
                full_response = "Error: LLM Manager not available"
                err_console.print(full_response)

            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt=user_input,
                    claude_reply=full_response,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={
                        "has_references": parsed_refs.has_references,
                        "referenced_files": [f.filename for f in parsed_refs.files if f.exists],
                        "referenced_functions": [f.function_name for f in parsed_refs.functions if f.found],
                        "reference_errors": len(error_messages) if error_messages else 0
                    }
                )

            # セッションに保存（追加）
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input=user_input,
                    ai_response=full_response,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="chat",
                    target_files=None,
                    metadata={
                        "has_references": parsed_refs.has_references,
                        "referenced_files": [f.filename for f in parsed_refs.files if f.exists],
                        "referenced_functions": [f.function_name for f in parsed_refs.functions if f.found],
                        "reference_errors": len(error_messages) if error_messages else 0
                    },
                    workflow_state=None,
                    tokens_used=_last_usage,
                )

        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "chat interaction")
            else:
                err_console.print(f"Error in chat: {e}")

    def cmd_think(self, args):
        """Problem analysis (Step 1 of think→plan→write workflow)"""
        # 引数処理
        if isinstance(args, str):
            args = args.strip()
            goal = args if args else None
        elif isinstance(args, list):
            goal = " ".join(args).strip() if args else None
        else:
            goal = None
            
        # 目標の取得
        if not goal:
            goal = self.get_multiline_input(
                "What would you like me to think about?",
                allow_empty=False
            )
            if not goal:
                err_console.print("Operation cancelled.")
                return
        
        err_console.print(f"Analyzing: {goal}")
        
        # ワークフロー状態の初期化
        if hasattr(self, 'shared_state') and self.shared_state:
            self.shared_state.workflow_state["current_goal"] = goal
            self.shared_state.workflow_state["think_result"] = None
            self.shared_state.workflow_state["plan_result"] = None
        
        # コンテキスト生成（修正：user_promptを渡す）
        context = self.context.generate_context_for_prompt(goal)
        
        # プロンプト生成
        try:
            prompt_data = prompt_manager.render_prompt(
                "problem_analysis",
                {"goal": goal}
            )
            
            if not prompt_data:
                err_console.print("Error: Failed to generate analysis prompt")
                return
                
            prompt = prompt_data["prompt"]
            system_prompt = prompt_data["system_prompt"]
            
        except Exception as e:
            err_console.print(f"Error generating prompt: {e}")
            return
        
        try:
            # LLM応答生成
            if hasattr(self, 'llm_manager') and self.llm_manager:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    context=context,
                    system_prompt=system_prompt
                )
                response_content = response.content if hasattr(response, 'content') else str(response)
            else:
                response_content = "Error: LLM Manager not available"
                err_console.print(response_content)
                return
                
            # ワークフロー状態の更新
            if hasattr(self, 'shared_state') and self.shared_state:
                self.shared_state.workflow_state["think_result"] = response_content
            
            # 結果表示
            model_prefix = self._get_model_prefix()
            self._display_with_typewriter(response_content, model_prefix)
            
            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt=f"/think {goal}",
                    claude_reply=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={"command": "think", "goal": goal}
                )
                
            # セッションに保存
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input=f"/think {goal}",
                    ai_response=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="think",
                    metadata={"goal": goal},
                    tokens_used=getattr(response, 'usage', None),
                )
                
            err_console.print(Text.from_ansi(f"\n Next step: {GREEN}/plan{RESET}"))
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "think command")
            else:
                err_console.print(f"Error in think command: {e}")

    def cmd_plan(self, args):
        """Implementation planning (Step 2 of think→plan→write workflow)"""
        # 前のステップの結果を確認
        if hasattr(self, 'shared_state') and self.shared_state:
            if not self.shared_state.workflow_state.get("think_result"):
                err_console.print(StatusIndicator.error("Please run /think first to analyze your goal."))
                return
                
            goal = self.shared_state.workflow_state.get("current_goal", "")
            think_result = self.shared_state.workflow_state.get("think_result", "")
        else:
            err_console.print("Error: Workflow state not available")
            return
            
        err_console.print(f"📋 Creating implementation plan for: {goal}")
        
        # コンテキスト生成（修正：user_promptを渡す）
        context = self.context.generate_context_for_prompt(goal)
        
        # プロンプト生成
        prompt_data = prompt_manager.render_prompt(
            "implementation_plan",
            {
                "goal": goal,
                "analysis": think_result
            }
        )
        prompt = prompt_data["prompt"]
        system_prompt = prompt_data["system_prompt"]
        
        try:
            # LLM応答生成
            if hasattr(self, 'llm_manager') and self.llm_manager:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    context=context,
                    system_prompt=system_prompt
                )
                response_content = response.content if hasattr(response, 'content') else str(response)
            else:
                response_content = "Error: LLM Manager not available"
                err_console.print(response_content)
                return
                
            # ワークフロー状態の更新
            if hasattr(self, 'shared_state') and self.shared_state:
                self.shared_state.workflow_state["plan_result"] = response_content
            
            # 結果表示
            model_prefix = self._get_model_prefix()
            self._display_with_typewriter(response_content, model_prefix)
            
            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt="/plan",
                    claude_reply=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={"command": "plan", "goal": goal}
                )
                
            # セッションに保存
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input="/plan",
                    ai_response=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="plan",
                    metadata={"goal": goal},
                    tokens_used=getattr(response, 'usage', None),
                )
                
            err_console.print(Text.from_ansi(f"\n Next step: {GREEN}/write [filename]{RESET}"))
            
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "plan command")
            else:
                err_console.print(f"Error in plan command: {e}")

    def cmd_write(self, args):
        """Code generation (Step 3 of think→plan→write workflow)"""
        # 前のステップの結果を確認
        if hasattr(self, 'shared_state') and self.shared_state:
            if not self.shared_state.workflow_state.get("plan_result"):
                err_console.print(StatusIndicator.error("Please run /plan first to create an implementation plan."))
                return
                
            goal = self.shared_state.workflow_state.get("current_goal", "")
            think_result = self.shared_state.workflow_state.get("think_result", "")
            plan_result = self.shared_state.workflow_state.get("plan_result", "")
        else:
            err_console.print("Error: Workflow state not available")
            return
            
        # ファイル名の取得
        if isinstance(args, str):
            filename = args.strip()
        elif isinstance(args, list):
            filename = " ".join(args).strip()
        else:
            filename = ""
            
        if not filename:
            filename = input("Enter filename to write to: ")
            if not filename:
                err_console.print("Operation cancelled.")
                return
                
        err_console.print(f"✍️ Writing implementation to: {filename}")
        
        # コンテキスト生成（修正：user_promptを渡す）
        context = self.context.generate_context_for_prompt(f"{goal}\n{filename}")
        
        # プロンプト生成
        prompt_data = prompt_manager.render_prompt(
            "code_generation",
            {
                "goal": goal,
                "analysis": think_result,
                "plan": plan_result,
                "additional_context": f"Target file: {filename}"
            }
        )
        prompt = prompt_data["prompt"]
        system_prompt = prompt_data["system_prompt"]
        
        try:
            # LLM応答生成
            if hasattr(self, 'llm_manager') and self.llm_manager:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    context=context,
                    system_prompt=system_prompt
                )
                response_content = response.content if hasattr(response, 'content') else str(response)
            else:
                response_content = "Error: LLM Manager not available"
                err_console.print(response_content)
                return
                
            # 結果表示
            model_prefix = self._get_model_prefix()
            self._display_with_typewriter(response_content, model_prefix)
            
            # ファイルへの保存確認
            confirmation = input(f"\nSave this implementation to {filename}? (y/n): ")
            if confirmation.lower() == 'y':
                # ファイル保存処理
                file_path = Path(filename)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(response_content)
                    
                err_console.print(f"✅ Implementation saved to {filename}")
                
                # ワークフロー状態のクリア（一連の作業が完了）
                if hasattr(self, 'shared_state') and self.shared_state:
                    self.cmd_clear_workflow([])
            else:
                err_console.print("File not saved.")
            
            # メモリに保存
            if hasattr(self, 'memory') and self.memory:
                self.memory.add_entry(
                    user_prompt=f"/write {filename}",
                    claude_reply=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    metadata={"command": "write", "filename": filename, "goal": goal}
                )
                
            # セッションに保存
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.add_entry(
                    user_input=f"/write {filename}",
                    ai_response=response_content,
                    model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                    command_type="write",
                    metadata={"filename": filename, "goal": goal},
                    tokens_used=getattr(response, 'usage', None),
                )
                
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "write command")
            else:
                err_console.print(f"Error in write command: {e}")

    def cmd_workflow_status(self, args):
        """Display workflow status"""
        if hasattr(self, 'shared_state') and self.shared_state:
            goal = self.shared_state.workflow_state.get("current_goal")
            think_done = bool(self.shared_state.workflow_state.get("think_result"))
            plan_done = bool(self.shared_state.workflow_state.get("plan_result"))
            
            err_console.print("\n📊 Current Workflow Status:")
            err_console.print(f"Goal: {goal if goal else 'Not set'}")
            err_console.print(f"Step 1 (Think): {'✅ Completed' if think_done else '❌ Not completed'}")
            err_console.print(f"Step 2 (Plan): {'✅ Completed' if plan_done else '❌ Not completed'}")
            err_console.print(f"Step 3 (Write): {'⏳ Ready to start' if plan_done else '❌ Not ready'}")
            
            # 次のステップのガイダンス
            if not goal:
                err_console.print(Text.from_ansi(f"\nNext step: {GREEN}/think [your goal]{RESET}"))
            elif not think_done:
                err_console.print(Text.from_ansi(f"\nNext step: {GREEN}/think {goal}{RESET}"))
            elif not plan_done:
                err_console.print(Text.from_ansi(f"\nNext step: {GREEN}/plan{RESET}"))
            else:
                err_console.print(Text.from_ansi(f"\nNext step: {GREEN}/write [filename]{RESET}"))
        else:
            err_console.print("Error: Workflow state not available")

    def cmd_clear_workflow(self, args):
        """Clear workflow state"""
        if hasattr(self, 'shared_state') and self.shared_state:
            # ワークフロー状態をリセット
            self.shared_state.workflow_state["current_goal"] = None
            self.shared_state.workflow_state["think_result"] = None
            self.shared_state.workflow_state["plan_result"] = None
            
            err_console.print("✅ Workflow state cleared. You can start a new workflow with /think.")
        else:
            err_console.print("Error: Workflow state not available")

    def cmd_semi_auto(self, args):
        """Automatic implementation with AI assistance
        - Two-step verification prompt (empowering users to make decisions)
        - Detailed intermediate output (process visualization)
        - Supports @filename syntax to load spec from file
        """

        # 引数処理
        if isinstance(args, str):
            goal = args.strip() if args else None
        elif isinstance(args, list):
            goal = " ".join(args).strip() if args else None
        else:
            goal = None
            
        if not goal:
            goal = self.get_multiline_input(
                "What would you like me to implement automatically?",
                allow_empty=False
            )
            if not goal:
                err_console.print("Operation cancelled.")
                return
        
        # @ファイル参照の処理
        if goal.startswith('@'):
            spec_filepath = goal[1:].strip()  # @を除去 + 前後空白除去
            logger.debug(f"[@File Reference] Detected: {spec_filepath}")
            
            # 空パスチェック
            if not spec_filepath:
                err_console.print("❌ No spec file specified. Usage: /make @filename.md")
                logger.debug("[@File Reference] ERROR: Empty filepath")
                return
            
            if os.path.exists(spec_filepath):
                try:
                    with open(spec_filepath, 'r', encoding='utf-8') as f:
                        goal = f.read()
                    
                    # 空ファイルチェック
                    if not goal.strip():
                        err_console.print(f"❌ Spec file is empty: {spec_filepath}")
                        logger.debug(f"[@File Reference] ERROR: File is empty: {spec_filepath}")
                        return
                    
                    err_console.print(Text.from_ansi(f"{GREEN}✓ Loaded: {spec_filepath} ({len(goal):,} chars) successfully!{RESET}"))
                    logger.debug(f"[@File Reference] SUCCESS: Loaded {spec_filepath} ({len(goal):,} chars)")
                except UnicodeDecodeError:
                    err_console.print(f"❌ Failed to read spec file (encoding issue, UTF-8 expected): {spec_filepath}")
                    logger.debug(f"[@File Reference] ERROR: UnicodeDecodeError for {spec_filepath}")
                    return
                except Exception as e:
                    err_console.print(f"❌ Failed to read spec file: {e}")
                    logger.debug(f"[@File Reference] ERROR: {e}")
                    return
            else:
                err_console.print(f"❌ Spec file not found: {spec_filepath}")
                logger.debug(f"[@File Reference] ERROR: File not found: {spec_filepath}")
                return
        
        try:
            # Import semi-auto engine
            from cognix.semi_auto_engine import SemiAutoEngine, SemiAutoResult
            
            # Initialize engine
            self.engine = SemiAutoEngine(
                llm_manager=self.llm_manager,
                context=self.context,
                impact_analyzer=getattr(self, 'impact_analyzer', None),
                related_finder=getattr(self, 'related_finder', None),
                diff_engine=getattr(self, 'diff_engine', None),
                repository_analyzer=getattr(self, 'repository_analyzer', None),
                config=self.config
            )
            
            # 開始メッセージ（アイコン統一 + 改行追加）
            err_console.print()  # 空行
            err_console.print(f"{Icon.ROBOT.value} Starting automated implementation...")
            
            # ⭐ Zen HUD: ゴール表示を短縮（最初の行、最大100文字）
            goal_first_line = goal.split('\n')[0].strip()
            if len(goal_first_line) > 100:
                goal_display = goal_first_line[:97] + "..."
            else:
                goal_display = goal_first_line
            err_console.print(f"{Icon.SEARCH.value} Goal: {goal_display}")
            
            err_console.print()  # 空行
            
            # Execute implementation
            result = self.engine.execute_semi_auto_implementation(goal)
            
            # エラーチェック（アイコン統一）
            if not result.success:
                err_console.print(f"{Icon.ERROR.value} auto implementation failed: {result.error}")
                return
            
            
            # Phase 2: Analysis Results削除（Zen HUD設計）
            # 分析結果は内部で処理され、最終的なQuality/Recommendationsのみ表示
            
            
            
            # Phase 2: Zen HUD要約表示のみ（Diff詳細は削除）
            # 設計書: 完了後は要約だけ（Lint/Diff推定/Secrets）
            
            
            # Zen HUD: Quality要約 (新フォーマット)
            if result.quality_scores:
                file_count = len(result.quality_scores)
                avg_score = int(sum(result.quality_scores.values()) * 100 / len(result.quality_scores))
                console.print()  # 空行
                console.print(Text.from_ansi(f"{GREEN}✓ Code generation completed successfully!{RESET}"))
                console.print()  # 空行
                
                # ⭐ Zen HUD: Lint/Review サマリー
                if result.zen_summary:
                    zen = result.zen_summary
                    
                    # Lint行
                    lint_info = zen.get("lint", {})
                    if lint_info.get("initial", 0) > 0:
                        if lint_info.get("final", 0) == 0:
                            console.print(Text.from_ansi(f"ⓘ Lint check : {lint_info['initial']} error(s) → {GREEN}✓ auto-fixed{RESET}"))
                        else:
                            console.print(Text.from_ansi(f"ⓘ Lint check : {lint_info['initial']} error(s) → {lint_info['final']} remaining"))
                    else:
                        console.print(Text.from_ansi(f"ⓘ Lint check : {GREEN}✓ no issues{RESET}"))
                    
                    # Review行（改善版：増えた場合も考慮）
                    review_info = zen.get("review", {})
                    initial = review_info.get("initial", 0)
                    final = review_info.get("final", 0)
                    
                    if initial == 0 and final == 0:
                        console.print(Text.from_ansi(f"ⓘ Code review : {GREEN}✓ no issues{RESET}"))
                    elif final == 0:
                        # 全て修正済み
                        console.print(Text.from_ansi(f"ⓘ Code review : {initial} issue(s) → {GREEN}✓ auto-fixed{RESET}"))
                    elif final < initial:
                        # 一部修正（減った）
                        fixed_count = initial - final
                        console.print(Text.from_ansi(f"ⓘ Code review : {initial} issue(s) → {GREEN}✓ {fixed_count} fixed{RESET} ({final} remaining)"))
                    else:
                        # 同じか増えた場合はシンプルに表示
                        console.print(Text.from_ansi(f"ⓘ Code review : {final} issue(s) remaining"))
                
                # 🆕 Test行（Lint→Review→Test→ファイル数 の順序）
                if result.zen_summary:
                    test_info = result.zen_summary.get("test", {})
                    if not test_info.get("skipped") and test_info.get("total", 0) > 0:
                        t_passed = test_info.get("passed", 0)
                        t_failed_initial = test_info.get("failed_initial", 0)
                        t_failed_final = test_info.get("failed_final", 0)
                        
                        if t_failed_final == 0:
                            if t_failed_initial > 0:
                                console.print(Text.from_ansi(
                                    f"ⓘ Test check  : {t_passed} passed, {t_failed_initial} failed → {GREEN}✓ auto-fixed{RESET}"
                                ))
                            else:
                                console.print(Text.from_ansi(
                                    f"ⓘ Test check  : {GREEN}✓ {t_passed} passed{RESET}"
                                ))
                        else:
                            console.print(Text.from_ansi(
                                f"ⓘ Test check  : {t_passed} passed, {t_failed_final} failed"
                            ))
                
                # ファイル数表示
                file_word = "file" if file_count == 1 else "files"
                console.print(Text.from_ansi(f"{GREEN}✓ Generated {file_count} {file_word}{RESET}"))
                
                console.print()  # 空行
                
            # Zen HUD: Recommendations 1行・最大3件
            if result.recommendations:
                from cognix import hud_components as hud
                compact = hud.recommendations_compact(result.recommendations, max_items=3)
                if compact:
                    console.print(Text.from_ansi(f"{YELLOW}⊹ Recommendations:{RESET} {compact}"))
                    console.print()  # 空行
            
            # ==========================================
            # 改善案A: 品質サマリー表示（承認前）
            # ==========================================
            if result.quality_scores:
                console.print(Text.from_ansi(f"Quality Scores:"))
                
                for filename, score in result.quality_scores.items():
                    # パーセント表示（0.90 → 90%）
                    score_percent = int(score * 100)
                    
                    # 色とグレード判定
                    if score >= 0.9:
                        color = GREEN
                        grade = "Excellent"
                    elif score >= 0.75:
                        color = GREEN
                        grade = "Good"
                    elif score >= 0.6:
                        color = YELLOW
                        grade = "Fair"
                    else:
                        color = YELLOW
                        grade = "Needs Review"
                    
                    console.print(Text.from_ansi(
                        f"  {color}{filename}{RESET}: {score_percent}% {color}{grade}{RESET}"
                    ))
                
                console.print()  # 空行
            
            # ==========================================
            # 改善案A: 影響分析サマリー表示（承認前）
            # ==========================================
            if result.impact_analysis:
                console.print(Text.from_ansi(f"{GREEN}Impact Analysis:{RESET}"))
                
                for filename, impact in result.impact_analysis.items():
                    risk_level = impact.get('risk_level', 'LOW')
                    
                    if risk_level == 'HIGH':
                        color = YELLOW
                        icon = "◼"  # 高リスク
                    elif risk_level == 'MEDIUM':
                        color = YELLOW
                        icon = "◆"  # 中リスク
                    else:
                        color = GREEN
                        icon = "◇"  # 低リスク
                    
                    console.print(Text.from_ansi(
                        f"  {color}{icon} {filename}: {risk_level} RISK{RESET}"
                    ))
                
                console.print()  # 空行
            
            
            
            # Phase 2: 最終メニュー（ループ版 - [t] Try again対応）
            max_lint_attempts = 3
            lint_attempt = 0
            prev_lint_fail_count = None
            current_lint_result = getattr(result, 'lint_result', None)  # ← 初回のLint結果を取得
            
            while True:  # ← ループ構造に変更
                console.print("Next:")
                console.print(Text.from_ansi(f"  [{CYAN}a{RESET}] Apply"))
                console.print(Text.from_ansi(f"  [{CYAN}r{RESET}] Reject"))
                console.print(Text.from_ansi(f"  [{CYAN}v{RESET}] View details"))
                
                # [t] Try again選択肢（Syntax errors + Quality issues + Code review issues チェック）
                # Lint結果からSyntax error数を取得
                lint_error_count = 0
                if current_lint_result:
                    lint_error_count = len(current_lint_result.get('errors', []))
                
                # Quality issues のカウント
                quality_issue_count = 0
                if hasattr(result, 'quality_scores') and result.quality_scores:
                    for filename, score in result.quality_scores.items():
                        if score < 0.70:  # 70%未満は問題あり
                            quality_issue_count += 1
                
                # ⭐ Code review remaining issues のカウント（Zen HUD対応）
                review_remaining_count = 0
                if hasattr(result, 'zen_summary') and result.zen_summary:
                    review_remaining_count = result.zen_summary.get("review", {}).get("final", 0)
                
                # Syntax errors も Quality issues も Code review issues も 0 の場合のみ [t] 非表示
                show_try_again = True
                total_issues = lint_error_count + quality_issue_count + review_remaining_count
                if current_lint_result is not None and total_issues == 0:
                    # Lint実行済み、かつ、全て0の場合のみ非表示
                    show_try_again = False
                
                if not show_try_again:
                    # [t]を表示しない
                    pass
                elif lint_attempt >= max_lint_attempts:
                    # 最大試行回数到達時は disabled表示
                    console.print(Text.from_ansi(f"  [{CYAN}t{RESET}] Try again (disabled - max attempts)"))
                elif lint_attempt > 0:
                    # 試行回数表示
                    console.print(Text.from_ansi(f"  [{CYAN}t{RESET}] Try again ({lint_attempt}/{max_lint_attempts} attempts used)"))
                else:
                    # 初回表示（何を修正するか明示）
                    # ⭐ Zen HUD対応: review_remaining_countも含める
                    issue_parts = []
                    if lint_error_count > 0:
                        issue_parts.append(f"{lint_error_count} syntax error(s)")
                    if quality_issue_count > 0:
                        issue_parts.append(f"{quality_issue_count} quality issue(s)")
                    if review_remaining_count > 0:
                        issue_parts.append(f"{review_remaining_count} review issue(s)")
                    
                    if issue_parts:
                        console.print(Text.from_ansi(f"  [{CYAN}t{RESET}] Try again (fix {' + '.join(issue_parts)})"))
                    else:
                        console.print(Text.from_ansi(f"  [{CYAN}t{RESET}] Try again"))
                
                # 非対話モード: auto_mode=True なら自動Apply
                _auto = getattr(getattr(self, '_cli_instance', None), 'auto_mode', False)
                if _auto:
                    err_console.print(f"\n[auto] Auto-applying (non-interactive mode)...")
                    choice = "a"
                else:
                    choice = input("\nYour choice: ").strip().lower()
                
                if choice == "r":
                    err_console.print(Text.from_ansi(f"{MAGENTA}✕ Implementation rejected by user{RESET}"))
                    err_console.print()  # 改行を追加
                    return
                
                elif choice == "v":
                    # View details フロー
                    detail_result = self._handle_review_details(result)
                    
                    if detail_result == "applied":
                        # Apply済み: 終了
                        return
                    elif detail_result == "rejected":
                        # Reject済み: 終了
                        return
                    elif detail_result == "back":
                        # Back: メニューに戻る
                        continue
                    else:
                        # 予期しない戻り値
                        continue
                
                elif choice == "t":
                    # ⭐ 全ての問題が0の場合のみ「No need to retry」
                    if current_lint_result is not None and total_issues == 0:
                        err_console.print(f"{Icon.SUCCESS.value} All issues are already resolved. No need to retry.")
                        continue
                    
                    # Lint再実行処理
                    if lint_attempt >= max_lint_attempts:
                        err_console.print(f"{Icon.WARNING.value} Max attempts reached ({max_lint_attempts}/{max_lint_attempts}). Please choose [a]pply or [r]eject.")
                        continue
                    
                    lint_attempt += 1
                    err_console.print()  # 空行（StepHUD表示前のセパレーション）
                    
                    # 全チェック再実行（Gチェック → Import → Lint → Quality → 総合レビュー）
                    # ⭐ StepHUDが進捗表示を担当（Code Generationスタイル）
                    updated_code, new_lint_result, new_quality_scores = self.engine.retry_full_validation(
                        result.generated_code,
                        goal,  # 総合レビューで使用
                        current_lint_result,
                        attempt=lint_attempt,
                        max_attempts=max_lint_attempts
                    )
                    
                    # current_lint_resultを更新（次のループで使用）
                    current_lint_result = new_lint_result
                    
                    # 結果を更新（SemiAutoResultは不変なので新規作成）
                    # SemiAutoResult is already imported at the top
                    # ⭐ zen_summaryをengineから取得
                    new_zen_summary = getattr(self.engine, '_zen_summary', None)
                    result = SemiAutoResult(
                        success=True,
                        analysis=result.analysis,
                        generated_code=updated_code,
                        quality_scores=new_quality_scores if new_quality_scores else result.quality_scores,
                        recommendations=result.recommendations,
                        error=result.error,
                        impact_analysis=result.impact_analysis,
                        lint_result=current_lint_result,
                        zen_summary=new_zen_summary,  # ⭐ Zen HUD対応
                        test_result=new_zen_summary.get("test") if new_zen_summary else None  # 🆕 テスト結果引き継ぎ
                    )
                    
                    # ⭐ Try again後のZen HUDサマリー表示
                    if new_zen_summary:
                        console.print()  # 空行
                        
                        # Lint行
                        lint_info = new_zen_summary.get("lint", {})
                        if lint_info.get("initial", 0) > 0:
                            if lint_info.get("final", 0) == 0:
                                console.print(Text.from_ansi(f"ⓘ Lint check : {lint_info['initial']} error(s) → {GREEN}✓ auto-fixed{RESET}"))
                            else:
                                console.print(Text.from_ansi(f"ⓘ Lint check : {lint_info['initial']} error(s) → {lint_info['final']} remaining"))
                        else:
                            console.print(Text.from_ansi(f"ⓘ Lint check : {GREEN}✓ no issues{RESET}"))
                        
                        # Review行（改善版：増えた場合も考慮）
                        review_info = new_zen_summary.get("review", {})
                        initial = review_info.get("initial", 0)
                        final = review_info.get("final", 0)
                        
                        if initial == 0 and final == 0:
                            console.print(Text.from_ansi(f"ⓘ Code review : {GREEN}✓ no issues{RESET}"))
                        elif final == 0:
                            # 全て修正済み
                            console.print(Text.from_ansi(f"ⓘ Code review : {initial} issue(s) → {GREEN}✓ auto-fixed{RESET}"))
                        elif final < initial:
                            # 一部修正（減った）
                            fixed_count = initial - final
                            console.print(Text.from_ansi(f"ⓘ Code review : {initial} issue(s) → {GREEN}✓ {fixed_count} fixed{RESET} ({final} remaining)"))
                        else:
                            # 同じか増えた場合はシンプルに表示
                            console.print(Text.from_ansi(f"ⓘ Code review : {final} issue(s) remaining"))
                        
                        # 🆕 Test行（retry後）（Lint→Review→Test→ファイル数 の順序）
                        if new_zen_summary:
                            test_info = new_zen_summary.get("test", {})
                            if not test_info.get("skipped") and test_info.get("total", 0) > 0:
                                t_passed = test_info.get("passed", 0)
                                t_failed_initial = test_info.get("failed_initial", 0)
                                t_failed_final = test_info.get("failed_final", 0)
                                
                                if t_failed_final == 0:
                                    if t_failed_initial > 0:
                                        console.print(Text.from_ansi(
                                            f"ⓘ Test check  : {t_passed} passed, {t_failed_initial} failed → {GREEN}✓ auto-fixed{RESET}"
                                        ))
                                    else:
                                        console.print(Text.from_ansi(
                                            f"ⓘ Test check  : {GREEN}✓ {t_passed} passed{RESET}"
                                        ))
                                else:
                                    console.print(Text.from_ansi(
                                        f"ⓘ Test check  : {t_passed} passed, {t_failed_final} failed"
                                    ))
                        
                        # ファイル数表示
                        if result.quality_scores:
                            file_count = len(result.quality_scores)
                            file_word = "file" if file_count == 1 else "files"
                            console.print(Text.from_ansi(f"{GREEN}✓ Validated {file_count} {file_word}{RESET}"))
                        
                        console.print()  # 空行
                    
                    # ループ継続
                    continue
                
                elif choice == "a":
                    # Apply処理へ
                    break  # ← ループを抜ける
                
                else:
                    err_console.print(f"{Icon.ERROR.value} Invalid choice. Please try again.")
                    continue
            
            # choice == "a" の場合のみここに到達
            # choice == "a" の場合のみ続行
            
            # コード適用（アイコン統一）
            err_console.print(f"\n{Icon.GEAR.value} Applying implementation...")
            final_result = self.engine.apply_generated_code(result)
            
            if final_result.success:
                err_console.print(Text.from_ansi(f"{GREEN}{Icon.SUCCESS.value} Auto implementation completed successfully!{RESET}"))
                err_console.print()  # 空行を追加
                
                if final_result.applied_files:
                    err_console.print(f"{Icon.FOLDER.value} Files created/modified: {len(final_result.applied_files)}")
                    for file in final_result.applied_files:
                        err_console.print(f"   • {file}")
                    err_console.print()  # 空行を追加
                
                if final_result.backup_paths:
                    err_console.print(f"{Icon.PACKAGE.value} Backups created: {len(final_result.backup_paths)}")
                    # バックアップファイルの個別パス表示（Files created/modifiedと同じフォーマット）
                    for backup_path in final_result.backup_paths:
                        err_console.print(f"   • {backup_path}")
                    err_console.print()  # 空行を追加
                                    
                # メモリ保存
                if hasattr(self, 'memory') and self.memory:
                    self.memory.add_entry(
                        user_prompt=f"Semi-auto implementation: {goal}",
                        claude_reply=f"Implementation completed with {len(final_result.applied_files or [])} files",
                        model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                        metadata={
                            "command_type": "semi_auto",
                            "files_generated": final_result.applied_files,
                            "quality_scores": final_result.quality_scores
                        }
                    )
                
                # セッション保存
                if hasattr(self, 'session_manager') and self.session_manager:
                    self.session_manager.add_entry(
                        user_input=f"/semi-auto {goal}",
                        ai_response=f"Implementation completed successfully",
                        model_used=getattr(self.llm_manager, 'current_model', 'unknown'),
                        command_type="semi_auto",
                        target_files=final_result.applied_files or [],
                        metadata={
                            "goal": goal,
                            "files_count": len(final_result.applied_files or []),
                            "quality_average": sum(final_result.quality_scores.values()) / len(final_result.quality_scores) if final_result.quality_scores else 0
                        }
                    )
                
            else:
                err_console.print(f"{Icon.ERROR.value} Failed to apply implementation: {final_result.error}")
                    
        except ImportError:
            err_console.print(f"{Icon.ERROR.value} Semi-auto engine not available. Please check installation.")

        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, "semi-auto command")
            else:
                err_console.print(f"Error in semi-auto command: {e}")
        finally:
            pass  # HUD管理はsemi_auto_engineに委譲


    def _handle_review_details(self, result):
        """Review details インタラクティブフロー（設計書準拠）
        
        Args:
            result: 生成結果オブジェクト
        """
        from cognix.diff_viewer import DiffViewer
        

        # files_dataを事前生成（Impact Analysis用）
        files_data = []
        for filename in result.generated_code.keys():
            file_path = Path(filename)
            if file_path.exists():
                old_content = file_path.read_text(encoding='utf-8')
                new_content = result.generated_code[filename]
                
                old_lines = old_content.splitlines()
                new_lines = new_content.splitlines()
                
                additions = len([l for l in new_lines if l not in old_lines])
                deletions = len([l for l in old_lines if l not in new_lines])
                
                files_data.append({
                    'name': filename,
                    'added': additions,
                    'removed': deletions
                })
            else:
                line_count = len(result.generated_code[filename].splitlines())
                files_data.append({
                    'name': filename,
                    'added': line_count,
                    'removed': 0
                })
        
        # Impact Analysisが利用可能かチェック
        has_impact_analysis = bool(result.impact_analysis if hasattr(result, 'impact_analysis') else False)

        while True:
            # Zen: ファイル一覧（余白で区切り）
            console.print()
            file_count = len(result.generated_code)
            console.print(f"[bold]{file_count} files changed[/bold]")
            console.print()
            
            file_list = list(result.generated_code.items())
            for idx, (filename, _) in enumerate(file_list, 1):
                # Diff推定を計算
                file_path = Path(filename)
                if file_path.exists():
                    old_content = file_path.read_text(encoding='utf-8')
                    new_content = result.generated_code[filename]
                    
                    old_lines = old_content.splitlines()
                    new_lines = new_content.splitlines()
                    
                    additions = len([l for l in new_lines if l not in old_lines])
                    deletions = len([l for l in old_lines if l not in new_lines])
                    
                    # Zen: シンプルな差分表示（Cognix green + 白）
                    console.print(Text.from_ansi(f"  {idx}  {GREEN}{filename}{RESET}  +{additions} / -{deletions}"))
                else:
                    line_count = len(result.generated_code[filename].splitlines())
                    console.print(Text.from_ansi(f"  {idx}  {GREEN}{filename}{RESET}  new, {line_count} lines"))
            
            # Zen: メニュー（キーはシアン色）
            console.print()
            console.print(Text.from_ansi(f"  [{CYAN}1{RESET}]-[{CYAN}{len(file_list)}{RESET}]  Preview / diff"))
            # Impact Analysisがある場合のみメニューに表示
            if has_impact_analysis:
                console.print(Text.from_ansi(f"  [{CYAN}i{RESET}]      Impact analysis"))
            console.print()
            console.print(Text.from_ansi(f"  [{CYAN}a{RESET}] Apply    [{CYAN}r{RESET}] Reject    [{CYAN}b{RESET}] Back"))
            
            choice = input("\nYour choice: ").strip().lower()
            
            # 数値選択: ファイルプレビュー
            if choice.isdigit():
                file_idx = int(choice) - 1
                if 0 <= file_idx < len(file_list):
                    filename, content = file_list[file_idx]
                    self._show_file_preview(filename, content, result)
                else:
                    err_console.print(f"{Icon.ERROR.value} Invalid file number")
                continue
            
            # i: Impact analysis
            if choice == "i":
                if has_impact_analysis:
                    self._show_impact_analysis(result, files_data)
                else:
                    console.print("\nImpact analysis is not available.")
                    console.print("No existing files to analyze.")
                    input("\nPress Enter to continue...")
                continue
            
            # a: Apply
            if choice == "a":
                err_console.print(f"\n{Icon.GEAR.value} Applying implementation...")
                final_result = self.engine.apply_generated_code(result)
                
                if final_result.success:
                    err_console.print(Text.from_ansi(f"{GREEN}✓ Implementation applied successfully!{RESET}"))
                    self._show_apply_summary(final_result)
                else:
                    err_console.print(f"{Icon.ERROR.value} Failed to apply: {final_result.error}")
                return "applied"
            
            # r: Reject
            if choice == "r":
                err_console.print(Text.from_ansi(f"{MAGENTA}✕ Implementation rejected by user{RESET}"))
                err_console.print()  # 改行を追加
                return "rejected"
            
            # b: Back
            if choice == "b":
                return "back"
            
            err_console.print(f"{Icon.ERROR.value} Invalid choice")
    
    def _show_file_preview(self, filename: str, content: str, result=None):
        """ファイルプレビュー表示（Preview → Diff切替対応）
        
        Args:
            filename: ファイル名
            content: ファイル内容
            result: 生成結果オブジェクト（サマリー表示用、省略可能）
        """
        from rich.syntax import Syntax
        from rich.panel import Panel
        
        file_path = Path(filename)
        icon = FileIconMapper.get_icon(filename)
        
        # 初手: Preview表示
        console.print(f"\n{icon} Preview: {filename}")
        
        # 言語推測
        ext = file_path.suffix.lstrip('.')
        language = ext if ext else "text"
        
        # 全内容を表示（50行制限を削除）
        syntax = Syntax(content, language, theme="monokai", line_numbers=True)
        panel = Panel(syntax, border_style="cyan", padding=(0, 1))
        console.print(panel)
        
        # ==========================================
        # 【新規追加】ファイル詳細サマリー表示
        # ==========================================
        if result is not None:
            self._show_file_details_summary(filename, result)
        
        # Diff切替オプション
        console.print()
        console.print(Text.from_ansi(f"[{CYAN}d{RESET}] Show diff   [{CYAN}b{RESET}] Back to file list"))
        choice = input("Your choice: ").strip().lower()
        
        if choice == "d":
            self._show_file_diff(filename, content)
    
    def _show_file_details_summary(self, filename: str, result):
        """ファイル詳細サマリー表示（[v] View details用）
        
        ソースコード表示後にQuality、Review Issues、Lint結果を表示
        
        Args:
            filename: ファイル名
            result: 生成結果オブジェクト
        """
        try:
            from semi_auto_engine import get_file_details_summary, format_file_details_for_display
        except ImportError:
            try:
                from cognix.semi_auto_engine import get_file_details_summary, format_file_details_for_display
            except ImportError:
                # インポートできない場合はスキップ
                return
        
        # サマリーデータを取得
        details = get_file_details_summary(
            generated_code=result.generated_code if hasattr(result, 'generated_code') else {},
            quality_scores=result.quality_scores if hasattr(result, 'quality_scores') else {},
            lint_result=result.lint_result if hasattr(result, 'lint_result') else None,
            zen_summary=result.zen_summary if hasattr(result, 'zen_summary') else None,
            filename=filename
        )
        
        # フォーマットして表示
        summary_text = format_file_details_for_display(details)
        console.print(summary_text)
    
    def _show_file_diff(self, filename: str, new_content: str):
        """ファイルのDiff表示
        
        Args:
            filename: ファイル名
            new_content: 新しい内容
        """
        from rich.syntax import Syntax
        from rich.panel import Panel
        import difflib
        
        file_path = Path(filename)
        
        if not file_path.exists():
            # 新規ファイル: 全内容を表示（diffではなく）
            icon = FileIconMapper.get_icon(filename)
            console.print(f"\n{icon} New file: {filename} (full content)")
            
            # 言語推測
            ext = file_path.suffix.lstrip('.')
            language = ext if ext else "text"
            
            # 全内容を表示（50行制限なし）
            syntax = Syntax(new_content, language, theme="monokai", line_numbers=True)
            panel = Panel(syntax, border_style="cyan", padding=(0, 1))
            console.print(panel)
            
            input("\nPress Enter to continue...")
            return
        
        old_content = file_path.read_text(encoding='utf-8')
        
        # Unified diff生成
        diff_lines = list(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        ))
        
        diff_text = "".join(diff_lines)
        
        # シンタックスハイライト
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
        panel = Panel(syntax, border_style="cyan", padding=(0, 1))
        console.print(panel)
        
        input("\nPress Enter to continue...")
    
    def _show_impact_analysis(self, result: Dict, files_data: List[Dict]) -> None:
        """Impact Analysis結果を表示（Zen版）"""
        
        if not getattr(result, 'impact_analysis', {}):
            console.print("\nNo impact analysis available")
            console.print("\nPress Enter to return...")
            input()
            return
        
        # Zen: タイトル（余白で区切り）
        console.print()
        console.print("[bold]Impact Analysis[/bold]")
        console.print()
        
        diff_info = {}
        for file_info in files_data:
            filename = file_info['name']
            diff_info[filename] = {
                'added': file_info['added'],
                'removed': file_info['removed']
            }
        
        for filename, impact_data in result.impact_analysis.items():
            added = diff_info.get(filename, {}).get('added', 0)
            removed = diff_info.get(filename, {}).get('removed', 0)
            
            # Zen: ファイル名と差分（Cognix green + 白）
            console.print(Text.from_ansi(f"{GREEN}{filename}{RESET}  +{added} / -{removed}"))
            
            # Zen: リスクレベル（白ラベル + 色付きの値）
            risk_level = impact_data.get('risk_level', 'unknown').upper()
            if risk_level == 'LOW':
                console.print(Text.from_ansi(f"  Risk         {GREEN}{risk_level}{RESET}"))
            elif risk_level == 'HIGH':
                console.print(f"  Risk         [red]{risk_level}[/red]")
            elif risk_level == 'MEDIUM':
                console.print(f"  Risk         [yellow]{risk_level}[/yellow]")
            else:
                console.print(f"  Risk         {risk_level}")
            
            # Zen: 複雑度（白）
            complexity = impact_data.get('complexity', 0)
            console.print(f"  Complexity   {complexity}/10")
            
            # Zen: 依存関係（白）
            dependencies = impact_data.get('dependencies', [])
            dep_count = len(dependencies)
            console.print(f"  Dependencies {dep_count} files")
            
            # Zen: 影響ファイル（白）
            affected_files = impact_data.get('affected_files', [])
            if affected_files:
                # フルパス → ファイル名のみに変換
                affected_names = [Path(f).name for f in affected_files[:3]]
                affected_str = ', '.join(affected_names)
                if len(affected_files) > 3:
                    affected_str += f" +{len(affected_files) - 3}"
                console.print(f"  Affects      : {affected_str}")
            else:
                console.print(f"  Affects      none")
            
            # Zen: 警告はシンプルに（HIGHのみ）
            if risk_level == 'HIGH' and affected_files:
                console.print(f"  [yellow]⚠ Used by {len(affected_files)} files[/yellow]")
            
            console.print()
        
        # Zen: サマリー（シンプルに）
        risk_counts = {'high': 0, 'medium': 0, 'low': 0}
        
        for impact_data in result.impact_analysis.values():
            risk_level = impact_data.get('risk_level', 'unknown').lower()
            if risk_level in risk_counts:
                risk_counts[risk_level] += 1
        
        # サマリー文字列を構築
        summary_parts = []
        if risk_counts['high'] > 0:
            summary_parts.append(f"[red]{risk_counts['high']} high[/red]")
        if risk_counts['medium'] > 0:
            summary_parts.append(f"[yellow]{risk_counts['medium']} medium[/yellow]")
        if risk_counts['low'] > 0:
            # Cognix greenを使用
            low_text = Text.from_ansi(f"{GREEN}{risk_counts['low']} low{RESET}")
            summary_parts.append(low_text)
        
        if summary_parts:
            # summary_partsにTextオブジェクトが含まれる可能性があるため個別に処理
            console.print(Text.from_ansi(f"{GREEN}{risk_counts['low']} low{RESET} risk") if risk_counts['low'] > 0 and risk_counts['high'] == 0 and risk_counts['medium'] == 0 else ' · '.join([str(p) for p in summary_parts]) + ' risk')
        
        console.print("\nPress Enter to return...")
        input()
    
    def _show_lints_summary(self, result):
        """Lints要約表示（Top3 + ... +N more）
        
        Args:
            result: 生成結果オブジェクト
        """
        console.print("\n" + "="*60)
        console.print("Lints Summary (Top 3)")
        console.print("="*60)
        
        # 【推測】result.lint_results が存在すると仮定
        if hasattr(result, 'lint_results') and result.lint_results:
            issues = result.lint_results[:3]
            for issue in issues:
                console.print(f"  • {issue}")
            
            remaining = len(result.lint_results) - 3
            if remaining > 0:
                console.print(f"\n  ... +{remaining} more")
        else:
            console.print("No lint issues found")
        
        input("\nPress Enter to continue...")
    
    def _show_apply_summary(self, final_result):
        """Apply後のサマリー表示
        
        Args:
            final_result: 適用結果オブジェクト
        """
        if final_result.applied_files:
            err_console.print(f"{Icon.FOLDER.value} Files created/modified: {len(final_result.applied_files)}")
            for file in final_result.applied_files:
                err_console.print(f"   • {file}")
            err_console.print()  # 空行を追加
        
        if hasattr(final_result, 'backup_paths') and final_result.backup_paths:
            err_console.print()  # 空行を追加
            err_console.print(f"{Icon.PACKAGE.value} Backups created: {len(final_result.backup_paths)}")
            # バックアップファイルの個別パス表示（Files created/modifiedと同じフォーマット）
            for backup_path in final_result.backup_paths:
                err_console.print(f"   • {backup_path}")
        
        # ==========================================
        # 改善案C: 品質スコア表示（Apply後）
        # ==========================================
        if hasattr(final_result, 'quality_scores') and final_result.quality_scores:
            err_console.print(Text.from_ansi(f"{Icon.CHART.value} Quality Scores:"))
            
            total_score = 0
            count = 0
            
            for filename, score in final_result.quality_scores.items():
                # パーセント表示（0.90 → 90%）
                score_percent = int(score * 100)
                
                # 色とグレード判定
                if score >= 0.9:
                    color = GREEN
                    grade = "Excellent"
                elif score >= 0.75:
                    color = GREEN
                    grade = "Good"
                elif score >= 0.6:
                    color = YELLOW
                    grade = "Fair"
                else:
                    color = YELLOW
                    grade = "Needs Review"
                
                err_console.print(Text.from_ansi(
                    f"   {color}{filename}{RESET}: {score_percent}% {color}{grade}{RESET}"
                ))
                
                total_score += score
                count += 1
            
            # 平均スコア表示
            if count > 0:
                avg_score = total_score / count
                avg_percent = int(avg_score * 100)
                err_console.print()
                err_console.print(Text.from_ansi(
                    f"   Average Quality: {GREEN}{avg_percent}%{RESET}"
                ))
                err_console.print()


    def cmd_make(self, args):
        """Alias for /semi-auto command
        
        Short command for semi-automatic code generation.
        Usage: /make <goal>
        Example: /make create a calculator
        """
        # cmd_semi_autoに処理を委譲
        return self.cmd_semi_auto(args)