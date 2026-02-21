#!/usr/bin/env python3
"""
Task Manager CLI - Models module.
Core data classes for User, Project, Task, EventLog, RecurringRule, and TaskDependency.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EventType(Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_STATUS_CHANGED = "task_status_changed"
    PROJECT_CREATED = "project_created"
    PROJECT_DELETED = "project_deleted"
    USER_CREATED = "user_created"
    COMMENT_ADDED = "comment_added"

@dataclass
class User:
    id: int
    username: str
    email: str
    role: str = "member"  # "admin", "member", "viewer"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def can_edit(self) -> bool:
        return self.role in ("admin", "member")

    def can_delete(self) -> bool:
        return self.role == "admin"

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class Task:
    id: int
    title: str
    project_id: int
    assignee_id: Optional[int] = None
    status: str = "todo"
    priority: str = "medium"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    due_date: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def is_overdue(self) -> bool:
        if not self.due_date or self.status == "done":
            return False
        try:
            due = datetime.fromisoformat(self.due_date)
            return datetime.now() > due
        except ValueError:
            return False

    def mark_done(self):
        self.status = "done"
        self.completed_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def update_status(self, new_status: str):
        valid = [s.value for s in TaskStatus]
        if new_status not in valid:
            raise ValueError(f"Invalid status '{new_status}'. Valid: {valid}")
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now().isoformat()
        if new_status == "done":
            self.completed_at = datetime.now().isoformat()
        return old_status

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class Project:
    id: int
    name: str
    owner_id: int
    description: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class EventLog:
    id: int
    event_type: str
    entity_type: str  # "task", "project", "user"
    entity_id: int
    user_id: int
    timestamp: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class Comment:
    id: int
    task_id: int
    user_id: int
    text: str
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class RecurringRule:
    id: int
    task_template_id: int
    frequency: str  # "daily", "weekly", "biweekly", "monthly"
    next_run: str  # ISO date
    end_date: Optional[str] = None
    created_count: int = 0
    active: bool = True
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    def should_run(self) -> bool:
        """Check if rule should create a task now"""
        if not self.active:
            return False

        now = datetime.now().date()
        try:
            next_run_date = datetime.fromisoformat(self.next_run).date()
        except ValueError:
            return False

        if next_run_date > now:
            return False

        if self.end_date:
            try:
                end_date_obj = datetime.fromisoformat(self.end_date).date()
                if now > end_date_obj:
                    return False
            except ValueError:
                pass

        return True

    def advance(self) -> None:
        """Move next_run forward based on frequency"""
        try:
            current = datetime.fromisoformat(self.next_run)
        except ValueError:
            current = datetime.now()

        if self.frequency == "daily":
            current += timedelta(days=1)
        elif self.frequency == "weekly":
            current += timedelta(weeks=1)
        elif self.frequency == "biweekly":
            current += timedelta(weeks=2)
        elif self.frequency == "monthly":
            # Handle month-end edge cases
            month = current.month + 1
            year = current.year
            if month > 12:
                month = 1
                year += 1
            # Use min to handle Feb 28/29, etc.
            day = min(current.day, self._days_in_month(year, month))
            current = current.replace(year=year, month=month, day=day)

        self.next_run = current.isoformat()
        self.created_count += 1

    @staticmethod
    def _days_in_month(year: int, month: int) -> int:
        """Helper to get days in a month"""
        if month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif month in [4, 6, 9, 11]:
            return 30
        else:  # February
            return 29 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 28

@dataclass
class TaskDependency:
    id: int
    task_id: int  # blocked task
    depends_on_id: int  # blocking task
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)