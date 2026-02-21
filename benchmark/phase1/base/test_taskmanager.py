#!/usr/bin/env python3
"""
Task Manager CLI - Comprehensive test suite.
Tests all modules: models, storage, filters, formatters, validators,
exporters, plugins, commands.
"""

import os
import sys
import json
import shutil
import unittest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import models
import storage
import filters
import formatters
import validators
import exporters
import plugins
import commands


class BaseTestCase(unittest.TestCase):
    """Base test with temp data directory setup/teardown."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_data_dir = storage.DATA_DIR
        storage.DATA_DIR = Path(self.test_dir) / "data"
        storage.USERS_FILE = storage.DATA_DIR / "users.json"
        storage.PROJECTS_FILE = storage.DATA_DIR / "projects.json"
        storage.TASKS_FILE = storage.DATA_DIR / "tasks.json"
        storage.EVENTS_FILE = storage.DATA_DIR / "events.json"
        storage.COMMENTS_FILE = storage.DATA_DIR / "comments.json"
        storage.ensure_data_dir()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        storage.DATA_DIR = self.orig_data_dir
        storage.USERS_FILE = storage.DATA_DIR / "users.json"
        storage.PROJECTS_FILE = storage.DATA_DIR / "projects.json"
        storage.TASKS_FILE = storage.DATA_DIR / "tasks.json"
        storage.EVENTS_FILE = storage.DATA_DIR / "events.json"
        storage.COMMENTS_FILE = storage.DATA_DIR / "comments.json"


# ====================================================================
# Model Tests
# ====================================================================

class TestModels(BaseTestCase):

    def test_user_creation(self):
        u = models.User(id=1, username="alice", email="alice@test.com")
        self.assertEqual(u.username, "alice")
        self.assertEqual(u.role, "member")
        self.assertTrue(u.can_edit())
        self.assertFalse(u.can_delete())

    def test_user_admin(self):
        u = models.User(id=1, username="admin", email="admin@test.com", role="admin")
        self.assertTrue(u.can_edit())
        self.assertTrue(u.can_delete())

    def test_user_viewer(self):
        u = models.User(id=1, username="viewer", email="v@test.com", role="viewer")
        self.assertFalse(u.can_edit())
        self.assertFalse(u.can_delete())

    def test_task_creation_defaults(self):
        t = models.Task(id=1, title="Test", project_id=1)
        self.assertEqual(t.status, "todo")
        self.assertEqual(t.priority, "medium")
        self.assertFalse(t.is_overdue())

    def test_task_overdue(self):
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        t = models.Task(id=1, title="Late", project_id=1, due_date=yesterday)
        self.assertTrue(t.is_overdue())

    def test_task_not_overdue_when_done(self):
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        t = models.Task(id=1, title="Done", project_id=1, due_date=yesterday, status="done")
        self.assertFalse(t.is_overdue())

    def test_task_mark_done(self):
        t = models.Task(id=1, title="Test", project_id=1)
        t.mark_done()
        self.assertEqual(t.status, "done")
        self.assertIsNotNone(t.completed_at)

    def test_task_update_status_valid(self):
        t = models.Task(id=1, title="Test", project_id=1)
        old = t.update_status("in_progress")
        self.assertEqual(old, "todo")
        self.assertEqual(t.status, "in_progress")

    def test_task_update_status_invalid(self):
        t = models.Task(id=1, title="Test", project_id=1)
        with self.assertRaises(ValueError):
            t.update_status("invalid_status")

    def test_task_to_dict(self):
        t = models.Task(id=1, title="Test", project_id=1, tags=["bug"])
        d = t.to_dict()
        self.assertEqual(d["id"], 1)
        self.assertIn("bug", d["tags"])

    def test_event_creation(self):
        e = models.EventLog(id=1, event_type="task_created",
                            entity_type="task", entity_id=1, user_id=1)
        self.assertNotEqual(e.timestamp, "")

    def test_comment_creation(self):
        c = models.Comment(id=1, task_id=1, user_id=1, text="Hello")
        self.assertEqual(c.text, "Hello")
        self.assertNotEqual(c.created_at, "")


# ====================================================================
# Storage Tests
# ====================================================================

class TestStorage(BaseTestCase):

    def test_save_and_load_users(self):
        users = [models.User(id=1, username="alice", email="a@t.com")]
        storage.save_users(users)
        loaded = storage.load_users()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].username, "alice")

    def test_get_user_by_id(self):
        users = [
            models.User(id=1, username="alice", email="a@t.com"),
            models.User(id=2, username="bob", email="b@t.com"),
        ]
        storage.save_users(users)
        self.assertEqual(storage.get_user_by_id(2).username, "bob")
        self.assertIsNone(storage.get_user_by_id(99))

    def test_save_and_load_tasks(self):
        tasks = [
            models.Task(id=1, title="Task A", project_id=1),
            models.Task(id=2, title="Task B", project_id=1, tags=["bug"]),
        ]
        storage.save_tasks(tasks)
        loaded = storage.load_tasks()
        self.assertEqual(len(loaded), 2)
        self.assertIn("bug", loaded[1].tags)

    def test_get_tasks_by_project(self):
        tasks = [
            models.Task(id=1, title="A", project_id=1),
            models.Task(id=2, title="B", project_id=2),
            models.Task(id=3, title="C", project_id=1),
        ]
        storage.save_tasks(tasks)
        p1_tasks = storage.get_tasks_by_project(1)
        self.assertEqual(len(p1_tasks), 2)

    def test_get_tasks_by_assignee(self):
        tasks = [
            models.Task(id=1, title="A", project_id=1, assignee_id=1),
            models.Task(id=2, title="B", project_id=1, assignee_id=2),
            models.Task(id=3, title="C", project_id=1, assignee_id=1),
        ]
        storage.save_tasks(tasks)
        u1_tasks = storage.get_tasks_by_assignee(1)
        self.assertEqual(len(u1_tasks), 2)

    def test_add_event(self):
        e = storage.add_event("task_created", "task", 1, 1, {"title": "Test"})
        self.assertEqual(e.event_type, "task_created")
        events = storage.load_events()
        self.assertEqual(len(events), 1)

    def test_comments_round_trip(self):
        comments = [models.Comment(id=1, task_id=1, user_id=1, text="Hello")]
        storage.save_comments(comments)
        loaded = storage.load_comments()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].text, "Hello")

    def test_next_id_empty(self):
        self.assertEqual(storage.get_next_task_id(), 1)
        self.assertEqual(storage.get_next_user_id(), 1)

    def test_next_id_existing(self):
        storage.save_tasks([models.Task(id=5, title="X", project_id=1)])
        self.assertEqual(storage.get_next_task_id(), 6)


# ====================================================================
# Filter Tests
# ====================================================================

class TestFilters(BaseTestCase):

    def _make_tasks(self):
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
        return [
            models.Task(id=1, title="Bug fix", project_id=1, status="todo",
                         priority="high", tags=["bug"], assignee_id=1,
                         due_date=yesterday),
            models.Task(id=2, title="Feature", project_id=1, status="in_progress",
                         priority="medium", tags=["feature"], assignee_id=2,
                         due_date=tomorrow),
            models.Task(id=3, title="Docs update", project_id=2, status="done",
                         priority="low", tags=["docs"], assignee_id=1,
                         completed_at=datetime.now().isoformat()),
            models.Task(id=4, title="Critical bug", project_id=1, status="blocked",
                         priority="critical", tags=["bug", "urgent"], assignee_id=1),
        ]

    def test_filter_by_status(self):
        tasks = self._make_tasks()
        result = filters.filter_by_status(tasks, "todo")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)

    def test_filter_by_priority(self):
        tasks = self._make_tasks()
        result = filters.filter_by_priority(tasks, "critical")
        self.assertEqual(len(result), 1)

    def test_filter_by_tag(self):
        tasks = self._make_tasks()
        result = filters.filter_by_tag(tasks, "bug")
        self.assertEqual(len(result), 2)

    def test_filter_by_assignee(self):
        tasks = self._make_tasks()
        result = filters.filter_by_assignee(tasks, 1)
        self.assertEqual(len(result), 3)

    def test_filter_overdue(self):
        tasks = self._make_tasks()
        result = filters.filter_overdue(tasks)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)

    def test_filter_due_within(self):
        tasks = self._make_tasks()
        result = filters.filter_due_within(tasks, 3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 2)

    def test_search_tasks(self):
        tasks = self._make_tasks()
        result = filters.search_tasks(tasks, "bug")
        self.assertEqual(len(result), 2)

    def test_sort_by_priority(self):
        tasks = self._make_tasks()
        result = filters.sort_tasks(tasks, "priority")
        self.assertEqual(result[0].priority, "critical")
        self.assertEqual(result[-1].priority, "low")

    def test_apply_filters_combined(self):
        tasks = self._make_tasks()
        result = filters.apply_filters(tasks, {"tag": "bug", "sort_by": "priority"})
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].priority, "critical")


# ====================================================================
# Validator Tests
# ====================================================================

class TestValidators(BaseTestCase):

    def test_valid_title(self):
        ok, msg = validators.validate_title("Good Title")
        self.assertTrue(ok)

    def test_empty_title(self):
        ok, msg = validators.validate_title("")
        self.assertFalse(ok)

    def test_long_title(self):
        ok, msg = validators.validate_title("x" * 201)
        self.assertFalse(ok)

    def test_valid_email(self):
        ok, msg = validators.validate_email("test@example.com")
        self.assertTrue(ok)

    def test_invalid_email(self):
        ok, msg = validators.validate_email("not-an-email")
        self.assertFalse(ok)

    def test_valid_username(self):
        ok, msg = validators.validate_username("alice_99")
        self.assertTrue(ok)

    def test_short_username(self):
        ok, msg = validators.validate_username("ab")
        self.assertFalse(ok)

    def test_valid_status(self):
        ok, msg = validators.validate_status("in_progress")
        self.assertTrue(ok)

    def test_invalid_status(self):
        ok, msg = validators.validate_status("flying")
        self.assertFalse(ok)

    def test_valid_date(self):
        ok, msg = validators.validate_date("2025-06-15")
        self.assertTrue(ok)

    def test_invalid_date(self):
        ok, msg = validators.validate_date("not-a-date")
        self.assertFalse(ok)

    def test_validate_tags_valid(self):
        ok, msg = validators.validate_tags(["bug", "feature"])
        self.assertTrue(ok)

    def test_validate_tags_invalid_chars(self):
        ok, msg = validators.validate_tags(["bug fix"])
        self.assertFalse(ok)

    def test_validate_task_create_full(self):
        ok, errors = validators.validate_task_create(
            "Test Task", 1, priority="high", due_date="2025-12-31", tags=["bug"]
        )
        self.assertTrue(ok)
        self.assertEqual(len(errors), 0)

    def test_validate_task_create_invalid(self):
        ok, errors = validators.validate_task_create(
            "", -1, priority="ultra", due_date="nope", tags=["bug fix!!"]
        )
        self.assertFalse(ok)
        self.assertGreater(len(errors), 0)


# ====================================================================
# Exporter Tests
# ====================================================================

class TestExporters(BaseTestCase):

    def _make_tasks(self):
        return [
            models.Task(id=1, title="A", project_id=1, tags=["bug"]),
            models.Task(id=2, title="B", project_id=1, status="done",
                         completed_at=datetime.now().isoformat()),
        ]

    def test_export_csv(self):
        tasks = self._make_tasks()
        filepath = os.path.join(self.test_dir, "out.csv")
        count = exporters.export_to_csv(tasks, filepath)
        self.assertEqual(count, 2)
        self.assertTrue(os.path.exists(filepath))
        with open(filepath) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 3)  # header + 2 rows

    def test_export_json(self):
        tasks = self._make_tasks()
        filepath = os.path.join(self.test_dir, "out.json")
        count = exporters.export_to_json(tasks, filepath)
        self.assertEqual(count, 2)
        with open(filepath) as f:
            data = json.load(f)
        self.assertEqual(data["count"], 2)

    def test_export_markdown(self):
        tasks = self._make_tasks()
        filepath = os.path.join(self.test_dir, "out.md")
        count = exporters.export_to_markdown(tasks, filepath)
        self.assertEqual(count, 2)
        with open(filepath) as f:
            content = f.read()
        self.assertIn("| A |", content)

    def test_export_empty(self):
        self.assertEqual(exporters.export_to_csv([], "x.csv"), 0)
        self.assertEqual(exporters.export_to_json([], "x.json"), 0)

    def test_generate_summary(self):
        tasks = self._make_tasks()
        s = exporters.generate_summary(tasks)
        self.assertEqual(s["total"], 2)
        self.assertIn("todo", s["by_status"])


# ====================================================================
# Plugin Tests
# ====================================================================

class TestPlugins(BaseTestCase):

    def test_register_and_fire(self):
        pm = plugins.PluginManager()
        results = []
        pm.register("task_post_create", lambda **kw: results.append(kw))
        pm.fire("task_post_create", task_id=1)
        self.assertEqual(len(results), 1)

    def test_unregister(self):
        hook = plugins.PluginHook("test")
        cb = lambda **kw: None
        hook.register(cb)
        self.assertEqual(hook.callback_count, 1)
        hook.unregister(cb)
        self.assertEqual(hook.callback_count, 0)

    def test_fire_empty_hook(self):
        pm = plugins.PluginManager()
        result = pm.fire("nonexistent_hook")
        self.assertEqual(result, [])

    def test_callback_error_handling(self):
        hook = plugins.PluginHook("test")
        hook.register(lambda **kw: 1 / 0)
        results = hook.fire()
        self.assertIn("error", results[0])

    def test_list_hooks(self):
        pm = plugins.PluginManager()
        hooks = pm.list_hooks()
        self.assertIn("task_post_create", hooks)
        self.assertIn("task_status_change", hooks)


# ====================================================================
# Formatter Tests
# ====================================================================

class TestFormatters(BaseTestCase):

    def test_format_task_line(self):
        t = models.Task(id=1, title="Bug", project_id=1, priority="high", tags=["bug"])
        line = formatters.format_task_line(t)
        self.assertIn("#1", line)
        self.assertIn("Bug", line)
        self.assertIn("!!", line)

    def test_format_task_detail(self):
        t = models.Task(id=1, title="Bug", project_id=1, description="Fix it")
        detail = formatters.format_task_detail(t)
        self.assertIn("Fix it", detail)
        self.assertIn("Task #1", detail)

    def test_format_task_table(self):
        tasks = [models.Task(id=i, title=f"Task {i}", project_id=1) for i in range(3)]
        table = formatters.format_task_table(tasks)
        self.assertIn("Total: 3 tasks", table)

    def test_format_task_table_empty(self):
        self.assertIn("no tasks", formatters.format_task_table([]))

    def test_format_summary(self):
        summary = {"total": 5, "by_status": {"todo": 3, "done": 2},
                    "by_priority": {"high": 2, "low": 3}, "overdue": 1}
        output = formatters.format_summary(summary)
        self.assertIn("Total Tasks: 5", output)
        self.assertIn("Overdue: 1", output)

    def test_format_event_line(self):
        e = models.EventLog(id=1, event_type="task_created", entity_type="task",
                            entity_id=1, user_id=1, details={"title": "X"})
        line = formatters.format_event_line(e)
        self.assertIn("task_created", line)


if __name__ == "__main__":
    unittest.main()
