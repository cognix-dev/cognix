# cognix/ui.py
"""
アイコン統一システム - Cognix UI改善計画書 Phase 1 Day 2
完全Zen記号化でミニマルな美学を追求
"""

from enum import Enum
from pathlib import Path
from rich.console import Console
from rich.theme import Theme

# Import theme colors
from cognix.theme_zen import GREEN, RESET

# --- Zen HUD integration (safe optional import) ---
try:
    from cognix.ui_zen_integration import render_logo_once_if_needed as _zen_logo_once
except Exception:
    _zen_show_logo = None
    _zen_tips_line = None

# カスタムテーマ
custom_theme = Theme({
    "info": "cyan",
    "success": "bold green",
    "warning": "yellow",
    "error": "bold red",
    "debug": "dim",
    "highlight": "bold magenta",
})

console = Console(theme=custom_theme, stderr=True)


class Icon(str, Enum):
    """統一アイコン定義（Zen Theme完全版）
    
    全てのCognixコンポーネントで使用する記号を一元管理
    ミニマルな美学を追求し、環境依存性を排除
    """
    
    # ステータス（Zen化）
    SUCCESS = "✓"   # ✅ → ✓（チェックマーク）
    ERROR = "✕"     # ❌ → ✕（バツ印）
    WARNING = "ⓘ"   # ⚠️ → ⚠（警告三角）
    INFO = "ⓘ"      # ℹ️ → ⓘ（情報マーク）
    
    # プロセス（Zen化）
    ROBOT = "●"     # 🤖 → ⚙（歯車・機械処理）
    GEAR = "●"      # 既存のまま（Zen的）
    SEARCH = "⊙"    # 🔍 → ⊙（検索・焦点）
    ROCKET = "↑"    # 🚀 → ↑（上昇・デプロイ）
    BRAIN = "◉"     # 🧠 → ◉（思考・分析）
    CHART = "≡"     # 📊 → ≡（データ・統計）
    LIGHT = "◆"     # 💡 → ◆（洞察・ヒント）
    
    # ファイル操作（Zen化）
    FILE = "▭"      # 📄 → ▭（ドキュメント・矩形）
    FOLDER = "▢"    # 📁 → ▢（フォルダ・箱）
    EDIT = "✎"      # ✏️ → ✎（編集・鉛筆）
    DELETE = "✕"    # 🗑️ → ✕（削除・バツ）
    PACKAGE = "▣"   # 📦 → ▣（パッケージ・箱）
    
    # プログラミング言語（Zen化）
    PYTHON = "◇"    # 🐍 → ◇（ダイヤモンド）
    JAVASCRIPT = "◈" # 📜 → ◈（JS的なシンボル）
    HTML = "⟐"      # 🌐 → ⟐（タグ的な形）
    CSS = "◐"       # 🎨 → ◐（スタイル・半円）
    JSON = "≣"      # 📊 → ≣（構造化データ）
    MARKDOWN = "≋"  # 📝 → ≋（マークアップ・波線）
    YAML = "⊞"      # ⚙️ → ⊞（構成・十字）
    
    # Git（Zen化）
    GIT_BRANCH = "⎇"  # 🌿 → ⎇（ブランチ・分岐）
    GIT_COMMIT = "●"  # 📌 → ●（コミット・点）
    GIT_MERGE = "⋈"   # 🔀 → ⋈（マージ・結合）
    
    # リスクレベル（Zen化）
    RISK_HIGH = "◼"   # 🔴 → ◼（高リスク・黒四角）
    RISK_MEDIUM = "◆" # 🟡 → ◆（中リスク・ダイヤ）
    RISK_LOW = "◇"    # 🟢 → ◇（低リスク・白ダイヤ）
    
    # その他（Zen化）
    PARTY = "✦"       # 🎉 → ✦（祝福・星）
    CLOCK = "⏱"       # ⏰ → ⏱（時計）
    FIRE = "◆"        # 🔥 → ◆（炎・重要）
    STAR = "⋆"        # ⭐ → ⋆（星）
    WRENCH = "⚙"      # 🔧 → ⚙（修理・歯車）
    SPARKLE = "✦"     # ✨ → ✦（輝き）
    SKIP = "⇥"        # ⏭️ → ⇥（スキップ）


