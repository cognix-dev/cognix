"""
Session Manager for Cognix
Handles session save/restore functionality
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import shutil


@dataclass
class SessionEntry:
    """Single session entry (user input and AI response)"""
    timestamp: str
    user_input: str
    ai_response: str
    model_used: str
    command_type: Optional[str] = None  # edit, review, chat, etc.
    target_files: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SessionData:
    """Complete session data"""
    session_id: str
    created_at: str
    last_updated: str
    current_model: str
    current_directory: str
    entries: List[SessionEntry]
    total_entries: int = 0
    metadata: Optional[Dict[str, Any]] = None
    workflow_state: Optional[Dict[str, Any]] = None  # ← 追加

    def __post_init__(self):
        self.total_entries = len(self.entries)

class SessionManager:
    """Manager for session save/restore operations"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize session manager"""
        if base_dir is None:
            base_dir = Path.home() / ".cognix"
        
        self.base_dir = Path(base_dir)
        self.sessions_dir = self.base_dir / "sessions"
        self.autosave_path = self.sessions_dir / "autosave.json"
        
        # Create directories if they don't exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session = None
        self._init_current_session()
    
    def _init_current_session(self):
        """Initialize current session"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        current_time = datetime.now().isoformat()
        current_dir = str(Path.cwd())
        
        self.current_session = SessionData(
            session_id=session_id,
            created_at=current_time,
            last_updated=current_time,
            current_model="claude-sonnet-4-20250514",  # Default model
            current_directory=current_dir,
            entries=[],
            metadata={},
            workflow_state=None,  # ← 追加
        )
    
    # session.py の add_entry メソッドを以下に置き換え

    def add_entry(
        self,
        user_input: str,
        ai_response: str,
        model_used: str,
        command_type: Optional[str] = None,
        target_files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_state: Optional[Dict[str, Any]] = None,  # ← 追加パラメータ
    ):
        """Add entry to current session"""
        if self.current_session is None:
            self._init_current_session()
        
        entry = SessionEntry(
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            ai_response=ai_response,
            model_used=model_used,
            command_type=command_type,
            target_files=target_files or [],
            metadata=metadata or {}
        )
        
        self.current_session.entries.append(entry)
        self.current_session.last_updated = datetime.now().isoformat()
        self.current_session.current_model = model_used
        self.current_session.total_entries = len(self.current_session.entries)
        
        # ワークフロー状態を保存（新機能）
        if workflow_state is not None:
            self.current_session.workflow_state = workflow_state
        
        # Auto-save after each entry
        self.autosave()
    
    def autosave(self):
        """Auto-save current session"""
        if self.current_session is None:
            return
        
        try:
            self._save_session_to_file(self.current_session, self.autosave_path)
        except Exception as e:
            print(f"Warning: Failed to autosave session: {e}")
    
    def save_session(self, name: str) -> bool:
        """Save current session with given name"""
        if self.current_session is None:
            return False
        
        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_name:
            return False
        
        session_file = self.sessions_dir / f"{safe_name}.json"
        
        try:
            # Update session metadata
            self.current_session.session_id = safe_name
            self.current_session.last_updated = datetime.now().isoformat()
            
            self._save_session_to_file(self.current_session, session_file)
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def _save_session_to_file(self, session: SessionData, file_path: Path):
        """Save session data to file"""
        session_dict = asdict(session)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(session_dict, f, indent=2, ensure_ascii=False)
    
    def load_session(self, name: str) -> Optional[SessionData]:
        """Load session by name"""
        if name == "autosave":
            session_file = self.autosave_path
        else:
            session_file = self.sessions_dir / f"{name}.json"
        
        return self._load_session_from_file(session_file)
    
    def _load_session_from_file(self, file_path: Path) -> Optional[SessionData]:
        """Load session from file with robust validation"""
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            required_fields = ['session_id', 'created_at', 'last_updated', 'current_model', 'current_directory']
            for field in required_fields:
                if field not in data:
                    print(f"Warning: Session file {file_path} missing required field: {field}")
                    return None
            
            # Validate and convert entries
            entries = []
            for i, entry_data in enumerate(data.get('entries', [])):
                try:
                    # Validate entry structure
                    required_entry_fields = ['timestamp', 'user_input', 'ai_response', 'model_used']
                    for field in required_entry_fields:
                        if field not in entry_data:
                            print(f"Warning: Skipping malformed entry {i} in session {file_path}")
                            continue
                    
                    # Create entry with defaults for optional fields
                    entry = SessionEntry(
                        timestamp=entry_data['timestamp'],
                        user_input=entry_data['user_input'],
                        ai_response=entry_data['ai_response'],
                        model_used=entry_data['model_used'],
                        command_type=entry_data.get('command_type'),
                        target_files=entry_data.get('target_files', []),
                        metadata=entry_data.get('metadata', {})
                    )
                    entries.append(entry)
                    
                except (KeyError, TypeError, ValueError) as e:
                    print(f"Warning: Skipping invalid entry {i} in session {file_path}: {e}")
                    continue
            
            # Validate timestamp format
            try:
                from datetime import datetime
                datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                datetime.fromisoformat(data['last_updated'].replace('Z', '+00:00'))
            except ValueError:
                print(f"Warning: Invalid timestamp format in session {file_path}")
                # Continue with invalid timestamps rather than failing completely
            
            # Create SessionData object with validation
            session_data = SessionData(
                session_id=str(data['session_id']),
                created_at=str(data['created_at']),
                last_updated=str(data['last_updated']),
                current_model=str(data['current_model']),
                current_directory=str(data['current_directory']),
                entries=entries,
                total_entries=data.get('total_entries', len(entries)),
                metadata=data.get('metadata', {}) if isinstance(data.get('metadata'), dict) else {},
                workflow_state=data.get('workflow_state')  # ← 追加
            )
            
            # Final validation
            if len(entries) != session_data.total_entries:
                print(f"Warning: Entry count mismatch in session {file_path}. Expected {session_data.total_entries}, got {len(entries)}")
                session_data.total_entries = len(entries)
            
            return session_data
            
        except json.JSONDecodeError as e:
            print(f"Error: Corrupted session file {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error loading session from {file_path}: {e}")
            return None
    
    def resume_session(self, name: str) -> bool:
        """Resume session by name"""
        session = self.load_session(name)
        if session is None:
            return False
        
        self.current_session = session
        self.current_session.last_updated = datetime.now().isoformat()
        
        # Auto-save after resuming
        self.autosave()
        return True
    
    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all available sessions"""
        sessions = {}
        
        # Check autosave
        if self.autosave_path.exists():
            session = self._load_session_from_file(self.autosave_path)
            if session:
                sessions["autosave"] = {
                    "name": "autosave",
                    "created_at": session.created_at,
                    "last_updated": session.last_updated,
                    "entries": session.total_entries,
                    "model": session.current_model,
                    "directory": session.current_directory
                }
        
        # Check saved sessions
        for session_file in self.sessions_dir.glob("*.json"):
            if session_file.name == "autosave.json":
                continue
                
            session = self._load_session_from_file(session_file)
            if session:
                name = session_file.stem
                sessions[name] = {
                    "name": name,
                    "created_at": session.created_at,
                    "last_updated": session.last_updated,
                    "entries": session.total_entries,
                    "model": session.current_model,
                    "directory": session.current_directory
                }
        
        return sessions
    
    def delete_session(self, name: str) -> bool:
        """Delete session by name"""
        if name == "autosave":
            session_file = self.autosave_path
        else:
            session_file = self.sessions_dir / f"{name}.json"
        
        try:
            if session_file.exists():
                session_file.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def has_autosave(self) -> bool:
        """Check if autosave exists"""
        return self.autosave_path.exists()
    
    def get_autosave_info(self) -> Optional[Dict[str, Any]]:
        """Get autosave session info"""
        if not self.has_autosave():
            return None
        
        session = self._load_session_from_file(self.autosave_path)
        if session is None:
            return None
        
        return {
            "created_at": session.created_at,
            "last_updated": session.last_updated,
            "entries": session.total_entries,
            "model": session.current_model,
            "directory": session.current_directory
        }
    
    def clear_current_session(self):
        """Clear current session and start fresh"""
        self._init_current_session()
        
        # Remove autosave
        if self.autosave_path.exists():
            try:
                self.autosave_path.unlink()
            except Exception as e:
                print(f"Warning: Failed to remove autosave: {e}")
    
    def export_session(self, name: str, export_path: str, format: str = "json") -> bool:
        """Export session to external file"""
        session = self.load_session(name)
        if session is None:
            return False
        
        export_file = Path(export_path)
        
        try:
            if format.lower() == "json":
                self._save_session_to_file(session, export_file)
            elif format.lower() == "markdown":
                self._export_session_to_markdown(session, export_file)
            else:
                return False
            
            return True
        except Exception as e:
            print(f"Error exporting session: {e}")
            return False
    
    def _export_session_to_markdown(self, session: SessionData, file_path: Path):
        """Export session to markdown format"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Cognix Session: {session.session_id}\n\n")
            f.write(f"**Created:** {session.created_at}\n")
            f.write(f"**Last Updated:** {session.last_updated}\n")
            f.write(f"**Model:** {session.current_model}\n")
            f.write(f"**Directory:** {session.current_directory}\n")
            f.write(f"**Total Entries:** {session.total_entries}\n\n")
            
            for i, entry in enumerate(session.entries, 1):
                f.write(f"## Entry {i} - {entry.timestamp}\n\n")
                
                if entry.command_type:
                    f.write(f"**Command:** {entry.command_type}\n")
                
                if entry.target_files:
                    f.write(f"**Files:** {', '.join(entry.target_files)}\n")
                
                f.write(f"**Model:** {entry.model_used}\n\n")
                
                f.write("### User Input\n")
                f.write(f"```\n{entry.user_input}\n```\n\n")
                
                f.write("### AI Response\n")
                f.write(f"{entry.ai_response}\n\n")
                
                if entry.metadata:
                    f.write("### Metadata\n")
                    f.write(f"```json\n{json.dumps(entry.metadata, indent=2)}\n```\n\n")
                
                f.write("---\n\n")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        if self.current_session is None:
            return {}
        
        stats = {
            "session_id": self.current_session.session_id,
            "created_at": self.current_session.created_at,
            "last_updated": self.current_session.last_updated,
            "total_entries": self.current_session.total_entries,
            "current_model": self.current_session.current_model,
            "current_directory": self.current_session.current_directory
        }
        
        if self.current_session.entries:
            # Calculate additional stats
            models_used = {}
            command_types = {}
            target_files = set()
            
            for entry in self.current_session.entries:
                # Model usage
                models_used[entry.model_used] = models_used.get(entry.model_used, 0) + 1
                
                # Command types
                if entry.command_type:
                    command_types[entry.command_type] = command_types.get(entry.command_type, 0) + 1
                
                # Target files
                if entry.target_files:
                    target_files.update(entry.target_files)
            
            stats.update({
                "models_used": models_used,
                "command_types": command_types,
                "unique_files": len(target_files),
                "files_touched": list(target_files)
            })
        
        return stats