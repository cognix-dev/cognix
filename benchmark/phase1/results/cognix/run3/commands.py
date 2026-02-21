#!/usr/bin/env python3
"""
Task Manager CLI - Commands module.
All CLI command handlers.
"""

import sys
import json
from typing import List, Optional
from datetime import datetime, timedelta
from models import Task, Project, User, Comment
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

    add_event("project_created", "project", project.id, owner_id,
              {"name": name})
    print(f"Created project #{project.id}: {name}")
    return True

def cmd_list_projects(**kwargs):
    """List all projects."""
    projects = load_projects()
    if not projects:
        print("No projects found.")
        return
    tasks = load_tasks()
    for p in projects:
        task_count = len([t for t in tasks if t.project_id == p.id])
        print(format_project_line(p, task_count))

def cmd_show_project(project_id: int, **kwargs):
    """Show detailed project information."""
    project = get_project_by_id(project_id)
    if not project:
        print(f"Error: Project #{project_id} not found", file=sys.stderr)
        return False

    tasks = get_tasks_by_project(project_id)
    print(format_project_detail(project, tasks))
    return True

def cmd_add_task(title: str, project_id: int, assignee_id: Optional[int] = None,
                 priority: str = "medium", due_date: str = "",
                 tags: List[str] = None, description: str = "", **kwargs):
    """Create a new task."""
    tags = tags or []
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
        assignee_id=assignee_id, priority=priority, due_date=due_date,
        tags=tags, description=description,
    )
    tasks.append(task)
    save_tasks(tasks)

    add_event("task_created", "task", task.id, assignee_id or project.owner_id,
              {"title": title, "project_id": project_id})

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
    """Show detailed task information."""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False

    comments = get_comments_for_task(task_id)
    events = get_events_for_entity("task", task_id)
    print(format_task_detail(task, comments, events))
    return True

def cmd_update_task(task_id: int, **kwargs):
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
    plugin_manager.fire("task_pre_update", task=task, updates=kwargs)

    changes = {}
    if "title" in kwargs:
        ok, msg = validate_title(kwargs["title"])
        if not ok:
            print(f"Error: {msg}", file=sys.stderr)
            return False
        task.title = kwargs["title"]
        changes["title"] = kwargs["title"]

    if "status" in kwargs:
        old_status = task.status
        new_status = kwargs["status"]
        try:
            task.update_status(new_status)
            changes["status"] = f"{old_status} -> {new_status}"
            
            # Check dependencies when marking as done
            if new_status == "done":
                deps = get_dependencies_for_task(task_id)
                if deps:
                    incomplete_deps = []
                    for dep in deps:
                        dep_task = get_task_by_id(dep.depends_on_id)
                        if dep_task and dep_task.status != "done":
                            incomplete_deps.append(f"#{dep.depends_on_id}")
                    
                    if incomplete_deps:
                        print(f"WARNING: Task has incomplete dependencies: {', '.join(incomplete_deps)}", 
                              file=sys.stderr)
            
            plugin_manager.fire("task_status_change", task=task,
                              old_status=old_status, new_status=new_status)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return False

    if "priority" in kwargs:
        task.priority = kwargs["priority"]
        changes["priority"] = kwargs["priority"]

    if "assignee_id" in kwargs:
        task.assignee_id = kwargs["assignee_id"]
        changes["assignee_id"] = kwargs["assignee_id"]

    if "due_date" in kwargs:
        task.due_date = kwargs["due_date"]
        changes["due_date"] = kwargs["due_date"]

    if "tags" in kwargs:
        task.tags = kwargs["tags"]
        changes["tags"] = kwargs["tags"]

    if "description" in kwargs:
        task.description = kwargs["description"]
        changes["description"] = kwargs["description"]

    if changes:
        task.updated_at = datetime.now().isoformat()
        save_tasks(tasks)
        add_event("task_updated", "task", task_id, task.assignee_id or 0, changes)

        # Fire post-update hook
        plugin_manager.fire("task_post_update", task=task, changes=changes)

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

