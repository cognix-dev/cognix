#!/usr/bin/env python3
"""
Task Manager CLI - Commands module.
All CLI command handlers.
"""

import sys
import json
from typing import List, Optional
from datetime import datetime, timedelta
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
)
from filters import apply_filters
from formatters import (
    format_task_line, format_task_detail, format_task_table,
    format_project_line, format_project_detail,
    format_summary, format_user_line, format_dashboard,
)
from exporters import export_to_csv, export_to_json, export_to_markdown, generate_summary
from validators import (
    validate_task_create, validate_title, validate_email, validate_username,
    validate_frequency, validate_no_circular_dependency,
)
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
    """Show detailed project view."""
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
    if tags is None:
        tags = []

    ok, errors = validate_task_create(title, project_id, "todo", priority, due_date, tags)
    if not ok:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        return False

    project = get_project_by_id(project_id)
    if not project:
        print(f"Error: Project #{project_id} not found", file=sys.stderr)
        return False

    if assignee_id:
        assignee = get_user_by_id(assignee_id)
        if not assignee:
            print(f"Error: User #{assignee_id} not found", file=sys.stderr)
            return False

    # Fire pre-create hook
    plugin_manager.fire("task_pre_create", title=title, project_id=project_id)

    tasks = load_tasks()
    task = Task(
        id=get_next_task_id(), title=title, project_id=project_id,
        assignee_id=assignee_id, priority=priority, description=description,
        tags=tags, due_date=due_date or None,
    )
    tasks.append(task)
    save_tasks(tasks)

    add_event("task_created", "task", task.id, assignee_id or 0,
              {"title": title, "priority": priority})

    # Fire post-create hook
    plugin_manager.fire("task_post_create", task=task)

    print(f"Created task #{task.id}: {title}")
    return True

def cmd_list_tasks(filters: Optional[dict] = None, format: str = "lines", **kwargs):
    """List tasks with optional filtering."""
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
    """Show detailed task view."""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    comments = get_comments_for_task(task_id)
    events = get_events_for_entity("task", task_id)
    print(format_task_detail(task, comments, events))
    return True

def cmd_update_task(task_id: int, **kwargs):
    """Update a task with new values."""
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
    plugin_manager.fire("task_pre_update", task=task, updates=kwargs)

    changed = False
    old_status = task.status

    for key, value in kwargs.items():
        if hasattr(task, key) and value is not None:
            setattr(task, key, value)
            changed = True

    if changed:
        task.updated_at = datetime.now().isoformat()
        
        # Check for dependency warnings when changing to "done"
        if "status" in kwargs and kwargs["status"] == "done":
            deps = get_dependencies_for_task(task_id)
            if deps:
                incomplete_deps = []
                for dep in deps:
                    blocking_task = get_task_by_id(dep.depends_on_id)
                    if blocking_task and blocking_task.status != "done":
                        incomplete_deps.append(blocking_task)
                
                if incomplete_deps:
                    print(f"WARNING: Task #{task_id} depends on incomplete tasks:", file=sys.stderr)
                    for bt in incomplete_deps:
                        print(f"  - Task #{bt.id}: {bt.title} (status: {bt.status})", file=sys.stderr)
        
        save_tasks(tasks)

        if "status" in kwargs and kwargs["status"] != old_status:
            add_event("task_status_changed", "task", task_id, 0,
                      {"old_status": old_status, "new_status": task.status})
            plugin_manager.fire("task_status_change", task=task, old_status=old_status)
        else:
            add_event("task_updated", "task", task_id, 0, {"fields": list(kwargs.keys())})

        # Fire post-update hook
        plugin_manager.fire("task_post_update", task=task)

        print(f"Updated task #{task_id}")
        return True
    else:
        print("No changes made.")
        return False

def cmd_delete_task(task_id: int, user_id: int, **kwargs):
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
    dependencies = [d for d in dependencies 
                   if d.task_id != task_id and d.depends_on_id != task_id]
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

# ===== RECURRING TASKS =====

def cmd_add_recurring(task_id: int, frequency: str, end_date: Optional[str] = None, **kwargs):
    """Create a recurring rule from an existing task template"""
    # Validate frequency
    valid, msg = validate_frequency(frequency)
    if not valid:
        print(f"Error: {msg}", file=sys.stderr)
        return False
    
    # Validate task exists
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False
    
    # Validate end_date format if provided
    if end_date:
        from validators import validate_date
        valid, msg = validate_date(end_date)
        if not valid:
            print(f"Error: Invalid end_date: {msg}", file=sys.stderr)
            return False
    
    # Create rule with next_run = tomorrow
    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    
    rule = RecurringRule(
        id=get_next_recurring_id(),
        task_template_id=task_id,
        frequency=frequency,
        next_run=tomorrow,
        end_date=end_date,
        created_count=0,
        active=True,
        created_at=datetime.now().isoformat()
    )
    
    rules = load_recurring_rules()
    rules.append(rule)
    save_recurring_rules(rules)
    
    print(f"Recurring rule #{rule.id} created for task #{task_id} ({frequency})")
    return True

