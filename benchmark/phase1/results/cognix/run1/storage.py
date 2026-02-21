#!/usr/bin/env python3
"""
Task Manager CLI - Storage module.
JSON file-based persistence for all entities.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from models import User, Task, Project, EventLog, Comment, RecurringRule, TaskDependency

DATA_DIR = Path("data")
USERS_FILE = DATA_DIR / "users.json"
PROJECTS_FILE = DATA_DIR / "projects.json"
TASKS_FILE = DATA_DIR / "tasks.json"
EVENTS_FILE = DATA_DIR / "events.json"
COMMENTS_FILE = DATA_DIR / "comments.json"
RECURRING_FILE = DATA_DIR / "recurring.json"
DEPENDENCIES_FILE = DATA_DIR / "dependencies.json"

def ensure_data_dir():
    """Create data directory if it doesn't exist."""
    DATA_DIR.mkdir(exist_ok=True)

def _load_json(filepath: Path) -> list:
    """Load a JSON array from file."""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_json(filepath: Path, data: list):
    """Save a JSON array to file."""
    ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---- Users ----

def load_users() -> List[User]:
    raw = _load_json(USERS_FILE)
    return [User(**r) for r in raw]

def save_users(users: List[User]):
    _save_json(USERS_FILE, [u.to_dict() for u in users])

def get_user_by_id(user_id: int) -> Optional[User]:
    for u in load_users():
        if u.id == user_id:
            return u
    return None

def get_next_user_id() -> int:
    users = load_users()
    return max((u.id for u in users), default=0) + 1

# ---- Projects ----

def load_projects() -> List[Project]:
    raw = _load_json(PROJECTS_FILE)
    return [Project(**r) for r in raw]

def save_projects(projects: List[Project]):
    _save_json(PROJECTS_FILE, [p.to_dict() for p in projects])

def get_project_by_id(project_id: int) -> Optional[Project]:
    for p in load_projects():
        if p.id == project_id:
            return p
    return None

def get_next_project_id() -> int:
    projects = load_projects()
    return max((p.id for p in projects), default=0) + 1

# ---- Tasks ----

def load_tasks() -> List[Task]:
    raw = _load_json(TASKS_FILE)
    return [Task(**r) for r in raw]

def save_tasks(tasks: List[Task]):
    _save_json(TASKS_FILE, [t.to_dict() for t in tasks])

def get_task_by_id(task_id: int) -> Optional[Task]:
    for t in load_tasks():
        if t.id == task_id:
            return t
    return None

def get_tasks_by_project(project_id: int) -> List[Task]:
    return [t for t in load_tasks() if t.project_id == project_id]

def get_tasks_by_assignee(user_id: int) -> List[Task]:
    return [t for t in load_tasks() if t.assignee_id == user_id]

def get_next_task_id() -> int:
    tasks = load_tasks()
    return max((t.id for t in tasks), default=0) + 1

# ---- Events ----

def load_events() -> List[EventLog]:
    raw = _load_json(EVENTS_FILE)
    return [EventLog(**r) for r in raw]

def save_events(events: List[EventLog]):
    _save_json(EVENTS_FILE, [e.to_dict() for e in events])

def add_event(event_type: str, entity_type: str, entity_id: int,
              user_id: int, details: Dict[str, Any] = None):
    """Append a single event to the log."""
    events = load_events()
    new_id = max((e.id for e in events), default=0) + 1
    event = EventLog(
        id=new_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        details=details or {},
    )
    events.append(event)
    save_events(events)
    return event

def get_events_for_entity(entity_type: str, entity_id: int) -> List[EventLog]:
    return [e for e in load_events()
            if e.entity_type == entity_type and e.entity_id == entity_id]

# ---- Comments ----

def load_comments() -> List[Comment]:
    raw = _load_json(COMMENTS_FILE)
    return [Comment(**r) for r in raw]

def save_comments(comments: List[Comment]):
    _save_json(COMMENTS_FILE, [c.to_dict() for c in comments])

def get_comments_for_task(task_id: int) -> List[Comment]:
    return [c for c in load_comments() if c.task_id == task_id]

def get_next_comment_id() -> int:
    comments = load_comments()
    return max((c.id for c in comments), default=0) + 1

# ---- Recurring Rules ----

def load_recurring_rules() -> List[RecurringRule]:
    raw = _load_json(RECURRING_FILE)
    return [RecurringRule(**r) for r in raw]

def save_recurring_rules(rules: List[RecurringRule]):
    _save_json(RECURRING_FILE, [r.to_dict() for r in rules])

def get_recurring_rule_by_id(rule_id: int) -> Optional[RecurringRule]:
    for rule in load_recurring_rules():
        if rule.id == rule_id:
            return rule
    return None

def get_next_recurring_id() -> int:
    rules = load_recurring_rules()
    return max((r.id for r in rules), default=0) + 1

# ---- Dependencies ----

def load_dependencies() -> List[TaskDependency]:
    raw = _load_json(DEPENDENCIES_FILE)
    return [TaskDependency(**r) for r in raw]

def save_dependencies(dependencies: List[TaskDependency]):
    _save_json(DEPENDENCIES_FILE, [d.to_dict() for d in dependencies])

def get_dependencies_for_task(task_id: int) -> List[TaskDependency]:
    """Get all dependencies where task_id depends on others"""
    dependencies = load_dependencies()
    return [dep for dep in dependencies if dep.task_id == task_id]

def get_dependents_of_task(task_id: int) -> List[TaskDependency]:
    """Get all dependencies where others depend on task_id"""
    dependencies = load_dependencies()
    return [dep for dep in dependencies if dep.depends_on_id == task_id]

def get_next_dependency_id() -> int:
    dependencies = load_dependencies()
    return max((d.id for d in dependencies), default=0) + 1