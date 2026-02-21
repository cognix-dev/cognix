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
        storage.RECURRING_FILE = storage.DATA_DIR / "recurring.json"
        storage.DEPENDENCIES_FILE = storage.DATA_DIR / "dependencies.json"
        storage.ensure_data_dir()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        storage.DATA_DIR = self.orig_data_dir
        storage.USERS_FILE = storage.DATA_DIR / "users.json"
        storage.PROJECTS_FILE = storage.DATA_DIR / "projects.json"
        storage.TASKS_FILE = storage.DATA_DIR / "tasks.json"
        storage.EVENTS_FILE = storage.DATA_DIR / "events.json"
        storage.COMMENTS_FILE = storage.DATA_DIR / "comments.json"
        storage.RECURRING_FILE = storage.DATA_DIR / "recurring.json"
        storage.DEPENDENCIES_FILE = storage.DATA_DIR / "dependencies.json"

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
        self.assertIsNone(t.assignee_id)

    def test_task_overdue(self):
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        t = models.Task(id=1, title="Test", project_id=1, due_date=yesterday)
        self.assertTrue(t.is_overdue())

    def test_task_not_overdue_when_done(self):
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        t = models.Task(id=1, title="Test", project_id=1, due_date=yesterday, status="done")
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
            t.update_status("invalid")

    def test_task_to_dict(self):
        t = models.Task(id=1, title="Test", project_id=1, tags=["bug", "urgent"])
        d = t.to_dict()
        self.assertEqual(d["id"], 1)
        self.assertEqual(d["title"], "Test")
        self.assertEqual(d["tags"], ["bug", "urgent"])

    def test_event_creation(self):
        e = models.EventLog(id=1, event_type="task_created", entity_type="task",
                            entity_id=1, user_id=1)
        self.assertEqual(e.event_type, "task_created")
        self.assertIsNotNone(e.timestamp)

    def test_comment_creation(self):
        c = models.Comment(id=1, task_id=1, user_id=1, text="Great work!")
        self.assertEqual(c.text, "Great work!")
        self.assertIsNotNone(c.created_at)

# ====================================================================
# Storage Tests
# ====================================================================

class TestStorage(BaseTestCase):

    def test_save_and_load_users(self):
        users = [
            models.User(id=1, username="alice", email="alice@test.com"),
            models.User(id=2, username="bob", email="bob@test.com"),
        ]
        storage.save_users(users)
        loaded = storage.load_users()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].username, "alice")

    def test_get_user_by_id(self):
        users = [models.User(id=1, username="alice", email="alice@test.com")]
        storage.save_users(users)
        user = storage.get_user_by_id(1)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "alice")

    def test_save_and_load_tasks(self):
        tasks = [models.Task(id=1, title="Task 1", project_id=1)]
        storage.save_tasks(tasks)
        loaded = storage.load_tasks()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].title, "Task 1")

    def test_get_tasks_by_project(self):
        tasks = [
            models.Task(id=1, title="T1", project_id=1),
            models.Task(id=2, title="T2", project_id=2),
            models.Task(id=3, title="T3", project_id=1),
        ]
        storage.save_tasks(tasks)
        proj1_tasks = storage.get_tasks_by_project(1)
        self.assertEqual(len(proj1_tasks), 2)

    def test_get_tasks_by_assignee(self):
        tasks = [
            models.Task(id=1, title="T1", project_id=1, assignee_id=10),
            models.Task(id=2, title="T2", project_id=1, assignee_id=20),
            models.Task(id=3, title="T3", project_id=1, assignee_id=10),
        ]
        storage.save_tasks(tasks)
        user10_tasks = storage.get_tasks_by_assignee(10)
        self.assertEqual(len(user10_tasks), 2)

    def test_add_event(self):
        event = storage.add_event("task_created", "task", 1, 1, {"title": "Test"})
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "task_created")

    def test_comments_round_trip(self):
        comments = [models.Comment(id=1, task_id=1, user_id=1, text="Hello")]
        storage.save_comments(comments)
        loaded = storage.load_comments()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].text, "Hello")

    def test_next_id_empty(self):
        self.assertEqual(storage.get_next_user_id(), 1)
        self.assertEqual(storage.get_next_task_id(), 1)

    def test_next_id_existing(self):
        users = [models.User(id=5, username="alice", email="a@test.com")]
        storage.save_users(users)
        self.assertEqual(storage.get_next_user_id(), 6)

