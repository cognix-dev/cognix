#!/usr/bin/env python3
"""
Task Manager CLI - Commands module.
All CLI command handlers.
"""

import sys
import json
from typing import List, Optional
from models import Task, Project, User, Comment, RecurringRule, TaskDependency
from storage import (
    load_tasks, save_tasks, get_task_by_id, get_next_task_id,
    load_projects, save_projects, get_project_by_id, get_next_project_id,
    load_users, save_users, get_user_by_id, get_next_user_id,
    load_comments, save_comments, get_next_comment_id,
    get_tasks_by_project, get_comments_for_task,
    get_events_for_entity, add_event, ensure_data_dir,
    load_recurring_rules, save_recurring_rules, get_recurring_rule_by_id, get_next_recurring_id,
    load_dependencies, save_dependencies, get_dependencies_for_task, get_dependents_of_task, get_next_dependency_id,
)
from filters import apply_filters
from formatters import (
    format_task_line, format_task_detail, format_task_table,
    format_project_line, format_project_detail,
    format_summary, format_user_line,
)
from exporters import export_to_csv, export_to_json, export_to_markdown, generate_summary
from validators import validate_task_create, validate_title, validate_email, validate_username
from plugins import plugin_manager


def cmd_init(**kwargs):
    """Initialize the data directory."""
    ensure_data_dir()
    print("Data directory initialized.")


def cmd_add_user(username: str, email: str, role: str = "member", **kwargs):
    """Add a new user."""
    ok, msg = validate_username(username)
    if not ok:
        print(f"Error: {msg}", file=sys.stderr)
        return False

    ok, msg = validate_email(email)
    if not ok:
        print(f"Error: {msg}", file=sys.stderr)
        return False

    users = load_users()
    if any(u.username == username for u in users):
        print(f"Error: Username '{username}' already exists", file=sys.stderr)
        return False

    user = User(id=get_next_user_id(), username=username, email=email, role=role)
    users.append(user)
    save_users(users)

    add_event("user_created", "user", user.id, user.id, {"username": username})
    print(f"Created user #{user.id}: {username}")
    return True


def cmd_list_users(**kwargs):
    """List all users."""
    users = load_users()
    if not users:
        print("No users found.")
        return
    for u in users:
        print(format_user_line(u))


def cmd_add_project(name: str, owner_id: int, description: str = "", **kwargs):
    """Create a new project."""
    ok, msg = validate_title(name)
    if not ok:
        print(f"Error: {msg}", file=sys.stderr)
        return False

    owner = get_user_by_id(owner_id)
    if not owner:
        print(f"Error: User #{owner_id} not found", file=sys.stderr)
        return False

    projects = load_projects()
    project = Project(
        id=get_next_project_id(), name=name,
        owner_id=owner_id, description=description,
    )
    projects.append(project)
    save_projects(projects)

    add_event("project_created", "project", project.id, owner_id, {"name": name})
    print(f"Created project #{project.id}: {name}")
    return True


def cmd_list_projects(**kwargs):
    """List all projects."""
    projects = load_projects()
    if not projects:
        print("No projects found.")
        return
    for p in projects:
        task_count = len(get_tasks_by_project(p.id))
        print(format_project_line(p, task_count))


def cmd_show_project(project_id: int, **kwargs):
    """Show detailed project info."""
    project = get_project_by_id(project_id)
    if not project:
        print(f"Error: Project #{project_id} not found", file=sys.stderr)
        return False
    tasks = get_tasks_by_project(project_id)
    print(format_project_detail(project, tasks))
    return True