class FileIconMapper:
    """ファイル拡張子からアイコンへのマッピング"""
    
    _ICON_MAP = {
        # Python
        ".py": Icon.PYTHON,
        ".pyi": Icon.PYTHON,
        
        # JavaScript/TypeScript
        ".js": Icon.JAVASCRIPT,
        ".jsx": Icon.JAVASCRIPT,
        ".ts": Icon.JAVASCRIPT,
        ".tsx": Icon.JAVASCRIPT,
        ".mjs": Icon.JAVASCRIPT,
        
        # Web
        ".html": Icon.HTML,
        ".htm": Icon.HTML,
        ".css": Icon.CSS,
        ".scss": Icon.CSS,
        ".sass": Icon.CSS,
        ".less": Icon.CSS,
        
        # Data
        ".json": Icon.JSON,
        
        # Documentation
        ".md": Icon.MARKDOWN,
        ".markdown": Icon.MARKDOWN,
        ".txt": "≋",      # Zen化
        ".rst": "≋",      # Zen化
        
        # Config
        ".yml": Icon.YAML,
        ".yaml": Icon.YAML,
        ".toml": "⊞",     # Zen化
        ".ini": "⊞",      # Zen化
        ".cfg": "⊞",      # Zen化
        
        # Environment
        ".env": "◈",      # Zen化（鍵→ダイヤ）
        ".env.example": "◈",
        ".env.local": "◈",
        
        # Package managers
        "package.json": "▣",
        "package-lock.json": "◈",
        "requirements.txt": "▣",
        "Pipfile": "▣",
        "Pipfile.lock": "◈",
        "poetry.lock": "◈",
        "pyproject.toml": "▣",
        
        # Others
        ".gitignore": "⎇",
        ".dockerignore": "◈",
        "Dockerfile": "◈",
        "docker-compose.yml": "◈",
        "Makefile": "⚙",
    }
    
    @classmethod
    def get_icon(cls, filename: str) -> str:
        """ファイル名から適切なアイコンを取得
        
        Args:
            filename: ファイル名 (例: "app.py", "package.json")
            
        Returns:
            適切な記号アイコン
        """
        # 完全一致チェック (特定のファイル名)
        if filename in cls._ICON_MAP:
            icon = cls._ICON_MAP[filename]
            # Enumの場合は.valueを取得
            return icon.value if isinstance(icon, Icon) else icon
        
        # 拡張子チェック
        ext = Path(filename).suffix.lower()
        icon = cls._ICON_MAP.get(ext, Icon.FILE)
        # Enumの場合は.valueを取得
        return icon.value if isinstance(icon, Icon) else icon


def print_file_list(files: list[str], style: str = ""):
    """ファイルリストをアイコン付きで表示
    
    Args:
        files: ファイル名のリスト
        style: Rich console style (例: "green", "bold cyan")
    """
    for filename in files:
        icon = FileIconMapper.get_icon(filename)
        console.print(f"   {icon} {filename}", style=style)


def get_risk_icon(score: float) -> str:
    """影響スコアからリスクアイコンを取得
    
    Args:
        score: 影響スコア (0.0 ~ 1.0)
        
    Returns:
        リスクレベルに応じた記号アイコン
    """
    if score > 0.7:
        return Icon.RISK_HIGH.value
    elif score > 0.4:
        return Icon.RISK_MEDIUM.value
    else:
        return Icon.RISK_LOW.value


# ===== Phase 1: 基本視覚強化 =====


class ColorScheme:
    """統一的な色定義
    
    Cognix全体で使用する色スキームを一元管理
    coloramaとRich両対応
    """
    
    # colorama用
    try:
        from colorama import Fore, Style, just_fix_windows_console
        just_fix_windows_console()
        
        SUCCESS = Fore.GREEN
        ERROR = Fore.RED
        WARNING = Fore.YELLOW
        INFO = Fore.CYAN
        HIGHLIGHT = Fore.MAGENTA
        DIM = Style.DIM
        BRIGHT = Style.BRIGHT
        RESET = Style.RESET_ALL
        
    except (ImportError, AttributeError):
        # colorama未使用の場合は空文字列
        SUCCESS = ""
        ERROR = ""
        WARNING = ""
        INFO = ""
        HIGHLIGHT = ""
        DIM = ""
        BRIGHT = ""
        RESET = ""
    
    # Rich style名（console.print()で使用）
    RICH_SUCCESS = "success"
    RICH_ERROR = "error"
    RICH_WARNING = "warning"
    RICH_INFO = "info"
    RICH_HIGHLIGHT = "highlight"
    RICH_DEBUG = "debug"


