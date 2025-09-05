"""
Related File Finder for Cognix v0.1.4
Basic file relationship detection through imports, tests, and naming patterns
"""

import re
import os
from pathlib import Path
from typing import List, Set


class BasicRelatedFinder:
    """Basic file relationship finder for v0.1.4"""
    
    def __init__(self, context_manager):
        """Initialize with FileContext"""
        self.context = context_manager
        self.project_files = self._get_python_files()
    
    def _get_python_files(self) -> List[str]:
        """Get list of Python files from context (excluding site-packages)"""
        python_files = []
        for file_path, file_info in self.context.files.items():
            # Only exclude specific problematic paths
            if ('site-packages' in file_path or 
                'Lib\\site-packages' in file_path or
                'lib/python' in file_path):
                continue
            
            if file_info.language == 'python' and not file_info.is_binary:
                python_files.append(file_path)
        return python_files
    
    def find_related(self, target_file: str, imports: bool = False, used_by: bool = False, tests: bool = False) -> List[str]:
        """Find files related to target file"""
        
        # Resolve target file
        target_path = self._resolve_target_file(target_file)
        if not target_path:
            return []
        
        target_basename = Path(target_path).stem
        
        # Handle specific options
        if imports:
            return self._find_imports(target_path)
        elif used_by:
            return self._find_used_by(target_path, target_basename)
        elif tests:
            return self._find_test_files(target_basename)
        else:
            # Default: find all relationships
            return self._find_all_related(target_path, target_basename)
    
    def _resolve_target_file(self, target_file: str) -> str:
        """Resolve target file path"""
        
        # Try direct path
        if os.path.exists(target_file):
            return target_file
        
        # Try adding .py extension
        if not target_file.endswith('.py'):
            py_file = target_file + '.py'
            if os.path.exists(py_file):
                return py_file
        
        # Search in project files
        for file_path in self.project_files:
            if Path(file_path).name == target_file or Path(file_path).name == target_file + '.py':
                full_path = self.context.root_dir / file_path
                if full_path.exists():
                    return str(full_path)
        
        return None
    
    def _find_imports(self, target_file: str) -> List[str]:
        """Find files that target file imports"""
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return []
        
        imports = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # from module import ...
            if line.startswith('from ') and ' import' in line:
                module = line.split(' import')[0].replace('from ', '').strip()
                if not module.startswith('.'):  # Skip relative imports
                    import_file = self._module_to_file(module)
                    if import_file:
                        imports.append(import_file)
            
            # import module
            elif line.startswith('import '):
                module = line.replace('import ', '').strip()
                # Handle comma-separated imports
                modules = [m.strip() for m in module.split(',')]
                for m in modules:
                    if '.' not in m:  # Skip package imports for now
                        import_file = self._module_to_file(m)
                        if import_file:
                            imports.append(import_file)
        
        return list(set(imports))  # Remove duplicates
    
    def _find_used_by(self, target_file: str, target_basename: str) -> List[str]:
        """Find files that import/use target file"""
        used_by = []
        
        for file_path in self.project_files:
            full_path = self.context.root_dir / file_path
            if str(full_path) == target_file:
                continue
                
            try:
                content = self.context.get_file_content(file_path)
                if not content:
                    continue
                
                # Simple import pattern matching
                patterns = [
                    f"from {target_basename} import",
                    f"import {target_basename}",
                    f"from .{target_basename} import"
                ]
                
                for pattern in patterns:
                    if pattern in content:
                        used_by.append(file_path)
                        break
                        
            except:
                continue
        
        return used_by
    
    def _find_test_files(self, basename: str) -> List[str]:
        """Find test files for target"""
        test_files = []
        
        for file_path in self.project_files:
            filename = Path(file_path).name
            
            # Standard test patterns
            test_patterns = [
                f"test_{basename}.py",
                f"{basename}_test.py",
                f"test{basename}.py",
                f"Test{basename.title()}.py"
            ]
            
            if filename in test_patterns:
                test_files.append(file_path)
                continue
            
            # Check if in test directory and contains target name
            if 'test' in file_path.lower() and basename.lower() in filename.lower():
                test_files.append(file_path)
        
        return test_files
    
    def _find_name_related(self, basename: str) -> List[str]:
        """Find files with similar names"""
        name_related = []
        basename_lower = basename.lower()
        
        for file_path in self.project_files:
            filename = Path(file_path).stem.lower()
            
            # Skip exact matches and test files
            if filename == basename_lower or 'test' in filename:
                continue
            
            # Name similarity patterns
            if (basename_lower in filename or 
                filename in basename_lower or
                f"{basename_lower}_" in filename or
                f"_{basename_lower}" in filename):
                name_related.append(file_path)
        
        return name_related
    
    def _find_all_related(self, target_file: str, target_basename: str) -> List[str]:
        """Find all types of related files"""
        all_related = set()
        
        # 1. Import dependencies
        imports = self._find_imports(target_file)
        all_related.update(imports)
        
        # 2. Files that use this file
        used_by = self._find_used_by(target_file, target_basename)
        all_related.update(used_by)
        
        # 3. Test files
        tests = self._find_test_files(target_basename)
        all_related.update(tests)
        
        # 4. Name-related files
        name_related = self._find_name_related(target_basename)
        all_related.update(name_related)
        
        return list(all_related)
    
    def _module_to_file(self, module_name: str) -> str:
        """Convert module name to file path"""
        # Skip standard library modules
        standard_modules = {
            'sys', 'os', 'argparse', 'pathlib', 'logging', 're', 'json', 'datetime', 
            'ast', 'time', 'cmd', 'shlex', 'tempfile', 'traceback', 'typing', 'hashlib',
            'mimetypes', 'subprocess', 'threading', 'asyncio', 'functools', 'itertools',
            'collections', 'copy', 'pickle', 'base64', 'urllib', 'http', 'socket',
            'uuid', 'random', 'math', 'statistics', 'decimal', 'fractions'
        }
        if module_name in standard_modules:
            return None
        
        # Convert module path to file path
        # cognix.cli -> cognix/cli.py or cognix\cli.py
        module_path = module_name.replace('.', os.sep)
        
        possible_files = [
            f"{module_path}.py",
            f"{module_path}\\__init__.py",
            f"{module_path}/__init__.py"
        ]
        
        for file_path in possible_files:
            if file_path in self.project_files:
                return file_path
            
            # Also check with forward slashes (normalize path separators)
            normalized_path = file_path.replace('\\', '/')
            if normalized_path in self.project_files:
                return normalized_path
        
        return None
    
    def format_results(self, related_files: List[str], target_file: str, option: str = None) -> str:
        """Format results for display"""
        if not related_files:
            if option:
                return f"No {option} found for {Path(target_file).name}"
            else:
                return f"No related files found for {Path(target_file).name}"
        
        # Header based on option
        headers = {
            'imports': f"📥 Files imported by {Path(target_file).name}:",
            'used_by': f"📤 Files that use {Path(target_file).name}:",
            'tests': f"🧪 Test files for {Path(target_file).name}:"
        }
        
        if option in headers:
            output = [headers[option]]
        else:
            output = [f"🔍 Related files for: {Path(target_file).name}"]
        
        output.append("━" * 25)
        
        # List files
        for file_path in related_files:
            output.append(f"📄 {file_path}")
        
        output.append("")
        output.append(f"Found: {len(related_files)} files")
        
        return "\n".join(output)