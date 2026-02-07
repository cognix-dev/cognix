#!/usr/bin/env python3
"""
Spinner アニメーション完全実装
StepProgressを一時停止してSpinnerアニメーションを表示
"""
import sys
from pathlib import Path
import shutil

def apply_progress_fix():
    """progress.pyにpause/resume機能を追加"""
    progress_path = Path('cognix/progress.py')
    
    if not progress_path.exists():
        print("✗ Error: cognix/progress.py not found")
        return False
    
    # Backup
    backup_path = progress_path.with_name('progress.py.backup_spinner')
    shutil.copy2(progress_path, backup_path)
    print(f"✓ Backup created: {backup_path}")
    
    # Read the fixed version
    fixed_content = '''# cognix/progress.py
"""
ステップ表示システム - Cognix UI改善計画書 Phase 2 Day 5
進行状況を視覚的に表示し、ユーザーに処理の進捗を伝える

【修正内容】
- table.rowsの直接変更を削除
- テーブルを再作成する方式に変更
- グローバルフラグでLiveコンテキストを管理
- pause/resume機能を追加してSpinnerアニメーションを許可
"""

from typing import List, Optional
from rich.live import Live
from rich.table import Table
from rich.console import Console

console = Console(stderr=True)

# Global flag for Live context
_active_live_context = False

def is_live_context_active():
    """Check if Live context is currently active"""
    return _active_live_context


class StepProgress:
    """ステップごとの進捗表示"""
    
    def __init__(self, steps: List[str], title: str = "Progress"):
        """初期化"""
        self.steps = steps
        self.title = title
        self.current_step = 0
        self.step_statuses = ["⏳"] + ["⏸️"] * (len(steps) - 1)  # ステータス管理用
        self.live: Optional[Live] = None
        self._is_paused = False
    
    def _create_table(self) -> Table:
        """進捗テーブルを作成"""
        table = Table(
            title=f"⚙️  {self.title}",
            show_header=False,
            box=None,
            padding=(0, 1)
        )
        table.add_column("Status", style="white", width=3)
        table.add_column("Step", style="white")
        
        # 現在のステータスでテーブルを構築
        for i, (status, step) in enumerate(zip(self.step_statuses, self.steps)):
            table.add_row(status, step)
        
        return table
    
    def __enter__(self):
        """コンテキストマネージャー: 開始"""
        global _active_live_context
        _active_live_context = True
        
        self.live = Live(self._create_table(), refresh_per_second=4, console=console)
        self.live.__enter__()
        return self
    
    def __exit__(self, *args):
        """コンテキストマネージャー: 終了"""
        global _active_live_context
        _active_live_context = False
        
        if self.live:
            self.live.__exit__(*args)
    
    def pause(self):
        """Live表示を一時停止（Spinnerアニメーション用）"""
        global _active_live_context
        if self.live and not self._is_paused:
            self.live.stop()
            _active_live_context = False
            self._is_paused = True
    
    def resume(self):
        """Live表示を再開"""
        global _active_live_context
        if self.live and self._is_paused:
            self.live.start()
            _active_live_context = True
            self._is_paused = False
            # テーブルを更新して最新状態を反映
            self.live.update(self._create_table())
    
    def advance(self, status: str = "complete", message: Optional[str] = None):
        """現在のステップを完了して次へ"""
        if self.current_step >= len(self.steps):
            return
        
        # 現在のステップを完了
        icon = "✅" if status == "complete" else "❌"
        self.step_statuses[self.current_step] = icon
        
        if message:
            self.steps[self.current_step] = f"{self.steps[self.current_step]} - {message}"
        
        # 次のステップを開始
        self.current_step += 1
        if self.current_step < len(self.steps):
            self.step_statuses[self.current_step] = "⏳"
        
        # テーブルを再作成して更新
        if self.live and not self._is_paused:
            self.live.update(self._create_table())
'''
    
    # Write
    with open(progress_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"✓ Updated {progress_path}")
    return True