def cmd_add_task(title: str, project_id: int, assignee_id: Optional[int] = None,
                 priority: str = "medium", due_date: str = "",
                 tags: Optional[List[str]] = None, description: str = "", **kwargs):
    """Create a new task."""
    tags = tags or []
    ok, errors = validate_task_create(title, project_id, priority=priority,
                                      due_date=due_date, tags=tags)
    if not ok:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        return False

    project = get_project_by_id(project_id)
    if not project:
        print(f"Error: Project #{project_id} not found", file=sys.stderr)
        return False

    if assignee_id and not get_user_by_id(assignee_id):
        print(f"Error: User #{assignee_id} not found", file=sys.stderr)
        return False

    # Fire pre-create hook
    plugin_manager.fire("task_pre_create", title=title, project_id=project_id)

    tasks = load_tasks()
    task = Task(
        id=get_next_task_id(), title=title, project_id=project_id,
        assignee_id=assignee_id, priority=priority, due_date=due_date,
        tags=tags, description=description,
    )
    tasks.append(task)
    save_tasks(tasks)

    user_id = assignee_id or project.owner_id
    add_event("task_created", "task", task.id, user_id,
              {"title": title, "project_id": project_id})

    # Fire post-create hook
    plugin_manager.fire("task_post_create", task=task)

    print(f"Created task #{task.id}: {title}")
    return True


def cmd_list_tasks(filters: Optional[dict] = None, format: str = "lines", **kwargs):
    """List tasks with optional filters."""
    tasks = load_tasks()
    if filters:
        tasks = apply_filters(tasks, filters)

    if not tasks:
        print("No tasks found.")
        return

    if format == "table":
        print(format_task_table(tasks))
    else:
        for t in tasks:
            print(format_task_line(t, show_project=True))


def cmd_show_task(task_id: int, **kwargs):
    """Show detailed task info."""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False
    comments = get_comments_for_task(task_id)
    events = get_events_for_entity("task", task_id)
    print(format_task_detail(task, comments, events))
    return True


def cmd_update_task(task_id: int, **updates):
    """Update task fields."""
    tasks = load_tasks()
    task = None
    for t in tasks:
        if t.id == task_id:
            task = t
            break

    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    # Fire pre-update hook
    plugin_manager.fire("task_pre_update", task=task, updates=updates)

    changed = {}
    if "title" in updates:
        ok, msg = validate_title(updates["title"])
        if not ok:
            print(f"Error: {msg}", file=sys.stderr)
            return False
        changed["title"] = (task.title, updates["title"])
        task.title = updates["title"]

    if "status" in updates:
        old_status = task.update_status(updates["status"])
        changed["status"] = (old_status, updates["status"])

        # Check for incomplete dependencies when marking as done
        if updates["status"] == "done":
            dependencies = get_dependencies_for_task(task_id)
            incomplete_deps = []
            for dep in dependencies:
                dep_task = get_task_by_id(dep.depends_on_id)
                if dep_task and dep_task.status != "done":
                    incomplete_deps.append(dep_task)

            if incomplete_deps:
                print(f"WARNING: Task #{task_id} has {len(incomplete_deps)} incomplete dependencies:", file=sys.stderr)
                for dep_task in incomplete_deps:
                    print(f"  - Task #{dep_task.id}: {dep_task.title} (status: {dep_task.status})", file=sys.stderr)

        # Fire status change hook
        plugin_manager.fire("task_status_change", task=task,
                            old_status=old_status, new_status=updates["status"])

    if "priority" in updates:
        changed["priority"] = (task.priority, updates["priority"])
        task.priority = updates["priority"]

    if "assignee_id" in updates:
        changed["assignee_id"] = (task.assignee_id, updates["assignee_id"])
        task.assignee_id = updates["assignee_id"]

    if "due_date" in updates:
        changed["due_date"] = (task.due_date, updates["due_date"])
        task.due_date = updates["due_date"]

    if "tags" in updates:
        changed["tags"] = (task.tags, updates["tags"])
        task.tags = updates["tags"]

    if "description" in updates:
        changed["description"] = (task.description, updates["description"])
        task.description = updates["description"]

    from datetime import datetime
    task.updated_at = datetime.now().isoformat()
    save_tasks(tasks)

    add_event("task_updated", "task", task.id, task.assignee_id or 0,
              {"changed_fields": list(changed.keys())})

    # Fire post-update hook
    plugin_manager.fire("task_post_update", task=task, changes=changed)

    print(f"Updated task #{task_id}: {', '.join(changed.keys())}")
    return True


