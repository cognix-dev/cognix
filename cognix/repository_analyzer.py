"""
Repository Analyzer for Cognix
Provides AST-based analysis of code repositories with fallback mechanisms
"""

from pathlib import Path
import hashlib
import re
import ast
import json
from typing import Dict, List, Optional, Any, Iterator, Set
from datetime import datetime

from cognix.repository_manager import RepositoryFile
from cognix.logger import err_console


class RepositoryAnalyzer:
    """Repository analysis engine with AST parsing and fallback mechanisms"""
    
    # Supported languages and their file extensions
    SUPPORTED_LANGUAGES = {
        'python': ['.py', '.pyi'],
        'typescript': ['.ts', '.tsx'],
        'javascript': ['.js', '.jsx', '.mjs', '.cjs'],
        'html': ['.html', '.htm'],
        'css': ['.css', '.scss', '.sass', '.less'],
        'json': ['.json'],
        'markdown': ['.md', '.mdx'],
        'yaml': ['.yml', '.yaml'],
        'toml': ['.toml'],
        'ini': ['.ini', '.cfg'],
    }
    
    # Directories to ignore during analysis
    IGNORE_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv', '.env',
        'dist', 'build', '.next', '.cache', 'coverage', '.pytest_cache',
        '.tox', '.mypy_cache', '.DS_Store', 'Thumbs.db', '.idea', '.vscode',
        '.gradle', 'target', 'bin', 'obj', '.nuget', '.cognix'
    }
    
    # Files to ignore
    IGNORE_FILES = {
        '.gitignore', '.dockerignore', '.editorconfig', '.flake8',
        'package-lock.json', 'yarn.lock', 'poetry.lock', 'Pipfile.lock'
    }
    
    def __init__(self, enhanced_memory, context=None, related_finder=None):
        """Initialize repository analyzer"""
        self.memory = enhanced_memory
        self.context = context
        self.related_finder = related_finder
        self.analysis_stats = {
            'total_files': 0,
            'analyzed_files': 0,
            'skipped_files': 0,
            'errors': 0,
            'ast_successes': 0,
            'regex_fallbacks': 0
        }
    
    def analyze_project_incrementally(self, max_files: int = 100) -> Iterator[Dict[str, Any]]:
        """Analyze project incrementally with progress reporting"""
        try:
            # Get project root
            project_root = getattr(self.context, 'root_dir', Path.cwd()) if self.context else Path.cwd()
            if isinstance(project_root, str):
                project_root = Path(project_root)
            
            # Collect target files
            target_files = self._collect_target_files(project_root, max_files)
            self.analysis_stats['total_files'] = len(target_files)
            
            if not target_files:
                yield {
                    'progress': 1.0,
                    'current_file': None,
                    'confidence': 0.0,
                    'status': 'No supported files found',
                    'stats': self.analysis_stats
                }
                return
            
            # Analyze files incrementally
            analyzed_count = 0
            
            for file_path in target_files:
                try:
                    repo_file = self._analyze_single_file(file_path, project_root)
                    if repo_file:
                        self.memory.add_repository_file(repo_file)
                        analyzed_count += 1
                        self.analysis_stats['analyzed_files'] = analyzed_count
                        
                        # Yield progress
                        yield {
                            'progress': analyzed_count / len(target_files),
                            'current_file': str(file_path.relative_to(project_root)),
                            'confidence': repo_file.confidence_score,
                            'status': f'Analyzed {analyzed_count}/{len(target_files)} files',
                            'stats': self.analysis_stats
                        }
                    else:
                        self.analysis_stats['skipped_files'] += 1
                        
                except Exception as e:
                    self.analysis_stats['errors'] += 1
                    err_console.print(f"Analysis error for {file_path}: {e}")
                    continue
            
            # Build dependency graph
            self._build_dependency_graph()
            
            # Final progress report
            yield {
                'progress': 1.0,
                'current_file': None,
                'confidence': self._calculate_overall_confidence(),
                'status': f'Complete: {analyzed_count} files analyzed',
                'stats': self.analysis_stats
            }
            
        except Exception as e:
            yield {
                'progress': 0.0,
                'current_file': None,
                'confidence': 0.0,
                'status': f'Error: {str(e)}',
                'stats': self.analysis_stats
            }
    
    def _collect_target_files(self, project_root: Path, max_files: int) -> List[Path]:
        """Collect files for analysis with filtering"""
        target_files = []
        
        def should_include_file(file_path: Path) -> bool:
            # Check file name
            if file_path.name in self.IGNORE_FILES:
                return False
            
            # Check file size (max 1MB)
            try:
                if file_path.stat().st_size > 1024 * 1024:
                    return False
            except OSError:
                return False
            
            # Check file extension
            suffix = file_path.suffix.lower()
            for lang, extensions in self.SUPPORTED_LANGUAGES.items():
                if suffix in extensions:
                    return True
            return False
        
        def should_skip_dir(dir_path: Path) -> bool:
            return dir_path.name in self.IGNORE_DIRS
        
        try:
            # Use iterative approach to avoid deep recursion
            dirs_to_process = [project_root]
            
            while dirs_to_process and len(target_files) < max_files:
                current_dir = dirs_to_process.pop(0)
                
                try:
                    for item in current_dir.iterdir():
                        if len(target_files) >= max_files:
                            break
                        
                        if item.is_file() and should_include_file(item):
                            target_files.append(item)
                        elif item.is_dir() and not should_skip_dir(item):
                            dirs_to_process.append(item)
                            
                except (PermissionError, OSError):
                    continue
        
        except Exception as e:
            err_console.print(f"Error collecting files: {e}")
        
        return target_files
    
    def _analyze_single_file(self, file_path: Path, project_root: Path) -> Optional[RepositoryFile]:
        """Analyze a single file with AST parsing and regex fallback"""
        try:
            if not file_path.exists():
                return None
            
            # Read file content
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except (UnicodeDecodeError, OSError):
                try:
                    content = file_path.read_text(encoding='latin-1')
                except Exception:
                    return None
            
            if not content.strip():
                return None
            
            # Detect language
            language = self._detect_language(file_path)
            if not language:
                return None
            
            # Extract information using AST or regex fallback
            dependencies = self._extract_dependencies(content, language, file_path)
            exports = self._extract_exports(content, language)
            functions = self._extract_functions(content, language)
            classes = self._extract_classes(content, language)
            confidence = self._calculate_confidence(content, dependencies, functions, classes)
            complexity = self._calculate_complexity(content, dependencies, functions, classes)
            
            # Convert path to relative if possible
            try:
                relative_path = str(file_path.relative_to(project_root))
            except ValueError:
                relative_path = str(file_path)
            
            return RepositoryFile(
                file_path=relative_path,
                language=language,
                content_hash=self._calculate_content_hash(content),
                file_size=len(content),
                line_count=content.count('\n') + 1,
                last_modified=datetime.now().isoformat(),
                last_analyzed=datetime.now().isoformat(),
                imports=dependencies,  # Use dependencies as imports
                exports=exports,
                functions=functions,
                classes=classes,
                dependencies=dependencies,
                confidence_score=confidence,
                complexity=complexity,
                analysis_version="1.0"
            )
            
        except Exception as e:
            err_console.print(f"Error analyzing file {file_path}: {e}")
            return None
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension"""
        suffix = file_path.suffix.lower()
        for language, extensions in self.SUPPORTED_LANGUAGES.items():
            if suffix in extensions:
                return language
        return None
    
    def _extract_dependencies(self, content: str, language: str, file_path: Path) -> List[str]:
        """Extract dependencies from file content"""
        dependencies = []
        
        try:
            if language == 'python':
                dependencies = self._extract_python_dependencies(content)
            elif language in ['javascript', 'typescript']:
                dependencies = self._extract_js_ts_dependencies(content)
            elif language == 'json':
                dependencies = self._extract_json_dependencies(content)
            elif language == 'html':
                dependencies = self._extract_html_dependencies(content)
            
            # Remove duplicates and sort
            return sorted(list(set(dependencies)))
            
        except Exception as e:
            err_console.print(f"Warning: Dependency extraction failed for {file_path}: {e}")
            return []
    
    def _extract_python_dependencies(self, content: str) -> List[str]:
        """Extract Python imports using AST with regex fallback"""
        dependencies = []
        
        # Try AST parsing first
        try:
            tree = ast.parse(content)
            self.analysis_stats['ast_successes'] += 1
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append(node.module.split('.')[0])
                        
        except SyntaxError:
            # Fallback to regex parsing
            self.analysis_stats['regex_fallbacks'] += 1
            dependencies = self._extract_python_dependencies_regex(content)
        
        return dependencies
    
    def _extract_python_dependencies_regex(self, content: str) -> List[str]:
        """Extract Python imports using regex"""
        dependencies = []
        
        # Regular import pattern
        import_pattern = re.compile(r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)', re.MULTILINE)
        for match in import_pattern.finditer(content):
            module_name = match.group(1).split('.')[0]
            dependencies.append(module_name)
        
        # From import pattern
        from_pattern = re.compile(r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import', re.MULTILINE)
        for match in from_pattern.finditer(content):
            module_name = match.group(1).split('.')[0]
            dependencies.append(module_name)
        
        return dependencies
    
    def _extract_js_ts_dependencies(self, content: str) -> List[str]:
        """Extract JavaScript/TypeScript dependencies"""
        dependencies = []
        
        # ES6 imports
        import_patterns = [
            re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
            re.compile(r"import\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
        ]
        
        # CommonJS requires
        require_pattern = re.compile(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE)
        
        # Dynamic imports
        dynamic_pattern = re.compile(r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE)
        
        all_patterns = import_patterns + [require_pattern, dynamic_pattern]
        
        for pattern in all_patterns:
            for match in pattern.finditer(content):
                dep = match.group(1)
                # Extract package name (before / or @scope/package)
                if dep.startswith('@'):
                    parts = dep.split('/')
                    if len(parts) >= 2:
                        dependencies.append(f"{parts[0]}/{parts[1]}")
                elif dep.startswith('.'):
                    continue  # Skip relative imports
                else:
                    dependencies.append(dep.split('/')[0])
        
        return dependencies
    
    def _extract_json_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from JSON files (package.json, etc.)"""
        dependencies = []
        
        try:
            data = json.loads(content)
            
            # package.json dependencies
            for dep_type in ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']:
                if dep_type in data and isinstance(data[dep_type], dict):
                    dependencies.extend(data[dep_type].keys())
        
        except json.JSONDecodeError:
            pass
        
        return dependencies
    
    def _extract_html_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from HTML files (CSS and JS)"""
        dependencies = []
        
        # Extract CSS dependencies from <link> tags
        # Pattern: <link href="styles.css" ...> or <link href="./styles.css" ...>
        css_pattern = r'<link[^>]+href=["' + "'" + r']([^"' + "'" + r']+\.css)["' + "'" + r']'
        css_matches = re.findall(css_pattern, content, re.IGNORECASE)
        dependencies.extend(css_matches)
        
        # Extract JS dependencies from <script> tags
        # Pattern: <script src="script.js" ...> or <script src="./script.js" ...>
        js_pattern = r'<script[^>]+src=["' + "'" + r']([^"' + "'" + r']+\.js)["' + "'" + r']'
        js_matches = re.findall(js_pattern, content, re.IGNORECASE)
        dependencies.extend(js_matches)
        
        # Remove ./ prefix if present
        dependencies = [dep.lstrip('./') for dep in dependencies]
        
        return dependencies
    
    def _extract_exports(self, content: str, language: str) -> List[str]:
        """Extract exported functions, classes, and variables"""
        exports = []
        
        try:
            if language == 'python':
                exports = self._extract_python_exports(content)
            elif language in ['javascript', 'typescript']:
                exports = self._extract_js_ts_exports(content)
                
        except Exception:
            pass  # Graceful failure for exports
        
        return exports
    
    def _extract_python_exports(self, content: str) -> List[str]:
        """Extract Python exports (public functions and classes)"""
        exports = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith('_'):  # Public functions
                        exports.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith('_'):  # Public classes
                        exports.append(node.name)
                        
        except SyntaxError:
            # Regex fallback for exports
            func_pattern = re.compile(r'^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', re.MULTILINE)
            class_pattern = re.compile(r'^class\s+([a-zA-Z_][a-zA-Z0-9_]*)', re.MULTILINE)
            
            for pattern in [func_pattern, class_pattern]:
                for match in pattern.finditer(content):
                    name = match.group(1)
                    if not name.startswith('_'):
                        exports.append(name)
        
        return exports
    
    def _extract_js_ts_exports(self, content: str) -> List[str]:
        """Extract JavaScript/TypeScript exports"""
        exports = []
        
        # Export patterns
        patterns = [
            re.compile(r'export\s+(?:function|class)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', re.MULTILINE),
            re.compile(r'export\s+(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', re.MULTILINE),
            re.compile(r'export\s*{\s*([^}]+)\s*}', re.MULTILINE),
        ]
        
        for pattern in patterns:
            for match in pattern.finditer(content):
                if '{' in match.group(0):
                    # Handle export { a, b, c } syntax
                    export_list = match.group(1)
                    names = [name.strip().split(' as ')[0] for name in export_list.split(',')]
                    exports.extend(name.strip() for name in names if name.strip())
                else:
                    exports.append(match.group(1))
        
        return exports
    
    def _extract_functions(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Extract function definitions"""
        functions = []
        
        try:
            if language == 'python':
                functions = self._extract_python_functions(content)
            elif language in ['javascript', 'typescript']:
                functions = self._extract_js_ts_functions(content)
                
        except Exception:
            pass  # Graceful failure
        
        return functions
    
    def _extract_python_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract Python functions using AST with regex fallback"""
        functions = []
        
        try:
            tree = ast.parse(content)
            self.analysis_stats['ast_successes'] += 1
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append({
                        'name': node.name,
                        'line': node.lineno,
                        'params': [arg.arg for arg in node.args.args],  # 'args' -> 'params'
                        'decorators': [self._format_decorator(d) for d in node.decorator_list],
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'docstring': ast.get_docstring(node) or ""
                    })
                    
        except SyntaxError:
            self.analysis_stats['regex_fallbacks'] += 1
            functions = self._extract_python_functions_regex(content)
        
        return functions
    
    def _extract_python_functions_regex(self, content: str) -> List[Dict[str, Any]]:
        """Extract Python functions using regex"""
        functions = []
        lines = content.split('\n')
        
        func_pattern = re.compile(r'^(\s*(?:@.*\n\s*)*)(async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)')
        
        for i, line in enumerate(lines):
            match = func_pattern.match(line)
            if match:
                decorators_str, is_async, name, args_str = match.groups()
                decorators = re.findall(r'@([a-zA-Z_][a-zA-Z0-9_]*)', decorators_str or '')
                params = [arg.strip().split(':')[0].strip() for arg in args_str.split(',') if arg.strip()]
                
                functions.append({
                    'name': name,
                    'line': i + 1,
                    'params': params,  # 'args' -> 'params'
                    'decorators': decorators,
                    'is_async': bool(is_async),
                    'docstring': ""
                })
        
        return functions
    
    def _extract_js_ts_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract JavaScript/TypeScript functions"""
        functions = []
        
        patterns = [
            re.compile(r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)', re.MULTILINE),
            re.compile(r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?function\s*\(([^)]*)\)', re.MULTILINE),
            re.compile(r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?\s*\(([^)]*)\)\s*=>', re.MULTILINE),
        ]
        
        lines = content.split('\n')
        
        for pattern in patterns:
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                name, args_str = match.groups()
                params = [arg.strip().split(':')[0].strip() for arg in args_str.split(',') if arg.strip()]
                
                functions.append({
                    'name': name,
                    'line': line_num,
                    'params': params,  # 'args' -> 'params'
                    'is_async': 'async' in match.group(0),
                    'docstring': ""
                })
        
        return functions
    
    def _extract_classes(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Extract class definitions"""
        classes = []
        
        try:
            if language == 'python':
                classes = self._extract_python_classes(content)
            elif language in ['javascript', 'typescript']:
                classes = self._extract_js_ts_classes(content)
                
        except Exception:
            pass  # Graceful failure
        
        return classes
    
    def _extract_python_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract Python classes using AST with regex fallback"""
        classes = []
        
        try:
            tree = ast.parse(content)
            self.analysis_stats['ast_successes'] += 1
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Extract methods with their parameters
                    methods = []
                    for n in node.body:
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            methods.append({
                                'name': n.name,
                                'params': [arg.arg for arg in n.args.args]
                            })
                    
                    classes.append({
                        'name': node.name,
                        'line': node.lineno,
                        'methods': methods,
                        'bases': [self._format_base(b) for b in node.bases],
                        'decorators': [self._format_decorator(d) for d in node.decorator_list],
                        'docstring': ast.get_docstring(node) or ""
                    })
                    
        except SyntaxError:
            self.analysis_stats['regex_fallbacks'] += 1
            classes = self._extract_python_classes_regex(content)
        
        return classes
    
    def _extract_python_classes_regex(self, content: str) -> List[Dict[str, Any]]:
        """Extract Python classes using regex"""
        classes = []
        
        class_pattern = re.compile(r'^class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(([^)]*)\))?:', re.MULTILINE)
        
        for match in class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            name = match.group(1)
            bases_str = match.group(2) or ""
            bases = [base.strip() for base in bases_str.split(',') if base.strip()]
            
            classes.append({
                'name': name,
                'line': line_num,
                'methods': [],  # Would need more complex parsing
                'bases': bases,
                'decorators': [],
                'docstring': ""
            })
        
        return classes
    
    def _extract_js_ts_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract JavaScript/TypeScript classes"""
        classes = []
        
        class_pattern = re.compile(r'class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*(?:extends\s+([a-zA-Z_$][a-zA-Z0-9_$]*))?\s*{', re.MULTILINE)
        
        for match in class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            name = match.group(1)
            extends = match.group(2)
            
            # Extract methods for this class
            methods = self._extract_js_class_methods(content, match.end())
            
            classes.append({
                'name': name,
                'line': line_num,
                'methods': methods,
                'extends': extends or "",
                'docstring': ""
            })
        
        return classes
    
    def _extract_js_class_methods(self, content: str, class_start: int) -> List[Dict[str, Any]]:
        """Extract methods from a JavaScript/TypeScript class body"""
        methods = []
        
        # Find the class body (between { and matching })
        brace_count = 1
        class_end = class_start
        
        for i in range(class_start, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    class_end = i
                    break
        
        if class_end == class_start:
            return methods
        
        class_body = content[class_start:class_end]
        
        # Method patterns
        method_patterns = [
            # Regular methods: methodName(params) { ... }
            re.compile(r'^\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)\s*{', re.MULTILINE),
            # Async methods: async methodName(params) { ... }
            re.compile(r'^\s*async\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)\s*{', re.MULTILINE),
            # Getters/Setters: get/set methodName() { ... }
            re.compile(r'^\s*(?:get|set)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)\s*{', re.MULTILINE),
        ]
        
        # JavaScript keywords to exclude (not methods)
        js_keywords = {'if', 'while', 'for', 'switch', 'catch', 'with'}
        
        for pattern in method_patterns:
            for method_match in pattern.finditer(class_body):
                method_name = method_match.group(1)
                
                # Skip JavaScript keywords
                if method_name in js_keywords:
                    continue
                
                params_str = method_match.group(2)
                
                # Parse parameters
                params = []
                if params_str.strip():
                    for param in params_str.split(','):
                        param = param.strip()
                        # Remove default values and types
                        param = param.split('=')[0].strip()
                        param = param.split(':')[0].strip()
                        if param:
                            params.append(param)
                
                methods.append({
                    'name': method_name,
                    'params': params
                })
        
        return methods
    
    def _format_decorator(self, decorator) -> str:
        """Format AST decorator node as string"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return f"{decorator.func.id}()"
        return str(decorator)
    
    def _format_base(self, base) -> str:
        """Format AST base class node as string"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{base.value.id}.{base.attr}" if hasattr(base.value, 'id') else str(base)
        return str(base)
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of file content"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
    
    def _calculate_confidence(self, content: str, dependencies: List[str], 
                            functions: List[Dict[str, Any]], classes: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for analysis results"""
        confidence = 0.0
        
        # Base score for successful parsing
        confidence += 0.3
        
        # Score for finding dependencies
        if dependencies:
            confidence += min(0.2, len(dependencies) * 0.02)
        
        # Score for finding functions
        if functions:
            confidence += min(0.2, len(functions) * 0.03)
        
        # Score for finding classes
        if classes:
            confidence += min(0.15, len(classes) * 0.05)
        
        # Score for content complexity (lines of code)
        lines = content.count('\n')
        if lines > 10:
            confidence += min(0.1, lines / 1000)
        
        # Bonus for docstrings and comments
        if 'docstring' in content.lower() or '"""' in content or "'''" in content:
            confidence += 0.05
        
        return min(1.0, confidence)

    def _calculate_complexity(self, content: str, dependencies: List[str], 
                            functions: List[Dict[str, Any]], classes: List[Dict[str, Any]]) -> int:
        """
        Calculate complexity score (0-10) based on code characteristics
        
        Args:
            content: File content
            dependencies: List of dependencies
            functions: List of functions
            classes: List of classes
            
        Returns:
            Complexity score (0-10)
        """
        complexity = 0
        
        # Factor 1: File size (lines of code)
        lines = content.count('\n')
        if lines < 50:
            complexity += 0  # Very simple
        elif lines < 200:
            complexity += 2  # Simple
        elif lines < 500:
            complexity += 4  # Medium
        elif lines < 1000:
            complexity += 6  # Complex
        else:
            complexity += 8  # Very complex
        
        # Factor 2: Number of classes
        class_count = len(classes)
        if class_count > 0:
            complexity += min(3, class_count)  # Max +3
        
        # Factor 3: Number of functions/methods
        function_count = len(functions)
        # Count methods in classes
        method_count = sum(len(cls.get('methods', [])) for cls in classes)
        total_functions = function_count + method_count
        
        if total_functions > 20:
            complexity += 3
        elif total_functions > 10:
            complexity += 2
        elif total_functions > 5:
            complexity += 1
        
        # Factor 4: Dependencies
        dep_count = len(dependencies)
        if dep_count > 10:
            complexity += 2
        elif dep_count > 5:
            complexity += 1
        
        # Cap at 10
        return min(10, complexity)
    
    def _calculate_overall_confidence(self) -> float:
        """Calculate overall analysis confidence"""
        if not self.memory.repository_data:
            return 0.0
        
        total_confidence = sum(rf.confidence_score for rf in self.memory.repository_data.values())
        return total_confidence / len(self.memory.repository_data)
    
    def _build_dependency_graph(self):
        """Build dependency graph from analyzed files"""
        try:
            for file_path, repo_file in self.memory.repository_data.items():
                if repo_file.dependencies:
                    # Filter to only include dependencies that are other files in the project
                    internal_dependencies = []
                    
                    for dep in repo_file.dependencies:
                        # Look for matching files in the repository
                        for other_path in self.memory.repository_data.keys():
                            if self._is_internal_dependency(dep, other_path, repo_file.language):
                                internal_dependencies.append(other_path)
                    
                    if internal_dependencies:
                        self.memory.update_dependency_graph(file_path, internal_dependencies)
                        
        except Exception as e:
            err_console.print(f"Warning: Failed to build dependency graph: {e}")
    
    def _is_internal_dependency(self, dependency: str, file_path: str, language: str) -> bool:
        """Check if a dependency refers to an internal file"""
        if language == 'python':
            # Convert file path to module name
            module_path = file_path.replace('/', '.').replace('\\', '.')
            if module_path.endswith('.py'):
                module_path = module_path[:-3]
            
            return dependency in module_path or module_path.endswith(dependency)
        
        elif language in ['javascript', 'typescript']:
            # Check for relative imports or matching names
            file_name = Path(file_path).stem
            return dependency == file_name or dependency.endswith(file_name)
        
        return False
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis summary"""
        return {
            'stats': self.analysis_stats,
            'repository_summary': self.memory.get_repository_summary() if self.memory else {},
            'analysis_efficiency': {
                'ast_success_rate': (
                    self.analysis_stats['ast_successes'] / 
                    max(1, self.analysis_stats['ast_successes'] + self.analysis_stats['regex_fallbacks'])
                ),
                'overall_success_rate': (
                    self.analysis_stats['analyzed_files'] / 
                    max(1, self.analysis_stats['total_files'])
                ),
                'error_rate': (
                    self.analysis_stats['errors'] / 
                    max(1, self.analysis_stats['total_files'])
                )
            }
        }