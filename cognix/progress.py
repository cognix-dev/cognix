# progress.py
import time
import threading
from typing import List, Tuple, Optional
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cognix.logger import console
from cognix.logger import (
    enable_live_buffering,
    disable_live_buffering_and_flush,
)

def is_live_context_active() -> bool:
    return StepProgress._global_active  # type: ignore[attr-defined]

class StepProgress:
    _global_active: bool = False  # 再入防止

    def __init__(self, steps: List[str], title: str = "Progress"):
        self.steps: List[Tuple[str, bool, float]] = [(s, False, 0.0) for s in steps]
        self.title = title
        self.current_step = 0
        self._live: Optional[Live] = None
        self._start_time = 0.0
        self._stop_timer = False
        self._timer_thread: Optional[threading.Thread] = None
        self._is_active = False

    # -- 表示部
    def _render_display(self):
        # シンプルなステップ表示（Cyber-Zen HUD仕様）
        lines = []
        for i, (name, done, elapsed) in enumerate(self.steps):
            # 仕様: ✓（完了）/ ⟳（実行中）/ ·（待機）
            if done:
                mark = "✓"
            elif i == self.current_step:
                mark = "⟳"
            else:
                mark = "·"
            
            # タイマーは行末に表示（仕様: (mm:ss)）
            if i == self.current_step and elapsed > 0:
                minutes = int(elapsed) // 60
                seconds = int(elapsed) % 60
                timer = f"({minutes:02d}:{seconds:02d})"
                # 行末にタイマーを配置
                lines.append(f"{mark} {name:<50}{timer:>10}")
            else:
                lines.append(f"{mark} {name}")
        body = "\n".join(lines)
        return Panel(body, title=self.title, border_style="cyan")

    def _update_timer(self):
        while not self._stop_timer and self._is_active:
            if self._live:
                # 経過秒を更新
                step = list(self.steps)[self.current_step]
                self.steps[self.current_step] = (step[0], step[1], step[2] + 1.0)
                self._live.update(self._render_display())
            time.sleep(1.0)

    def __enter__(self):
        if StepProgress._global_active:
            raise RuntimeError("StepProgress is already active")
        StepProgress._global_active = True
        self._is_active = True
        self._start_time = time.perf_counter()

        # ★ Live中はstderrをバッファ（stdoutのLiveと衝突させない）
        enable_live_buffering()

        # Live開始（stdout）
        self._live = Live(
            self._render_display(),
            refresh_per_second=8,
            transient=True,
            console=console,  # stdout
        )
        self._live.start()

        self._stop_timer = False
        self._timer_thread = threading.Thread(target=self._update_timer, daemon=True)
        self._timer_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # 最後のフレームを描画
            if self._live:
                # 現在のステップを完了扱いに
                if self.current_step < len(self.steps):
                    name, _, elapsed = self.steps[self.current_step]
                    self.steps[self.current_step] = (name, True, elapsed)
                self._live.update(self._render_display())
                self._live.stop()  # ← 先に止める（ここで transient により画面がクリア）

        finally:
            # ★ Live終了後に stderr バッファを一括フラッシュ
            disable_live_buffering_and_flush()

            self._is_active = False
            StepProgress._global_active = False
            self._stop_timer = True
            if self._timer_thread:
                self._timer_thread.join(timeout=0.8)

    def advance(self):
        # 現ステップを完了
        if self.current_step < len(self.steps):
            name, _, elapsed = self.steps[self.current_step]
            self.steps[self.current_step] = (name, True, elapsed)
        # 次へ
        if self.current_step + 1 < len(self.steps):
            self.current_step += 1
        if self._live:
            self._live.update(self._render_display())