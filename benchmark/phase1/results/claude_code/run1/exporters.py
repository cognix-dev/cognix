#!/usr/bin/env python3
"""
Task Manager CLI - Exporters module.
Export tasks to various formats.
"""

import csv
import json
import io
from datetime import datetime
from typing import List
from models import Task


def export_to_csv(tasks: List[Task], filepath: str) -> int:
    """Export tasks to CSV file. Returns number of rows written."""
    if not tasks:
        return 0
    fieldnames = [
        "id", "title", "project_id", "assignee_id", "status",
        "priority", "description", "tags", "due_date",
        "created_at", "updated_at", "completed_at",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in tasks:
            row = t.to_dict()
            row["tags"] = ";".join(row.get("tags", []))
            writer.writerow(row)
    return len(tasks)


def export_to_json(tasks: List[Task], filepath: str) -> int:
    """Export tasks to JSON file. Returns number of records written."""
    if not tasks:
        return 0
    data = {
        "exported_at": datetime.now().isoformat(),
        "count": len(tasks),
        "tasks": [t.to_dict() for t in tasks],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return len(tasks)


def export_to_markdown(tasks: List[Task], filepath: str) -> int:
    """Export tasks as a Markdown table. Returns number of rows written."""
    if not tasks:
        return 0
    lines = [
        "# Task Export",
        "",
        f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "| ID | Title | Status | Priority | Assignee | Due Date |",
        "|-----|-------|--------|----------|----------|----------|",
    ]
    for t in tasks:
        due = t.due_date or "-"
        assignee = str(t.assignee_id) if t.assignee_id else "-"
        lines.append(
            f"| {t.id} | {t.title} | {t.status} | {t.priority} "
            f"| {assignee} | {due} |"
        )
    lines.append("")
    lines.append(f"**Total: {len(tasks)} tasks**")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return len(tasks)


def generate_summary(tasks: List[Task]) -> dict:
    """Generate summary statistics for a set of tasks."""
    if not tasks:
        return {"total": 0}

    by_status = {}
    by_priority = {}
    by_assignee = {}
    overdue_count = 0

    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1
        by_priority[t.priority] = by_priority.get(t.priority, 0) + 1
        aid = t.assignee_id or "unassigned"
        by_assignee[aid] = by_assignee.get(aid, 0) + 1
        if t.is_overdue():
            overdue_count += 1

    return {
        "total": len(tasks),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_assignee": by_assignee,
        "overdue": overdue_count,
    }