def cmd_delete_task(task_id: int, user_id: int = 0, **kwargs):
    """Delete a task."""
    tasks = load_tasks()
    task = None
    for t in tasks:
        if t.id == task_id:
            task = t
            break

    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    # Fire pre-delete hook
    plugin_manager.fire("task_pre_delete", task=task)

    # Remove all dependencies involving this task
    dependencies = load_dependencies()
    original_dep_count = len(dependencies)
    dependencies = [d for d in dependencies
                    if d.task_id != task_id and d.depends_on_id != task_id]
    if len(dependencies) < original_dep_count:
        save_dependencies(dependencies)

    tasks = [t for t in tasks if t.id != task_id]
    save_tasks(tasks)

    add_event("task_deleted", "task", task_id, user_id,
              {"title": task.title, "project_id": task.project_id})

    # Fire post-delete hook
    plugin_manager.fire("task_post_delete", task_id=task_id)

    print(f"Deleted task #{task_id}")
    return True


def cmd_add_comment(task_id: int, user_id: int, text: str, **kwargs):
    """Add a comment to a task."""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    if not text.strip():
        print("Error: Comment text cannot be empty", file=sys.stderr)
        return False

    comments = load_comments()
    comment = Comment(
        id=get_next_comment_id(), task_id=task_id,
        user_id=user_id, text=text,
    )
    comments.append(comment)
    save_comments(comments)

    add_event("comment_added", "task", task_id, user_id, {"text_length": len(text)})
    print(f"Added comment #{comment.id} to task #{task_id}")
    return True


def cmd_export(format: str = "csv", output: str = "", filters: Optional[dict] = None, **kwargs):
    """Export tasks to file."""
    tasks = load_tasks()
    if filters:
        tasks = apply_filters(tasks, filters)

    # Fire pre-export hook
    plugin_manager.fire("export_pre", format=format, count=len(tasks))

    if format == "csv":
        filepath = output or "tasks_export.csv"
        count = export_to_csv(tasks, filepath)
    elif format == "json":
        filepath = output or "tasks_export.json"
        count = export_to_json(tasks, filepath)
    elif format == "markdown":
        filepath = output or "tasks_export.md"
        count = export_to_markdown(tasks, filepath)
    else:
        print(f"Error: Unknown format '{format}'", file=sys.stderr)
        return False

    # Fire post-export hook
    plugin_manager.fire("export_post", format=format, filepath=filepath, count=count)

    print(f"Exported {count} tasks to {filepath}")
    return True


def cmd_summary(project_id: Optional[int] = None, **kwargs):
    """Show task summary statistics."""
    tasks = load_tasks()
    if project_id:
        tasks = [t for t in tasks if t.project_id == project_id]
    summary = generate_summary(tasks)
    print(format_summary(summary))
    return True


# ====================================================================
# Recurring Tasks Commands
# ====================================================================

def cmd_add_recurring(task_id: int, frequency: str, end_date: Optional[str] = None, **kwargs):
    """Create a recurring rule from an existing task (used as template)."""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    valid_frequencies = ["daily", "weekly", "biweekly", "monthly"]
    if frequency not in valid_frequencies:
        print(f"Error: Invalid frequency '{frequency}'. Valid: {', '.join(valid_frequencies)}", file=sys.stderr)
        return False

    from datetime import datetime
    next_run = datetime.now().isoformat()

    rules = load_recurring_rules()
    rule = RecurringRule(
        id=get_next_recurring_id(),
        task_template_id=task_id,
        frequency=frequency,
        next_run=next_run,
        end_date=end_date,
    )
    rules.append(rule)
    save_recurring_rules(rules)

    print(f"Created recurring rule #{rule.id} for task #{task_id} ({frequency})")
    return True


def cmd_list_recurring(**kwargs):
    """List all recurring rules with status."""
    rules = load_recurring_rules()
    if not rules:
        print("No recurring rules found.")
        return

    for r in rules:
        status = "active" if r.active else "inactive"
        end_info = f" until {r.end_date}" if r.end_date else " (no end date)"
        print(f"Rule #{r.id}: template=Task#{r.task_template_id}, freq={r.frequency}, "
              f"next_run={r.next_run}, status={status}, created={r.created_count}{end_info}")


