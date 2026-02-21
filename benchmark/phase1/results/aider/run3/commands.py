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
    load_dependencies, save_dependencies, get_dependencies_for_task, 
    get_dependents_of_task, get_next_dependency_id,
    load_events,
)
from filters import apply_filters
from formatters import (
    format_task_line, format_task_detail, format_task_table,
    format_project_line, format_project_detail,
    format_summary, format_user_line,
)
from exporters import export_to_csv, export_to_json, export_to_markdown, generate_summary
from validators import validate_task_create, validate_title, validate_email, validate_username, validate_no_circular_dependency
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

        # Check dependencies if marking as done
        if updates["status"] == "done":
            deps = get_dependencies_for_task(task_id)
            if deps:
                incomplete = []
                for dep in deps:
                    dep_task = get_task_by_id(dep.depends_on_id)
                    if dep_task and dep_task.status != "done":
                        incomplete.append(dep.depends_on_id)
                if incomplete:
                    print(f"WARNING: Task #{task_id} depends on incomplete tasks: {incomplete}")

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

    tasks = [t for t in tasks if t.id != task_id]
    save_tasks(tasks)

    # Remove all dependencies involving this task
    deps = load_dependencies()
    deps = [d for d in deps if d.task_id != task_id and d.depends_on_id != task_id]
    save_dependencies(deps)

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
    """Create a recurring rule from an existing task."""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    valid_frequencies = ["daily", "weekly", "biweekly", "monthly"]
    if frequency not in valid_frequencies:
        print(f"Error: Invalid frequency '{frequency}'. Valid: {', '.join(valid_frequencies)}", file=sys.stderr)
        return False

    if end_date:
        from validators import validate_date
        ok, msg = validate_date(end_date)
        if not ok:
            print(f"Error: {msg}", file=sys.stderr)
            return False

    from datetime import datetime
    rules = load_recurring_rules()
    rule = RecurringRule(
        id=get_next_recurring_id(),
        task_template_id=task_id,
        frequency=frequency,
        next_run=datetime.now().isoformat(),
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
        template = get_task_by_id(r.task_template_id)
        template_title = template.title if template else "(deleted)"
        status = "active" if r.active else "inactive"
        end_info = f" until {r.end_date}" if r.end_date else ""
        print(f"Rule #{r.id}: {template_title} ({r.frequency}, {status}, created {r.created_count} tasks, next: {r.next_run[:10]}{end_info})")


def cmd_run_recurring(user_id: int = 0, **kwargs):
    """Check all active rules and create tasks for those that should run."""
    rules = load_recurring_rules()
    tasks = load_tasks()
    
    plugin_manager.fire("recurring_pre_run", rule_count=len(rules))
    
    created_count = 0
    for rule in rules:
        if not rule.should_run():
            continue

        template = get_task_by_id(rule.task_template_id)
        if not template:
            continue

        # Create new task from template
        new_task = Task(
            id=get_next_task_id(),
            title=template.title,
            project_id=template.project_id,
            assignee_id=template.assignee_id,
            status="todo",
            priority=template.priority,
            description=template.description,
            tags=template.tags[:],
            due_date=template.due_date,
        )
        tasks.append(new_task)
        created_count += 1

        add_event("task_created", "task", new_task.id, user_id,
                  {"title": new_task.title, "recurring_rule_id": rule.id})

        # Advance the rule
        rule.advance()

    save_tasks(tasks)
    save_recurring_rules(rules)

    plugin_manager.fire("recurring_post_run", created_count=created_count)

    print(f"Created {created_count} tasks from recurring rules")
    return True


def cmd_cancel_recurring(rule_id: int, **kwargs):
    """Deactivate a recurring rule."""
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
    """Create a task dependency."""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    depends_on = get_task_by_id(depends_on_id)
    if not depends_on:
        print(f"Error: Task #{depends_on_id} not found", file=sys.stderr)
        return False

    if task_id == depends_on_id:
        print(f"Error: Task cannot depend on itself", file=sys.stderr)
        return False

    deps = load_dependencies()

    # Check for duplicate
    for d in deps:
        if d.task_id == task_id and d.depends_on_id == depends_on_id:
            print(f"Error: Dependency already exists", file=sys.stderr)
            return False

    # Check for circular dependency
    ok, msg = validate_no_circular_dependency(task_id, depends_on_id, deps)
    if not ok:
        print(f"Error: {msg}", file=sys.stderr)
        return False

    dep = TaskDependency(
        id=get_next_dependency_id(),
        task_id=task_id,
        depends_on_id=depends_on_id,
    )
    deps.append(dep)
    save_dependencies(deps)

    print(f"Added dependency: task #{task_id} depends on task #{depends_on_id}")
    return True


def cmd_list_dependencies(task_id: int, **kwargs):
    """Show what a task depends on and what depends on it."""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    depends_on = get_dependencies_for_task(task_id)
    dependents = get_dependents_of_task(task_id)

    print(f"Dependencies for task #{task_id}: {task.title}")
    print()

    if depends_on:
        print(f"This task depends on ({len(depends_on)}):")
        for d in depends_on:
            dep_task = get_task_by_id(d.depends_on_id)
            if dep_task:
                status_icon = "✓" if dep_task.status == "done" else "○"
                print(f"  {status_icon} #{dep_task.id}: {dep_task.title} ({dep_task.status})")
    else:
        print("This task has no dependencies.")

    print()

    if dependents:
        print(f"Tasks that depend on this ({len(dependents)}):")
        for d in dependents:
            dep_task = get_task_by_id(d.task_id)
            if dep_task:
                print(f"  #{dep_task.id}: {dep_task.title} ({dep_task.status})")
    else:
        print("No tasks depend on this.")

    return True


def cmd_remove_dependency(task_id: int, depends_on_id: int, **kwargs):
    """Remove a task dependency."""
    deps = load_dependencies()
    found = False
    new_deps = []
    for d in deps:
        if d.task_id == task_id and d.depends_on_id == depends_on_id:
            found = True
        else:
            new_deps.append(d)

    if not found:
        print(f"Error: Dependency not found", file=sys.stderr)
        return False

    save_dependencies(new_deps)
    print(f"Removed dependency: task #{task_id} no longer depends on task #{depends_on_id}")
    return True


# ====================================================================
# Activity Dashboard Command
# ====================================================================

def cmd_dashboard(days: int = 7, user_id: Optional[int] = None, **kwargs):
    """Show activity analytics for the specified period."""
    from datetime import datetime, timedelta
    
    tasks = load_tasks()
    events = load_events()
    
    # Calculate date range
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    # Filter tasks and events by date range
    tasks_created = []
    tasks_completed = []
    
    for t in tasks:
        try:
            created_dt = datetime.fromisoformat(t.created_at)
            if created_dt >= start_date:
                if user_id is None or t.assignee_id == user_id:
                    tasks_created.append(t)
        except ValueError:
            pass
        
        if t.status == "done" and t.completed_at:
            try:
                completed_dt = datetime.fromisoformat(t.completed_at)
                if completed_dt >= start_date:
                    if user_id is None or t.assignee_id == user_id:
                        tasks_completed.append(t)
            except ValueError:
                pass
    
    # Calculate metrics
    created_count = len(tasks_created)
    completed_count = len(tasks_completed)
    completion_rate = (completed_count / created_count * 100) if created_count > 0 else 0.0
    
    # Average completion time
    completion_times = []
    for t in tasks_completed:
        try:
            created_dt = datetime.fromisoformat(t.created_at)
            completed_dt = datetime.fromisoformat(t.completed_at)
            delta = completed_dt - created_dt
            completion_times.append(delta.total_seconds() / 3600)  # hours
        except ValueError:
            pass
    
    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0.0
    
    # Most active user
    user_activity = {}
    for t in tasks_created + tasks_completed:
        if t.assignee_id:
            user_activity[t.assignee_id] = user_activity.get(t.assignee_id, 0) + 1
    most_active_user = max(user_activity.items(), key=lambda x: x[1])[0] if user_activity else None
    
    # Busiest project
    project_activity = {}
    for t in tasks_created + tasks_completed:
        project_activity[t.project_id] = project_activity.get(t.project_id, 0) + 1
    busiest_project = max(project_activity.items(), key=lambda x: x[1])[0] if project_activity else None
    
    # Overdue tasks
    overdue_count = sum(1 for t in tasks if t.is_overdue())
    
    # Tasks by status
    status_breakdown = {}
    for t in tasks:
        if user_id is None or t.assignee_id == user_id:
            status_breakdown[t.status] = status_breakdown.get(t.status, 0) + 1
    
    # Build dashboard data
    dashboard_data = {
        "days": days,
        "user_id": user_id,
        "tasks_created": created_count,
        "tasks_completed": completed_count,
        "completion_rate": completion_rate,
        "avg_completion_time": avg_completion_time,
        "most_active_user": most_active_user,
        "busiest_project": busiest_project,
        "overdue_count": overdue_count,
        "status_breakdown": status_breakdown,
    }
    
    from formatters import format_dashboard
    print(format_dashboard(dashboard_data))
    return True
