#!/usr/bin/env python3
"""
Task Manager CLI - Formatters module.
Display formatting for tasks, projects, and summaries.
"""

from typing import List, Optional, Dict, Any
from models import Task, Project, User, EventLog, Comment


# Status display icons
STATUS_ICONS = {
    "todo": "○",
    "in_progress": "◐",
    "blocked": "✖",
    "done": "●",
    "cancelled": "⊘",
}

# Priority display markers
PRIORITY_MARKERS = {
    "critical": "!!!",
    "high": "!!",
    "medium": "!",
    "low": "",
}


def format_task_line(task: Task, show_project: bool = False) -> str:
    """Format a single task as a one-line summary."""
    icon = STATUS_ICONS.get(task.status, "?")
    marker = PRIORITY_MARKERS.get(task.priority, "")
    assignee = f" @{task.assignee_id}" if task.assignee_id else ""
    project = f" [P{task.project_id}]" if show_project else ""
    overdue = " OVERDUE" if task.is_overdue() else ""
    due = f" due:{task.due_date}" if task.due_date else ""
    tags = f" #{' #'.join(task.tags)}" if task.tags else ""
    return f"{icon} #{task.id} {marker} {task.title}{project}{assignee}{due}{overdue}{tags}"


def format_task_detail(task: Task, comments: Optional[List[Comment]] = None,
                       events: Optional[List[EventLog]] = None) -> str:
    """Format a detailed view of a single task."""
    lines = [
        f"Task #{task.id}: {task.title}",
        f"  Status:      {task.status}",
        f"  Priority:    {task.priority}",
        f"  Project:     {task.project_id}",
        f"  Assignee:    {task.assignee_id or 'unassigned'}",
        f"  Description: {task.description or '(none)'}",
        f"  Tags:        {', '.join(task.tags) if task.tags else '(none)'}",
        f"  Due Date:    {task.due_date or '(none)'}",
        f"  Created:     {task.created_at}",
        f"  Updated:     {task.updated_at}",
    ]
    if task.completed_at:
        lines.append(f"  Completed:   {task.completed_at}")
    if task.is_overdue():
        lines.append("  ⚠ OVERDUE")

    if comments:
        lines.append("")
        lines.append(f"  Comments ({len(comments)}):")
        for c in comments:
            lines.append(f"    [{c.created_at[:10]}] User {c.user_id}: {c.text}")

    if events:
        lines.append("")
        lines.append(f"  History ({len(events)}):")
        for e in events[-5:]:  # Last 5 events
            lines.append(f"    [{e.timestamp[:19]}] {e.event_type}: {e.details}")

    return "\n".join(lines)


def format_task_table(tasks: List[Task]) -> str:
    """Format tasks as an ASCII table."""
    if not tasks:
        return "(no tasks)"

    header = f"{'ID':>5} {'Status':<12} {'Pri':<8} {'Title':<30} {'Assignee':<10} {'Due':<12}"
    separator = "-" * len(header)
    lines = [header, separator]

    for t in tasks:
        assignee = str(t.assignee_id) if t.assignee_id else "-"
        due = t.due_date[:10] if t.due_date else "-"
        title = t.title[:28] + ".." if len(t.title) > 30 else t.title
        lines.append(
            f"{t.id:>5} {t.status:<12} {t.priority:<8} {title:<30} {assignee:<10} {due:<12}"
        )

    lines.append(separator)
    lines.append(f"Total: {len(tasks)} tasks")
    return "\n".join(lines)


def format_project_line(project: Project, task_count: int = 0) -> str:
    """Format a project as a one-line summary."""
    return f"[P{project.id}] {project.name} (owner: {project.owner_id}, tasks: {task_count})"


def format_project_detail(project: Project, tasks: List[Task]) -> str:
    """Format detailed project view with task breakdown."""
    by_status = {}
    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1

    lines = [
        f"Project #{project.id}: {project.name}",
        f"  Owner:       {project.owner_id}",
        f"  Description: {project.description or '(none)'}",
        f"  Created:     {project.created_at}",
        f"  Tasks:       {len(tasks)}",
    ]
    if by_status:
        lines.append("  Breakdown:")
        for status, count in sorted(by_status.items()):
            icon = STATUS_ICONS.get(status, "?")
            lines.append(f"    {icon} {status}: {count}")

    return "\n".join(lines)


def format_summary(summary: dict) -> str:
    """Format the summary statistics dict."""
    if summary.get("total", 0) == 0:
        return "No tasks found."

    lines = [
        f"Total Tasks: {summary['total']}",
        "",
        "By Status:",
    ]
    for status, count in sorted(summary.get("by_status", {}).items()):
        icon = STATUS_ICONS.get(status, "?")
        lines.append(f"  {icon} {status}: {count}")

    lines.append("")
    lines.append("By Priority:")
    for priority, count in sorted(summary.get("by_priority", {}).items()):
        lines.append(f"  {PRIORITY_MARKERS.get(priority, '')} {priority}: {count}")

    if summary.get("overdue", 0) > 0:
        lines.append(f"\n⚠ Overdue: {summary['overdue']}")

    return "\n".join(lines)


def format_event_line(event: EventLog) -> str:
    """Format a single event log entry."""
    ts = event.timestamp[:19] if event.timestamp else "?"
    details_str = ""
    if event.details:
        details_str = " | " + ", ".join(f"{k}={v}" for k, v in event.details.items())
    return f"[{ts}] {event.event_type} on {event.entity_type}#{event.entity_id} by user {event.user_id}{details_str}"


def format_user_line(user: User) -> str:
    """Format a user as a one-line summary."""
    return f"User #{user.id}: {user.username} ({user.email}) role={user.role}"