class StatusIndicator:
    """ステータス表示の統一インターフェース
    
    記号 + 色分けで一貫したステータス表示を提供
    
    Colorama版（ANSI文字列）とRich Markup版を提供:
    - 通常メソッド: Colorama用（プレーンテキスト出力用）
    - _rich版メソッド: Rich Console用（err_console.print()用）
    """
    
    # ===== Colorama版（ANSI文字列）=====
    
    @staticmethod
    def pending(text: str) -> str:
        """保留中のステータス（Colorama版）"""
        return f"{ColorScheme.INFO}⏱ {text}{ColorScheme.RESET}"
    
    @staticmethod
    def running(text: str) -> str:
        """実行中のステータス（Colorama版）"""
        return f"{ColorScheme.HIGHLIGHT}▶ {text}{ColorScheme.RESET}"
    
    @staticmethod
    def success(text: str) -> str:
        """成功ステータス（Colorama版）"""
        return f"{ColorScheme.SUCCESS}✓ {text}{ColorScheme.RESET}"
    
    @staticmethod
    def error(text: str) -> str:
        """エラーステータス（Colorama版）"""
        return f"{ColorScheme.ERROR}✕ {text}{ColorScheme.RESET}"
    
    @staticmethod
    def warning(text: str) -> str:
        """警告ステータス（Colorama版）"""
        return f"{ColorScheme.WARNING}⚠ {text}{ColorScheme.RESET}"
    
    @staticmethod
    def info(text: str) -> str:
        """情報ステータス（Colorama版）"""
        return f"{ColorScheme.INFO}ⓘ {text}{ColorScheme.RESET}"
    
    # ===== Rich Markup版（err_console.print()用）=====
    
    @staticmethod
    def pending_rich(text: str) -> str:
        """保留中のステータス（Rich Markup版）
        
        err_console.print()で使用する場合はこちらを使用
        """
        return f"[cyan]⏱ {text}[/cyan]"
    
    @staticmethod
    def running_rich(text: str) -> str:
        """実行中のステータス（Rich Markup版）
        
        err_console.print()で使用する場合はこちらを使用
        """
        return f"[magenta]▶ {text}[/magenta]"
    
    @staticmethod
    def success_rich(text: str) -> str:
        """成功ステータス（Rich Markup版）
        
        err_console.print()で使用する場合はこちらを使用
        """
        return f"[green]✓ {text}[/green]"
    
    @staticmethod
    def error_rich(text: str) -> str:
        """エラーステータス（Rich Markup版）
        
        err_console.print()で使用する場合はこちらを使用
        """
        return f"[red]✕ {text}[/red]"
    
    @staticmethod
    def warning_rich(text: str) -> str:
        """警告ステータス（Rich Markup版）
        
        err_console.print()で使用する場合はこちらを使用
        """
        return f"[yellow]⚠ {text}[/yellow]"
    
    @staticmethod
    def info_rich(text: str) -> str:
        """情報ステータス（Rich Markup版）
        
        err_console.print()で使用する場合はこちらを使用
        """
        return f"[cyan]ⓘ {text}[/cyan]"

def print_success_banner(message: str, details: str = None):
    """成功メッセージをバナー形式で表示
    
    Args:
        message: メインメッセージ
        details: 詳細情報（オプション）
    """
    from rich.panel import Panel
    
    content = f"[bold green]✓ {message}[/bold green]"
    if details:
        content += f"\n[dim]{details}[/dim]"
    
    console.print(Panel(
        content,
        border_style="green",
        padding=(1, 2)
    ))


def print_error_banner(message: str, details: str = None):
    """エラーメッセージをバナー形式で表示
    
    Args:
        message: メインメッセージ
        details: 詳細情報（オプション）
    """
    from rich.panel import Panel
    
    content = f"[bold red]✕ {message}[/bold red]"
    if details:
        content += f"\n[dim]{details}[/dim]"
    
    console.print(Panel(
        content,
        border_style="red",
        padding=(1, 2)
    ))


