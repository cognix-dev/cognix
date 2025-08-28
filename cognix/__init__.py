"""
Cognix: AI-powered CLI development assistant
"""

__version__ = "0.1.1"
__author__ = "Cognix"
__description__ = "AI-powered CLI development assistant"
__url__ = "https://github.com/cognix-dev/cognix"

# Core imports
from .config import Config
from .memory import Memory
from .context import FileContext
from .llm import LLMManager, LLMResponse
from .diff_engine import DiffEngine
from .session import SessionManager, SessionEntry, SessionData
from .cli import CognixCLI

# Public API
__all__ = [
    '__version__',
    '__author__',
    '__description__',
    '__url__',
    'Config',
    'Memory',
    'FileContext',
    'LLMManager',
    'LLMResponse',
    'DiffEngine',
    'SessionManager',
    'SessionEntry',
    'SessionData',
    'CognixCLI'
]

def get_version():
    """Get the current version of Cognix."""
    return __version__