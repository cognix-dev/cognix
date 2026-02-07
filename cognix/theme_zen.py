# cognix.theme_zen
from __future__ import annotations
import os, sys, shutil

UNICODE_OK = os.getenv("COGNIX_FORCE_ASCII", "0") not in ("1", "true", "True")

CHECK = "✓" if UNICODE_OK else "OK"
RUN   = "⟳" if UNICODE_OK else ">"
DOT   = "·" if UNICODE_OK else "."
WARN  = "ⓘ" if UNICODE_OK else "!"

RESET = "\033[0m"
DIM   = "\033[2m"
FG    = "\033[38;5;252m"
WHITE = "\033[38;5;255m"  # 白色（Previous Session用）
GREEN = "\033[92m"  # ANSI bright green (same as Rich's bright_green)
GREEN_BRIGHT = "\033[1;92m"  # Bold bright green
ACCENT = GREEN
WARN_FG = "\033[38;5;179m"
YELLOW = "\033[38;5;226m"  # RUNNINGステータス用
CYAN = "\033[38;5;51m"     # 代替アクセント色
ORANGE = "\033[38;5;214m"  # 焼き色（バージョン表示用）
MAGENTA = "\033[95m"  # ANSI bright magenta (拒否メッセージ用)

def is_tty() -> bool:
    try:
        return sys.stdout.isatty()
    except Exception:
        return False

def term_width(default: int = 80) -> int:
    try:
        w = shutil.get_terminal_size((default, 24)).columns
        return max(40, min(160, w))
    except Exception:
        return default

def rule(title: str | None = None) -> str:
    w = term_width()
    bar = "─" if UNICODE_OK else "-"
    rule_line = bar * w if not title else (bar * ((w - len(f" {title} ")) // 2)) + f" {title} " + (bar * ((w - len(f" {title} ")) - (w - len(f" {title} ")) // 2))
    # ルール線を緑色に
    return color(rule_line, GREEN)

def color(s: str, code: str) -> str:
    if not is_tty():
        return s
    return f"{code}{s}{RESET}"

def rule_rich(title: str | None = None) -> str:
    """Richマークアップ版のrule（err_console.print()用）"""
    w = term_width()
    bar = "─" if UNICODE_OK else "-"
    if not title:
        rule_line = bar * w
    else:
        left_len = (w - len(f" {title} ")) // 2
        right_len = w - len(f" {title} ") - left_len
        rule_line = (bar * left_len) + f" {title} " + (bar * right_len)
    # Richマークアップで緑色に
    return f"[#78af00]{rule_line}[/#78af00]"  # RGB(120,175,0) = cognix green