def cmd_run_recurring(user_id: int, **kwargs):
    """Check all active rules, create new tasks for those where should_run() is True, advance the rule."""
    rules = load_recurring_rules()
    tasks = load_tasks()
    created_count = 0

    for rule in rules:
        if rule.should_run():
            # Find the template task
            template = get_task_by_id(rule.task_template_id)
            if not template:
                print(f"Warning: Template task #{rule.task_template_id} not found for rule #{rule.id}", file=sys.stderr)
                continue

            # Create a new task from the template
            new_task = Task(
                id=get_next_task_id(),
                title=template.title,
                project_id=template.project_id,
                assignee_id=template.assignee_id,
                status="todo",
                priority=template.priority,
                description=template.description,
                tags=template.tags.copy(),
                due_date=template.due_date,
            )
            tasks.append(new_task)
            created_count += 1

            # Advance the rule
            rule.advance()

    save_tasks(tasks)
    save_recurring_rules(rules)

    print(f"Created {created_count} tasks from recurring rules")
    return True


def cmd_cancel_recurring(rule_id: int, **kwargs):
    """Set rule.active = False."""
    rules = load_recurring_rules()
    rule = None
    for r in rules:
        if r.id == rule_id:
            rule = r
            break

    if not rule:
        print(f"Error: Recurring rule #{rule_id} not found", file=sys.stderr)
        return False

    rule.active = False
    save_recurring_rules(rules)

    print(f"Cancelled recurring rule #{rule_id}")
    return True


# ====================================================================
# Task Dependencies Commands
# ====================================================================

def cmd_add_dependency(task_id: int, depends_on_id: int, **kwargs):
    """Create a dependency. Validates both tasks exist, no self-dependency, no duplicate, no circular."""
    # Validate both tasks exist
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    depends_on_task = get_task_by_id(depends_on_id)
    if not depends_on_task:
        print(f"Error: Task #{depends_on_id} not found", file=sys.stderr)
        return False

    # Validate no self-dependency
    if task_id == depends_on_id:
        print(f"Error: Task cannot depend on itself", file=sys.stderr)
        return False

    dependencies = load_dependencies()

    # Validate no duplicate dependency
    for d in dependencies:
        if d.task_id == task_id and d.depends_on_id == depends_on_id:
            print(f"Error: Dependency already exists", file=sys.stderr)
            return False

    # Validate no circular dependency
    from validators import validate_no_circular_dependency
    ok, msg = validate_no_circular_dependency(task_id, depends_on_id, dependencies)
    if not ok:
        print(f"Error: {msg}", file=sys.stderr)
        return False

    # Create the dependency
    dependency = TaskDependency(
        id=get_next_dependency_id(),
        task_id=task_id,
        depends_on_id=depends_on_id,
    )
    dependencies.append(dependency)
    save_dependencies(dependencies)

    print(f"Added dependency: Task #{task_id} depends on Task #{depends_on_id}")
    return True


def cmd_list_dependencies(task_id: int, **kwargs):
    """Show what a task depends on and what depends on it."""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    print(f"Dependencies for Task #{task_id}: {task.title}")
    print()

    # What this task depends on
    depends_on = get_dependencies_for_task(task_id)
    if depends_on:
        print(f"This task depends on ({len(depends_on)}):")
        for d in depends_on:
            dep_task = get_task_by_id(d.depends_on_id)
            if dep_task:
                print(f"  - Task #{dep_task.id}: {dep_task.title} (status: {dep_task.status})")
    else:
        print("This task has no dependencies")

    print()

    # What depends on this task
    dependents = get_dependents_of_task(task_id)
    if dependents:
        print(f"Tasks that depend on this ({len(dependents)}):")
        for d in dependents:
            dep_task = get_task_by_id(d.task_id)
            if dep_task:
                print(f"  - Task #{dep_task.id}: {dep_task.title} (status: {dep_task.status})")
    else:
        print("No tasks depend on this")

    return True


