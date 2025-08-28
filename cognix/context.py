"""
File Context Manager for Cognix
Handles file indexing, content extraction, and project awareness
"""

import os
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import hashlib
import json
from dataclasses import dataclass, asdict


@dataclass
class FileInfo:
    """Information about a file"""
    path: str
    size: int
    modified: float
    content_hash: str
    file_type: str
    language: Optional[str] = None
    encoding: str = "utf-8"
    line_count: int = 0
    is_binary: bool = False


class FileContext:
    """Manages file context and project awareness"""
    
    # Common programming file extensions and their languages
    LANGUAGE_MAP = {
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
        '.vim': 'vim',
        '.dockerfile': 'dockerfile',
        '.gitignore': 'gitignore',
        '.env': 'env'
    }
    
    # Files and directories to exclude by default
    DEFAULT_EXCLUDES = {
        '.git', '.svn', '.hg', '.bzr',
        'node_modules', '__pycache__', '.pytest_cache',
        'venv', 'env', '.venv', '.env',
        'build', 'dist', 'target',
        '.idea', '.vscode', '.vs',
        '*.pyc', '*.pyo', '*.pyd',
        '*.class', '*.jar', '*.war',
        '*.o', '*.so', '*.dll', '*.dylib',
        '*.exe', '*.bin',
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp',
        '*.mp3', '*.mp4', '*.avi', '*.mov',
        '*.zip', '*.tar', '*.gz', '*.rar',
        '.DS_Store', 'Thumbs.db'
    }
    
    def __init__(self, root_dir: str = None, claude_md_path: str = None):
        """Initialize file context manager"""
        self.root_dir = Path(root_dir or os.getcwd()).resolve()
        self.claude_md_path = claude_md_path or "CLAUDE.md"
        self.files: Dict[str, FileInfo] = {}
        self.excludes: Set[str] = set(self.DEFAULT_EXCLUDES)
        self.claude_config: Dict[str, Any] = {}
        self.load_claude_config()
        self.scan_directory()       
    
    def load_claude_config(self):
        """Load configuration from CLAUDE.md file"""
        claude_file = self.root_dir / self.claude_md_path
        
        if not claude_file.exists():
            return
        
        try:
            content = claude_file.read_text(encoding='utf-8')
            
            # Simple parser for CLAUDE.md format
            config = {}
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    # Handle special cases
                    if key == 'excluded_dirs':
                        # Parse array format: [".git", "node_modules"]
                        if value.startswith('[') and value.endswith(']'):
                            dirs = [
                                d.strip().strip('"\'') 
                                for d in value[1:-1].split(',')
                                if d.strip()
                            ]
                            self.excludes.update(dirs)
                    else:
                        config[key] = value
            
            self.claude_config = config
            
        except Exception as e:
            print(f"Warning: Failed to parse CLAUDE.md: {e}")
    
    def get_file_language(self, file_path: Path) -> Optional[str]:
        """Determine programming language from file extension"""
        suffix = file_path.suffix.lower()
        
        # Check exact filename matches first (e.g., Dockerfile)
        filename = file_path.name.lower()
        if filename in self.LANGUAGE_MAP:
            return self.LANGUAGE_MAP[filename]
        
        # Check extension
        return self.LANGUAGE_MAP.get(suffix)
    
    def is_text_file(self, file_path: Path) -> bool:
        """Check if file is likely a text file"""
        try:
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type.startswith('text/'):
                return True
            
            # Check by reading a small sample
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
                
            # If we can decode as UTF-8, likely text
            try:
                sample.decode('utf-8')
                return True
            except UnicodeDecodeError:
                pass
            
            # Check for null bytes (binary indicator)
            if b'\x00' in sample:
                return False
            
            # Check percentage of printable characters
            printable_chars = sum(1 for b in sample if 32 <= b <= 126 or b in [9, 10, 13])
            if len(sample) > 0 and printable_chars / len(sample) > 0.7:
                return True
                
            return False
            
        except Exception:
            return False
    
    def should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded from indexing"""
        path_str = str(path)
        name = path.name
        
        # Check against exclude patterns
        for exclude in self.excludes:
            if exclude.startswith('*'):
                # Wildcard pattern
                pattern = exclude[1:]
                if path_str.endswith(pattern) or name.endswith(pattern):
                    return True
            elif exclude in path_str or name == exclude:
                return True
                
        return False
    
    def calculate_content_hash(self, file_path: Path) -> str:
        """Calculate hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
    
    def scan_directory(self, force_rescan: bool = False):
        """Scan directory for files and build index"""
        self.files.clear()
        
        try:
            file_count = 0
            processed_count = 0
            
            # スキャン制限を追加（大量ディレクトリ対策）
            MAX_SCAN_ITEMS = 5000  # 最大スキャン項目数
            MAX_PROCESSED_FILES = 500  # 最大処理ファイル数
            
            for file_path in self.root_dir.rglob('*'):
                file_count += 1
                
                # スキャン制限チェック
                if file_count >= MAX_SCAN_ITEMS:
                    break
                
                if processed_count >= MAX_PROCESSED_FILES:
                    break
                
                if not file_path.is_file():
                    continue
                    
                if self.should_exclude(file_path):
                    continue
                
                processed_count += 1
                                
                try:
                    stat = file_path.stat()
                    relative_path = str(file_path.relative_to(self.root_dir))
                    
                    is_text = self.is_text_file(file_path)
                    line_count = 0
                    
                    if is_text:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                line_count = sum(1 for _ in f)
                        except Exception:
                            is_text = False
                    
                    file_info = FileInfo(
                        path=relative_path,
                        size=stat.st_size,
                        modified=stat.st_mtime,
                        content_hash=self.calculate_content_hash(file_path),
                        file_type=file_path.suffix.lower(),
                        language=self.get_file_language(file_path),
                        line_count=line_count,
                        is_binary=not is_text
                    )
                    
                    self.files[relative_path] = file_info
                    
                except Exception as e:
                    print(f"Warning: Failed to process {file_path}: {e}")
            
        except Exception as e:
            print(f"Error during directory scan: {e}")
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get content of a specific file"""
        full_path = self.root_dir / file_path
        
        if not full_path.exists():
            return None
        
        file_info = self.files.get(file_path)
        if file_info and file_info.is_binary:
            return None
        
        try:
            return full_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Warning: Failed to read {file_path}: {e}")
            return None
    
    def get_files_by_language(self, language: str) -> List[FileInfo]:
        """Get all files of a specific programming language"""
        return [
            file_info for file_info in self.files.values()
            if file_info.language == language
        ]
    
    def get_files_by_pattern(self, pattern: str) -> List[FileInfo]:
        """Get files matching a pattern"""
        import fnmatch
        
        results = []
        for file_info in self.files.values():
            if fnmatch.fnmatch(file_info.path, pattern):
                results.append(file_info)
        
        return results
    
    def search_content(self, query: str, file_types: List[str] = None) -> List[Dict[str, Any]]:
        """Search for content across files"""
        results = []
        query_lower = query.lower()
        
        for file_path, file_info in self.files.items():
            if file_info.is_binary:
                continue
                
            if file_types and file_info.file_type not in file_types:
                continue
            
            content = self.get_file_content(file_path)
            if not content:
                continue
            
            # Search for matches
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                if query_lower in line.lower():
                    results.append({
                        'file': file_path,
                        'line': line_num,
                        'content': line.strip(),
                        'language': file_info.language
                    })
        
        return results
    
    def get_project_summary(self) -> Dict[str, Any]:
        """Get summary of the project"""
        total_files = len(self.files)
        total_size = sum(f.size for f in self.files.values())
        total_lines = sum(f.line_count for f in self.files.values() if not f.is_binary)
        
        # Count by language
        languages = {}
        file_types = {}
        
        for file_info in self.files.values():
            if file_info.language:
                languages[file_info.language] = languages.get(file_info.language, 0) + 1
            
            if file_info.file_type:
                file_types[file_info.file_type] = file_types.get(file_info.file_type, 0) + 1
        
        return {
            'root_directory': str(self.root_dir),
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_lines': total_lines,
            'languages': languages,
            'file_types': file_types,
            'claude_config': self.claude_config,
            'excluded_patterns': list(self.excludes)
        }
    
    def get_relevant_files(self, query: str, max_files: int = 10) -> List[str]:
        """Get files most relevant to a query"""
        # Simple relevance scoring based on filename and content matches
        scores = {}
        
        for file_path, file_info in self.files.items():
            score = 0
            
            # Filename relevance
            if query.lower() in file_path.lower():
                score += 10
            
            # Language relevance
            if file_info.language and query.lower() in file_info.language.lower():
                score += 5
            
            # Content relevance (for small files)
            if not file_info.is_binary and file_info.size < 50000:
                content = self.get_file_content(file_path)
                if content and query.lower() in content.lower():
                    score += 3
            
            if score > 0:
                scores[file_path] = score
        
        # Sort by score and return top files
        sorted_files = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [file_path for file_path, _ in sorted_files[:max_files]]
    
    def generate_context_for_prompt(self, user_prompt: str, max_context_size: int = 8000) -> str:
        """Generate relevant context for a user prompt"""
        context_parts = []
        current_size = 0
        
        # Add project summary
        summary = self.get_project_summary()
        summary_text = f"""Project Context:
