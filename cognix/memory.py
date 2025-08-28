"""
Memory System for Cognix
Handles storing and retrieving conversation history and file context
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class MemoryEntry:
    """Represents a single memory entry"""
    id: str
    timestamp: str
    user_prompt: str
    claude_reply: str
    model_used: str
    file_path: Optional[str] = None
    file_before: Optional[str] = None
    file_after: Optional[str] = None
    interaction_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Memory:
    """Memory management system"""
    
    def __init__(self, memory_dir: str = None):
        """Initialize memory system"""
        if memory_dir is None:
            memory_dir = os.path.expanduser("~/.cognix/memory")
        
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory_file = self.memory_dir / "memory.json"
        self.entries: List[MemoryEntry] = []
        
        self.load_memory()
    
    def _generate_id(self) -> str:
        """Generate unique ID for memory entry"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
    
    def _generate_interaction_hash(self, prompt: str, file_path: str = None) -> str:
        """Generate hash for interaction tracking"""
        content = f"{prompt}_{file_path or ''}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
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
        """Add new memory entry"""
        entry = MemoryEntry(
            id=self._generate_id(),
            timestamp=datetime.now().isoformat(),
            user_prompt=user_prompt,
            claude_reply=claude_reply,
            model_used=model_used,
            file_path=file_path,
            file_before=file_before,
            file_after=file_after,
            interaction_hash=self._generate_interaction_hash(user_prompt, file_path),
            metadata=metadata or {}
        )
        
        self.entries.append(entry)
        self.save_memory()
        return entry.id
    
    def get_entries(self, limit: int = None) -> List[MemoryEntry]:
        """Get memory entries, optionally limited"""
        entries = sorted(self.entries, key=lambda x: x.timestamp, reverse=True)
        if limit:
            entries = entries[:limit]
        return entries
    
    def get_entry_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get specific memory entry by ID"""
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None
    
    def get_entries_for_file(self, file_path: str) -> List[MemoryEntry]:
        """Get all memory entries related to a specific file"""
        return [
            entry for entry in self.entries
            if entry.file_path == file_path
        ]
    
    def search_entries(self, query: str) -> List[MemoryEntry]:
        """Search memory entries by content"""
        query_lower = query.lower()
        results = []
        
        for entry in self.entries:
            if (query_lower in entry.user_prompt.lower() or
                query_lower in entry.claude_reply.lower() or
                (entry.file_path and query_lower in entry.file_path.lower())):
                results.append(entry)
        
        return sorted(results, key=lambda x: x.timestamp, reverse=True)
    
    def get_conversation_context(self, limit: int = 5) -> List[Dict[str, str]]:
        """Get recent conversation context for LLM"""
        recent_entries = self.get_entries(limit=limit)
        context = []
        
        for entry in reversed(recent_entries):
            context.append({
                "role": "user",
                "content": entry.user_prompt
            })
            context.append({
                "role": "assistant", 
                "content": entry.claude_reply
            })
        
        return context
    
    def clear_memory(self):
        """Clear all memory entries"""
        self.entries = []
        self.save_memory()
    
    def cleanup_old_entries(self, days: int = 30):
        """Remove entries older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        self.entries = [
            entry for entry in self.entries
            if datetime.fromisoformat(entry.timestamp) > cutoff_date
        ]
        
        self.save_memory()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        total_entries = len(self.entries)
        unique_files = len(set(
            entry.file_path for entry in self.entries
            if entry.file_path
        ))
        
        models_used = {}
        for entry in self.entries:
            models_used[entry.model_used] = models_used.get(entry.model_used, 0) + 1
        
        oldest_entry = None
        newest_entry = None
        if self.entries:
            sorted_entries = sorted(self.entries, key=lambda x: x.timestamp)
            oldest_entry = sorted_entries[0].timestamp
            newest_entry = sorted_entries[-1].timestamp
        
        return {
            "total_entries": total_entries,
            "unique_files": unique_files,
            "models_used": models_used,
            "oldest_entry": oldest_entry,
            "newest_entry": newest_entry,
            "memory_file_size": self.memory_file.stat().st_size if self.memory_file.exists() else 0
        }
    
    def save_memory(self):
        """Save memory entries to file"""
        try:
            data = {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "entries": [asdict(entry) for entry in self.entries]
            }
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Warning: Failed to save memory: {e}")
    
    def load_memory(self):
        """Load memory entries from file"""
        try:
            if not self.memory_file.exists():
                return
            
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.entries = []
            for entry_data in data.get("entries", []):
                entry = MemoryEntry(**entry_data)
                self.entries.append(entry)
                
        except Exception as e:
            print(f"Warning: Failed to load memory: {e}")
            self.entries = []
    
    def export_memory(self, export_path: str, format: str = "json"):
        """Export memory to different formats"""
        export_file = Path(export_path)
        
        if format.lower() == "json":
            data = {
                "export_date": datetime.now().isoformat(),
                "total_entries": len(self.entries),
                "entries": [asdict(entry) for entry in self.entries]
            }
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif format.lower() == "txt":
            with open(export_file, 'w', encoding='utf-8') as f:
                f.write(f"Cognix Memory Export\n")
                f.write(f"Export Date: {datetime.now().isoformat()}\n")
                f.write(f"Total Entries: {len(self.entries)}\n")
                f.write("=" * 50 + "\n\n")
                
                for entry in sorted(self.entries, key=lambda x: x.timestamp):
                    f.write(f"Entry ID: {entry.id}\n")
                    f.write(f"Timestamp: {entry.timestamp}\n")
                    f.write(f"Model: {entry.model_used}\n")
                    if entry.file_path:
                        f.write(f"File: {entry.file_path}\n")
                    f.write(f"User: {entry.user_prompt}\n")
                    f.write(f"Claude: {entry.claude_reply}\n")
                    f.write("-" * 30 + "\n\n")
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def import_memory(self, import_path: str):
        """Import memory from file"""
        import_file = Path(import_path)
        
        if not import_file.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")
        
        with open(import_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imported_entries = []
        for entry_data in data.get("entries", []):
            entry = MemoryEntry(**entry_data)
            imported_entries.append(entry)
        
        # Merge with existing entries, avoiding duplicates
        existing_hashes = {entry.interaction_hash for entry in self.entries}
        
        for entry in imported_entries:
            if entry.interaction_hash not in existing_hashes:
                self.entries.append(entry)
        
        self.save_memory()
        return len(imported_entries)