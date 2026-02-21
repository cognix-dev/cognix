#!/usr/bin/env python3
"""
Task Manager CLI - Filters module.
Advanced filtering and search for tasks.
"""

from datetime import datetime, timedelta
from typing import List
from models import Task

def filter_by_status(tasks: List[Task], status: str) -> List[Task]:
    """Filter tasks by status."""
    return [t for t in tasks if t.status == status]

def filter_by_priority(tasks: List[Task], priority: str) -> List[Task]:
    """Filter tasks by priority."""
    return [t for t in tasks if t.priority == priority]

def filter_by_tag(tasks: List[Task], tag: str) -> List[Task]:
    """Filter tasks that have a specific tag."""
    return [t for t in tasks if tag in t.tags]

def filter_by_assignee(tasks: List[Task], assignee_id: int) -> List[Task]:
    """Filter tasks assigned to a specific user."""
    return [t for t in tasks if t.assignee_id == assignee_id]

def filter_by_project(tasks: List[Task], project_id: int) -> List[Task]:
    """Filter tasks belonging to a specific project."""
    return [t for t in tasks if t.project_id == project_id]

def filter_overdue(tasks: List[Task]) -> List[Task]:
    """Return tasks that are past their due date and not done."""
    return [t for t in tasks if t.is_overdue()]

def filter_due_within(tasks: List[Task], days: int) -> List[Task]:
    """Return tasks due within the next N days."""
    now = datetime.now()
    cutoff = now + timedelta(days=days)
    result = []
    for t in tasks:
        if not t.due_date or t.status == "done":
            continue
        try:
            due = datetime.fromisoformat(t.due_date)
            if now <= due <= cutoff:
                result.append(t)
        except ValueError:
            continue
    return result

def filter_completed_between(tasks: List[Task], start: str, end: str) -> List[Task]:
    """Return tasks completed within a date range (ISO format strings)."""
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        return []
    result = []
    for t in tasks:
        if t.status != "done" or not t.completed_at:
            continue
        try:
            completed = datetime.fromisoformat(t.completed_at)
            if start_dt <= completed <= end_dt:
                result.append(t)
        except ValueError:
            continue
    return result

def search_tasks(tasks: List[Task], query: str) -> List[Task]:
    """Search tasks by title and description (case-insensitive)."""
    query_lower = query.lower()
    return [
        t for t in tasks
        if query_lower in t.title.lower() or query_lower in t.description.lower()
    ]

def sort_tasks(tasks: List[Task], sort_by: str = "created_at",
               reverse: bool = False) -> List[Task]:
    """Sort tasks by a field."""
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_order = {"todo": 0, "in_progress": 1, "blocked": 2, "done": 3, "cancelled": 4}

    if sort_by == "priority":
        key_fn = lambda t: priority_order.get(t.priority, 99)
    elif sort_by == "status":
        key_fn = lambda t: status_order.get(t.status, 99)
    elif sort_by == "due_date":
        key_fn = lambda t: t.due_date or "9999-12-31"
    elif sort_by == "title":
        key_fn = lambda t: t.title.lower()
    else:
        key_fn = lambda t: getattr(t, sort_by, "")

    return sorted(tasks, key=key_fn, reverse=reverse)

def apply_filters(tasks: List[Task], filters: dict) -> List[Task]:
    """Apply multiple filters from a dict.

    Supported keys:
        status, priority, tag, assignee_id, project_id,
        overdue (bool), due_within_days (int),
        search (str), sort_by (str), sort_reverse (bool)
    """
    result = list(tasks)

    if "status" in filters:
        result = filter_by_status(result, filters["status"])
    if "priority" in filters:
        result = filter_by_priority(result, filters["priority"])
    if "tag" in filters:
        result = filter_by_tag(result, filters["tag"])
    if "assignee_id" in filters:
        result = filter_by_assignee(result, int(filters["assignee_id"]))
    if "project_id" in filters:
        result = filter_by_project(result, int(filters["project_id"]))
    if filters.get("overdue"):
        result = filter_overdue(result)
    if "due_within_days" in filters:
        result = filter_due_within(result, int(filters["due_within_days"]))
    if "search" in filters:
        result = search_tasks(result, filters["search"])

    sort_by = filters.get("sort_by", "created_at")
    sort_reverse = filters.get("sort_reverse", False)
    result = sort_tasks(result, sort_by, sort_reverse)

    return result