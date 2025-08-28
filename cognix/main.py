#!/usr/bin/env python3
"""
Cognix - Main CLI Entry Point
AI-powered CLI-based development assistant
"""

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
  /edit <file>     - Edit a specific file with AI assistance
  /review <dir>    - Review and analyze a directory
  /fix <file>      - Fix/modify a file directly with AI
  /think <goal>    - Analyze problem with AI
  /plan            - Create implementation plan
  /write           - Generate code from plan
  /status          - Show current memory and model state
  /init            - Create CLAUDE.md in current directory
  /config          - Edit or show configuration
  /reset           - Clear memory and start fresh
  /help            - Show help information
  
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
        help="Override model (e.g., claude-sonnet-4-20250514, gpt-4o)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Cognix 0.1.1"
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Enable automatic mode (no confirmations)"
    )

    args = parser.parse_args()
    
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
            print("\nNote: Please restart after setting up your API key.")
            return
        
        # Start interactive mode
        cli.run()
        
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        error_msg = str(e)
        if "No LLM providers available" in error_msg:
            print(f"\n❌ {error_msg}")
            print("\n💡 Quick start:")
            print("1. Get an API key from OpenAI or Anthropic")
            print("2. Create a .env file with your key:")
            print("   echo 'ANTHROPIC_API_KEY=your_key_here' > .env")
            print("3. Run the command again")
            sys.exit(1)
        else:
            print(f"Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()