"""
Utilities and Helper Functions for Cognix
Common functionality used across the application
"""

import os
import sys
import logging
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import mimetypes
import json
from datetime import datetime, timedelta


def setup_logging(verbose: bool = False, log_file: str = None):
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[]
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger = logging.getLogger()
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


def get_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""


def get_content_hash(content: str) -> str:
    """Calculate MD5 hash of content string"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def is_binary_file(file_path: str) -> bool:
    """Check if file is binary"""
    try:
        # Check MIME type first
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and not mime_type.startswith('text/'):
            return True
        
        # Read sample and check for null bytes
        with open(file_path, 'rb') as f:
            sample = f.read(1024)
            
        if b'\x00' in sample:
            return True
            
        # Check percentage of printable characters
        printable_chars = sum(1 for b in sample if 32 <= b <= 126 or b in [9, 10, 13])
        if len(sample) > 0 and printable_chars / len(sample) < 0.7:
            return True
            
        return False
        
    except Exception:
        return True


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def safe_filename(filename: str) -> str:
    """Convert string to safe filename"""
    # Remove/replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    safe_name = filename
    
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Remove control characters
    safe_name = ''.join(char for char in safe_name if ord(char) >= 32)
    
    # Limit length
    if len(safe_name) > 255:
        safe_name = safe_name[:255]
    
    return safe_name.strip()


def find_project_root(start_path: str = None) -> Optional[str]:
    """Find project root by looking for common project files"""
    if start_path is None:
        start_path = os.getcwd()
    
    path = Path(start_path).resolve()
    
    # Common project root indicators
    root_indicators = [
        '.git',
        '.gitignore',
        'package.json',
        'requirements.txt',
        'setup.py',
        'pyproject.toml',
        'Cargo.toml',
        'pom.xml',
        'build.gradle',
        'Makefile',
        'CLAUDE.md',
        '.cognix.json'
    ]
    
    # Walk up the directory tree
    for parent in [path] + list(path.parents):
        for indicator in root_indicators:
            if (parent / indicator).exists():
                return str(parent)
    
    return None


def get_editor_command() -> List[str]:
    """Get editor command from environment"""
    editor = os.getenv('EDITOR', 'nano')
    
    # Handle common editors
    if 'code' in editor.lower():
        return [editor, '--wait']
    elif 'vim' in editor.lower() or 'nvim' in editor.lower():
        return [editor]
    elif 'emacs' in editor.lower():
        return [editor, '-nw']
    elif 'nano' in editor.lower():
        return [editor]
    else:
        return [editor]


def open_in_editor(file_path: str) -> bool:
    """Open file in configured editor"""
    try:
        editor_cmd = get_editor_command()
        editor_cmd.append(file_path)
        
        result = subprocess.run(editor_cmd, check=True)
        return result.returncode == 0
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_command(command: List[str], cwd: str = None, timeout: int = 30) -> Tuple[bool, str, str]:
    """Run shell command and return success, stdout, stderr"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return (
            result.returncode == 0,
            result.stdout,
            result.stderr
        )
        
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard"""
    try:
        if shutil.which('pbcopy'):  # macOS
            subprocess.run(['pbcopy'], input=text, text=True, check=True)
        elif shutil.which('xclip'):  # Linux
            subprocess.run(['xclip', '-selection', 'clipboard'], input=text, text=True, check=True)
        elif shutil.which('clip'):  # Windows
            subprocess.run(['clip'], input=text, text=True, check=True)
        else:
            return False
        
        return True
        
    except Exception:
        return False


def get_terminal_size() -> Tuple[int, int]:
    """Get terminal size (width, height)"""
    try:
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    except Exception:
        return 80, 24  # Default fallback


def print_table(headers: List[str], rows: List[List[str]], max_width: int = None):
    """Print formatted table"""
    if not rows:
        return
    
    if max_width is None:
        max_width, _ = get_terminal_size()
    
    # Calculate column widths
    col_widths = [len(header) for header in headers]
    
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Adjust widths if table is too wide
    total_width = sum(col_widths) + len(col_widths) * 3 + 1
    if total_width > max_width:
        # Proportionally reduce column widths
        scale_factor = (max_width - len(col_widths) * 3 - 1) / sum(col_widths)
        col_widths = [max(8, int(w * scale_factor)) for w in col_widths]
    
    # Print header
    header_row = "| " + " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers)) + " |"
    print(header_row)
    print("|" + "|".join("-" * (w + 2) for w in col_widths) + "|")
    
    # Print rows
    for row in rows:
        row_str = "| "
        for i, cell in enumerate(row):
            if i < len(col_widths):
                cell_str = str(cell)
                if len(cell_str) > col_widths[i]:
                    cell_str = cell_str[:col_widths[i]-3] + "..."
                row_str += cell_str.ljust(col_widths[i]) + " | "
        print(row_str.rstrip())


def print_diff_highlighted(diff_content: str):
    """Print diff with syntax highlighting (if available)"""
    lines = diff_content.split('\n')
    
    for line in lines:
        if line.startswith('+++') or line.startswith('---'):
            print(f"\033[1m{line}\033[0m")  # Bold
        elif line.startswith('@@'):
            print(f"\033[36m{line}\033[0m")  # Cyan
        elif line.startswith('+'):
            print(f"\033[32m{line}\033[0m")  # Green
        elif line.startswith('-'):
            print(f"\033[31m{line}\033[0m")  # Red
        else:
            print(line)


def create_temp_file(content: str, suffix: str = ".tmp") -> str:
    """Create temporary file with content"""
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name


def cleanup_temp_files(temp_files: List[str]):
    """Clean up temporary files"""
    for temp_file in temp_files:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def validate_model_name(model_name: str) -> bool:
    """Validate model name format"""
    valid_models = [
        "claude-3-opus", "claude-3-opus-20240229",
        "claude-3-sonnet", "claude-3-sonnet-20240229",
        "claude-3-haiku", "claude-3-haiku-20240307",
        "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
        "gpt-3.5-turbo"
    ]
    
    return model_name in valid_models


def parse_model_from_string(model_string: str) -> Optional[str]:
    """Parse model name from various string formats"""
    model_string = model_string.lower().strip()
    
    # Direct matches
    model_mappings = {
        "claude": "claude-3-opus",
        "claude-opus": "claude-3-opus",
        "claude-sonnet": "claude-3-sonnet", 
        "claude-haiku": "claude-3-haiku",
        "gpt4": "gpt-4",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt3.5": "gpt-3.5-turbo",
        "gpt-3.5": "gpt-3.5-turbo"
    }
    
    if model_string in model_mappings:
        return model_mappings[model_string]
    elif validate_model_name(model_string):
        return model_string
    
    return None


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count"""
    # Very rough approximation: ~4 characters per token on average
    return len(text) // 4