# ====================================================================
# Filter Tests
# ====================================================================

class TestFilters(BaseTestCase):

    def _make_tasks(self):
        return [
            models.Task(id=1, title="T1", project_id=1, status="todo", priority="high", tags=["bug"]),
            models.Task(id=2, title="T2", project_id=1, status="done", priority="low"),
            models.Task(id=3, title="T3", project_id=2, status="in_progress", priority="high", assignee_id=10),
        ]

    def test_filter_by_status(self):
        tasks = self._make_tasks()
        result = filters.filter_by_status(tasks, "done")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 2)

    def test_filter_by_priority(self):
        tasks = self._make_tasks()
        result = filters.filter_by_priority(tasks, "high")
        self.assertEqual(len(result), 2)

    def test_filter_by_tag(self):
        tasks = self._make_tasks()
        result = filters.filter_by_tag(tasks, "bug")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)

    def test_filter_by_assignee(self):
        tasks = self._make_tasks()
        result = filters.filter_by_assignee(tasks, 10)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 3)

    def test_filter_overdue(self):
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        tasks = [
            models.Task(id=1, title="T1", project_id=1, due_date=yesterday),
            models.Task(id=2, title="T2", project_id=1),
        ]
        result = filters.filter_overdue(tasks)
        self.assertEqual(len(result), 1)

    def test_filter_due_within(self):
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
        tasks = [
            models.Task(id=1, title="T1", project_id=1, due_date=tomorrow),
            models.Task(id=2, title="T2", project_id=1),
        ]
        result = filters.filter_due_within(tasks, 7)
        self.assertEqual(len(result), 1)

    def test_search_tasks(self):
        tasks = [
            models.Task(id=1, title="Fix bug", project_id=1),
            models.Task(id=2, title="Add feature", project_id=1, description="bug fix"),
            models.Task(id=3, title="Update docs", project_id=1),
        ]
        result = filters.search_tasks(tasks, "bug")
        self.assertEqual(len(result), 2)

    def test_sort_by_priority(self):
        tasks = self._make_tasks()
        result = filters.sort_tasks(tasks, "priority")
        self.assertEqual(result[0].priority, "high")

    def test_apply_filters_combined(self):
        tasks = self._make_tasks()
        result = filters.apply_filters(tasks, {"status": "todo", "priority": "high"})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)

# ====================================================================
# Validator Tests
# ====================================================================