def apply_semi_auto_engine_fix():
    """semi_auto_engine.pyにprogress一時停止を追加"""
    engine_path = Path('cognix/semi_auto_engine.py')
    
    if not engine_path.exists():
        print("✗ Error: cognix/semi_auto_engine.py not found")
        return False
    
    # Backup
    backup_path = engine_path.with_name('semi_auto_engine.py.backup_spinner')
    shutil.copy2(engine_path, backup_path)
    print(f"✓ Backup created: {backup_path}")
    
    # Read
    with open(engine_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 修正1: generate_implementation メソッド - progressを保存
    modified = False
    for i, line in enumerate(lines):
        if 'with StepProgress(steps, title="Code Generation") as progress:' in line:
            # 次の行にself._current_progress = progressを挿入
            indent = len(line) - len(line.lstrip())
            insert_line = ' ' * (indent + 4) + 'self._current_progress = progress\n'
            if i + 1 < len(lines) and 'self._current_progress' not in lines[i + 1]:
                lines.insert(i + 1, insert_line)
                modified = True
                print(f"✓ Added progress storage at line {i + 2}")
            break
    
    if not modified:
        print("✗ Could not find StepProgress context")
        return False
    
    # 修正2: _generate_code_implementation メソッド - Spinner周りにpause/resume
    modified = False
    for i, line in enumerate(lines):
        if 'with Spinner("Generating code with LLM..."):' in line:
            indent = len(line) - len(line.lstrip())
            base_indent = ' ' * indent
            inner_indent = ' ' * (indent + 4)
            
            # pause/resumeコードを挿入
            pause_code = [
                base_indent + '# StepProgressを一時停止してSpinnerアニメーションを表示\n',
                base_indent + 'if hasattr(self, \'_current_progress\') and self._current_progress:\n',
                inner_indent + 'self._current_progress.pause()\n',
                base_indent + '\n',
                base_indent + 'try:\n',
                inner_indent + line.lstrip(),  # with Spinner行
            ]
            
            # with Spinnerブロックの終わりを見つける
            block_end = i + 1
            block_indent = indent + 4
            while block_end < len(lines):
                next_line = lines[block_end]
                if next_line.strip() and not next_line.startswith(' ' * (block_indent + 1)):
                    break
                block_end += 1
            
            # resumeコードを追加
            resume_code = [
                base_indent + 'finally:\n',
                inner_indent + '# StepProgressを再開\n',
                inner_indent + 'if hasattr(self, \'_current_progress\') and self._current_progress:\n',
                inner_indent + '    self._current_progress.resume()\n',
                base_indent + '\n',
            ]
            
            # 既存のwith Spinner行を削除して新しいコードを挿入
            del lines[i]
            for j, code_line in enumerate(pause_code):
                lines.insert(i + j, code_line)
            
            # with Spinnerブロック内のインデントを調整
            for j in range(i + len(pause_code), block_end + len(pause_code) - 1):
                if lines[j].strip():
                    lines[j] = '    ' + lines[j]
            
            # resumeコードを挿入
            insert_pos = block_end + len(pause_code) - 1
            for j, code_line in enumerate(resume_code):
                lines.insert(insert_pos + j, code_line)
            
            modified = True
            print(f"✓ Added pause/resume around Spinner at line {i + 1}")
            break
    
    if not modified:
        print("✗ Could not find Spinner usage")
        return False
    
    # Write
    with open(engine_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✓ Updated {engine_path}")
    return True

def main():
    print("=== Spinner アニメーション完全実装 ===\n")
    
    # Apply progress.py fix
    print("1. progress.py にpause/resume機能を追加...")
    if not apply_progress_fix():
        return 1
    print()
    
    # Apply semi_auto_engine.py fix
    print("2. semi_auto_engine.py にpause/resume呼び出しを追加...")
    if not apply_semi_auto_engine_fix():
        return 1
    print()
    
    print("✅ 修正完了！\n")
    print("期待される動作:")
    print("  1. StepProgress表示")
    print("  2. LLM呼び出し前: StepProgressが一時停止")
    print("  3. ⠼ Generating code with LLM... (アニメーション)")
    print("  4. LLM呼び出し後: StepProgressが再開")
    print("  5. 次のステップへ")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())