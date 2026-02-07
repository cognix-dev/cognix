from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
import json
import hashlib
import ast
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field

@dataclass
class RepositoryFile:
    """Data class for managing repository file information"""
    file_path: str = ""
    language: str = ""
    content_hash: str = ""
    file_size: int = 0
    line_count: int = 0
    last_modified: str = ""
    last_analyzed: str = ""

    # Analysis results
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    classes: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    # Metadata
    confidence_score: float = 0.0
    complexity: int = 0  # Complexity score (0-10)
    analysis_version: str = ""

    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepositoryFile':
        """Create instance from dictionary"""
        return cls(**data)
class RepositoryManager:
    """Provides persistent understanding and management of projects"""

    def __init__(self, memory_manager, project_root: Optional[Path] = None):
        self.memory = memory_manager
        self.project_root = project_root or Path.cwd()
        self.repository_data: Dict[str, RepositoryFile] = {}
        self.index_data: Dict[str, Any] = {}
        self.stats: Dict[str, Any] = {}
        self.analysis_version = "1.0"
        
        # Supported file extensions
        self.supported_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php'
        }

    def initialize_repository(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Initialize repository understanding system

        Args:
            force_rebuild: Discard existing data and rebuild

        Returns:
            {
                "status": "success|error",
                "files_analyzed": int,
                "languages_detected": Dict[str, int],
                "analysis_time": float,
                "cache_status": "loaded|created|rebuilt"
            }
        """
        start_time = datetime.now()
        
        try:
            # Load existing data
            cache_status = "created"
            if not force_rebuild:
                loaded_data = self._load_repository_data()
                if loaded_data:
                    cache_status = "loaded"
                else:
                    cache_status = "created"
            else:
                cache_status = "rebuilt"

            # Scan project files
            files_to_analyze = self._scan_project_files()

            # Perform incremental analysis
            analysis_result = self._perform_incremental_analysis(files_to_analyze, force_rebuild)

            # Update statistics
            self._update_statistics()

            # Persist data
            self._save_repository_data()

            languages_detected = {}
            for repo_file in self.repository_data.values():
                lang = repo_file.language
                languages_detected[lang] = languages_detected.get(lang, 0) + 1

            return {
                "status": "success",
                "files_analyzed": len(files_to_analyze),
                "languages_detected": languages_detected,
                "analysis_time": (datetime.now() - start_time).total_seconds(),
                "cache_status": cache_status
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error_message": str(e),
                "files_analyzed": 0,
                "languages_detected": {},
                "analysis_time": (datetime.now() - start_time).total_seconds(),
                "cache_status": "error"
            }

    def analyze_project(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Analyze entire project

        Args:
            incremental: Whether to use incremental analysis

        Returns:
            {
                "total_files": int,
                "analyzed_files": int,
                "skipped_files": int,
                "languages": Dict[str, int],
                "project_structure": Dict[str, Any],
                "key_files": List[str],
                "potential_issues": List[str]
            }
        """
        analysis_results = {
            "total_files": 0,
            "analyzed_files": 0,
            "skipped_files": 0,
            "languages": {},
            "project_structure": {},
            "key_files": [],
            "potential_issues": []
        }

        try:
            # Utilize existing context.py to get file information
            try:
                from cognix.context import FileContext
                context = FileContext(self.project_root)
                files_info = context.files
            except ImportError:
                # If context.py is not available, scan files directly
                files_info = self._scan_project_files_dict()

            analysis_results["total_files"] = len(files_info)

            # Detailed analysis for each file
            for file_path, file_info in files_info.items():
                try:
                    # Convert FileInfo object to dictionary format
                    if hasattr(file_info, 'full_path'):
                        # FileInfo object case
                        file_info_dict = {
                            "full_path": str(file_info.full_path),
                            "size": getattr(file_info, 'size', 0),
                            "mtime": getattr(file_info, 'last_modified', 0)
                        }
                    else:
                        # Already dictionary format case
                        file_info_dict = file_info

                    # Check skip condition for incremental analysis
                    if incremental and self._should_skip_analysis(file_path, file_info_dict):
                        analysis_results["skipped_files"] += 1
                        continue

                    repo_file = self._analyze_single_file(file_path, file_info_dict)
                    if repo_file:
                        self.repository_data[file_path] = repo_file
                        analysis_results["analyzed_files"] += 1

                        # Update language statistics
                        lang = repo_file.language
                        analysis_results["languages"][lang] = analysis_results["languages"].get(lang, 0) + 1

                except Exception as e:
                    analysis_results["skipped_files"] += 1
                    analysis_results["potential_issues"].append(f"{file_path}: {str(e)}")

            # Identify key files
            analysis_results["key_files"] = self._identify_key_files()

            # Analyze project structure
            analysis_results["project_structure"] = self._analyze_project_structure()

        except Exception as e:
            analysis_results["potential_issues"].append(f"Project analysis error: {str(e)}")

        return analysis_results

    def get_file_info(self, file_path: str) -> Optional[RepositoryFile]:
        """Get file information"""
        return self.repository_data.get(file_path)

    def search_files(self, query: str, search_type: str = "name") -> List[RepositoryFile]:
        """
        Search files

        Args:
            query: Search query
            search_type: Search type (name/content/function/class)

        Returns:
            List of matched RepositoryFile objects
        """
        results = []
        query_lower = query.lower()

        for file_path, repo_file in self.repository_data.items():
            try:
                if search_type == "name":
                    if query_lower in file_path.lower():
                        results.append(repo_file)

                elif search_type == "content":
                    # Search in import statements
                    if any(query_lower in imp.lower() for imp in repo_file.imports):
                        results.append(repo_file)

                elif search_type == "function":
                    if any(query_lower in func["name"].lower() for func in repo_file.functions):
                        results.append(repo_file)

                elif search_type == "class":
                    if any(query_lower in cls["name"].lower() for cls in repo_file.classes):
                        results.append(repo_file)

            except Exception:
                # Ignore errors during search and continue to next file
                continue

        # Sort by relevance
        results.sort(key=lambda x: self._calculate_relevance_score(x, query, search_type), reverse=True)

        return results

    def get_project_summary(self) -> Dict[str, Any]:
        """Get project summary"""
        total_files = len(self.repository_data)
        total_size = sum(f.file_size for f in self.repository_data.values())
        total_lines = sum(f.line_count for f in self.repository_data.values())
        
        languages = {}
        for repo_file in self.repository_data.values():
            lang = repo_file.language
            languages[lang] = languages.get(lang, 0) + 1

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_lines": total_lines,
            "languages": languages,
            "key_files": self._identify_key_files()[:10],
            "last_updated": datetime.now().isoformat()
        }

    def find_similar_files(self, file_path: str, similarity_threshold: float = 0.7) -> List[Tuple[str, float]]:
        """Find similar files"""
        target_file = self.repository_data.get(file_path)
        if not target_file:
            return []

        similar_files = []
        
        for path, repo_file in self.repository_data.items():
            if path == file_path:
                continue
                
            similarity = self._calculate_file_similarity(target_file, repo_file)
            if similarity >= similarity_threshold:
                similar_files.append((path, similarity))

        similar_files.sort(key=lambda x: x[1], reverse=True)
        return similar_files

    def get_file_relationships(self, file_path: str) -> Dict[str, List[str]]:
        """Get file relationships"""
        target_file = self.repository_data.get(file_path)
        if not target_file:
            return {"imports": [], "imported_by": [], "similar": []}

        relationships = {
            "imports": [],
            "imported_by": [],
            "similar": []
        }

        # Analyze import relationships
        for dep in target_file.dependencies:
            for path, repo_file in self.repository_data.items():
                if dep in path or any(dep in export for export in repo_file.exports):
                    relationships["imports"].append(path)

        # Analyze reverse import relationships
        for path, repo_file in self.repository_data.items():
            if file_path in repo_file.dependencies:
                relationships["imported_by"].append(path)

        # Similar files
        similar_files = self.find_similar_files(file_path, 0.6)
        relationships["similar"] = [path for path, score in similar_files[:5]]

        return relationships

    # Internal methods (private)

    def _load_repository_data(self) -> bool:
        """Load repository data"""
        try:
            data = self.memory.load_repository_data()
            if data:
                # Convert to RepositoryFile objects
                for file_path, file_data in data.get("files", {}).items():
                    self.repository_data[file_path] = RepositoryFile(**file_data)
                
                self.index_data = data.get("index_data", {})
                self.stats = data.get("stats", {})
                return True
        except Exception as e:
            print(f"⚠️ Failed to load repository data: {e}")
        return False

    def _save_repository_data(self) -> bool:
        """Save repository data"""
        try:
            # Convert RepositoryFile objects to dictionaries
            files_dict = {}
            for file_path, repo_file in self.repository_data.items():
                files_dict[file_path] = asdict(repo_file)

            data = {
                "files": files_dict,
                "index_data": self.index_data,
                "stats": self.stats,
                "analysis_version": self.analysis_version,
                "last_updated": datetime.now().isoformat()
            }

            return self.memory.save_repository_data(data)
        except Exception as e:
            print(f"⚠️ Failed to save repository data: {e}")
            return False

    def _scan_project_files(self) -> List[str]:
        """Scan project files and return list of files to analyze"""
        files = []
        ignore_dirs = {'.git', '__pycache__', 'node_modules', '.pytest_cache', 'venv', 'env', '.venv'}
        
        for root, dirs, filenames in os.walk(self.project_root):
            # Exclude directories to ignore
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                ext = Path(filename).suffix.lower()
                
                if ext in self.supported_extensions:
                    rel_path = os.path.relpath(file_path, self.project_root)
                    files.append(rel_path)
        
        return files

    def _scan_project_files_dict(self) -> Dict[str, Dict]:
        """Scan project files and return dictionary format"""
        files_dict = {}
        for file_path in self._scan_project_files():
            full_path = self.project_root / file_path
            if full_path.exists():
                stat = full_path.stat()
                files_dict[file_path] = {
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "full_path": str(full_path)
                }
        return files_dict

    def _perform_incremental_analysis(self, files_to_analyze: List[str], force_rebuild: bool = False) -> Dict[str, Any]:
        """Perform incremental analysis"""
        analyzed_count = 0
        skipped_count = 0

        for file_path in files_to_analyze:
            try:
                full_path = self.project_root / file_path
                if not full_path.exists():
                    continue

                # Determine skip condition for incremental analysis
                stat = full_path.stat()
                file_info_dict = {
                    "full_path": str(full_path),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime
                }
                
                if not force_rebuild and self._should_skip_analysis(file_path, file_info_dict):
                    skipped_count += 1
                    continue

                # Analyze file
                repo_file = self._analyze_single_file(file_path, file_info_dict)
                if repo_file:
                    self.repository_data[file_path] = repo_file
                    analyzed_count += 1

            except Exception as e:
                print(f"⚠️ File analysis error ({file_path}): {e}")
                skipped_count += 1

        return {
            "analyzed": analyzed_count,
            "skipped": skipped_count
        }

    def _should_skip_analysis(self, file_path: str, file_info) -> bool:
        """Determine if file should be skipped in incremental analysis"""
        existing_file = self.repository_data.get(file_path)
        if not existing_file:
            return False

        # Check file's last modification time
        try:
            # Handle FileInfo object properly
            if hasattr(file_info, 'full_path'):
                # FileInfo object case
                full_path = Path(file_info.full_path)
                current_mtime = getattr(file_info, 'last_modified', None)
                if current_mtime is None:
                    # If last_modified is not available, get it from the file system
                    current_mtime = full_path.stat().st_mtime if full_path.exists() else 0
            elif isinstance(file_info, dict):
                # Dictionary case
                full_path = Path(file_info.get("full_path", self.project_root / file_path))
                current_mtime = file_info.get("mtime", 0)
            else:
                # Unknown format, skip this check
                return False
            
            if full_path.exists() and current_mtime:
                file_mtime = datetime.fromtimestamp(current_mtime)
                last_analyzed = datetime.fromisoformat(existing_file.last_analyzed)
                
                # Skip if file hasn't been updated since last analysis
                return file_mtime <= last_analyzed
        except Exception as e:
            print(f"⚠️ Skip analysis check error for {file_path}: {e}")
            
        return False

    def _analyze_single_file(self, file_path: str, file_info) -> Optional[RepositoryFile]:
        """Analyze single file and generate RepositoryFile object"""
        try:
            # Handle FileInfo object properly
            if hasattr(file_info, 'full_path'):
                # FileInfo object case
                full_path = Path(file_info.full_path)
                file_size = getattr(file_info, 'size', 0)
            elif isinstance(file_info, dict):
                # Dictionary case
                full_path = Path(file_info.get("full_path", self.project_root / file_path))
                file_size = file_info.get("size", 0)
            else:
                # Fallback to constructing path from project root
                full_path = self.project_root / file_path
                file_size = 0
            
            if not full_path.exists():
                return None

            # Get file system stats if size not provided
            if file_size == 0:
                stat = full_path.stat()
                file_size = stat.st_size
            else:
                stat = full_path.stat()

            ext = full_path.suffix.lower()
            language = self.supported_extensions.get(ext, "unknown")
            
            # Skip non-supported file types
            if language == "unknown":
                return None
            
            # Read file content
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Skip binary files
                return None
            except Exception as e:
                print(f"⚠️ Failed to read file {file_path}: {e}")
                return None

            # Content hash and line count
            content_hash = hashlib.md5(content.encode()).hexdigest()
            line_count = content.count('\n') + 1

            # Language-specific detailed analysis
            imports, exports, functions, classes, dependencies = self._analyze_file_content(content, language)

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(content, language, functions, classes)

            return RepositoryFile(
                file_path=file_path,
                language=language,
                content_hash=content_hash,
                file_size=file_size,
                line_count=line_count,
                last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                last_analyzed=datetime.now().isoformat(),
                imports=imports,
                exports=exports,
                functions=functions,
                classes=classes,
                dependencies=dependencies,
                confidence_score=confidence_score,
                complexity=0,  # Default complexity (will be calculated later)
                analysis_version=self.analysis_version
            )

        except Exception as e:
            print(f"⚠️ File analysis error ({file_path}): {e}")
            return None

    def _analyze_file_content(self, content: str, language: str) -> Tuple[List[str], List[str], List[Dict], List[Dict], List[str]]:
        """Analyze file content to extract imports, functions, classes, etc."""
        imports = []
        exports = []
        functions = []
        classes = []
        dependencies = []

        if language == "python":
            imports, exports, functions, classes, dependencies = self._analyze_python_content(content)
        elif language in ["javascript", "typescript"]:
            imports, exports, functions, classes, dependencies = self._analyze_js_content(content)
        else:
            # Simple analysis for other languages
            imports, exports, functions, classes, dependencies = self._analyze_generic_content(content, language)

        return imports, exports, functions, classes, dependencies

    def _analyze_python_content(self, content: str) -> Tuple[List[str], List[str], List[Dict], List[Dict], List[str]]:
        """Analyze Python file content"""
        imports = []
        exports = []
        functions = []
        classes = []
        dependencies = []

        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                        dependencies.append(alias.name)
                        
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    imports.append(module)
                    dependencies.append(module)
                    
                elif isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node) or ""
                    }
                    functions.append(func_info)
                    
                    # Public functions are treated as exports
                    if not node.name.startswith('_'):
                        exports.append(node.name)
                        
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "bases": [self._get_node_name(base) for base in node.bases],
                        "methods": [],
                        "docstring": ast.get_docstring(node) or ""
                    }
                    
                    # Collect methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info["methods"].append(item.name)
                    
                    classes.append(class_info)
                    
                    # Public classes are treated as exports
                    if not node.name.startswith('_'):
                        exports.append(node.name)

        except SyntaxError:
            # Simple analysis using regex for syntax errors
            imports, exports, functions, classes, dependencies = self._analyze_python_regex(content)

        return imports, exports, functions, classes, dependencies

    def _analyze_js_content(self, content: str) -> Tuple[List[str], List[str], List[Dict], List[Dict], List[str]]:
        """Analyze JavaScript/TypeScript file content (regex-based)"""
        import re
        
        imports = []
        exports = []
        functions = []
        classes = []
        dependencies = []

        # Analyze import statements
        import_patterns = [
            r'import\s+.*\s+from\s+["\']([^"\']+)["\']',
            r'import\s+["\']([^"\']+)["\']',
            r'require\s*\(\s*["\']([^"\']+)["\']\s*\)'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                imports.append(match)
                dependencies.append(match)

        # Analyze functions
        function_patterns = [
            r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(',
            r'const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*\([^)]*\)\s*=>',
            r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:\s*function\s*\(',
            r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{'
        ]
        
        for pattern in function_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                functions.append({
                    "name": match,
                    "line": 0,  # Accurate line number is difficult to get
                    "args": [],
                    "docstring": ""
                })

        # Analyze classes
        class_matches = re.findall(r'class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', content, re.MULTILINE)
        for match in class_matches:
            classes.append({
                "name": match,
                "line": 0,
                "bases": [],
                "methods": [],
                "docstring": ""
            })

        # Analyze exports
        export_patterns = [
            r'export\s+(?:default\s+)?(?:function|class|const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)',
            r'export\s*\{\s*([^}]+)\s*\}',
            r'module\.exports\s*=\s*([a-zA-Z_$][a-zA-Z0-9_$]*)'
        ]
        
        for pattern in export_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                if isinstance(match, str) and ',' in match:
                    # Multiple exports case
                    for export in match.split(','):
                        exports.append(export.strip())
                else:
                    exports.append(match)

        return imports, exports, functions, classes, dependencies

    def _analyze_python_regex(self, content: str) -> Tuple[List[str], List[str], List[Dict], List[Dict], List[str]]:
        """Simple analysis of Python files using regex"""
        import re
        
        imports = []
        exports = []
        functions = []
        classes = []
        dependencies = []

        # Analyze import statements
        import_matches = re.findall(r'^import\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.MULTILINE)
        from_matches = re.findall(r'^from\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.MULTILINE)
        
        imports.extend(import_matches)
        imports.extend(from_matches)
        dependencies.extend(import_matches)
        dependencies.extend(from_matches)

        # Analyze functions
        func_matches = re.findall(r'^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content, re.MULTILINE)
        for func_name in func_matches:
            functions.append({
                "name": func_name,
                "line": 0,
                "args": [],
                "docstring": ""
            })
            if not func_name.startswith('_'):
                exports.append(func_name)

        # Analyze classes
        class_matches = re.findall(r'^class\s+([a-zA-Z_][a-zA-Z0-9_]*)', content, re.MULTILINE)
        for class_name in class_matches:
            classes.append({
                "name": class_name,
                "line": 0,
                "bases": [],
                "methods": [],
                "docstring": ""
            })
            if not class_name.startswith('_'):
                exports.append(class_name)

        return imports, exports, functions, classes, dependencies

    def _analyze_generic_content(self, content: str, language: str) -> Tuple[List[str], List[str], List[Dict], List[Dict], List[str]]:
        """Generic file content analysis (regex-based)"""
        import re
        
        imports = []
        exports = []
        functions = []
        classes = []
        dependencies = []

        # Language-specific basic patterns
        if language in ['c', 'cpp']:
            # Analyze #include statements
            include_matches = re.findall(r'#include\s*[<"]([^>"]+)[>"]', content)
            imports.extend(include_matches)
            dependencies.extend(include_matches)
            
            # Analyze function declarations (simple)
            func_matches = re.findall(r'^\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{?', content, re.MULTILINE)
            for func_name in func_matches:
                if func_name not in ['if', 'for', 'while', 'switch']:  # Exclude control statements
                    functions.append({
                        "name": func_name,
                        "line": 0,
                        "args": [],
                        "docstring": ""
                    })

        elif language == 'java':
            # Analyze import statements
            import_matches = re.findall(r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content)
            imports.extend(import_matches)
            dependencies.extend(import_matches)
            
            # Analyze classes
            class_matches = re.findall(r'(?:public\s+)?class\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
            for class_name in class_matches:
                classes.append({
                    "name": class_name,
                    "line": 0,
                    "bases": [],
                    "methods": [],
                    "docstring": ""
                })

        return imports, exports, functions, classes, dependencies

    def _get_node_name(self, node) -> str:
        """Get name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_node_name(node.value)}.{node.attr}"
        else:
            return str(node)

    def _calculate_confidence_score(self, content: str, language: str, functions: List[Dict], classes: List[Dict]) -> float:
        """Calculate confidence score for file analysis"""
        score = 0.5  # Base score
        
        # Adjust score based on analyzed elements
        if functions:
            score += min(0.3, len(functions) * 0.05)
        
        if classes:
            score += min(0.2, len(classes) * 0.1)
        
        # Adjust based on file size
        lines = content.count('\n') + 1
        if 10 <= lines <= 500:
            score += 0.1
        elif lines > 500:
            score -= 0.1
            
        # Adjust based on language support level
        if language == "python":
            score += 0.1
        elif language in ["javascript", "typescript"]:
            score += 0.05
            
        return min(1.0, max(0.0, score))

    def _calculate_relevance_score(self, repo_file: RepositoryFile, query: str, search_type: str) -> float:
        """Calculate relevance score for search results"""
        score = 0.0
        query_lower = query.lower()
        
        if search_type == "name":
            file_name = Path(repo_file.file_path).name.lower()
            if query_lower == file_name:
                score += 1.0
            elif query_lower in file_name:
                score += 0.7
            elif query_lower in repo_file.file_path.lower():
                score += 0.5
                
        elif search_type == "function":
            for func in repo_file.functions:
                if query_lower == func["name"].lower():
                    score += 1.0
                elif query_lower in func["name"].lower():
                    score += 0.8
                    
        elif search_type == "class":
            for cls in repo_file.classes:
                if query_lower == cls["name"].lower():
                    score += 1.0
                elif query_lower in cls["name"].lower():
                    score += 0.8
                    
        # Also consider confidence score
        score *= repo_file.confidence_score
        
        return score

    def _calculate_file_similarity(self, file1: RepositoryFile, file2: RepositoryFile) -> float:
        """Calculate similarity between two files"""
        if file1.language != file2.language:
            return 0.0
            
        similarity = 0.0
        
        # Import similarity
        common_imports = set(file1.imports) & set(file2.imports)
        total_imports = set(file1.imports) | set(file2.imports)
        if total_imports:
            similarity += 0.3 * (len(common_imports) / len(total_imports))
        
        # Function name similarity
        func_names1 = set(f["name"] for f in file1.functions)
        func_names2 = set(f["name"] for f in file2.functions)
        common_funcs = func_names1 & func_names2
        total_funcs = func_names1 | func_names2
        if total_funcs:
            similarity += 0.4 * (len(common_funcs) / len(total_funcs))
        
        # Class name similarity
        class_names1 = set(c["name"] for c in file1.classes)
        class_names2 = set(c["name"] for c in file2.classes)
        common_classes = class_names1 & class_names2
        total_classes = class_names1 | class_names2
        if total_classes:
            similarity += 0.3 * (len(common_classes) / len(total_classes))
        
        return min(1.0, similarity)

    def _identify_key_files(self) -> List[str]:
        """Identify key files in the project"""
        key_files = []
        
        # Judgment based on file names
        key_patterns = [
            'main.py', 'app.py', 'index.py', '__init__.py',
            'main.js', 'index.js', 'app.js',
            'main.java', 'App.java',
            'main.cpp', 'main.c'
        ]
        
        for file_path, repo_file in self.repository_data.items():
            file_name = Path(file_path).name
            
            # Pattern matching
            if file_name in key_patterns:
                key_files.append(file_path)
                continue
            
            # Files with many dependencies
            if len(repo_file.dependencies) > 10:
                key_files.append(file_path)
                continue
                
            # Files with many functions/classes
            if len(repo_file.functions) + len(repo_file.classes) > 10:
                key_files.append(file_path)
                continue
        
        # Sort by file size and complexity
        key_files.sort(key=lambda x: (
            len(self.repository_data[x].functions) + len(self.repository_data[x].classes),
            self.repository_data[x].file_size
        ), reverse=True)
        
        return key_files[:10]

    def _analyze_project_structure(self) -> Dict[str, Any]:
        """Analyze project structure"""
        structure = {
            "directories": {},
            "file_types": {},
            "depth_analysis": {},
            "module_structure": {}
        }
        
        for file_path in self.repository_data.keys():
            path_parts = Path(file_path).parts
            
            # Analyze directory structure
            for i, part in enumerate(path_parts[:-1]):  # Exclude file name
                depth = i + 1
                if depth not in structure["depth_analysis"]:
                    structure["depth_analysis"][depth] = set()
                structure["depth_analysis"][depth].add('/'.join(path_parts[:depth]))
        
        # Convert sets to lists
        for depth in structure["depth_analysis"]:
            structure["depth_analysis"][depth] = list(structure["depth_analysis"][depth])
        
        return structure

    def _update_statistics(self):
        """Update statistical information"""
        self.stats = {
            "total_files": len(self.repository_data),
            "languages": {},
            "total_size": 0,
            "total_lines": 0,
            "last_updated": datetime.now().isoformat(),
            "analysis_version": self.analysis_version
        }
        
        for repo_file in self.repository_data.values():
            # Language-specific statistics
            lang = repo_file.language
            self.stats["languages"][lang] = self.stats["languages"].get(lang, 0) + 1
            
            # Total size and lines
            self.stats["total_size"] += repo_file.file_size
            self.stats["total_lines"] += repo_file.line_count

    # Interface for integration with other chats

    def get_file_metadata_for_impact(self, file_path: str) -> Optional[Dict]:
        """Provide file metadata for impact analysis"""
        repo_file = self.get_file_info(file_path)
        if repo_file:
            return {
                "dependencies": repo_file.dependencies,
                "exports": repo_file.exports,
                "functions": [f["name"] for f in repo_file.functions],
                "classes": [c["name"] for c in repo_file.classes],
                "confidence_score": repo_file.confidence_score
            }
        return None

    def get_file_context_for_editing(self, file_path: str) -> Dict[str, Any]:
        """Provide file context for safe editing"""
        repo_file = self.get_file_info(file_path)
        if repo_file:
            return {
                "file_info": asdict(repo_file),
                "related_files": self.get_file_relationships(file_path),
                "similar_files": self.find_similar_files(file_path),
                "editing_suggestions": self._generate_editing_suggestions(file_path)
            }
        return {}

    def _generate_editing_suggestions(self, file_path: str) -> List[str]:
        """Generate file editing suggestions"""
        suggestions = []
        repo_file = self.get_file_info(file_path)
        
        if not repo_file:
            return suggestions
        
        # Basic suggestions
        if repo_file.language == "python":
            if len(repo_file.functions) > 20:
                suggestions.append("File is too large. Consider splitting into multiple files.")
            
            if not repo_file.imports and len(repo_file.functions) > 5:
                suggestions.append("Consider using external libraries.")
        
        return suggestions