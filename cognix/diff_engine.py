"""
Diff and Patch Engine for Cognix
Handles generating and applying code diffs
"""

import difflib
import re
import os
import tempfile
import shutil
from typing import List, Tuple, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class DiffType(Enum):
    """Types of diffs"""
    UNIFIED = "unified"
    CONTEXT = "context"
    SIDE_BY_SIDE = "side_by_side"
    MINIMAL = "minimal"


@dataclass
class DiffResult:
    """Result of a diff operation"""
    original_file: str
    modified_file: str
    diff_content: str
    diff_type: DiffType
    line_changes: Dict[str, int]  # added, removed, modified
    is_binary: bool = False
    error: Optional[str] = None


@dataclass
class PatchResult:
    """Result of a patch operation"""
    success: bool
    file_path: str
    backup_path: Optional[str] = None
    error: Optional[str] = None
    changes_applied: int = 0


class DiffEngine:
    """Handles diff generation and patch application"""
    
    def __init__(self, backup_dir: str = None):
        """Initialize diff engine"""
        if backup_dir is None:
            backup_dir = os.path.expanduser("~/.cognix/backups")
        
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_diff(
        self,
        original_content: str,
        modified_content: str,
        original_file: str = "original",
        modified_file: str = "modified",
        diff_type: DiffType = DiffType.UNIFIED,
        context_lines: int = 3
    ) -> DiffResult:
        """Generate diff between two content strings"""
        
        try:
            # Split content into lines
            original_lines = original_content.splitlines(keepends=True)
            modified_lines = modified_content.splitlines(keepends=True)
            
            # Calculate line changes
            line_changes = self._calculate_line_changes(original_lines, modified_lines)
            
            # Generate diff based on type
            if diff_type == DiffType.UNIFIED:
                diff_content = self._generate_unified_diff(
                    original_lines, modified_lines, original_file, modified_file, context_lines
                )
            elif diff_type == DiffType.CONTEXT:
                diff_content = self._generate_context_diff(
                    original_lines, modified_lines, original_file, modified_file, context_lines
                )
            elif diff_type == DiffType.SIDE_BY_SIDE:
                diff_content = self._generate_side_by_side_diff(
                    original_lines, modified_lines, original_file, modified_file
                )
            elif diff_type == DiffType.MINIMAL:
                diff_content = self._generate_minimal_diff(
                    original_lines, modified_lines
                )
            else:
                raise ValueError(f"Unsupported diff type: {diff_type}")
            
            return DiffResult(
                original_file=original_file,
                modified_file=modified_file,
                diff_content=diff_content,
                diff_type=diff_type,
                line_changes=line_changes,
                is_binary=False
            )
            
        except Exception as e:
            return DiffResult(
                original_file=original_file,
                modified_file=modified_file,
                diff_content="",
                diff_type=diff_type,
                line_changes={"added": 0, "removed": 0, "modified": 0},
                error=str(e)
            )
    
    def generate_file_diff(
        self,
        original_file_path: str,
        modified_file_path: str = None,
        modified_content: str = None,
        diff_type: DiffType = DiffType.UNIFIED,
        context_lines: int = 3
    ) -> DiffResult:
        """Generate diff for files"""
        
        original_path = Path(original_file_path)
        
        if not original_path.exists():
            return DiffResult(
                original_file=original_file_path,
                modified_file=modified_file_path or "modified",
                diff_content="",
                diff_type=diff_type,
                line_changes={"added": 0, "removed": 0, "modified": 0},
                error=f"Original file not found: {original_file_path}"
            )
        
        try:
            # Read original content
            original_content = original_path.read_text(encoding='utf-8')
            
            # Get modified content
            if modified_content is not None:
                # Use provided content
                pass
            elif modified_file_path:
                # Read from modified file
                modified_path = Path(modified_file_path)
                if not modified_path.exists():
                    return DiffResult(
                        original_file=original_file_path,
                        modified_file=modified_file_path,
                        diff_content="",
                        diff_type=diff_type,
                        line_changes={"added": 0, "removed": 0, "modified": 0},
                        error=f"Modified file not found: {modified_file_path}"
                    )
                modified_content = modified_path.read_text(encoding='utf-8')
            else:
                raise ValueError("Either modified_file_path or modified_content must be provided")
            
            return self.generate_diff(
                original_content,
                modified_content,
                original_file_path,
                modified_file_path or "modified",
                diff_type,
                context_lines
            )
            
        except UnicodeDecodeError:
            # Handle binary files
            return DiffResult(
                original_file=original_file_path,
                modified_file=modified_file_path or "modified",
                diff_content="Binary files differ",
                diff_type=diff_type,
                line_changes={"added": 0, "removed": 0, "modified": 0},
                is_binary=True
            )
        except Exception as e:
            return DiffResult(
                original_file=original_file_path,
                modified_file=modified_file_path or "modified",
                diff_content="",
                diff_type=diff_type,
                line_changes={"added": 0, "removed": 0, "modified": 0},
                error=str(e)
            )
    
    def apply_patch(
        self,
        file_path: str,
        patch_content: str,
        create_backup: bool = True,
        dry_run: bool = False
    ) -> PatchResult:
        """Apply patch to a file"""
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            return PatchResult(
                success=False,
                file_path=str(file_path),
                error=f"File not found: {file_path}"
            )
        
        try:
            # Read original content
            original_content = file_path.read_text(encoding='utf-8')
            
            # Parse and apply patch
            modified_content, changes_count = self._apply_unified_patch(
                original_content, patch_content
            )
            
            if dry_run:
                return PatchResult(
                    success=True,
                    file_path=str(file_path),
                    changes_applied=changes_count
                )
            
            backup_path = None
            if create_backup:
                backup_path = self._create_backup(file_path, original_content)
            
            # Write modified content
            file_path.write_text(modified_content, encoding='utf-8')
            
            return PatchResult(
                success=True,
                file_path=str(file_path),
                backup_path=backup_path,
                changes_applied=changes_count
            )
            
        except Exception as e:
            return PatchResult(
                success=False,
                file_path=str(file_path),
                error=str(e)
            )
    
    def apply_content_replacement(
        self,
        file_path: str,
        new_content: str,
        create_backup: bool = True,
        dry_run: bool = False
    ) -> PatchResult:
        """Replace entire file content"""
        
        file_path = Path(file_path)
        
        try:
            backup_path = None
            
            if not dry_run:
                if create_backup and file_path.exists():
                    original_content = file_path.read_text(encoding='utf-8')
                    backup_path = self._create_backup(file_path, original_content)
                
                # Write new content
                file_path.write_text(new_content, encoding='utf-8')
            
            return PatchResult(
                success=True,
                file_path=str(file_path),
                backup_path=backup_path,
                changes_applied=1
            )
            
        except Exception as e:
            return PatchResult(
                success=False,
                file_path=str(file_path),
                error=str(e)
            )
    
    def preview_changes(
        self,
        file_path: str,
        new_content: str,
        diff_type: DiffType = DiffType.UNIFIED
    ) -> DiffResult:
        """Preview changes that would be made to a file"""
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            # New file
            return DiffResult(
                original_file=str(file_path),
                modified_file=str(file_path),
                diff_content=f"New file: {file_path}\n\n{new_content}",
                diff_type=diff_type,
                line_changes={"added": len(new_content.splitlines()), "removed": 0, "modified": 0}
            )
        
        try:
            original_content = file_path.read_text(encoding='utf-8')
            
            return self.generate_diff(
                original_content,
                new_content,
                str(file_path),
                str(file_path),
                diff_type
            )
            
        except Exception as e:
            return DiffResult(
                original_file=str(file_path),
                modified_file=str(file_path),
                diff_content="",
                diff_type=diff_type,
                line_changes={"added": 0, "removed": 0, "modified": 0},
                error=str(e)
            )
    
    def _calculate_line_changes(self, original_lines: List[str], modified_lines: List[str]) -> Dict[str, int]:
        """Calculate line changes statistics"""
        diff = list(difflib.unified_diff(original_lines, modified_lines, n=0))
        
        added = 0
        removed = 0
        
        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                added += 1
            elif line.startswith('-') and not line.startswith('---'):
                removed += 1
        
        modified = min(added, removed)
        added = added - modified
        removed = removed - modified
        
        return {
            "added": added,
            "removed": removed,
            "modified": modified
        }
    
    def _generate_unified_diff(
        self,
        original_lines: List[str],
        modified_lines: List[str],
        original_file: str,
        modified_file: str,
        context_lines: int
    ) -> str:
        """Generate unified diff"""
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=original_file,
            tofile=modified_file,
            n=context_lines
        )
        return ''.join(diff)
    
    def _generate_context_diff(
        self,
        original_lines: List[str],
        modified_lines: List[str],
        original_file: str,
        modified_file: str,
        context_lines: int
    ) -> str:
        """Generate context diff"""
        diff = difflib.context_diff(
            original_lines,
            modified_lines,
            fromfile=original_file,
            tofile=modified_file,
            n=context_lines
        )
        return ''.join(diff)
    
    def _generate_side_by_side_diff(
        self,
        original_lines: List[str],
        modified_lines: List[str],
        original_file: str,
        modified_file: str
    ) -> str:
        """Generate side-by-side diff"""
        diff = difflib.HtmlDiff()
        html_diff = diff.make_table(
            original_lines,
            modified_lines,
            fromdesc=original_file,
            todesc=modified_file
        )
        
        # Convert HTML to text representation
        # This is a simplified version - in practice, you might want to use a proper HTML parser
        text_diff = re.sub(r'<[^>]+>', '', html_diff)
        text_diff = re.sub(r'\s+', ' ', text_diff).strip()
        
        return text_diff
    
    def _generate_minimal_diff(self, original_lines: List[str], modified_lines: List[str]) -> str:
        """Generate minimal diff showing only changed lines"""
        diff_lines = []
        
        for line in difflib.unified_diff(original_lines, modified_lines, n=0):
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                continue
            if line.startswith('+') or line.startswith('-'):
                diff_lines.append(line)
        
        return '\n'.join(diff_lines)
    
    def _apply_unified_patch(self, original_content: str, patch_content: str) -> Tuple[str, int]:
        """Apply unified patch to content"""
        original_lines = original_content.splitlines(True)
        
        # Parse patch
        patch_lines = patch_content.splitlines()
        
        # Simple patch application (this is a basic implementation)
        # In practice, you might want to use a more robust patch library
        
        result_lines = original_lines.copy()
        changes_count = 0
        
        # Find and apply hunks
        i = 0
        while i < len(patch_lines):
            line = patch_lines[i]
            
            # Find hunk header
            if line.startswith('@@'):
                # Parse hunk header: @@ -start,count +start,count @@
                match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                if match:
                    old_start = int(match.group(1)) - 1  # Convert to 0-based
                    new_start = int(match.group(3)) - 1
                    
                    # Apply hunk
                    i += 1
                    hunk_changes = self._apply_hunk(result_lines, patch_lines, i, old_start)
                    changes_count += hunk_changes
                    
                    # Skip processed hunk lines
                    while i < len(patch_lines) and not patch_lines[i].startswith('@@'):
                        i += 1
                    continue
            
            i += 1
        
        return ''.join(result_lines), changes_count
    
    def _apply_hunk(self, result_lines: List[str], patch_lines: List[str], start_idx: int, old_start: int) -> int:
        """Apply a single hunk to result lines"""
        changes = 0
        line_offset = 0
        i = start_idx
        
        while i < len(patch_lines):
            line = patch_lines[i]
            
            if line.startswith('@@'):
                break
            elif line.startswith(' '):
                # Context line - no change
                pass
            elif line.startswith('-'):
                # Remove line
                if old_start + line_offset < len(result_lines):
                    del result_lines[old_start + line_offset]
                    changes += 1
                    line_offset -= 1
            elif line.startswith('+'):
                # Add line
                new_line = line[1:]
                if not new_line.endswith('\n'):
                    new_line += '\n'
                result_lines.insert(old_start + line_offset + 1, new_line)
                changes += 1
                line_offset += 1
            
            i += 1
        
        return changes
    
    def _create_backup(self, file_path: Path, content: str) -> str:
        """Create backup of file"""
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}_{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        backup_path.write_text(content, encoding='utf-8')
        return str(backup_path)
    
    def restore_from_backup(self, backup_path: str, target_path: str) -> PatchResult:
        """Restore file from backup"""
        backup_file = Path(backup_path)
        target_file = Path(target_path)
        
        if not backup_file.exists():
            return PatchResult(
                success=False,
                file_path=target_path,
                error=f"Backup file not found: {backup_path}"
            )
        
        try:
            backup_content = backup_file.read_text(encoding='utf-8')
            target_file.write_text(backup_content, encoding='utf-8')
            
            return PatchResult(
                success=True,
                file_path=target_path,
                changes_applied=1
            )
            
        except Exception as e:
            return PatchResult(
                success=False,
                file_path=target_path,
                error=str(e)
            )
    
    def list_backups(self, file_pattern: str = "*") -> List[Dict[str, Any]]:
        """List available backups"""
        import fnmatch
        from datetime import datetime
        
        backups = []
        
        for backup_file in self.backup_dir.glob("*.backup"):
            if fnmatch.fnmatch(backup_file.name, f"{file_pattern}*"):
                stat = backup_file.stat()
                backups.append({
                    "path": str(backup_file),
                    "name": backup_file.name,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return sorted(backups, key=lambda x: x["created"], reverse=True)
    
    def cleanup_old_backups(self, days: int = 30):
        """Clean up old backup files"""
        import time
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        removed_count = 0
        for backup_file in self.backup_dir.glob("*.backup"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                removed_count += 1
        
        return removed_count

    def create_backup(self, file_path: str) -> PatchResult:
        """
        Create backup of a file (public interface)
        
        Args:
            file_path (str): Path to the file to backup
            
        Returns:
            PatchResult: Result containing success status and backup path
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                return PatchResult(
                    success=False,
                    file_path=file_path,
                    error=f"File not found: {file_path}"
                )
            
            # Read file content
            content = file_path_obj.read_text(encoding='utf-8')
            
            # Create backup using existing private method
            backup_path = self._create_backup(file_path_obj, content)
            
            return PatchResult(
                success=True,
                file_path=file_path,
                backup_path=backup_path
            )
            
        except Exception as e:
            return PatchResult(
                success=False,
                file_path=file_path,
                error=f"Failed to create backup: {str(e)}"
            )