def cmd_list_recurring(**kwargs):
    """List all recurring rules"""
    rules = load_recurring_rules()
    if not rules:
        print("No recurring rules found.")
        return
    
    print("Recurring Rules:")
    print("=" * 80)
    for rule in rules:
        task = get_task_by_id(rule.task_template_id)
        task_title = task.title if task else "[deleted]"
        status = "Active" if rule.active else "Inactive"
        end = f"End: {rule.end_date}" if rule.end_date else "No end date"
        print(
            f"Rule #{rule.id} | {status} | {rule.frequency} | "
            f"Next: {rule.next_run} | Created: {rule.created_count} | {end}"
        )
        print(f"  Template: {task_title}")

def cmd_run_recurring(user_id: int, **kwargs):
    """Execute recurring rules and create tasks"""
    rules = load_recurring_rules()
    tasks = load_tasks()
    created_count = 0
    
    # Fire pre-run hook
    plugin_manager.fire("recurring_pre_run", user_id=user_id)
    
    for rule in rules:
        if not rule.should_run():
            continue
        
        # Get template task
        template = get_task_by_id(rule.task_template_id)
        if not template:
            continue  # Template deleted, skip
        
        # Create new task from template
        new_task = Task(
            id=get_next_task_id(),
            title=template.title,
            description=template.description,
            status="todo",
            priority=template.priority,
            due_date=template.due_date,
            assignee_id=user_id,
            project_id=template.project_id,
            tags=template.tags.copy() if template.tags else [],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            completed_at=None
        )
        
        tasks.append(new_task)
        rule.advance()
        created_count += 1
    
    save_tasks(tasks)
    save_recurring_rules(rules)
    
    # Fire post-run hook
    plugin_manager.fire("recurring_post_run", user_id=user_id, created_count=created_count)
    
    print(f"Created {created_count} task(s) from recurring rules")
    return True

def cmd_cancel_recurring(rule_id: int, **kwargs):
    """Deactivate a recurring rule"""
    rules = load_recurring_rules()
    
    for rule in rules:
        if rule.id == rule_id:
            rule.active = False
            save_recurring_rules(rules)
            print(f"Recurring rule #{rule_id} cancelled")
            return True
    
    print(f"Error: Recurring rule #{rule_id} not found", file=sys.stderr)
    return False

# ===== TASK DEPENDENCIES =====

def cmd_add_dependency(task_id: int, depends_on_id: int, **kwargs):
    """Create a dependency between tasks"""
    # Validate both tasks exist
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False
    
    depends_on_task = get_task_by_id(depends_on_id)
    if not depends_on_task:
        print(f"Error: Task #{depends_on_id} not found", file=sys.stderr)
        return False
    
    # Check for self-dependency
    if task_id == depends_on_id:
        print(f"Error: Task cannot depend on itself", file=sys.stderr)
        return False
    
    # Check for duplicate dependency
    dependencies = load_dependencies()
    for dep in dependencies:
        if dep.task_id == task_id and dep.depends_on_id == depends_on_id:
            print(f"Error: Dependency already exists", file=sys.stderr)
            return False
    
    # Check for circular dependency
    valid, msg = validate_no_circular_dependency(task_id, depends_on_id, dependencies)
    if not valid:
        print(f"Error: {msg}", file=sys.stderr)
        return False
    
    # Create dependency
    dependency = TaskDependency(
        id=get_next_dependency_id(),
        task_id=task_id,
        depends_on_id=depends_on_id,
        created_at=datetime.now().isoformat()
    )
    
    dependencies.append(dependency)
    save_dependencies(dependencies)
    
    print(f"Dependency created: Task #{task_id} depends on Task #{depends_on_id}")
    return True