def cmd_remove_dependency(task_id: int, depends_on_id: int, **kwargs):
    """Remove a dependency."""
    dependencies = load_dependencies()
    original_count = len(dependencies)

    dependencies = [d for d in dependencies
                    if not (d.task_id == task_id and d.depends_on_id == depends_on_id)]

    if len(dependencies) == original_count:
        print(f"Error: Dependency not found", file=sys.stderr)
        return False

    save_dependencies(dependencies)
    print(f"Removed dependency: Task #{task_id} no longer depends on Task #{depends_on_id}")
    return True


# ====================================================================
# Activity Dashboard Command
# ====================================================================

def cmd_dashboard(days: int = 7, user_id: Optional[int] = None, **kwargs):
    """Compute and print activity analytics."""
    from datetime import datetime, timedelta

    tasks = load_tasks()
    now = datetime.now()
    start_date = now - timedelta(days=days)

    # Filter by date range
    tasks_created_in_period = []
    tasks_completed_in_period = []

    for t in tasks:
        try:
            created = datetime.fromisoformat(t.created_at)
            if created >= start_date:
                tasks_created_in_period.append(t)
        except ValueError:
            pass

        if t.completed_at:
            try:
                completed = datetime.fromisoformat(t.completed_at)
                if completed >= start_date:
                    tasks_completed_in_period.append(t)
            except ValueError:
                pass

    # Filter by user if specified
    if user_id:
        tasks_created_in_period = [t for t in tasks_created_in_period if t.assignee_id == user_id]
        tasks_completed_in_period = [t for t in tasks_completed_in_period if t.assignee_id == user_id]

    # Compute metrics
    created_count = len(tasks_created_in_period)
    completed_count = len(tasks_completed_in_period)

    completion_rate = 0.0
    if created_count > 0:
        completion_rate = (completed_count / created_count) * 100

    # Average completion time
    total_completion_time = timedelta()
    valid_completion_times = 0
    for t in tasks_completed_in_period:
        try:
            created = datetime.fromisoformat(t.created_at)
            completed = datetime.fromisoformat(t.completed_at)
            total_completion_time += (completed - created)
            valid_completion_times += 1
        except (ValueError, TypeError):
            pass

    avg_completion_time = None
    if valid_completion_times > 0:
        avg_seconds = total_completion_time.total_seconds() / valid_completion_times
        avg_completion_time = timedelta(seconds=avg_seconds)

    # Most active user (who created/completed the most tasks)
    user_activity = {}
    for t in tasks_created_in_period + tasks_completed_in_period:
        uid = t.assignee_id
        if uid:
            user_activity[uid] = user_activity.get(uid, 0) + 1

    most_active_user_id = None
    most_active_user_count = 0
    for uid, count in user_activity.items():
        if count > most_active_user_count:
            most_active_user_id = uid
            most_active_user_count = count

    # Busiest project
    project_activity = {}
    for t in tasks_created_in_period + tasks_completed_in_period:
        pid = t.project_id
        project_activity[pid] = project_activity.get(pid, 0) + 1

    busiest_project_id = None
    busiest_project_count = 0
    for pid, count in project_activity.items():
        if count > busiest_project_count:
            busiest_project_id = pid
            busiest_project_count = count

    # Overdue tasks count
    overdue_count = sum(1 for t in tasks if t.is_overdue())

    # Tasks by status breakdown
    status_breakdown = {}
    for t in tasks:
        status_breakdown[t.status] = status_breakdown.get(t.status, 0) + 1

    # Create dashboard data
    dashboard_data = {
        "days": days,
        "tasks_created": created_count,
        "tasks_completed": completed_count,
        "completion_rate": completion_rate,
        "average_completion_time": avg_completion_time,
        "most_active_user": most_active_user_id,
        "busiest_project": busiest_project_id,
        "overdue_count": overdue_count,
        "status_breakdown": status_breakdown,
    }

    from formatters import format_dashboard
    print(format_dashboard(dashboard_data))
    return True
