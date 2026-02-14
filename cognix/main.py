#!/usr/bin/env python3
"""
Cognix - Main CLI Entry Point
AI-powered CLI-based development assistant
"""
# 起動アニメ / Tips は cli_main.py 側で処理

import sys
import os
import argparse
from pathlib import Path

# HTTPログを無効化（最初に実行）
import logging
logging.getLogger("anthropic").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)

# 修正後の正しいインポート
from cognix.cli import CognixCLI
from cognix.config import Config
from cognix.utils import setup_logging
from cognix.logger import err_console
from cognix import __version__

def main():
    # さらに確実にログを制御
    logging.getLogger("anthropic").propagate = False
    logging.getLogger("httpx").propagate = False
    logging.getLogger("httpcore").propagate = False

    parser = argparse.ArgumentParser(
        description="Cognix - AI-powered CLI development assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  AI driven development:
    /make            - Automatic implementation with AI assistance
    /review          - Code review

  Repository:
    /repo-init       - Initialize repository
    /repo-stats      - Display repository status

  Execution:
    /run             - Run command

  Utility:
    /status          - Display current status
    /model           - Switch or display model
    /exit            - Exit the CLI application

Interactive mode:
  Run without arguments to start interactive chat mode

Non-interactive mode:
  cognix --make "Create a Flask REST API"
  cognix --make-file spec.md
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file (default: ~/.cognix/config.json)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        help="Override model (e.g., claude-sonnet-4-5-20250929, gpt-5.1)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"Cognix {__version__}"
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Enable automatic mode (no confirmations)"
    )

    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Start in MCP server mode (for Claude Desktop, Cursor, etc.)"
    )

    # ===================================================
    # 非対話モード用フラグ
    # ===================================================
    parser.add_argument(
        "--make",
        type=str,
        metavar="PROMPT",
        help="Run /make with the given prompt non-interactively and exit"
    )

    parser.add_argument(
        "--make-file",
        type=str,
        metavar="FILE",
        help="Run /make with prompt read from FILE non-interactively and exit"
    )

    args = parser.parse_args()

    # --make と --make-file の排他チェック
    if args.make is not None and args.make_file:
        err_console.print("[red]Error: --make and --make-file cannot be used together.[/red]")
        sys.exit(1)
    
    # Check if MCP mode is requested
    if args.mcp:
        # Import and run MCP server
        try:
            from cognix.mcp_server import main as mcp_main
            import asyncio
            asyncio.run(mcp_main())
            return
        except ImportError as e:
            err_console.print(f"[red]Error: MCP dependencies not installed.[/red]")
            err_console.print(f"[yellow]Install with: pip install mcp>=1.0.0[/yellow]")
            err_console.print(f"[dim]Details: {e}[/dim]")
            sys.exit(1)
        except Exception as e:
            err_console.print(f"[red]Error starting MCP server: {e}[/red]")
            sys.exit(1)
    
    # Setup logging
    setup_logging(verbose=args.verbose)

    # ===================================================
    # 非対話モード: --make / --make-file
    # ===================================================
    if args.make is not None or args.make_file:
        _run_make_non_interactive(args)
        return
    
    try:
        # Initialize configuration
        config = Config(config_path=args.config)
        
        # Override model if specified
        if args.model:
            config.set("model", args.model)
        
        # Set auto mode
        auto_mode = args.auto
        
        # Initialize CLI
        cli = CognixCLI(config=config, auto_mode=auto_mode)
        
        # Show setup guide if first run
        if cli.is_first_run:
            cli._show_setup_guide()
            cli._mark_first_run_complete()
            err_console.print("\nNote: Please restart after setting up your API key.")
            return
        
        # Start interactive mode
        cli.run()
        
    except KeyboardInterrupt:
        err_console.print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        error_msg = str(e)
        if "No LLM providers available" in error_msg:
            err_console.print(f"\n❌ {error_msg}")
            err_console.print("\n◆ Quick start:")
            err_console.print("1. Get an API key from OpenAI or Anthropic")
            err_console.print("2. Create a .env file with your key:")
            err_console.print("   echo 'ANTHROPIC_API_KEY=your_key_here' > .env")
            err_console.print("3. Run the command again")
            sys.exit(1)
        else:
            err_console.print(f"Error: {e}")
            sys.exit(1)


def _run_make_non_interactive(args):
    """非対話モードで /make を実行する
    
    --make "PROMPT" または --make-file FILE で指定されたプロンプトを使い、
    REPLに入らずに /make を直接実行して終了する。
    
    auto_mode=True を強制設定し、対話メニュー（Apply/Reject）を
    スキップして自動Applyする。
    
    終了コード:
        0: 正常完了
        1: エラー
    """
    # プロンプトの取得
    if args.make_file:
        filepath = Path(args.make_file)
        if not filepath.exists():
            err_console.print(f"[red]Error: File not found: {args.make_file}[/red]")
            sys.exit(1)
        try:
            prompt = filepath.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            err_console.print(f"[red]Error: Failed to read file (encoding issue, UTF-8 expected): {args.make_file}[/red]")
            sys.exit(1)
        except Exception as e:
            err_console.print(f"[red]Error: Failed to read file: {e}[/red]")
            sys.exit(1)
        
        if not prompt.strip():
            err_console.print(f"[red]Error: File is empty: {args.make_file}[/red]")
            sys.exit(1)
    else:
        prompt = args.make
    
    if not prompt or not prompt.strip():
        err_console.print("[red]Error: Empty prompt.[/red]")
        sys.exit(1)

    try:
        # Configuration
        config = Config(config_path=args.config)
        
        if args.model:
            config.set("model", args.model)
        
        # auto_mode=True を強制（確認スキップ + 自動Apply）
        cli = CognixCLI(config=config, auto_mode=True)
        
        if cli.is_first_run:
            err_console.print("[red]Error: First run detected. Please run 'cognix' interactively first to complete setup.[/red]")
            sys.exit(1)
        
        # cmd_make を直接呼び出し
        cli.cmd_make(prompt)
        
        # 正常終了
        sys.exit(0)
        
    except KeyboardInterrupt:
        err_console.print("\n\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        err_console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
