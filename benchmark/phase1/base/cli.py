#!/usr/bin/env python3
"""
Task Manager CLI - Main entry point.
Usage: python cli.py <command> [options]
"""

import sys
import argparse
from commands import (
    cmd_init, cmd_add_user, cmd_list_users,
    cmd_add_project, cmd_list_projects, cmd_show_project,
    cmd_add_task, cmd_list_tasks, cmd_show_task,
    cmd_update_task, cmd_delete_task,
    cmd_add_comment, cmd_export, cmd_summary,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taskmanager",
        description="Task Manager CLI - Manage projects, tasks, and teams",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    sub.add_parser("init", help="Initialize data directory")

    # user add
    p = sub.add_parser("user-add", help="Add a user")
    p.add_argument("username")
    p.add_argument("email")
    p.add_argument("--role", default="member", choices=["admin", "member", "viewer"])

    # user list
    sub.add_parser("user-list", help="List users")

    # project add
    p = sub.add_parser("project-add", help="Create a project")
    p.add_argument("name")
    p.add_argument("--owner", type=int, required=True)
    p.add_argument("--description", default="")

    # project list
    sub.add_parser("project-list", help="List projects")

    # project show
    p = sub.add_parser("project-show", help="Show project details")
    p.add_argument("project_id", type=int)

    # task add
    p = sub.add_parser("task-add", help="Create a task")
    p.add_argument("title")
    p.add_argument("--project", type=int, required=True)
    p.add_argument("--assignee", type=int, default=None)
    p.add_argument("--priority", default="medium",
                   choices=["low", "medium", "high", "critical"])
    p.add_argument("--due", default="")
    p.add_argument("--tags", nargs="*", default=[])
    p.add_argument("--description", default="")

    # task list
    p = sub.add_parser("task-list", help="List tasks")
    p.add_argument("--status", default=None)
    p.add_argument("--priority", default=None)
    p.add_argument("--project", type=int, default=None)
    p.add_argument("--assignee", type=int, default=None)
    p.add_argument("--tag", default=None)
    p.add_argument("--search", default=None)
    p.add_argument("--sort", default="created_at")
    p.add_argument("--reverse", action="store_true")
    p.add_argument("--format", default="lines", choices=["lines", "table"])

    # task show
    p = sub.add_parser("task-show", help="Show task details")
    p.add_argument("task_id", type=int)

    # task update
    p = sub.add_parser("task-update", help="Update a task")
    p.add_argument("task_id", type=int)
    p.add_argument("--title", default=None)
    p.add_argument("--status", default=None)
    p.add_argument("--priority", default=None)
    p.add_argument("--assignee", type=int, default=None)
    p.add_argument("--due", default=None)
    p.add_argument("--tags", nargs="*", default=None)
    p.add_argument("--description", default=None)

    # task delete
    p = sub.add_parser("task-delete", help="Delete a task")
    p.add_argument("task_id", type=int)
    p.add_argument("--user", type=int, default=0)

    # comment add
    p = sub.add_parser("comment-add", help="Add a comment to a task")
    p.add_argument("task_id", type=int)
    p.add_argument("--user", type=int, required=True)
    p.add_argument("text")

    # export
    p = sub.add_parser("export", help="Export tasks")
    p.add_argument("--format", default="csv", choices=["csv", "json", "markdown"])
    p.add_argument("--output", default="")
    p.add_argument("--status", default=None)
    p.add_argument("--project", type=int, default=None)

    # summary
    p = sub.add_parser("summary", help="Show task summary")
    p.add_argument("--project", type=int, default=None)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        cmd_init()
    elif args.command == "user-add":
        cmd_add_user(args.username, args.email, args.role)
    elif args.command == "user-list":
        cmd_list_users()
    elif args.command == "project-add":
        cmd_add_project(args.name, args.owner, args.description)
    elif args.command == "project-list":
        cmd_list_projects()
    elif args.command == "project-show":
        cmd_show_project(args.project_id)
    elif args.command == "task-add":
        cmd_add_task(args.title, args.project, args.assignee,
                     args.priority, args.due, args.tags, args.description)
    elif args.command == "task-list":
        filters = {}
        if args.status:
            filters["status"] = args.status
        if args.priority:
            filters["priority"] = args.priority
        if args.project:
            filters["project_id"] = args.project
        if args.assignee:
            filters["assignee_id"] = args.assignee
        if args.tag:
            filters["tag"] = args.tag
        if args.search:
            filters["search"] = args.search
        filters["sort_by"] = args.sort
        filters["sort_reverse"] = args.reverse
        cmd_list_tasks(filters=filters, format=args.format)
    elif args.command == "task-show":
        cmd_show_task(args.task_id)
    elif args.command == "task-update":
        updates = {}
        if args.title is not None:
            updates["title"] = args.title
        if args.status is not None:
            updates["status"] = args.status
        if args.priority is not None:
            updates["priority"] = args.priority
        if args.assignee is not None:
            updates["assignee_id"] = args.assignee
        if args.due is not None:
            updates["due_date"] = args.due
        if args.tags is not None:
            updates["tags"] = args.tags
        if args.description is not None:
            updates["description"] = args.description
        if not updates:
            print("Error: No fields to update", file=sys.stderr)
            sys.exit(1)
        cmd_update_task(args.task_id, **updates)
    elif args.command == "task-delete":
        cmd_delete_task(args.task_id, args.user)
    elif args.command == "comment-add":
        cmd_add_comment(args.task_id, args.user, args.text)
    elif args.command == "export":
        filters = {}
        if args.status:
            filters["status"] = args.status
        if args.project:
            filters["project_id"] = args.project
        cmd_export(format=args.format, output=args.output, filters=filters)
    elif args.command == "summary":
        cmd_summary(project_id=args.project)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