class TestValidators(BaseTestCase):

    def test_valid_title(self):
        ok, msg = validators.validate_title("Valid Title")
        self.assertTrue(ok)

    def test_empty_title(self):
        ok, msg = validators.validate_title("")
        self.assertFalse(ok)

    def test_long_title(self):
        ok, msg = validators.validate_title("x" * 201)
        self.assertFalse(ok)

    def test_valid_email(self):
        ok, msg = validators.validate_email("user@example.com")
        self.assertTrue(ok)

    def test_invalid_email(self):
        ok, msg = validators.validate_email("not-an-email")
        self.assertFalse(ok)

    def test_valid_username(self):
        ok, msg = validators.validate_username("alice_123")
        self.assertTrue(ok)

    def test_short_username(self):
        ok, msg = validators.validate_username("ab")
        self.assertFalse(ok)

    def test_valid_status(self):
        ok, msg = validators.validate_status("todo")
        self.assertTrue(ok)

    def test_invalid_status(self):
        ok, msg = validators.validate_status("invalid")
        self.assertFalse(ok)

    def test_valid_date(self):
        ok, msg = validators.validate_date("2024-12-31")
        self.assertTrue(ok)

    def test_invalid_date(self):
        ok, msg = validators.validate_date("not-a-date")
        self.assertFalse(ok)

    def test_validate_tags_valid(self):
        ok, msg = validators.validate_tags(["bug", "urgent"])
        self.assertTrue(ok)

    def test_validate_tags_invalid_chars(self):
        ok, msg = validators.validate_tags(["bug!", "urgent"])
        self.assertFalse(ok)

    def test_validate_task_create_full(self):
        ok, errors = validators.validate_task_create(
            "Valid Task", 1, "todo", "high", "2024-12-31", ["bug"]
        )
        self.assertTrue(ok)

    def test_validate_task_create_invalid(self):
        ok, errors = validators.validate_task_create(
            "", 0, "invalid", "invalid", "bad-date", ["bad!"]
        )
        self.assertFalse(ok)
        self.assertGreater(len(errors), 0)

# ====================================================================
# Exporter Tests
# ====================================================================

class TestExporters(BaseTestCase):

    def _make_tasks(self):
        return [
            models.Task(id=1, title="Task 1", project_id=1, status="todo"),
            models.Task(id=2, title="Task 2", project_id=1, status="done"),
        ]

    def test_export_csv(self):
        tasks = self._make_tasks()
        filepath = os.path.join(self.test_dir, "test.csv")
        count = exporters.export_to_csv(tasks, filepath)
        self.assertEqual(count, 2)
        self.assertTrue(os.path.exists(filepath))

    def test_export_json(self):
        tasks = self._make_tasks()
        filepath = os.path.join(self.test_dir, "test.json")
        count = exporters.export_to_json(tasks, filepath)
        self.assertEqual(count, 2)
        self.assertTrue(os.path.exists(filepath))

    def test_export_markdown(self):
        tasks = self._make_tasks()
        filepath = os.path.join(self.test_dir, "test.md")
        count = exporters.export_to_markdown(tasks, filepath)
        self.assertEqual(count, 2)
        self.assertTrue(os.path.exists(filepath))

    def test_export_empty(self):
        filepath = os.path.join(self.test_dir, "empty.csv")
        count = exporters.export_to_csv([], filepath)
        self.assertEqual(count, 0)

    def test_generate_summary(self):
        tasks = self._make_tasks()
        summary = exporters.generate_summary(tasks)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["by_status"]["todo"], 1)
        self.assertEqual(summary["by_status"]["done"], 1)

# ====================================================================
# Plugin Tests
# ====================================================================

class TestPlugins(BaseTestCase):

    def test_register_and_fire(self):
        hook = plugins.PluginHook("test")
        results = []
        hook.register(lambda **kw: results.append("called"))
        hook.fire()
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

# ====================================================================
# Recurring Tasks Tests
# ====================================================================

