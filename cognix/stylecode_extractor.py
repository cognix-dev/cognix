"""
Style Code Extractor for Semi-Auto Engine
Extracts code blocks from chat messages in Aider-compatible format
"""

import re
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class StyleCodeExtractor:
    """Extract code blocks from chat messages in Aider-compatible format"""
    
    def __init__(self):
        self.code_block_pattern = re.compile(
            r'```(?:(\w+)\s+)?([^\n]*)\n(.*?)```',
            re.DOTALL | re.MULTILINE
        )
        self.file_path_pattern = re.compile(
            r'^([a-zA-Z0-9_\-\.\/\\]+\.(py|js|ts|html|css|json|md|txt|yml|yaml|xml|sql|sh|bat))$'
        )
        
    def extract_code_blocks(self, message: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from message text
        
        Args:
            message: Chat message text
            
        Returns:
            List of code block dictionaries with keys:
            - language: Programming language
            - filename: Extracted filename if present
            - content: Code content
            - line_start: Starting line number if specified
        """
        code_blocks = []
        matches = self.code_block_pattern.findall(message)
        
        for match in matches:
            language = match[0] if match[0] else 'text'
            header = match[1].strip()
            content = match[2].strip()
            
            if not content:
                continue
                
            code_block = {
                'language': language,
                'content': content,
                'filename': None,
                'line_start': None,
                'modification_type': 'create'
            }
            
            # Extract filename from header
            filename = self._extract_filename(header)
            if filename:
                code_block['filename'] = filename
                
            # Extract line numbers if present
            line_info = self._extract_line_info(header)
            if line_info:
                code_block['line_start'] = line_info['start']
                code_block['line_end'] = line_info.get('end')
                code_block['modification_type'] = 'update'
                
            code_blocks.append(code_block)
            
        return code_blocks
    
    def _extract_filename(self, header: str) -> Optional[str]:
        """Extract filename from code block header"""
        if not header:
            return None
            
        # Direct filename match
        if self.file_path_pattern.match(header):
            return header
            
        # Extract from various patterns
        patterns = [
            r'(?:file:|filename:)\s*([a-zA-Z0-9_\-\.\/\\]+\.\w+)',
            r'^([a-zA-Z0-9_\-\.\/\\]+\.\w+)',
            r'`([a-zA-Z0-9_\-\.\/\\]+\.\w+)`',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, header, re.IGNORECASE)
            if match:
                return match.group(1)
                
        return None
    
    def _extract_line_info(self, header: str) -> Optional[Dict[str, int]]:
        """Extract line number information from header"""
        # Pattern for line ranges: lines 10-20, line 15, etc.
        line_patterns = [
            r'lines?\s+(\d+)-(\d+)',
            r'lines?\s+(\d+):(\d+)',
            r'line\s+(\d+)',
            r'@\s*(\d+)-(\d+)',
            r'@\s*(\d+)',
        ]
        
        for pattern in line_patterns:
            match = re.search(pattern, header, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 1:
                    return {'start': int(groups[0])}
                elif len(groups) == 2:
                    return {'start': int(groups[0]), 'end': int(groups[1])}
                    
        return None
    
    def group_by_file(self, code_blocks: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """Group code blocks by filename"""
        grouped = {}
        
        for block in code_blocks:
            filename = block.get('filename', 'unknown')
            if filename not in grouped:
                grouped[filename] = []
            grouped[filename].append(block)
            
        return grouped
    
    def validate_file_path(self, filepath: str) -> bool:
        """Validate if filepath is safe and reasonable"""
        if not filepath:
            return False
            
        # Security checks
        if '..' in filepath or filepath.startswith('/'):
            return False
            
        # Check for reasonable file extension
        return bool(self.file_path_pattern.match(os.path.basename(filepath)))
    
    def extract_modifications(self, message: str) -> List[Dict[str, any]]:
        """
        Extract file modifications from message in Aider format
        
        Returns:
            List of modification dictionaries:
            - type: 'create', 'update', 'delete'
            - filename: Target file path
            - content: New content or changes
            - line_range: For updates, which lines to modify
        """
        modifications = []
        code_blocks = self.extract_code_blocks(message)
        
        for block in code_blocks:
            if not block.get('filename'):
                continue
                
            mod = {
                'type': block.get('modification_type', 'create'),
                'filename': block['filename'],
                'content': block['content'],
                'language': block['language']
            }
            
            if block.get('line_start'):
                mod['line_range'] = {
                    'start': block['line_start'],
                    'end': block.get('line_end', block['line_start'])
                }
                
            modifications.append(mod)
            
        return modifications
    
    def format_for_aider(self, modifications: List[Dict[str, any]]) -> str:
        """Format modifications in Aider-compatible command format"""
        commands = []
        
        for mod in modifications:
            if mod['type'] == 'create':
                commands.append(f"# Creating {mod['filename']}")
                commands.append(f"```{mod['language']} {mod['filename']}")
                commands.append(mod['content'])
                commands.append("```")
                commands.append("")
                
            elif mod['type'] == 'update':
                line_info = ""
                if 'line_range' in mod:
                    line_info = f" lines {mod['line_range']['start']}-{mod['line_range']['end']}"
                    
                commands.append(f"# Updating {mod['filename']}{line_info}")
                commands.append(f"```{mod['language']} {mod['filename']}")
                commands.append(mod['content'])
                commands.append("```")
                commands.append("")
                
        return "\n".join(commands)