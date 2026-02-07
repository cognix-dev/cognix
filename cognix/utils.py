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
    """Setup logging configuration.

    - Root logger を `force=True` で初期化（既存ハンドラの残存を防止）
    - Console handler は stdout ではなく **stderr** を使用（Rich Live との競合回避）
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Reset handlers explicitly
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[],
        force=True,   # ← 重要: 既存ハンドラをリセット
    )

    # Console handler -> stderr
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    logger = logging.getLogger()
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
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
    """Heuristically check if file is binary."""
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and not mime_type.startswith('text/'):
            return True

        with open(file_path, 'rb') as f:
            sample = f.read(1024)

        if b'\x00' in sample:
            return True

        printable = sum(1 for b in sample if 32 <= b <= 126 or b in (9, 10, 13))
        return len(sample) > 0 and printable / len(sample) < 0.7
    except Exception:
        return True


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate string to maximum length with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def ensure_directory(path: str) -> bool:
    """Ensure directory exists, create if not"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Failed to create directory {path}: {e}")
        return False


def safe_remove(path: str) -> bool:
    """Safely remove file or directory"""
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return True
    except Exception as e:
        logging.error(f"Failed to remove {path}: {e}")
        return False


def copy_file_safe(src: str, dst: str, backup: bool = True) -> bool:
    """Copy file with optional backup"""
    try:
        if backup and os.path.exists(dst):
            shutil.copy2(dst, f"{dst}.backup")
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        logging.error(f"Failed to copy {src} to {dst}: {e}")
        return False


def read_file_safe(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """Read file content safely"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to read {file_path}: {e}")
        return None


def write_file_safe(file_path: str, content: str, encoding: str = 'utf-8', backup: bool = True) -> bool:
    """Write content to file safely"""
    try:
        if backup and os.path.exists(file_path):
            shutil.copy2(file_path, f"{file_path}.backup")
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        logging.error(f"Failed to write {file_path}: {e}")
        return False


def run_command(command: List[str], cwd: str = None, capture_output: bool = True,
                timeout: int = 300, env: Dict[str, str] = None) -> Tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            env=env
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        logging.error(f"Command timed out after {timeout}s: {' '.join(command)}")
        return -1, "", "Command timed out"
    except Exception as e:
        logging.error(f"Command failed: {' '.join(command)}: {e}")
        return -1, "", str(e)


def find_files(directory: str, pattern: str = "*", recursive: bool = True,
               exclude_dirs: List[str] = None) -> List[str]:
    """Find files matching pattern."""
    import fnmatch

    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', 'node_modules', '.venv', 'venv']

    files: List[str] = []
    path = Path(directory)
    if not path.exists():
        return files

    try:
        if recursive:
            for item in path.rglob(pattern):
                if item.is_file() and not any(ex in item.parts for ex in exclude_dirs):
                    files.append(str(item))
        else:
            for item in path.glob(pattern):
                if item.is_file():
                    files.append(str(item))
    except Exception as e:
        logging.error(f"Error finding files in {directory}: {e}")

    return files


def get_file_type(file_path: str) -> str:
    """Get file type based on extension"""
    ext = Path(file_path).suffix.lower()
    type_mapping = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'javascript', '.tsx': 'typescript', '.java': 'java',
        '.cpp': 'cpp', '.cc': 'cpp', '.c': 'c', '.h': 'c', '.hpp': 'cpp',
        '.cs': 'csharp', '.rb': 'ruby', '.go': 'go', '.rs': 'rust',
        '.php': 'php', '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
        '.sh': 'shell', '.bash': 'shell', '.zsh': 'shell',
        '.html': 'html', '.css': 'css', '.scss': 'scss', '.sass': 'sass',
        '.json': 'json', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
        '.toml': 'toml', '.md': 'markdown', '.txt': 'text',
    }
    return type_mapping.get(ext, 'unknown')


def get_relative_path(path: str, base: str) -> str:
    """Get relative path from base"""
    try:
        return str(Path(path).relative_to(base))
    except ValueError:
        return path


def validate_path(path: str, must_exist: bool = False) -> bool:
    """Validate if path is valid"""
    try:
        p = Path(path)
        return p.exists() if must_exist else True
    except Exception:
        return False


def create_temp_file(suffix: str = '', prefix: str = 'tmp', text: bool = True) -> str:
    """Create temporary file and return path"""
    try:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, text=text)
        os.close(fd)
        return path
    except Exception as e:
        logging.error(f"Failed to create temp file: {e}")
        return ""


def create_temp_directory(suffix: str = '', prefix: str = 'tmp') -> str:
    """Create temporary directory and return path"""
    try:
        return tempfile.mkdtemp(suffix=suffix, prefix=prefix)
    except Exception as e:
        logging.error(f"Failed to create temp directory: {e}")
        return ""


def get_timestamp(format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Get current timestamp as string"""
    return datetime.now().strftime(format)


def parse_timestamp(timestamp_str: str, format: str = '%Y-%m-%d %H:%M:%S') -> Optional[datetime]:
    """Parse timestamp string to datetime"""
    try:
        return datetime.strptime(timestamp_str, format)
    except Exception:
        return None


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds/60:.1f}m"
    return f"{seconds/3600:.1f}h"