class TestRecurringTasks(BaseTestCase):

    def test_recurring_rule_should_run_active(self):
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=yesterday, active=True
        )
        self.assertTrue(rule.should_run())

    def test_recurring_rule_should_run_inactive(self):
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=yesterday, active=False
        )
        self.assertFalse(rule.should_run())

    def test_recurring_rule_should_run_future(self):
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=tomorrow, active=True
        )
        self.assertFalse(rule.should_run())

    def test_recurring_rule_should_run_past_end_date(self):
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        two_days_ago = (datetime.now() - timedelta(days=2)).date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=yesterday, end_date=two_days_ago, active=True
        )
        self.assertFalse(rule.should_run())

    def test_recurring_rule_advance_daily(self):
        today = datetime.now().date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=today, active=True
        )
        old_count = rule.created_count
        rule.advance()
        self.assertNotEqual(rule.next_run, today)
        self.assertEqual(rule.created_count, old_count + 1)

    def test_recurring_rule_advance_weekly(self):
        today = datetime.now().date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="weekly",
            next_run=today, active=True
        )
        rule.advance()
        expected = (datetime.now() + timedelta(weeks=1)).date().isoformat()
        self.assertEqual(rule.next_run[:10], expected[:10])

    def test_recurring_rule_advance_monthly(self):
        today = datetime.now().date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="monthly",
            next_run=today, active=True
        )
        rule.advance()
        # Just check it advanced
        self.assertNotEqual(rule.next_run, today)

    def test_recurring_storage_round_trip(self):
        rule = models.RecurringRule(
            id=1, task_template_id=5, frequency="daily",
            next_run="2024-12-01", active=True
        )
        storage.save_recurring_rules([rule])
        loaded = storage.load_recurring_rules()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].frequency, "daily")

    def test_cmd_run_recurring_creates_tasks(self):
        # Setup: create a task template
        task = models.Task(id=1, title="Template", project_id=1)
        storage.save_tasks([task])
        
        # Create a rule that should run
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=yesterday, active=True
        )
        storage.save_recurring_rules([rule])
        
        # Run recurring
        commands.cmd_run_recurring(user_id=1)
        
        # Check task was created
        tasks = storage.load_tasks()
        self.assertEqual(len(tasks), 2)  # Original + new

    def test_recurring_with_end_date_past(self):
        # Setup task template
        task = models.Task(id=1, title="Template", project_id=1)
        storage.save_tasks([task])
        
        # Create rule with end_date in the past
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        two_days_ago = (datetime.now() - timedelta(days=2)).date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=yesterday, end_date=two_days_ago, active=True
        )
        storage.save_recurring_rules([rule])
        
        # Run recurring
        commands.cmd_run_recurring(user_id=1)
        
        # Should not create new task
        tasks = storage.load_tasks()
        self.assertEqual(len(tasks), 1)  # Only original

    def test_cmd_cancel_recurring(self):
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run="2024-12-01", active=True
        )
        storage.save_recurring_rules([rule])
        
        commands.cmd_cancel_recurring(1)
        
        loaded = storage.load_recurring_rules()
        self.assertFalse(loaded[0].active)

# ====================================================================
# Dependency Tests
# ====================================================================

class TestDependencies(BaseTestCase):

    def test_dependency_creation_and_storage(self):
        dep = models.TaskDependency(id=1, task_id=2, depends_on_id=1)
        storage.save_dependencies([dep])
        loaded = storage.load_dependencies()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].task_id, 2)

    def test_self_dependency_rejection(self):
        task = models.Task(id=1, title="Task", project_id=1)
        storage.save_tasks([task])
        
        result = commands.cmd_add_dependency(1, 1)
        self.assertFalse(result)

    def test_duplicate_dependency_rejection(self):
        task1 = models.Task(id=1, title="Task1", project_id=1)
        task2 = models.Task(id=2, title="Task2", project_id=1)
        storage.save_tasks([task1, task2])
        
        commands.cmd_add_dependency(2, 1)
        result = commands.cmd_add_dependency(2, 1)
        self.assertFalse(result)

    def test_circular_dependency_direct(self):
        task1 = models.Task(id=1, title="Task1", project_id=1)
        task2 = models.Task(id=2, title="Task2", project_id=1)
        storage.save_tasks([task1, task2])
        
        commands.cmd_add_dependency(1, 2)
        result = commands.cmd_add_dependency(2, 1)
        self.assertFalse(result)

    def test_circular_dependency_transitive(self):
        task1 = models.Task(id=1, title="Task1", project_id=1)
        task2 = models.Task(id=2, title="Task2", project_id=1)
        task3 = models.Task(id=3, title="Task3", project_id=1)
        storage.save_tasks([task1, task2, task3])
        
        commands.cmd_add_dependency(1, 2)
        commands.cmd_add_dependency(2, 3)
        result = commands.cmd_add_dependency(3, 1)
        self.assertFalse(result)

    def test_delete_task_removes_dependencies(self):
        task1 = models.Task(id=1, title="Task1", project_id=1)
        task2 = models.Task(id=2, title="Task2", project_id=1)
        storage.save_tasks([task1, task2])
        
        commands.cmd_add_dependency(2, 1)
        deps = storage.load_dependencies()
        self.assertEqual(len(deps), 1)
        
        commands.cmd_delete_task(1, user_id=1)
        deps = storage.load_dependencies()
        self.assertEqual(len(deps), 0)

    def test_status_change_warns_incomplete_dependencies(self):
        task1 = models.Task(id=1, title="Task1", project_id=1, status="todo")
        task2 = models.Task(id=2, title="Task2", project_id=1, status="todo")
        storage.save_tasks([task1, task2])
        
        commands.cmd_add_dependency(2, 1)
        
        # Capture stderr to check for warning
        import io
        from contextlib import redirect_stderr
        
        f = io.StringIO()
        with redirect_stderr(f):
            commands.cmd_update_task(2, status="done")
        
        output = f.getvalue()
        self.assertIn("WARNING", output)

