#!/usr/bin/env python3
"""
Task Manager CLI - Validators module.
Input validation for all entities.
"""

import re
from datetime import datetime
from typing import Optional, Tuple, List
from models import TaskStatus, TaskPriority


def validate_title(title: str) -> Tuple[bool, str]:
    """Validate a task/project title."""
    if not title or not title.strip():
        return False, "Title cannot be empty"
    if len(title) > 200:
        return False, "Title must be 200 characters or less"
    if len(title.strip()) < 2:
        return False, "Title must be at least 2 characters"
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate an email address."""
    if not email:
        return False, "Email cannot be empty"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate a username."""
    if not username or not username.strip():
        return False, "Username cannot be empty"
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 50:
        return False, "Username must be 50 characters or less"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    return True, ""


def validate_status(status: str) -> Tuple[bool, str]:
    """Validate a task status."""
    valid_statuses = [s.value for s in TaskStatus]
    if status not in valid_statuses:
        return False, f"Invalid status '{status}'. Valid: {', '.join(valid_statuses)}"
    return True, ""


def validate_priority(priority: str) -> Tuple[bool, str]:
    """Validate a task priority."""
    valid_priorities = [p.value for p in TaskPriority]
    if priority not in valid_priorities:
        return False, f"Invalid priority '{priority}'. Valid: {', '.join(valid_priorities)}"
    return True, ""


def validate_date(date_str: str) -> Tuple[bool, str]:
    """Validate a date string (ISO format or YYYY-MM-DD)."""
    if not date_str:
        return True, ""  # Optional field
    try:
        datetime.fromisoformat(date_str)
        return True, ""
    except ValueError:
        pass
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, f"Invalid date format '{date_str}'. Use YYYY-MM-DD or ISO format"


def validate_role(role: str) -> Tuple[bool, str]:
    """Validate a user role."""
    valid_roles = ["admin", "member", "viewer"]
    if role not in valid_roles:
        return False, f"Invalid role '{role}'. Valid: {', '.join(valid_roles)}"
    return True, ""


def validate_tags(tags: List[str]) -> Tuple[bool, str]:
    """Validate a list of tags."""
    for tag in tags:
        if not tag.strip():
            return False, "Tags cannot be empty strings"
        if len(tag) > 50:
            return False, f"Tag '{tag}' exceeds 50 character limit"
        if not re.match(r'^[a-zA-Z0-9_-]+$', tag):
            return False, f"Tag '{tag}' contains invalid characters"
    if len(tags) > 10:
        return False, "Maximum 10 tags per task"
    return True, ""


def validate_task_create(title: str, project_id: int, status: str = "todo",
                         priority: str = "medium", due_date: str = "",
                         tags: List[str] = None) -> Tuple[bool, List[str]]:
    """Full validation for task creation. Returns (valid, error_list)."""
    errors = []

    ok, msg = validate_title(title)
    if not ok:
        errors.append(f"title: {msg}")

    if project_id <= 0:
        errors.append("project_id: Must be a positive integer")

    ok, msg = validate_status(status)
    if not ok:
        errors.append(f"status: {msg}")

    ok, msg = validate_priority(priority)
    if not ok:
        errors.append(f"priority: {msg}")

    if due_date:
        ok, msg = validate_date(due_date)
        if not ok:
            errors.append(f"due_date: {msg}")

    if tags:
        ok, msg = validate_tags(tags)
        if not ok:
            errors.append(f"tags: {msg}")

    return len(errors) == 0, errors
