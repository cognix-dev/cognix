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
        version="Cognix 0.2.0"
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

    args = parser.parse_args()
    
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

if __name__ == "__main__":
    main()