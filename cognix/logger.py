# logger.py
import os
import logging
from enum import IntEnum
from typing import Any, List, Tuple, Dict
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

# stdout: 進捗やLive用  / stderr: ログ用
console = Console(legacy_windows=False, force_terminal=None, highlight=False)
err_console = Console(stderr=True, legacy_windows=False, force_terminal=None, highlight=False)

# ---- Live中バッファリング: ここから ---------------------------------
_LIVE_BUFFER_ACTIVE: bool = False
_LIVE_BUFFER: List[Tuple[Tuple[Any, ...], Dict[str, Any]]] = []
_ORIG_ERR_PRINT = err_console.print  # 退避

def _buffering_err_print(*args: Any, **kwargs: Any):
    """Live中はstderr出力をバッファへ。Live外では通常出力。"""
    # Rich Console.print() は flush 引数を受け付けないので除外
    kwargs.pop('flush', None)
    if _LIVE_BUFFER_ACTIVE:
        _LIVE_BUFFER.append((args, kwargs))
        return
    _ORIG_ERR_PRINT(*args, **kwargs)

def enable_live_buffering():
    """StepProgress.enter から呼ぶ: Live中はstderr出力をバッファする"""
    global _LIVE_BUFFER_ACTIVE
    if not _LIVE_BUFFER_ACTIVE:
        _LIVE_BUFFER_ACTIVE = True

def disable_live_buffering_and_flush():
    """StepProgress.exit から呼ぶ: Live終了後にstderrバッファをまとめて吐く"""
    global _LIVE_BUFFER_ACTIVE
    if _LIVE_BUFFER_ACTIVE:
        _LIVE_BUFFER_ACTIVE = False
        # 一度に吐く（Live停止後なので画面は乱れない）
        for args, kwargs in _LIVE_BUFFER:
            _ORIG_ERR_PRINT(*args, **kwargs)
        _LIVE_BUFFER.clear()

# err_console.print を差し替える（以降、全ての stderr 出力はこの関数経由に）
err_console.print = _buffering_err_print  # type: ignore
# ---- Live中バッファリング: ここまで ---------------------------------

# ==========================================
# ⭐ ファイルログ出力機能を追加（COGNIX_DEBUG=1 の時のみ）
# ==========================================

_file_handler = None
_LOG_FILE = None

if os.getenv('COGNIX_DEBUG', '').lower() in ('1', 'true', 'yes'):
    # ログファイルのパスを決定
    _LOG_DIR = Path.home() / ".cognix" / "logs"
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = _LOG_DIR / "cognix_debug.log"

    # ファイルハンドラーを作成（UTF-8エンコーディング指定）
    _file_handler = logging.FileHandler(
        _LOG_FILE,
        mode='a',  # 追記モード
        encoding='utf-8'
    )
    _file_handler.setLevel(logging.DEBUG)  # ファイルには全てのレベルを出力

    # ファイルハンドラーのフォーマット（タイムスタンプ付き）
    _file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    _file_handler.setFormatter(_file_formatter)

# ⭐ RichHandlerを作成
_rich_handler = RichHandler(
    console=err_console,
    rich_tracebacks=True,
    show_path=False,
    markup=True,
)
_rich_handler.setLevel(logging.INFO)  # ⭐ 画面表示はINFO以上のみ

# ハンドラーのリストを作成
_handlers = [_rich_handler]
if _file_handler:
    _handlers.append(_file_handler)

# RichHandler を stderr に固定（Live と分離）
logging.basicConfig(
    level=logging.DEBUG,  # ⭐ DEBUGに設定（ファイル出力のため）
    handlers=_handlers,
    format="%(message)s",
    force=True,
)

_std_logger = logging.getLogger("cognix")
_std_logger.propagate = False  # 親へ伝播させない
_std_logger.setLevel(logging.DEBUG)  # ⭐ DEBUGレベルに設定

# ⭐ _std_logger に直接ハンドラーを追加
for handler in _handlers:
    _std_logger.addHandler(handler)
class LogLevel(IntEnum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2
    DEBUG = 3

class Logger:
    def __init__(self):
        self._level = self._detect_log_level()
        # ⭐ _std_logger.setLevel() は呼ばない
        # （logging.basicConfig で level=DEBUG に設定済み）
        # ファイル出力は常にDEBUGレベル、画面表示はlogger.debug()内で制御

    def _detect_log_level(self) -> LogLevel:
        if os.getenv("COGNIX_QUIET", "").lower() in ("1", "true", "yes"):
            return LogLevel.QUIET
        if os.getenv("COGNIX_VERBOSE", "").lower() in ("1", "true", "yes"):
            return LogLevel.VERBOSE
        if os.getenv("COGNIX_DEBUG", "").lower() in ("1", "true", "yes"):
            return LogLevel.DEBUG
        return LogLevel.NORMAL

    @property
    def level(self) -> LogLevel:
        return self._level


    def setLevel(self, level: str):
        m = {"QUIET": LogLevel.QUIET, "NORMAL": LogLevel.NORMAL,
             "VERBOSE": LogLevel.VERBOSE, "DEBUG": LogLevel.DEBUG,
             "WARNING": LogLevel.NORMAL}
        if level in m:
            self._level = m[level]
            # ⭐ _std_logger.setLevel() は呼ばない

    # 以降はすべて err_console.print（＝バッファ対応版）経由
    def normal(self, message: str, **kwargs: Any):
        if self._level >= LogLevel.NORMAL:
            err_console.print(message, **kwargs)

    def verbose(self, message: str, **kwargs: Any):
        if self._level >= LogLevel.VERBOSE:
            err_console.print(message, **kwargs)

    def debug(self, message: str, **kwargs: Any):
        if self._level >= LogLevel.DEBUG:
            err_console.print(f"[dim][DEBUG][/] {message}", **kwargs)
        
        # ⭐ デバッグログは常にファイルに出力（画面表示設定に関わらず）
        _std_logger.debug(message)

    def error(self, message: str, **kwargs: Any):
        err_console.print(f"❌ {message}", style="bold red", **kwargs)
        _std_logger.error(message)

    def success(self, message: str, **kwargs: Any):
        if self._level >= LogLevel.NORMAL:
            err_console.print(f"✅ {message}", style="bold green", **kwargs)
        _std_logger.info(f"SUCCESS: {message}")

    def warning(self, message: str, **kwargs: Any):
        if self._level >= LogLevel.NORMAL:
            err_console.print(f"⚠️  {message}", style="bold yellow", **kwargs)
        _std_logger.warning(message)

logger = Logger()

# ⭐ ログファイルパスを出力（起動時に1回だけ）
if os.getenv("COGNIX_DEBUG", "").lower() in ("1", "true", "yes"):
    print(f"📝 Debug log: {_LOG_FILE}")

__all__ = [
    "logger", "console", "err_console",
    "enable_live_buffering", "disable_live_buffering_and_flush",
    "LogLevel",
]