def parse_json_safe(json_str: str) -> Optional[Dict]:
    """Parse JSON string safely"""
    try:
        return json.loads(json_str)
    except Exception as e:
        logging.error(f"Failed to parse JSON: {e}")
        return None


def save_json_safe(data: Dict, file_path: str, indent: int = 2) -> bool:
    """Save data to JSON file safely"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Failed to save JSON to {file_path}: {e}")
        return False


def load_json_safe(file_path: str) -> Optional[Dict]:
    """Load data from JSON file safely"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load JSON from {file_path}: {e}")
        return None


def get_line_count(file_path: str) -> int:
    """Get number of lines in file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_file_extension(file_path: str) -> str:
    """Get file extension without dot"""
    return Path(file_path).suffix.lstrip('.')


def split_path(path: str) -> Tuple[str, str, str]:
    """Split path into directory, name, and extension"""
    p = Path(path)
    return str(p.parent), p.stem, p.suffix


def join_paths(*paths: str) -> str:
    """Join paths safely"""
    return str(Path(*paths))


def normalize_path(path: str) -> str:
    """Normalize path (resolve .., ., etc.)"""
    return str(Path(path).resolve())


def is_subpath(path: str, parent: str) -> bool:
    """Check if path is subpath of parent"""
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def get_common_prefix(paths: List[str]) -> str:
    """Get common prefix of paths"""
    if not paths:
        return ""
    parts_list = [Path(p).parts for p in paths]
    common: List[str] = []
    for parts in zip(*parts_list):
        if len(set(parts)) == 1:
            common.append(parts[0])
        else:
            break
    return str(Path(*common)) if common else ""


def backup_file(file_path: str, backup_dir: str = None) -> Optional[str]:
    """Create backup of file"""
    try:
        if not os.path.exists(file_path):
            return None
        if backup_dir:
            ensure_directory(backup_dir)
            backup_path = os.path.join(backup_dir, f"{Path(file_path).name}.backup")
        else:
            backup_path = f"{file_path}.backup"
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        logging.error(f"Failed to backup {file_path}: {e}")
        return None


def restore_backup(backup_path: str, original_path: str = None) -> bool:
    """Restore file from backup"""
    try:
        if not os.path.exists(backup_path):
            return False
        if original_path is None:
            original_path = backup_path.replace('.backup', '')
        shutil.copy2(backup_path, original_path)
        return True
    except Exception as e:
        logging.error(f"Failed to restore backup {backup_path}: {e}")
        return False


def clean_backups(directory: str, pattern: str = "*.backup") -> int:
    """Clean backup files in directory; returns number of files removed."""
    count = 0
    try:
        for backup in find_files(directory, pattern, recursive=False):
            try:
                os.remove(backup)
                count += 1
            except Exception as e:
                logging.error(f"Failed to remove backup {backup}: {e}")
        return count
    except Exception as e:
        logging.error(f"Failed to clean backups in {directory}: {e}")
        return 0


def get_directory_size(directory: str) -> int:
    """Get total size of directory in bytes"""
    total = 0
    try:
        for entry in os.scandir(directory):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_directory_size(entry.path)
    except Exception as e:
        logging.error(f"Failed to get directory size for {directory}: {e}")
    return total


def count_files_in_directory(directory: str, pattern: str = "*", recursive: bool = True) -> int:
    """Count files matching pattern in directory"""
    return len(find_files(directory, pattern, recursive))


def get_oldest_file(directory: str, pattern: str = "*") -> Optional[str]:
    """Get oldest file in directory"""
    files = find_files(directory, pattern, recursive=False)
    return min(files, key=lambda f: os.path.getmtime(f)) if files else None


def get_newest_file(directory: str, pattern: str = "*") -> Optional[str]:
    """Get newest file in directory"""
    files = find_files(directory, pattern, recursive=False)
    return max(files, key=lambda f: os.path.getmtime(f)) if files else None


# ===== Phase 2: Spinner 強化 =====

class Spinner:
    """Simple spinner animation.

    Phase 2:
    - If running inside Rich Live, just log once (no carriage moves on stdout)
    - Otherwise, show CLI spinner using colorama
    """

    def __init__(self, message: str = "Processing"):
        self.message = message
        self.is_spinning = False
        self.spinner_thread = None
        self.current_frame = 0
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def _is_in_rich_live(self) -> bool:
        try:
            from cognix.progress import is_live_context_active
            return is_live_context_active()
        except Exception:
            return False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

    def start(self):
        in_live = self._is_in_rich_live()
        if in_live:
            try:
                from cognix.logger import err_console
                err_console.print(f"⏳ {self.message}...", style="cyan")
            except Exception:
                sys.stdout.write("⏳ " + self.message + "...\n")
                sys.stdout.flush()
            self._was_in_live = True
            return

        self._was_in_live = False

        import threading
        import time

        # colorama 初期化（Windows 対応）
        colorama_initialized = False
        try:
            import colorama
            colorama.just_fix_windows_console()
            colorama_initialized = True
        except Exception:
            try:
                import colorama
                colorama.init()
                colorama_initialized = True
            except Exception:
                pass

        if not colorama_initialized:
            sys.stdout.write("⏳ " + self.message + "...\n")
            sys.stdout.flush()
            return

        self.is_spinning = True

        def spin():
            while self.is_spinning:
                frame = self.frames[self.current_frame % len(self.frames)]
                sys.stdout.write("\r" + frame + " " + self.message)
                sys.stdout.flush()
                self.current_frame += 1
                time.sleep(0.1)

        self.spinner_thread = threading.Thread(target=spin, daemon=True)
        self.spinner_thread.start()

    def stop(self):
        if getattr(self, "_was_in_live", False):
            try:
                from cognix.logger import err_console
                err_console.print(f"✓ {self.message}", style="green")
            except Exception:
                sys.stdout.write("✓ " + self.message + "\n")
                sys.stdout.flush()
            return

        self.is_spinning = False
        if self.spinner_thread:
            self.spinner_thread.join(timeout=0.5)

        clear = "\r" + " " * (len(self.message) + 3) + "\r"
        sys.stdout.write(clear)
        sys.stdout.write("✓ " + self.message + "\n")
        sys.stdout.flush()


class ProgressBar:
    """Simple progress bar"""

    def __init__(self, total: int, description: str = "Progress"):
        self.total = total
        self.current = 0
        self.description = description
        self.bar_length = 40

    def update(self, amount: int = 1):
        self.current = min(self.current + amount, self.total)
        self._display()

    def _display(self):
        percent = int((self.current / self.total) * 100) if self.total else 100
        filled = int((self.current / self.total) * self.bar_length) if self.total else 0
        bar = '█' * filled + '░' * (self.bar_length - filled)

        sys.stdout.write(f'\r{self.description}: |{bar}| {percent}% ({self.current}/{self.total})')
        sys.stdout.flush()

        if self.current >= self.total:
            sys.stdout.write('\n')
            sys.stdout.flush()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.current < self.total:
            self.current = self.total
            self._display()
