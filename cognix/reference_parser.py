"""
Reference Parser for Cognix v0.1.4 - Debug Version
Handles @filename and #function reference notation parsing
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class FileReference:
    """File reference (@filename)"""
    filename: str
    full_path: Optional[Path] = None
    exists: bool = False
    line_count: int = 0
    size: int = 0


@dataclass
class FunctionReference:
    """Function reference (#function)"""
    function_name: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    found: bool = False
    signature: Optional[str] = None


@dataclass
class ParsedReferences:
    """Result of parsing references from user input"""
    original_input: str
    files: List[FileReference]
    functions: List[FunctionReference]
    has_references: bool = False
    context_text: str = ""


class ReferenceParser:
    """Parse and resolve @filename and #function references"""
    
    def __init__(self, context_manager):
        """Initialize with FileContext for file operations"""
        self.context = context_manager
        
        # 日本語対応の正規表現パターン
        self.file_pattern = r'@([a-zA-Z0-9_/\\.\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF-]+(?:\.[a-zA-Z0-9]+)?)'
        self.func_pattern = r'#([a-zA-Z_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF][a-zA-Z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]*)'
        
    def parse(self, user_input: str) -> ParsedReferences:
        """Parse user input for references and generate context"""
        
        # Find all file and function references
        file_matches = re.findall(self.file_pattern, user_input)
        func_matches = re.findall(self.func_pattern, user_input)
                
        # Create reference objects
        file_refs = [self._resolve_file_reference(filename) for filename in file_matches]
        func_refs = [self._resolve_function_reference(func_name) for func_name in func_matches]
              
        # Check for composite references (@file #function)
        composite_refs = self._find_composite_references(user_input, file_refs, func_refs)
        
        # Generate context text
        context_text = self._generate_context_text(file_refs, func_refs, composite_refs)
        
        has_refs = bool(file_refs or func_refs)
        
        return ParsedReferences(
            original_input=user_input,
            files=file_refs,
            functions=func_refs,
            has_references=has_refs,
            context_text=context_text
        )
    
    def _resolve_file_reference(self, filename: str) -> FileReference:
        """Resolve a file reference to actual file"""
        
        # Try different path resolutions
        possible_paths = [
            Path(filename),  # Direct path
            self.context.root_dir / filename,  # Relative to project root
            self._find_file_by_name(filename)  # Search in project
        ]
        
        for path in possible_paths:
            if path and path.exists() and path.is_file():
                try:
                    stat = path.stat()
                    line_count = 0
                    
                    # Count lines for text files
                    if self.context.is_text_file(path):
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                line_count = sum(1 for _ in f)
                        except:
                            pass
                    
                    return FileReference(
                        filename=filename,
                        full_path=path,
                        exists=True,
                        line_count=line_count,
                        size=stat.st_size
                    )
                except Exception:
                    continue
        
        # File not found
        return FileReference(filename=filename, exists=False)
    
    def _find_file_by_name(self, filename: str) -> Optional[Path]:
        """Find file by name in project directory"""
        try:
            # Search for files with matching name
            for file_path, file_info in self.context.files.items():
                if Path(file_path).name == filename:
                    return self.context.root_dir / file_path
        except Exception:
            pass
        return None
    
    def _resolve_function_reference(self, func_name: str) -> FunctionReference:
        """Resolve a function reference across project files"""
        
        # Search through Python files for function definition
        for file_path, file_info in self.context.files.items():
            if file_info.language != 'python' or file_info.is_binary:
                continue
            
            content = self.context.get_file_content(file_path)
            if not content:
                continue
            
            # Parse AST to find function
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == func_name:
                        # Extract function signature
                        lines = content.split('\n')
                        if node.lineno <= len(lines):
                            signature = lines[node.lineno - 1].strip()
                            
                            return FunctionReference(
                                function_name=func_name,
                                file_path=file_path,
                                line_number=node.lineno,
                                found=True,
                                signature=signature
                            )
            except SyntaxError:
                # Fallback to regex search for malformed Python
                if self._regex_find_function(content, func_name):
                    return FunctionReference(
                        function_name=func_name,
                        file_path=file_path,
                        found=True
                    )
        
        # Function not found
        return FunctionReference(function_name=func_name, found=False)
    
    def _regex_find_function(self, content: str, func_name: str) -> bool:
        """Fallback regex-based function search"""
        pattern = rf'^\s*def\s+{re.escape(func_name)}\s*\('
        return bool(re.search(pattern, content, re.MULTILINE))
    
    def _find_composite_references(self, user_input: str, file_refs: List[FileReference], 
                                 func_refs: List[FunctionReference]) -> List[Tuple[FileReference, FunctionReference]]:
        """Find composite references like '@file #function'"""
        composite_refs = []
        
        # より柔軟な複合参照パターン
        composite_pattern = r'@([a-zA-Z0-9_/\\.-]+(?:\.[a-zA-Z0-9]+)?)\s+#([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(composite_pattern, user_input)
        
        for filename, func_name in matches:
            # Find matching file reference
            file_ref = None
            for f in file_refs:
                if f.filename == filename:
                    file_ref = f
                    break
            
            if file_ref and file_ref.exists:
                # Find function specifically in the referenced file
                specific_func_ref = self._find_function_in_file(file_ref.full_path, func_name)
                if specific_func_ref:
                    composite_refs.append((file_ref, specific_func_ref))
        
        return composite_refs
    
    def _find_function_in_file(self, file_path: Path, func_name: str) -> Optional[FunctionReference]:
        """Find specific function in specific file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    lines = content.split('\n')
                    signature = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else None
                    
                    return FunctionReference(
                        function_name=func_name,
                        file_path=str(file_path.relative_to(self.context.root_dir)),
                        line_number=node.lineno,
                        found=True,
                        signature=signature
                    )
        except Exception:
            pass
        return None
    
    def _generate_context_text(self, file_refs: List[FileReference], 
                             func_refs: List[FunctionReference],
                             composite_refs: List[Tuple[FileReference, FunctionReference]]) -> str:
        """Generate context text from resolved references"""
        
        context_parts = []
        
        # Handle composite references first (most specific)
        for file_ref, func_ref in composite_refs:
            if file_ref.exists and func_ref.found:
                context_parts.append(self._format_composite_reference(file_ref, func_ref))
        
        # Handle standalone file references
        used_file_names = {fr.filename for fr, _ in composite_refs}
        standalone_files = [f for f in file_refs if f.filename not in used_file_names]
        for file_ref in standalone_files:
            if file_ref.exists:
                context_parts.append(self._format_file_reference(file_ref))
        
        # Handle standalone function references
        used_func_names = {fr.function_name for _, fr in composite_refs}
        standalone_funcs = [f for f in func_refs if f.function_name not in used_func_names]
        for func_ref in standalone_funcs:
            if func_ref.found:
                context_parts.append(self._format_function_reference(func_ref))
        
        return "\n\n".join(context_parts) if context_parts else ""
    
    def _format_file_reference(self, file_ref: FileReference) -> str:
        """Format file reference for display"""
        try:
            content = file_ref.full_path.read_text(encoding='utf-8')
            
            # Truncate if too long
            if len(content) > 2000:
                content = content[:2000] + "\n... [truncated] ..."
            
            return f"""📁 File: {file_ref.filename} ({file_ref.line_count} lines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{content}"""
        except Exception as e:
            return f"📁 File: {file_ref.filename} (could not read content: {e})"
    
    def _format_function_reference(self, func_ref: FunctionReference) -> str:
        """Format function reference for display"""
        try:
            file_path = self.context.root_dir / func_ref.file_path
            content = file_path.read_text(encoding='utf-8')
            
            # Extract function content
            func_content = self._extract_function_content(content, func_ref.function_name)
            
            location = f" (found in {func_ref.file_path})" if func_ref.file_path else ""
            
            return f"""🔍 Function: {func_ref.function_name}{location}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{func_content}"""
        except Exception as e:
            return f"🔍 Function: {func_ref.function_name} (could not read content: {e})"
    
    def _format_composite_reference(self, file_ref: FileReference, func_ref: FunctionReference) -> str:
        """Format composite reference for display"""
        try:
            content = file_ref.full_path.read_text(encoding='utf-8')
            func_content = self._extract_function_content(content, func_ref.function_name)
            
            return f"""🎯 Target: {file_ref.filename} -> {func_ref.function_name}()
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{func_content}"""
        except Exception as e:
            return f"🎯 Target: {file_ref.filename} -> {func_ref.function_name}() (could not read content: {e})"
    
    def _extract_function_content(self, file_content: str, func_name: str) -> str:
        """Extract function content from file"""
        try:
            tree = ast.parse(file_content)
            lines = file_content.split('\n')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    start_line = node.lineno - 1
                    
                    # Find end line by looking at next function/class or end of file
                    end_line = len(lines)
                    for next_node in ast.walk(tree):
                        if (isinstance(next_node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) 
                            and next_node.lineno > node.lineno):
                            end_line = min(end_line, next_node.lineno - 1)
                    
                    # Extract function lines with proper indentation handling
                    func_lines = []
                    base_indent = None
                    
                    for i in range(start_line, min(end_line, len(lines))):
                        line = lines[i]
                        
                        if base_indent is None and line.strip():
                            base_indent = len(line) - len(line.lstrip())
                        
                        # Check if we've reached end of function
                        if (line.strip() and base_indent is not None and 
                            len(line) - len(line.lstrip()) <= base_indent and 
                            i > start_line and not line.lstrip().startswith(('@', 'def ', 'async def '))):
                            break
                        
                        func_lines.append(line)
                    
                    func_content = '\n'.join(func_lines)
                    
                    # Truncate if too long
                    if len(func_content) > 1500:
                        func_content = func_content[:1500] + "\n... [truncated] ..."
                    
                    return func_content
            
            return f"# Function '{func_name}' not found in this file"
            
        except Exception as e:
            # Fallback regex extraction
            return self._regex_extract_function(file_content, func_name)
    
    def _regex_extract_function(self, content: str, func_name: str) -> str:
        """Fallback regex-based function extraction"""
        lines = content.split('\n')
        func_lines = []
        in_function = False
        base_indent = None
        
        for line in lines:
            if re.match(rf'^\s*def\s+{re.escape(func_name)}\s*\(', line):
                in_function = True
                base_indent = len(line) - len(line.lstrip())
                func_lines.append(line)
                continue
            
            if in_function:
                if not line.strip():
                    func_lines.append(line)
                    continue
                
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= base_indent and not line.lstrip().startswith(('@', '#')):
                    break
                
                func_lines.append(line)
        
        result = '\n'.join(func_lines) if func_lines else f"# Function '{func_name}' not found"
        
        # Truncate if too long
        if len(result) > 1500:
            result = result[:1500] + "\n... [truncated] ..."
        
        return result