def cmd_add_recurring(task_id: int, frequency: str, end_date: Optional[str] = None, **kwargs):
    """Create a recurring rule from an existing task template"""
    from models import RecurringRule
    
    # Validate task exists
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False
    
    # Validate frequency
    valid_frequencies = ["daily", "weekly", "biweekly", "monthly"]
    if frequency not in valid_frequencies:
        print(f"Error: Invalid frequency. Must be one of: {', '.join(valid_frequencies)}", 
              file=sys.stderr)
        return False
    
    # Validate end_date format if provided
    if end_date:
        try:
            datetime.fromisoformat(end_date)
        except ValueError:
            print("Error: Invalid end_date format. Use YYYY-MM-DD", file=sys.stderr)
            return False
    
    # Create recurring rule
    rules = load_recurring_rules()
    rule = RecurringRule(
        id=get_next_recurring_id(),
        task_template_id=task_id,
        frequency=frequency,
        next_run=datetime.now().date().isoformat(),
        end_date=end_date,
        created_count=0,
        active=True,
    )
    
    rules.append(rule)
    save_recurring_rules(rules)
    
    print(f"Recurring rule #{rule.id} created for task #{task_id} ({frequency})")
    return True

def cmd_list_recurring(**kwargs):
    """List all recurring rules with status"""
    rules = load_recurring_rules()
    
    if not rules:
        print("No recurring rules found.")
        return
    
    print("Recurring Rules:")
    print("=" * 60)
    for rule in rules:
        template = get_task_by_id(rule.task_template_id)
        template_title = template.title if template else "[deleted]"
        status = "Active" if rule.active else "Inactive"
        
        print(f"ID: {rule.id} | {status}")
        print(f"  Template: #{rule.task_template_id} - {template_title}")
        print(f"  Frequency: {rule.frequency}")
        print(f"  Next run: {rule.next_run}")
        print(f"  End date: {rule.end_date or 'Never'}")
        print(f"  Tasks created: {rule.created_count}")
        print()

def cmd_run_recurring(user_id: int, **kwargs):
    """Check and run all active recurring rules"""
    rules = load_recurring_rules()
    tasks = load_tasks()
    created_count = 0
    
    # Trigger pre-run hook
    plugin_manager.fire("recurring_pre_run", rules=rules)
    
    for rule in rules:
        if not rule.should_run():
            continue
        
        # Get template task
        template = get_task_by_id(rule.task_template_id)
        if not template:
            continue  # Skip if template was deleted
        
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
        )
        
        tasks.append(new_task)
        rule.advance()
        created_count += 1
    
    save_tasks(tasks)
    save_recurring_rules(rules)
    
    # Trigger post-run hook
    plugin_manager.fire("recurring_post_run", rules=rules, created_count=created_count)
    
    print(f"Created {created_count} recurring task(s)")
    return True

def cmd_cancel_recurring(rule_id: int, **kwargs):
    """Deactivate a recurring rule"""
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
    
    print(f"Recurring rule #{rule_id} cancelled")
    return True

def cmd_add_dependency(task_id: int, depends_on_id: int, **kwargs):
    """Add a task dependency"""
    from models import TaskDependency
    
    # Validate both tasks exist
    task = get_task_by_id(task_id)
    depends_on = get_task_by_id(depends_on_id)
    
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False
    if not depends_on:
        print(f"Error: Task #{depends_on_id} not found", file=sys.stderr)
        return False
    
    # Validate no self-dependency
    if task_id == depends_on_id:
        print("Error: Task cannot depend on itself", file=sys.stderr)
        return False
    
    # Load existing dependencies
    dependencies = load_dependencies()
    
    # Check for duplicate
    for dep in dependencies:
        if dep.task_id == task_id and dep.depends_on_id == depends_on_id:
            print("Error: Dependency already exists", file=sys.stderr)
            return False
    
    # Check for circular dependency
    is_valid, error_msg = validate_no_circular_dependency(
        task_id, depends_on_id, dependencies
    )
    if not is_valid:
        print(f"Error: {error_msg}", file=sys.stderr)
        return False
    
    # Create dependency
    new_dep = TaskDependency(
        id=get_next_dependency_id(),
        task_id=task_id,
        depends_on_id=depends_on_id,
    )
    
    dependencies.append(new_dep)
    save_dependencies(dependencies)
    
    print(f"Dependency added: Task #{task_id} depends on Task #{depends_on_id}")
    return True

