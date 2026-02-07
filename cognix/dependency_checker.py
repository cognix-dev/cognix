"""
Dependency Checker Module
依存関係チェック機能を提供

配置先: cognix/dependency_checker.py
"""

import ast
import re
import importlib.util
from typing import Dict, List, Set


class DependencyChecker:
    """コードの依存関係をチェックするクラス"""
    
    # Python標準ライブラリのリスト
    STDLIB_MODULES = {
        'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 
        'asyncore', 'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex',
        'bisect', 'builtins', 'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 
        'cmath', 'cmd', 'code', 'codecs', 'codeop', 'collections', 'colorsys',
        'compileall', 'concurrent', 'configparser', 'contextlib', 'contextvars',
        'copy', 'copyreg', 'cProfile', 'crypt', 'csv', 'ctypes', 'curses',
        'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis', 'distutils',
        'doctest', 'email', 'encodings', 'enum', 'errno', 'faulthandler', 'fcntl',
        'filecmp', 'fileinput', 'fnmatch', 'formatter', 'fractions', 'ftplib',
        'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob', 'graphlib',
        'grp', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib',
        'imghdr', 'imp', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools',
        'json', 'keyword', 'lib2to3', 'linecache', 'locale', 'logging', 'lzma',
        'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder',
        'msilib', 'msvcrt', 'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers',
        'operator', 'optparse', 'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb',
        'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib',
        'posix', 'posixpath', 'pprint', 'profile', 'pstats', 'pty', 'pwd', 'py_compile',
        'pyclbr', 'pydoc', 'queue', 'quopri', 'random', 're', 'readline', 'reprlib',
        'resource', 'rlcompleter', 'runpy', 'sched', 'secrets', 'select', 'selectors',
        'shelve', 'shlex', 'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr',
        'socket', 'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat', 'statistics',
        'string', 'stringprep', 'struct', 'subprocess', 'sunau', 'symbol', 'symtable',
        'sys', 'sysconfig', 'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile',
        'termios', 'test', 'textwrap', 'threading', 'time', 'timeit', 'tkinter',
        'token', 'tokenize', 'trace', 'traceback', 'tracemalloc', 'tty', 'turtle',
        'turtledemo', 'types', 'typing', 'unicodedata', 'unittest', 'urllib', 'uu',
        'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser', 'winreg',
        'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile',
        'zipimport', 'zlib', '_thread'
    }
    
    def __init__(self):
        self.cache: Dict[str, bool] = {}
    
    def check_code_dependencies(self, code: str, language: str = 'python') -> Dict:
        """
        コードの依存関係をチェック
        
        Args:
            code: ソースコード
            language: 言語 (現在はpythonのみサポート)
            
        Returns:
            依存関係情報の辞書
        """
        if language.lower() != 'python':
            return self._empty_result()
        
        # 依存関係を抽出
        all_deps = self._extract_python_dependencies(code)
        
        if not all_deps:
            return self._empty_result()
        
        # 分類
        stdlib = []
        third_party = []
        missing = []
        
        for dep in all_deps:
            if self._is_stdlib(dep):
                stdlib.append(dep)
            else:
                third_party.append(dep)
                if not self._is_installed(dep):
                    missing.append(dep)
        
        # インストールコマンド生成
        install_cmd = ""
        if missing:
            install_cmd = f"pip install {' '.join(missing)}"
        
        return {
            'all_dependencies': sorted(all_deps),
            'missing_dependencies': sorted(missing),
            'stdlib_modules': sorted(stdlib),
            'third_party': sorted(third_party),
            'install_command': install_cmd,
            'has_missing': len(missing) > 0
        }
    
    def _extract_python_dependencies(self, code: str) -> Set[str]:
        """Pythonコードからimportを抽出"""
        dependencies = set()
        
        # AST解析を試行
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dep = alias.name.split('.')[0]
                        dependencies.add(dep)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dep = node.module.split('.')[0]
                        dependencies.add(dep)
        except SyntaxError:
            # 構文エラー時はregexフォールバック
            dependencies = self._extract_python_dependencies_regex(code)
        
        return dependencies
    
    def _extract_python_dependencies_regex(self, code: str) -> Set[str]:
        """正規表現でimportを抽出（フォールバック）"""
        dependencies = set()
        
        # import xxx
        pattern1 = re.compile(r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_]*)', re.MULTILINE)
        for match in pattern1.finditer(code):
            dependencies.add(match.group(1))
        
        # from xxx import
        pattern2 = re.compile(r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import', re.MULTILINE)
        for match in pattern2.finditer(code):
            dependencies.add(match.group(1))
        
        return dependencies
    
    def _is_stdlib(self, module_name: str) -> bool:
        """標準ライブラリか判定"""
        return module_name in self.STDLIB_MODULES
    
    def _is_installed(self, module_name: str) -> bool:
        """モジュールがインストール済みか確認"""
        # キャッシュチェック
        if module_name in self.cache:
            return self.cache[module_name]
        
        # インストール確認
        spec = importlib.util.find_spec(module_name)
        installed = spec is not None
        
        # キャッシュに保存
        self.cache[module_name] = installed
        
        return installed
    
    def _empty_result(self) -> Dict:
        """空の結果を返す"""
        return {
            'all_dependencies': [],
            'missing_dependencies': [],
            'stdlib_modules': [],
            'third_party': [],
            'install_command': '',
            'has_missing': False
        }