def print_warning_banner(message: str, details: str = None):
    """警告メッセージをバナー形式で表示
    
    Args:
        message: メインメッセージ
        details: 詳細情報（オプション）
    """
    from rich.panel import Panel
    
    content = f"[bold yellow]⚠ {message}[/bold yellow]"
    if details:
        content += f"\n[dim]{details}[/dim]"
    
    console.print(Panel(
        content,
        border_style="yellow",
        padding=(1, 2)
    ))


def print_info_banner(message: str, details: str = None):
    """情報メッセージをバナー形式で表示
    
    Args:
        message: メインメッセージ
        details: 詳細情報（オプション）
    """
    from rich.panel import Panel
    
    content = f"[bold cyan]ⓘ {message}[/bold cyan]"
    if details:
        content += f"\n[dim]{details}[/dim]"
    
    console.print(Panel(
        content,
        border_style="cyan",
        padding=(1, 2)
    ))

def print_usage_statistics(stats: dict):
    """トークン使用量と経過時間の統計を表示
    
    Args:
        stats: get_token_statistics()から返される統計情報
    
    Phase 2: /usageコマンド用の表示機能
    """
    from rich.table import Table
    from rich.panel import Panel
    
    # セッション情報テーブル
    session_table = Table(show_header=False, box=None, padding=(0, 1))
    session_table.add_column("Property", style="cyan", no_wrap=True)
    session_table.add_column("Value", style="white")
    
    session_table.add_row("Total Interactions", f"{stats.get('entries_count', 0)} messages")
    session_table.add_row("Session Duration", stats.get('duration_formatted', '0s'))
    
    # トークン使用量テーブル
    token_table = Table(show_header=True, box=None, padding=(0, 1))
    token_table.add_column("Category", style="cyan", no_wrap=True)
    token_table.add_column("Input Tokens", style="white", justify="right")
    token_table.add_column("Output Tokens", style="white", justify="right")
    token_table.add_column("Total", style="bold white", justify="right")
    
    input_tokens = stats.get('total_tokens_input', 0)
    output_tokens = stats.get('total_tokens_output', 0)
    total_tokens = stats.get('total_tokens', 0)
    
    token_table.add_row(
        "Session Total",
        f"{input_tokens:,}",
        f"{output_tokens:,}",
        f"{total_tokens:,}"
    )
    
    # コスト見積もりテーブル
    cost_table = Table(show_header=False, box=None, padding=(0, 1))
    cost_table.add_column("Item", style="cyan", no_wrap=True)
    cost_table.add_column("Cost", style="white", justify="right")
    
    input_cost = stats.get('input_cost', 0.0)
    output_cost = stats.get('output_cost', 0.0)
    total_cost = stats.get('estimated_cost', 0.0)
    
    cost_table.add_row("Input Cost ($3.00/MTok)", f"${input_cost:.4f}")
    cost_table.add_row("Output Cost ($15.00/MTok)", f"${output_cost:.4f}")
    cost_table.add_row("[bold]Estimated Total Cost[/bold]", f"[bold]${total_cost:.4f}[/bold]")
    
    # パネルで表示
    console.print("\n≡ Token Usage Statistics\n", style="bold cyan")
    console.print(Panel(session_table, title="Session Information", border_style="cyan"))
    console.print(Panel(token_table, title="Token Consumption", border_style="cyan"))
    # （末尾）
    console.print(Panel(cost_table, title="Cost Estimation", border_style="cyan"))


# ============================================================================
# Phase 5: 起動アニメーション
# ============================================================================

def show_startup_animation(config=None):
    """
    起動ロゴアニメを表示（Zenがあれば version を渡す / 無ければ静的）
    """
    try:
        version = getattr(config, "version", None) or "0.2.2"
    except Exception:
        version = "0.2.2"

    if '_zen_logo_once' in globals() and _zen_logo_once:
        try:
            _zen_logo_once(version=version)
            return
        except Exception:
            pass  # フォールバックへ

    console.print("Cognix CLI initialized")

def tips_help_line() -> str:
    """
    Tips 行（ANSIコードで返す：err_console.print(Text.from_ansi())用）
    
    """
    # グリーンで色付けする部分: /help, /make, goal, @
    return (
        "⊹  Help: " + GREEN + "/help" + RESET + 
        "   ·   Build: " + GREEN + "/make" + RESET + ' "' + GREEN + "goal" + RESET + '"' +
        "   ·   Spec: " + GREEN + "/make" + RESET + " " + GREEN + "@" + RESET + "file.md"
    )