# ====================================================================
# Dashboard Tests
# ====================================================================

class TestDashboard(BaseTestCase):

    def test_dashboard_no_data(self):
        result = commands.cmd_dashboard(days=7)
        self.assertTrue(result)

    def test_dashboard_counts_created_in_period(self):
        now = datetime.now()
        recent = (now - timedelta(days=3)).isoformat()
        old = (now - timedelta(days=10)).isoformat()
        
        tasks = [
            models.Task(id=1, title="Recent", project_id=1, created_at=recent),
            models.Task(id=2, title="Old", project_id=1, created_at=old),
        ]
        storage.save_tasks(tasks)
        
        # Just verify it runs without error
        result = commands.cmd_dashboard(days=7)
        self.assertTrue(result)

    def test_dashboard_counts_completed_in_period(self):
        now = datetime.now()
        recent = (now - timedelta(days=3)).isoformat()
        
        task = models.Task(id=1, title="Done", project_id=1, status="done", completed_at=recent)
        storage.save_tasks([task])
        
        result = commands.cmd_dashboard(days=7)
        self.assertTrue(result)

    def test_dashboard_completion_rate(self):
        now = datetime.now()
        recent = (now - timedelta(days=3)).isoformat()
        
        tasks = [
            models.Task(id=1, title="Done", project_id=1, status="done", 
                       created_at=recent, completed_at=recent),
            models.Task(id=2, title="Todo", project_id=1, status="todo", created_at=recent),
        ]
        storage.save_tasks(tasks)
        
        result = commands.cmd_dashboard(days=7)
        self.assertTrue(result)

    def test_dashboard_average_completion_time(self):
        now = datetime.now()
        start = (now - timedelta(days=3)).isoformat()
        end = (now - timedelta(days=2)).isoformat()
        
        task = models.Task(id=1, title="Done", project_id=1, status="done",
                          created_at=start, completed_at=end)
        storage.save_tasks([task])
        
        result = commands.cmd_dashboard(days=7)
        self.assertTrue(result)

    def test_format_dashboard(self):
        data = {
            "days": 7,
            "tasks_created": 5,
            "tasks_completed": 3,
            "completion_rate": 60.0,
            "avg_completion_time": "2.5 hours",
            "overdue_count": 1,
            "by_status": {"todo": 2, "done": 3},
            "most_active_user": "User #1: alice",
            "busiest_project": "Project #1: Web App"
        }
        output = formatters.format_dashboard(data)
        self.assertIn("ACTIVITY DASHBOARD", output)
        self.assertIn("60.0%", output)

if __name__ == "__main__":
    unittest.main()