def cmd_list_dependencies(task_id: int, **kwargs):
    """List dependencies for a task"""
    task = get_task_by_id(task_id)
    if not task:
        print(f"Error: Task #{task_id} not found", file=sys.stderr)
        return False
    
    # Get what this task depends on
    depends_on = get_dependencies_for_task(task_id)
    
    # Get what depends on this task
    dependents = get_dependents_of_task(task_id)
    
    print(f"Dependencies for Task #{task_id}: {task.title}")
    print("=" * 60)
    
    if depends_on:
        print("\nThis task depends on:")
        for dep in depends_on:
            dep_task = get_task_by_id(dep.depends_on_id)
            if dep_task:
                status_icon = "●" if dep_task.status == "done" else "○"
                print(f"  {status_icon} #{dep_task.id}: {dep_task.title} ({dep_task.status})")
    else:
        print("\nThis task has no dependencies.")
    
    if dependents:
        print("\nTasks that depend on this:")
        for dep in dependents:
            dep_task = get_task_by_id(dep.task_id)
            if dep_task:
                status_icon = "●" if dep_task.status == "done" else "○"
                print(f"  {status_icon} #{dep_task.id}: {dep_task.title} ({dep_task.status})")
    else:
        print("\nNo tasks depend on this.")
    
    return True

def cmd_remove_dependency(task_id: int, depends_on_id: int, **kwargs):
    """Remove a dependency"""
    dependencies = load_dependencies()
    
    found = False
    for i, dep in enumerate(dependencies):
        if dep.task_id == task_id and dep.depends_on_id == depends_on_id:
            dependencies.pop(i)
            found = True
            break
    
    if not found:
        print(f"Error: Dependency not found", file=sys.stderr)
        return False
    
    save_dependencies(dependencies)
    print(f"Dependency removed: Task #{task_id} no longer depends on Task #{depends_on_id}")
    return True

def cmd_dashboard(days: int = 7, user_id: Optional[int] = None, **kwargs):
    """Show activity dashboard analytics"""
    tasks = load_tasks()
    now = datetime.now()
    period_start = now - timedelta(days=days)
    
    # Filter by user if specified
    if user_id:
        tasks = [t for t in tasks if t.assignee_id == user_id]
    
    # Calculate metrics
    tasks_created = 0
    tasks_completed = 0
    completion_times = []
    overdue_count = 0
    by_status = {}
    user_activity = {}
    project_activity = {}
    
    for t in tasks:
        # Count by status
        by_status[t.status] = by_status.get(t.status, 0) + 1
        
        # Check if overdue
        if t.is_overdue():
            overdue_count += 1
        
        # Track user activity
        if t.assignee_id:
            user_activity[t.assignee_id] = user_activity.get(t.assignee_id, 0) + 1
        
        # Track project activity
        project_activity[t.project_id] = project_activity.get(t.project_id, 0) + 1
        
        # Check if created in period
        try:
            created = datetime.fromisoformat(t.created_at)
            if created >= period_start:
                tasks_created += 1
        except ValueError:
            pass
        
        # Check if completed in period
        if t.status == "done" and t.completed_at:
            try:
                completed = datetime.fromisoformat(t.completed_at)
                if completed >= period_start:
                    tasks_completed += 1
                    
                    # Calculate completion time
                    created = datetime.fromisoformat(t.created_at)
                    time_diff = completed - created
                    completion_times.append(time_diff.total_seconds())
            except ValueError:
                pass
    
    # Calculate completion rate
    completion_rate = 0.0
    if tasks_created > 0:
        completion_rate = (tasks_completed / tasks_created) * 100
    
    # Calculate average completion time
    avg_completion_time = "N/A"
    if completion_times:
        avg_seconds = sum(completion_times) / len(completion_times)
        avg_days = avg_seconds / 86400
        if avg_days < 1:
            avg_hours = avg_seconds / 3600
            avg_completion_time = f"{avg_hours:.1f} hours"
        else:
            avg_completion_time = f"{avg_days:.1f} days"
    
    # Find most active user
    most_active_user = "N/A"
    if user_activity:
        top_user_id = max(user_activity, key=user_activity.get)
        top_user = get_user_by_id(top_user_id)
        if top_user:
            most_active_user = f"{top_user.username} ({user_activity[top_user_id]} tasks)"
    
    # Find busiest project
    busiest_project = "N/A"
    if project_activity:
        top_project_id = max(project_activity, key=project_activity.get)
        top_project = get_project_by_id(top_project_id)
        if top_project:
            busiest_project = f"{top_project.name} ({project_activity[top_project_id]} tasks)"
    
    # Build dashboard data
    dashboard_data = {
        "period_days": days,
        "tasks_created": tasks_created,
        "tasks_completed": tasks_completed,
        "completion_rate": completion_rate,
        "avg_completion_time": avg_completion_time,
        "overdue_count": overdue_count,
        "by_status": by_status,
        "most_active_user": most_active_user,
        "busiest_project": busiest_project,
    }
    
    print(format_dashboard(dashboard_data))
    return True