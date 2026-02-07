# cognix.progress_zen
"""
Zen HUD: Fixed-line Step display (設計書準拠 最終版)

Design spec compliance:
- Fixed line height during Live display
- Symbol replacement only (⟳/·/✓)
- Timer at line end (auto-updating)
- transient=True (Live完了後消える)
- 完了後に確定出力を残す
"""

from __future__ import annotations
import time
import threading
from typing import List
from rich.live import Live
from rich.console import Group
from rich.text import Text
from cognix.logger import console, enable_live_buffering, disable_live_buffering_and_flush

# 色定義のインポート
from cognix.theme_zen import GREEN, YELLOW, DIM, RESET, CYAN


class StepHUD:
    """Zen HUD: Fixed-line Step display with auto-updating timer"""
    
    def __init__(self, section_title: str | None = None, steps: List[str] | None = None):
        """
        Args:
            section_title: Section title (e.g. "Code Generation")
            steps: List of step names
        """
        self.section_title = section_title or ""
        self.steps = steps or []
        self.step_states = [0] * len(self.steps)  # 0=pending, 1=running, 2=complete
        self.step_start_times = [0.0] * len(self.steps)  # 各ステップの開始時刻
        self.current_step = 0
        self.t0 = None
        self._live: Live | None = None
        self._terminal_width = 80
        self._stop_timer = False
        self._timer_thread: threading.Thread | None = None
        
        # スピナーアニメーション用（記号+色の両方変化、14段階の滑らかなグラデーション）
        self._spinner_frames = [
            "\033[2;38;5;51m░\033[0m",   # dim ░
            "\033[38;5;51m░\033[0m",     # normal ░
            "\033[38;5;51m▒\033[0m",     # normal ▒
            "\033[1;38;5;51m▒\033[0m",   # bold ▒
            "\033[1;38;5;51m▓\033[0m",   # bold ▓
            "\033[1;38;5;87m▓\033[0m",   # bright bold ▓
            "\033[1;38;5;87m█\033[0m",   # bright bold █
            "\033[1;38;5;123m█\033[0m",  # very bright bold █ (ピーク)
            "\033[1;38;5;87m█\033[0m",   # bright bold █ (戻る)
            "\033[1;38;5;87m▓\033[0m",   # bright bold ▓ (戻る)
            "\033[1;38;5;51m▓\033[0m",   # bold ▓ (戻る)
            "\033[1;38;5;51m▒\033[0m",   # bold ▒ (戻る)
            "\033[38;5;51m▒\033[0m",     # normal ▒ (戻る)
            "\033[38;5;51m░\033[0m",     # normal ░ (戻る)
        ]
        self._spinner_index = 0  # 現在のフレーム
        self._spinner_update_counter = 0  # 更新カウンター
    
    def start(self):
        """Start HUD - enable Live display"""
        self.t0 = time.time()
        
        # 端末幅を取得
        try:
            import shutil
            self._terminal_width = shutil.get_terminal_size().columns
        except Exception:
            self._terminal_width = 80
        
        # stderr バッファリング有効化
        enable_live_buffering()
        
        # Live開始（transient=True: 終了後は消える、最終状態は別途print）
        self._live = Live(
            self._render_display(),
            refresh_per_second=4,
            console=console,  # stdout
            transient=True  # 終了後は消える（残像防止）
        )
        self._live.start()
        
        # タイマースレッド開始
        self._stop_timer = False
        self._timer_thread = threading.Thread(target=self._update_timer, daemon=True)
        self._timer_thread.start()
    
    def _update_timer(self):
        """タイマー自動更新スレッド（スピナーアニメーション付き）"""
        while not self._stop_timer:
            if self._live:
                # スピナーフレーム更新（0.2秒ごと）
                self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
                
                self._live.update(self._render_display())
            time.sleep(0.1)  # 0.1秒ごとに更新（スピナーアニメーション用）
    
    def _render_display(self) -> Group:
        """HUD表示をレンダリング"""
        lines = []
        
        # タイトル行 + プログレスバー
        if self.section_title:
            # プログレスバー計算
            total = len(self.steps)
            completed = sum(1 for state in self.step_states if state == 2)  # state==2は完了
            running = sum(1 for state in self.step_states if state == 1)    # state==1は実行中
            
            # 方式A: 実行中を0.5としてカウント（ユーザー体感に近い）
            # 例: 5ステップ、1つ目実行中 → (0 + 0.5) / 5 = 10%
            progress = completed + (running * 0.5)
            percent = int((progress / total) * 100) if total > 0 else 0
            
            # プログレスバー描画（30文字幅）
            bar_width = 30
            filled = int((progress / total) * bar_width) if total > 0 else 0
            bar_filled = "━" * filled
            bar_empty = "─" * (bar_width - filled)
            progress_bar = f"{bar_filled}{bar_empty}"
            
            # プログレスバーの色を決定
            # - 100%完了: 緑
            # - それ以外（実行中あり/進行中）: シアン
            if percent >= 100:
                bar_color = GREEN
            else:
                bar_color = CYAN
            
            # タイトル + プログレスバー + パーセンテージ（色付き）
            # タイトルも含めてすべてbar_colorで色付け
            title_line = f"{bar_color}{self.section_title} {progress_bar}{RESET} {bar_color}{percent}% ({completed}/{total}){RESET}"
            # ANSIコードを含むのでText.from_ansi()を使用
            from rich.text import Text
            lines.append(Text.from_ansi(title_line))
        
        # 各ステップ行
        for i, step_name in enumerate(self.steps):
            state = self.step_states[i]
            
            # 記号とタグの色選択
            if state == 2:  # complete
                symbol = f"{GREEN}✓{RESET}"
                status_tag = f"{GREEN}[DONE]{RESET}"
            elif state == 1:  # running
                symbol = self._spinner_frames[self._spinner_index]  # 動的スピナー
                status_tag = f"{CYAN}[RUNNING]{RESET}"
            else:  # pending
                symbol = "·"
                status_tag = "[PENDING]"
            
            # タイマー表示（実行中のステップのみ）
            if state == 1 and self.step_start_times[i] > 0:
                elapsed = int(time.time() - self.step_start_times[i])
                mm = elapsed // 60
                ss = elapsed % 60
                timer = f"{mm:02d}:{ss:02d}"
                
                # 2行表示: 1行目=ステップ名、2行目=タグ+タイマー（頭を揃える）
                line1 = f"{symbol} {step_name}"
                line2 = f"  {status_tag}  ({timer})"  # 2文字インデント（記号+スペース分）
                
                lines.append(Text.from_ansi(line1))
                lines.append(Text.from_ansi(line2))
            else:
                # タイマーなし（完了/待機）
                # 2行表示: 1行目=ステップ名、2行目=タグ（頭を揃える）
                line1 = f"{symbol} {step_name}"
                line2 = f"  {status_tag}"  # 2文字インデント（記号+スペース分）
                
                lines.append(Text.from_ansi(line1))
                lines.append(Text.from_ansi(line2))
        
        return Group(*lines)
    
    def mark(self, step_name: str):
        """Mark step as running"""
        for i, name in enumerate(self.steps):
            if name == step_name:
                self.step_states[i] = 1  # running
                self.step_start_times[i] = time.time()  # 開始時刻を記録
                self.current_step = i
                break
        
        if self._live:
            self._live.update(self._render_display())
    
    def complete(self, step_name: str):
        """Mark step as completed"""
        for i, name in enumerate(self.steps):
            if name == step_name:
                self.step_states[i] = 2  # complete
                break
        
        if self._live:
            self._live.update(self._render_display())
    
    def pending(self, step_name: str):
        """Mark step as pending"""
        for i, name in enumerate(self.steps):
            if name == step_name:
                self.step_states[i] = 0  # pending
                break
        
        if self._live:
            self._live.update(self._render_display())
    
    def finish(self, success: bool = True):
        """End HUD - stop Live display and print final state"""
        # タイマースレッド停止
        self._stop_timer = True
        if self._timer_thread:
            self._timer_thread.join(timeout=1.0)
        
        if self._live:
            # Live停止（transient=Trueなので消える）
            self._live.stop()
            self._live = None
        
        # 最終状態を通常のprint文で出力（残像防止のため）
        self._print_final_state(success)
        
        # stderr バッファをフラッシュ
        disable_live_buffering_and_flush()
    
    def _print_final_state(self, success: bool):
        """最終状態を通常のprint文で出力"""
        from rich.text import Text
        
        # タイトル行 + プログレスバー（100%完了）
        if self.section_title:
            total = len(self.steps)
            bar_width = 30
            bar_filled = "━" * bar_width
            
            if success:
                title_line = f"{GREEN}{self.section_title} {bar_filled}{RESET} {GREEN}100% ({total}/{total}){RESET}"
            else:
                completed = sum(1 for state in self.step_states if state == 2)
                progress = completed + (sum(1 for state in self.step_states if state == 1) * 0.5)
                percent = int((progress / total) * 100) if total > 0 else 0
                filled = int((progress / total) * bar_width) if total > 0 else 0
                bar_filled = "━" * filled
                bar_empty = "─" * (bar_width - filled)
                title_line = f"{YELLOW}{self.section_title} {bar_filled}{bar_empty}{RESET} {YELLOW}{percent}% ({completed}/{total}){RESET}"
            
            console.print(Text.from_ansi(title_line))
        
        # 各ステップ行（全て完了状態で表示）
        for i, step_name in enumerate(self.steps):
            if success:
                # 成功時は全て完了
                symbol = f"{GREEN}✓{RESET}"
                status_tag = f"{GREEN}[DONE]{RESET}"
            else:
                # 失敗時は実際の状態
                state = self.step_states[i]
                if state == 2:
                    symbol = f"{GREEN}✓{RESET}"
                    status_tag = f"{GREEN}[DONE]{RESET}"
                elif state == 1:
                    symbol = f"{YELLOW}●{RESET}"
                    status_tag = f"{YELLOW}[STOPPED]{RESET}"
                else:
                    symbol = "·"
                    status_tag = "[PENDING]"
            
            line1 = f"{symbol} {step_name}"
            line2 = f"  {status_tag}"
            
            console.print(Text.from_ansi(line1))
            console.print(Text.from_ansi(line2))