def split_text_by_tokens(text: str, max_tokens: int) -> List[str]:
    """Split text into chunks by estimated token count"""
    if estimate_tokens(text) <= max_tokens:
        return [text]
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        para_tokens = estimate_tokens(paragraph)
        current_tokens = estimate_tokens(current_chunk)
        
        if current_tokens + para_tokens <= max_tokens:
            if current_chunk:
                current_chunk += '\n\n' + paragraph
            else:
                current_chunk = paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = paragraph
            
            # If single paragraph is too large, split by sentences
            if para_tokens > max_tokens:
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    sentence_tokens = estimate_tokens(sentence)
                    current_tokens = estimate_tokens(current_chunk)
                    
                    if current_tokens + sentence_tokens <= max_tokens:
                        if current_chunk:
                            current_chunk += '. ' + sentence
                        else:
                            current_chunk = sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def get_language_from_filename(filename: str) -> Optional[str]:
    """Get programming language from filename"""
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'jsx',
        '.tsx': 'tsx',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cxx': 'cpp',
        '.cc': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'zsh',
        '.fish': 'fish',
        '.ps1': 'powershell',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.xml': 'xml',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.cfg': 'ini',
        '.conf': 'config',
        '.md': 'markdown',
        '.markdown': 'markdown',
        '.rst': 'restructuredtext',
        '.txt': 'text',
        '.sql': 'sql',
        '.r': 'r',
        '.R': 'r',
        '.m': 'matlab',
        '.pl': 'perl',
        '.lua': 'lua',
        '.vim': 'vim'
    }
    
    path = Path(filename)
    suffix = path.suffix.lower()
    
    # Check exact filename matches first
    if path.name.lower() in ['dockerfile', 'makefile', 'rakefile']:
        return path.name.lower()
    
    return language_map.get(suffix)


def format_code_block(code: str, language: str = None) -> str:
    """Format code in markdown code block"""
    if language:
        return f"```{language}\n{code}\n```"
    else:
        return f"```\n{code}\n```"


def extract_code_from_markdown(text: str) -> List[Dict[str, str]]:
    """Extract code blocks from markdown text"""
    import re
    
    # Pattern to match code blocks
    pattern = r'```(\w+)?\n(.*?)\n```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    code_blocks = []
    for language, code in matches:
        code_blocks.append({
            'language': language or 'text',
            'code': code.strip()
        })
    
    return code_blocks


def confirm_action(prompt: str, default: bool = False) -> bool:
    """Ask user for confirmation"""
    suffix = " [Y/n]" if default else " [y/N]"
    
    try:
        response = input(prompt + suffix + " ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', 'true', '1']
        
    except (KeyboardInterrupt, EOFError):
        return False


def get_user_input(prompt: str, default: str = None, required: bool = False) -> Optional[str]:
    """Get user input with optional default"""
    full_prompt = prompt
    if default:
        full_prompt += f" [{default}]"
    full_prompt += ": "
    
    try:
        response = input(full_prompt).strip()
        
        if not response:
            if default:
                return default
            elif required:
                print("Input is required.")
                return get_user_input(prompt, default, required)
            else:
                return None
        
        return response
        
    except (KeyboardInterrupt, EOFError):
        return None


class ProgressBar:
    """Simple console progress bar"""
    
    def __init__(self, total: int, width: int = 50, description: str = ""):
        self.total = total
        self.width = width
        self.description = description
        self.current = 0
        self.start_time = datetime.now()
    
    def update(self, increment: int = 1):
        """Update progress"""
        self.current = min(self.current + increment, self.total)
        self._draw()
    
    def set_progress(self, current: int):
        """Set absolute progress"""
        self.current = min(current, self.total)
        self._draw()
    
    def _draw(self):
        """Draw progress bar"""
        if self.total == 0:
            return
        
        percent = self.current / self.total
        filled = int(self.width * percent)
        bar = '█' * filled + '░' * (self.width - filled)
        
        elapsed = datetime.now() - self.start_time
        elapsed_str = format_duration(elapsed.total_seconds())
        
        print(f"\r{self.description} |{bar}| {self.current}/{self.total} ({percent:.1%}) {elapsed_str}", end='', flush=True)
        
        if self.current >= self.total:
            print()  # New line when complete


def create_backup_filename(original_path: str) -> str:
    """Create backup filename with timestamp"""
    path = Path(original_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{path.stem}_{timestamp}{path.suffix}.backup"


def ensure_directory_exists(directory: str) -> bool:
    """Ensure directory exists, create if necessary"""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False