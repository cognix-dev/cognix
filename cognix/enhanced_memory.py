"""
Enhanced Memory System for Cognix
Extends the existing Memory class with persistent repository understanding capabilities
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from cognix.memory import Memory
from cognix.logger import err_console
from cognix.repository_manager import RepositoryFile  # Use shared RepositoryFile class


class EnhancedMemory(Memory):
    """Memory management system with repository understanding capabilities"""
    
    def __init__(self, memory_dir: str = None):
        """Initialize enhanced memory system"""
        # Initialize parent Memory class
        super().__init__(memory_dir)
        
        # Initialize new repository features
        self.repository_file = self.memory_dir / "repository_data.json"
        self.repository_enabled = False
        self.repository_data: Dict[str, RepositoryFile] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        
        # Try to load existing repository data
        self._load_repository_data()
    
    def enable_repository_features(self):
        """Enable repository understanding features"""
        self.repository_enabled = True
    
    def is_repository_enabled(self) -> bool:
        """Check if repository features are enabled"""
        return self.repository_enabled
    
    def _load_repository_data(self) -> bool:
        """Load persisted repository data"""
        if not self.repository_file.exists():
            return False
        
        try:
            with open(self.repository_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Version compatibility check
            version = data.get('version', '1.0')
            if version != '1.0':
                err_console.print(f"Warning: Repository data version mismatch: {version}")
                return False
            
            # Data restoration
            repo_files = data.get('repository_files', {})
            self.repository_data = {
                path: RepositoryFile.from_dict(file_data)
                for path, file_data in repo_files.items()
            }
            
            self.dependency_graph = data.get('dependency_graph', {})
            
            return True
            
        except Exception as e:
            err_console.print(f"Warning: Failed to load repository data: {e}")
            return False
    
    def _save_repository_data(self):
        """Persist repository data to disk"""
        if not self.repository_enabled:
            return
        
        try:
            data = {
                'version': '1.0',
                'last_saved': datetime.now().isoformat(),
                'repository_files': {
                    path: repo_file.to_dict()
                    for path, repo_file in self.repository_data.items()
                },
                'dependency_graph': self.dependency_graph,
                'stats': {
                    'total_files': len(self.repository_data),
                    'languages': self._get_language_stats()
                }
            }
            
            # Atomic write operation
            temp_file = self.repository_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self.repository_file)
            
        except Exception as e:
            err_console.print(f"Error saving repository data: {e}")
    
    def _get_language_stats(self) -> Dict[str, int]:
        """Get language distribution statistics"""
        stats = {}
        for repo_file in self.repository_data.values():
            lang = repo_file.language
            stats[lang] = stats.get(lang, 0) + 1
        return stats
    
    def add_repository_file(self, repo_file: RepositoryFile):
        """Add repository file information"""
        if not self.repository_enabled:
            return
        
        self.repository_data[repo_file.file_path] = repo_file
        self._save_repository_data()
    
    def get_repository_file(self, file_path: str) -> Optional[RepositoryFile]:
        """Get repository file information"""
        return self.repository_data.get(file_path)
    
    def update_dependency_graph(self, file_path: str, dependencies: List[str]):
        """Update dependency graph"""
        if not self.repository_enabled:
            return
        
        self.dependency_graph[file_path] = dependencies
        self._save_repository_data()
    
    def get_dependent_files(self, file_path: str) -> List[str]:
        """Get files that depend on the specified file"""
        dependent_files = []
        for path, deps in self.dependency_graph.items():
            if file_path in deps:
                dependent_files.append(path)
        return dependent_files
    
    def get_repository_summary(self) -> Dict[str, Any]:
        """Get repository summary information"""
        if not self.repository_enabled or not self.repository_data:
            return {
                'enabled': self.repository_enabled,
                'total_files': 0,
                'languages': {},
                'avg_confidence': 0.0
            }
        
        total_confidence = sum(rf.confidence_score for rf in self.repository_data.values())
        avg_confidence = total_confidence / len(self.repository_data)
        
        return {
            'enabled': True,
            'total_files': len(self.repository_data),
            'languages': self._get_language_stats(),
            'avg_confidence': avg_confidence,
            'dependency_connections': len([deps for deps in self.dependency_graph.values() if deps]),
            'last_updated': max([rf.last_analyzed for rf in self.repository_data.values()], default='Never')
        }
    
    def add_entry(
        self,
        user_prompt: str,
        claude_reply: str,
        model_used: str,
        file_path: str = None,
        file_before: str = None,
        file_after: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Enhanced add_entry method with repository context"""
        
        # Execute existing functionality
        entry_id = super().add_entry(
            user_prompt=user_prompt,
            claude_reply=claude_reply,
            model_used=model_used,
            file_path=file_path,
            file_before=file_before,
            file_after=file_after,
            metadata=metadata
        )
        
        # Additional processing if repository features are enabled
        if self.repository_enabled and file_path:
            self._update_repository_context(entry_id, file_path, metadata)
        
        return entry_id
    
    def _update_repository_context(self, entry_id: str, file_path: str, metadata: Dict[str, Any]):
        """Add repository context to entry"""
        try:
            repo_file = self.get_repository_file(file_path)
            if repo_file:
                # Add repository information to metadata
                if metadata is None:
                    metadata = {}
                
                metadata.update({
                    'repository_context': {
                        'confidence_score': repo_file.confidence_score,
                        'dependencies': repo_file.dependencies[:5],  # Max 5 dependencies
                        'functions_count': len(repo_file.functions),
                        'classes_count': len(repo_file.classes)
                    }
                })
                
                # Update entry metadata
                entry = self.get_entry_by_id(entry_id)
                if entry:
                    entry.metadata = metadata
        except Exception as e:
            # Repository feature errors should not affect existing functionality
            err_console.print(f"Warning: Repository context update failed: {e}")
    
    def search_repository_files(self, query: str) -> List[RepositoryFile]:
        """Search repository files by various criteria"""
        if not self.repository_enabled:
            return []
        
        query_lower = query.lower()
        results = []
        
        for repo_file in self.repository_data.values():
            # Search in file path
            if query_lower in repo_file.file_path.lower():
                results.append(repo_file)
                continue
            
            # Search in function names
            for func in repo_file.functions:
                if query_lower in func.get('name', '').lower():
                    results.append(repo_file)
                    break
            
            # Search in class names
            for cls in repo_file.classes:
                if query_lower in cls.get('name', '').lower():
                    results.append(repo_file)
                    break
            
            # Search in dependencies
            for dep in repo_file.dependencies:
                if query_lower in dep.lower():
                    results.append(repo_file)
                    break
        
        return results
    
    def get_files_by_language(self, language: str) -> List[RepositoryFile]:
        """Get all files of a specific language"""
        if not self.repository_enabled:
            return []
        
        return [
            repo_file for repo_file in self.repository_data.values()
            if repo_file.language == language
        ]
    
    def get_high_confidence_files(self, min_confidence: float = 0.7) -> List[RepositoryFile]:
        """Get files with high confidence analysis"""
        if not self.repository_enabled:
            return []
        
        return [
            repo_file for repo_file in self.repository_data.values()
            if repo_file.confidence_score >= min_confidence
        ]
    
    def find_related_files(self, file_path: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Find files related to the specified file"""
        if not self.repository_enabled:
            return []
        
        related_files = []
        
        # Direct dependencies
        dependencies = self.dependency_graph.get(file_path, [])
        for dep in dependencies:
            if dep in self.repository_data:
                related_files.append({
                    'file_path': dep,
                    'relationship': 'dependency',
                    'confidence': self.repository_data[dep].confidence_score
                })
        
        # Files that depend on this file
        dependents = self.get_dependent_files(file_path)
        for dependent in dependents:
            if dependent in self.repository_data:
                related_files.append({
                    'file_path': dependent,
                    'relationship': 'dependent',
                    'confidence': self.repository_data[dependent].confidence_score
                })
        
        # Sort by confidence and limit results
        related_files.sort(key=lambda x: x['confidence'], reverse=True)
        return related_files[:max_results]
    
    def cleanup_stale_repository_data(self, days: int = 7):
        """Remove repository data for files that no longer exist or are stale"""
        if not self.repository_enabled:
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        files_to_remove = []
        
        for file_path, repo_file in self.repository_data.items():
            # Check if file still exists
            if not Path(file_path).exists():
                files_to_remove.append(file_path)
                continue
            
            # Check if analysis is stale
            try:
                analyzed_date = datetime.fromisoformat(repo_file.last_analyzed)
                if analyzed_date < cutoff_date:
                    files_to_remove.append(file_path)
            except ValueError:
                # Invalid date format, remove the entry
                files_to_remove.append(file_path)
        
        # Remove stale entries
        for file_path in files_to_remove:
            del self.repository_data[file_path]
            
            # Also remove from dependency graph
            if file_path in self.dependency_graph:
                del self.dependency_graph[file_path]
        
        if files_to_remove:
            self._save_repository_data()
            err_console.print(f"Cleaned up {len(files_to_remove)} stale repository entries")
    
    def export_repository_data(self, export_path: str, format: str = "json"):
        """Export repository data to external file"""
        if not self.repository_enabled:
            return False
        
        export_file = Path(export_path)
        
        try:
            if format.lower() == "json":
                data = {
                    'export_date': datetime.now().isoformat(),
                    'total_files': len(self.repository_data),
                    'repository_files': {
                        path: repo_file.to_dict()
                        for path, repo_file in self.repository_data.items()
                    },
                    'dependency_graph': self.dependency_graph,
                    'statistics': self.get_repository_summary()
                }
                
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            return True
            
        except Exception as e:
            err_console.print(f"Error exporting repository data: {e}")
            return False
    
    def get_enhanced_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics including repository data"""
        # Get base memory stats
        base_stats = super().get_memory_stats()
        
        # Add repository stats if enabled
        if self.repository_enabled:
            repo_summary = self.get_repository_summary()
            base_stats.update({
                'repository_enabled': True,
                'repository_files': repo_summary['total_files'],
                'repository_languages': repo_summary['languages'],
                'repository_avg_confidence': repo_summary['avg_confidence'],
                'repository_dependencies': repo_summary['dependency_connections'],
                'repository_last_updated': repo_summary['last_updated']
            })
        else:
            base_stats['repository_enabled'] = False
        
        return base_stats