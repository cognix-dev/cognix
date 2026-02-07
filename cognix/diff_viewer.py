# cognix/diff_viewer.py
"""
Diff表示とファイル適用管理システム - Cognix UI改善計画書 Phase 2 Day 3-4
ユーザーに変更内容を視覚的に表示し、安全にファイルを適用する
"""

from pathlib import Path
from typing import Tuple
import difflib
from cognix.logger import err_console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from cognix.ui import Icon, FileIconMapper


class DiffViewer:
    """Diff表示とファイル適用を管理"""
    
    @staticmethod
    def show_diff_and_confirm(
        filename: str, 
        new_content: str,
        auto_apply: bool = False
    ) -> bool:
        """Diffを表示して適用確認
        
        Args:
            filename: 対象ファイル名
            new_content: 新しいコンテンツ
            auto_apply: 自動適用モード
            
        Returns:
            True: 適用する, False: スキップ
        """
        file_path = Path(filename)
        icon = FileIconMapper.get_icon(filename)
        
        # 新規ファイルの場合
        if not file_path.exists():
            return DiffViewer._handle_new_file(
                filename, new_content, icon, auto_apply
            )
        
        # 既存ファイルの場合
        old_content = file_path.read_text(encoding='utf-8')
        
        # 内容が同じならスキップ
        if old_content == new_content:
            err_console.print(f"{Icon.SUCCESS} [dim]{filename} - No changes[/]")
            return False
        
        return DiffViewer._handle_existing_file(
            filename, old_content, new_content, icon, auto_apply
        )
    
    @staticmethod
    def _handle_new_file(filename: str, content: str, icon: str, auto_apply: bool) -> bool:
        """新規ファイル作成の処理
        
        Args:
            filename: ファイル名
            content: ファイル内容
            icon: アイコン絵文字
            auto_apply: 自動適用モード
            
        Returns:
            True: 作成する, False: スキップ
        """
        err_console.print(f"\n{icon} [bold cyan]New file:[/] {filename}")
        
        # プレビュー表示（最初の20行）
        lines = content.splitlines()
        preview_lines = lines[:20]
        
        # 言語を推測
        ext = Path(filename).suffix.lstrip('.')
        language = ext if ext else "text"
        
        # シンタックスハイライト
        preview = "\n".join(preview_lines)
        if len(lines) > 20:
            preview += f"\n... ({len(lines) - 20} more lines)"
        
        syntax = Syntax(preview, language, theme="monokai", line_numbers=True)
        panel = Panel(syntax, title=f"Preview: {filename}", border_style="cyan", padding=(1, 2))
        err_console.print(panel)
        
        # 統計情報
        err_console.print(f"[cyan]Lines: {len(lines)} | Characters: {len(content)}[/]")
        
        if auto_apply:
            return True
        
        return Confirm.ask(f"Create [cyan]{filename}[/]?", default=True)
    
    @staticmethod
    def _handle_existing_file(filename: str, old_content: str, new_content: str, icon: str, auto_apply: bool) -> bool:
        """既存ファイル更新の処理
        
        Args:
            filename: ファイル名
            old_content: 既存の内容
            new_content: 新しい内容
            icon: アイコン絵文字
            auto_apply: 自動適用モード
            
        Returns:
            True: 適用する, False: スキップ
        """
        err_console.print(f"\n{icon} [bold cyan]Changes in:[/] {filename}")
        
        # Unified diff生成
        diff_lines = list(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        ))
        
        # Diffテキスト作成
        diff_text = "".join(diff_lines)
        
        # シンタックスハイライト（diff形式）
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
        panel = Panel(syntax, border_style="cyan", padding=(1, 2))
        err_console.print(panel)
        
        # 統計情報
        additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        
        err_console.print(f"[green]+{additions}[/] [red]-{deletions}[/]")
        
        if auto_apply:
            return True
        
        return Confirm.ask(f"Apply changes to [cyan]{filename}[/]?", default=True)
    
    @staticmethod
    def apply_files_with_diff(files: dict[str, str], auto_apply: bool = False) -> Tuple[list[str], list[str]]:
        """複数ファイルにDiff表示と適用
        
        Args:
            files: {filename: content} の辞書
            auto_apply: 自動適用モード
            
        Returns:
            (applied, skipped): 適用されたファイルとスキップされたファイルのリスト
        """
        err_console.print(f"\n{Icon.SEARCH} [bold]Reviewing changes...[/]\n")
        
        applied = []
        skipped = []
        
        for filename, content in files.items():
            try:
                should_apply = DiffViewer.show_diff_and_confirm(filename, content, auto_apply)
                
                if should_apply:
                    # ファイル書き込み
                    file_path = Path(filename)
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding='utf-8')
                    
                    applied.append(filename)
                    icon = FileIconMapper.get_icon(filename)
                    err_console.print(f"{Icon.SUCCESS} Applied {icon} {filename}", style="green")
                else:
                    skipped.append(filename)
                    err_console.print(f"⏭️  Skipped {filename}", style="yellow")
            
            except Exception as e:
                err_console.print(f"{Icon.ERROR} Error processing {filename}: {e}", style="bold red")
                skipped.append(filename)
        
        # サマリー表示
        DiffViewer._print_summary(applied, skipped)
        
        return applied, skipped
    
    @staticmethod
    def _print_summary(applied: list[str], skipped: list[str]):
        """適用結果のサマリーを表示
        
        Args:
            applied: 適用されたファイルのリスト
            skipped: スキップされたファイルのリスト
        """
        err_console.print(f"\n{Icon.CHART} [bold]Summary:[/]")
        
        table = Table(show_header=False, box=None)
        table.add_column("Status", style="white", width=20)
        table.add_column("Count", style="cyan", width=5)
        
        table.add_row(f"{Icon.SUCCESS.value} Applied", str(len(applied)))
        table.add_row("⏭️  Skipped", str(len(skipped)))
        
        err_console.print(table)
        
        if applied:
            err_console.print(f"\n{Icon.PARTY} [bold green]Changes applied successfully![/]")