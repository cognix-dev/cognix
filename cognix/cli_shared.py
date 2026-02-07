"""
CLI 共有機能と状態管理モジュール

このモジュールは、CLI全体で共有される状態とヘルパーメソッドを提供します。
具体的には以下の機能を含みます：

1. 共有状態管理（CLISharedState）
2. 共通機能の提供（CLIModuleBase）
3. ユーティリティ関数
"""

import os
import sys
import json
import time
from typing import Dict, List, Set, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field  # dataclassとfieldのインポートを追加
from cognix.logger import err_console

@dataclass
class CLISharedState:
    # 複数行入力状態
    multiline_buffer: List[str] = field(default_factory=list)
    empty_line_count: int = 0
    original_prompt: str = "cognix> "
    
    # ワークフロー状態
    workflow_state: Dict[str, Any] = field(default_factory=lambda: {
        "think_result": None,
        "plan_result": None, 
        "current_goal": None
    })
    
    # セッション状態
    current_session_id: Optional[str] = None
    temp_files: List[str] = field(default_factory=list)

class CLIModuleBase:
    """すべての機能モジュールの基底クラス
    
    依存性注入パターンを使用して、各モジュールに必要な依存関係を設定します。
    初期化は2段階で行い、クラスの生成と依存関係の設定を分離します。
    """
    
    def __init__(self):
        """基本初期化 - 引数なし
        
        依存オブジェクトはset_dependenciesで後から設定します
        """
        # 依存オブジェクト - 初期化後にset_dependenciesで設定
        self.shared_state = None
        self.config = None
        self.memory = None
        self.context = None
        self.llm_manager = None
        self.code_assistant = None
        self.diff_engine = None
        self.session_manager = None
        self.error_handler = None
        self.run_command = None
        
        # オプション依存 - 存在する場合のみ設定
        self.related_finder = None
        self.impact_analyzer = None
        self.safe_editor = None
        
    def set_dependencies(self, cli_instance):
        """依存関係の設定
        
        Args:
            cli_instance: 依存オブジェクトを持つメインCLIインスタンス
        """
        self._cli_instance = cli_instance
        
        # 共有状態
        self.shared_state = cli_instance.shared_state
        
        # 必須依存
        self.config = cli_instance.config
        self.memory = cli_instance.memory
        self.context = cli_instance.context
        self.llm_manager = cli_instance.llm_manager
        self.code_assistant = cli_instance.code_assistant
        self.diff_engine = cli_instance.diff_engine
        self.session_manager = cli_instance.session_manager
        self.error_handler = cli_instance.error_handler
        self.run_command = cli_instance.run_command
        
        # オプション依存 - 存在する場合のみ設定
        if hasattr(cli_instance, 'related_finder'):
            self.related_finder = cli_instance.related_finder
            
        if hasattr(cli_instance, 'impact_analyzer'):
            self.impact_analyzer = cli_instance.impact_analyzer
            
        if hasattr(cli_instance, 'safe_editor'):
            self.safe_editor = cli_instance.safe_editor

        if hasattr(cli_instance, 'repository_analyzer'):
            self.repository_analyzer = cli_instance.repository_analyzer

    def safe_execute(self, func, *args, context: str = "", **kwargs):
        """安全な実行ラッパー"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if hasattr(self, 'error_handler') and self.error_handler:
                self.error_handler.handle_error(e, context)
            else:
                err_console.print(f"Error in {context}: {str(e)}")
            return None

    def validate_file_exists(self, file_path: str) -> bool:
        """ファイル存在確認"""
        if not Path(file_path).exists():
            err_console.print(f"Error: File not found: {file_path}")
            return False
        return True

    # 共通ヘルパーメソッド
    def _display_with_typewriter(self, text: str, prefix: str = ""):
        """タイプライターエフェクトでテキストを表示
        
        Args:
            text: 表示するテキスト
            prefix: テキストの前に表示するプレフィックス
        """
        if not text:
            return
            
        err_console.print(prefix, end="", flush=True)
        
        delay = 0.001  # タイプ間隔（秒）
        
        for char in text:
            err_console.print(char, end="", flush=True)
            time.sleep(delay)
            
        err_console.print()  # 最後に改行
    
    def _stream_with_typewriter(self, stream_generator, prefix: str = ""):
        """ストリーミングでタイプライターエフェクト表示
        
        Args:
            stream_generator: ストリーミング生成器
            prefix: テキストの前に表示するプレフィックス
        """
        if not stream_generator:
            return
            
        err_console.print(prefix, end="", flush=True)
        
        for chunk in stream_generator:
            if hasattr(chunk, 'content'):
                content = chunk.content
            else:
                content = str(chunk)
                
            err_console.print(content, end="", flush=True)
            
        err_console.print()  # 最後に改行
    
    def _display_command_result(self, content: str, command_type: str = "result"):
        """コマンド結果の表示
        
        Args:
            content: 表示する内容
            command_type: コマンドタイプ
        """
        model_prefix = self._get_model_prefix()
        self._display_with_typewriter(content, model_prefix)
    
    def _get_model_prefix(self) -> str:
        """モデルプレフィックスの取得（[Sonnet 4.5]> 形式）"""
        if hasattr(self, 'llm_manager') and self.llm_manager:
            model_name = getattr(self.llm_manager, 'current_model', 'AI')
            if ':' in model_name:
                model_name = model_name.split(':')[0]
            
            # configから動的に表示名を取得
            if hasattr(self, 'config') and self.config:
                model_display = self.config.get_model_display_name(model_name)
            else:
                model_display = model_name
            
            return f"[{model_display}]> "
        return "[AI]> "
    
    def get_multiline_input(self, prompt: str, allow_empty: bool = False) -> str:
        """複数行入力の取得
        
        Args:
            prompt: 入力プロンプト
            allow_empty: 空入力を許可するかどうか
            
        Returns:
            入力された複数行テキスト
        """
        err_console.print(f"{prompt} (End with an empty line)")
        lines = []
        
        while True:
            line = input("> ")
            if not line:
                break
            lines.append(line)
            
        result = "\n".join(lines)
        
        if not result and not allow_empty:
            return ""
            
        return result
    
    def get_input_with_options(self, prompt: str, allow_empty: bool = False) -> str:
        """オプション付き入力の取得
        
        Args:
            prompt: 入力プロンプト
            allow_empty: 空入力を許可するかどうか
            
        Returns:
            入力されたテキスト
        """
        user_input = input(f"{prompt}: ")
        
        if not user_input and not allow_empty:
            err_console.print("Input cannot be empty.")
            return self.get_input_with_options(prompt, allow_empty)
            
        return user_input
    
    def _confirm_action(self, message: str, auto_apply: bool = None) -> bool:
        """ユーザー確認の取得
        
        Args:
            message: 確認メッセージ
            auto_apply: 自動適用フラグ
            
        Returns:
            確認結果 (True/False)
        """
        if auto_apply is not None:
            return auto_apply
            
        confirmation = input(f"{message} (y/n): ")
        return confirmation.lower() == 'y'
    
    def _toggle_typewriter_effect(self):
        """タイプライターエフェクトの切り替え"""
        # この実装はダミーです。実際の実装では設定値を変更します。
        err_console.print("Typewriter effect toggled")