def cmd_list_dependencies(task_id: int, **kwargs):
    """Show what a task depends on and what depends on it"""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False
    
    print(f"Dependencies for Task #{task_id}: {task.title}")
    print("=" * 60)
    
    # What this task depends on
    deps = get_dependencies_for_task(task_id)
    if deps:
        print("\nThis task depends on:")
        for dep in deps:
            blocking_task = get_task_by_id(dep.depends_on_id)
            if blocking_task:
                status_icon = "●" if blocking_task.status == "done" else "○"
                print(f"  {status_icon} Task #{blocking_task.id}: {blocking_task.title} ({blocking_task.status})")
    else:
        print("\nThis task has no dependencies.")
    
    # What depends on this task
    dependents = get_dependents_of_task(task_id)
    if dependents:
        print("\nTasks that depend on this:")
        for dep in dependents:
            dependent_task = get_task_by_id(dep.task_id)
            if dependent_task:
                print(f"  - Task #{dependent_task.id}: {dependent_task.title} ({dependent_task.status})")
    else:
        print("\nNo tasks depend on this.")
    
    return True

def cmd_remove_dependency(task_id: int, depends_on_id: int, **kwargs):
    """Remove a dependency"""
    dependencies = load_dependencies()
    
    for i, dep in enumerate(dependencies):
        if dep.task_id == task_id and dep.depends_on_id == depends_on_id:
            dependencies.pop(i)
            save_dependencies(dependencies)
            print(f"Dependency removed: Task #{task_id} no longer depends on Task #{depends_on_id}")
            return True
    
    print(f"Error: Dependency not found", file=sys.stderr)
    return False

# ===== DASHBOARD =====

def cmd_dashboard(days: int = 7, user_id: Optional[int] = None, **kwargs):
    """Show activity analytics dashboard"""
    tasks = load_tasks()
    
    # Calculate date range
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    # Initialize metrics
    tasks_created = 0
    tasks_completed = 0
    completion_times = []
    overdue_count = 0
    by_status = {}
    user_activity = {}
    project_activity = {}
    
    # Analyze all tasks
    for task in tasks:
        # Count by status
        by_status[task.status] = by_status.get(task.status, 0) + 1
        
        # Count overdue
        if task.is_overdue():
            overdue_count += 1
        
        # Track user activity
        if task.assignee_id:
            user_activity[task.assignee_id] = user_activity.get(task.assignee_id, 0) + 1
        
        # Track project activity
        project_activity[task.project_id] = project_activity.get(task.project_id, 0) + 1
        
        # Tasks created in period
        try:
            created_dt = datetime.fromisoformat(task.created_at)
            if created_dt >= start_date:
                tasks_created += 1
        except (ValueError, AttributeError):
            pass
        
        # Tasks completed in period
        if task.status == "done" and task.completed_at:
            try:
                completed_dt = datetime.fromisoformat(task.completed_at)
                if completed_dt >= start_date:
                    tasks_completed += 1
                    
                    # Calculate completion time
                    try:
                        created_dt = datetime.fromisoformat(task.created_at)
                        completion_time = (completed_dt - created_dt).total_seconds()
                        completion_times.append(completion_time)
                    except (ValueError, AttributeError):
                        pass
            except (ValueError, AttributeError):
                pass
    
    # Calculate completion rate
    if tasks_created > 0:
        completion_rate = (tasks_completed / tasks_created) * 100
    else:
        completion_rate = 0.0
    
    # Calculate average completion time
    if completion_times:
        avg_seconds = sum(completion_times) / len(completion_times)
        avg_hours = avg_seconds / 3600
        if avg_hours < 1:
            avg_time_str = f"{avg_seconds / 60:.1f} minutes"
        elif avg_hours < 24:
            avg_time_str = f"{avg_hours:.1f} hours"
        else:
            avg_time_str = f"{avg_hours / 24:.1f} days"
    else:
        avg_time_str = "N/A"
    
    # Find most active user
    if user_activity:
        most_active_user_id = max(user_activity, key=user_activity.get)
        user = get_user_by_id(most_active_user_id)
        most_active_user = f"User #{most_active_user_id}: {user.username}" if user else f"User #{most_active_user_id}"
    else:
        most_active_user = "N/A"
    
    # Find busiest project
    if project_activity:
        busiest_project_id = max(project_activity, key=project_activity.get)
        project = get_project_by_id(busiest_project_id)
        busiest_project = f"Project #{busiest_project_id}: {project.name}" if project else f"Project #{busiest_project_id}"
    else:
        busiest_project = "N/A"
    
    # Build dashboard data
    dashboard_data = {
        "days": days,
        "tasks_created": tasks_created,
        "tasks_completed": tasks_completed,
        "completion_rate": completion_rate,
        "avg_completion_time": avg_time_str,
        "overdue_count": overdue_count,
        "by_status": by_status,
        "most_active_user": most_active_user,
        "busiest_project": busiest_project,
    }
    
    print(format_dashboard(dashboard_data))
    return True