- Root: {summary['root_directory']}
- Files: {summary['total_files']} ({summary['total_lines']} lines)
- Languages: {', '.join(summary['languages'].keys())}
"""
        context_parts.append(summary_text)
        current_size += len(summary_text)
        
        # Add Claude config if available
        if self.claude_config:
            config_text = f"\nCLAUDE.md Configuration:\n"
            for key, value in self.claude_config.items():
                config_text += f"- {key}: {value}\n"
            
            if current_size + len(config_text) < max_context_size:
                context_parts.append(config_text)
                current_size += len(config_text)
        
        # Add relevant files
        relevant_files = self.get_relevant_files(user_prompt)
        
        for file_path in relevant_files:
            if current_size >= max_context_size:
                break
                
            content = self.get_file_content(file_path)
            if not content:
                continue
            
            file_context = f"\n--- {file_path} ---\n{content}\n"
            
            if current_size + len(file_context) < max_context_size:
                context_parts.append(file_context)
                current_size += len(file_context)
            else:
                # Add truncated version
                remaining_space = max_context_size - current_size - 200
                if remaining_space > 100:
                    truncated = content[:remaining_space] + "...\n[truncated]"
                    file_context = f"\n--- {file_path} ---\n{truncated}\n"
                    context_parts.append(file_context)
                break
        
        return ''.join(context_parts)
    
    def refresh(self):
        """Refresh file index"""
        self.scan_directory(force_rescan=True)
    
    def export_index(self, export_path: str):
        """Export file index to JSON"""
        data = {
            'root_directory': str(self.root_dir),
            'scan_time': os.path.getctime(str(self.root_dir)),
            'files': {path: asdict(info) for path, info in self.files.items()},
            'claude_config': self.claude_config,
            'summary': self.get_project_summary()
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)