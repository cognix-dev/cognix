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
        self.assertIsNone(t.completed_at)

    def test_task_overdue(self):
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        t = models.Task(id=1, title="Test", project_id=1, due_date=yesterday, status="todo")
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
        t = models.Task(id=1, title="Test", project_id=1, tags=["bug"])
        d = t.to_dict()
        self.assertEqual(d["title"], "Test")
        self.assertIn("bug", d["tags"])

    def test_event_creation(self):
        e = models.EventLog(id=1, event_type="test", entity_type="task",
                            entity_id=1, user_id=1)
        self.assertIsNotNone(e.timestamp)

    def test_comment_creation(self):
        c = models.Comment(id=1, task_id=1, user_id=1, text="Hello")
        self.assertEqual(c.text, "Hello")
        self.assertIsNotNone(c.created_at)

# ====================================================================
# Storage Tests
# ====================================================================

class TestStorage(BaseTestCase):

    def test_save_and_load_users(self):
        users = [models.User(id=1, username="alice", email="a@test.com")]
        storage.save_users(users)
        loaded = storage.load_users()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].username, "alice")

    def test_get_user_by_id(self):
        users = [models.User(id=1, username="alice", email="a@test.com")]
        storage.save_users(users)
        u = storage.get_user_by_id(1)
        self.assertIsNotNone(u)
        self.assertEqual(u.username, "alice")

    def test_save_and_load_tasks(self):
        tasks = [models.Task(id=1, title="Test", project_id=1)]
        storage.save_tasks(tasks)
        loaded = storage.load_tasks()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].title, "Test")

    def test_get_tasks_by_project(self):
        tasks = [
            models.Task(id=1, title="T1", project_id=1),
            models.Task(id=2, title="T2", project_id=2),
        ]
        storage.save_tasks(tasks)
        p1_tasks = storage.get_tasks_by_project(1)
        self.assertEqual(len(p1_tasks), 1)

    def test_get_tasks_by_assignee(self):
        tasks = [
            models.Task(id=1, title="T1", project_id=1, assignee_id=1),
            models.Task(id=2, title="T2", project_id=1, assignee_id=2),
        ]
        storage.save_tasks(tasks)
        u1_tasks = storage.get_tasks_by_assignee(1)
        self.assertEqual(len(u1_tasks), 1)

    def test_add_event(self):
        storage.add_event("test", "task", 1, 1, {"key": "value"})
        events = storage.load_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "test")

    def test_comments_round_trip(self):
        comments = [models.Comment(id=1, task_id=1, user_id=1, text="Hi")]
        storage.save_comments(comments)
        loaded = storage.load_comments()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].text, "Hi")

    def test_next_id_empty(self):
        self.assertEqual(storage.get_next_user_id(), 1)
        self.assertEqual(storage.get_next_task_id(), 1)

    def test_next_id_existing(self):
        users = [models.User(id=5, username="test", email="t@test.com")]
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
            models.Task(id=3, title="T3", project_id=2, status="todo", priority="high", assignee_id=1),
        ]

    def test_filter_by_status(self):
        tasks = self._make_tasks()
        result = filters.filter_by_status(tasks, "todo")
        self.assertEqual(len(result), 2)

    def test_filter_by_priority(self):
        tasks = self._make_tasks()
        result = filters.filter_by_priority(tasks, "high")
        self.assertEqual(len(result), 2)

    def test_filter_by_tag(self):
        tasks = self._make_tasks()
        result = filters.filter_by_tag(tasks, "bug")
        self.assertEqual(len(result), 1)

    def test_filter_by_assignee(self):
        tasks = self._make_tasks()
        result = filters.filter_by_assignee(tasks, 1)
        self.assertEqual(len(result), 1)

    def test_filter_overdue(self):
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        tasks = [
            models.Task(id=1, title="T1", project_id=1, due_date=yesterday, status="todo"),
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
        result = filters.filter_due_within(tasks, 2)
        self.assertEqual(len(result), 1)

    def test_search_tasks(self):
        tasks = self._make_tasks()
        result = filters.search_tasks(tasks, "T2")
        self.assertEqual(len(result), 1)

    def test_sort_by_priority(self):
        tasks = self._make_tasks()
        result = filters.sort_tasks(tasks, "priority")
        self.assertEqual(result[0].priority, "high")

    def test_apply_filters_combined(self):
        tasks = self._make_tasks()
        result = filters.apply_filters(tasks, {"status": "todo", "priority": "high"})
        self.assertEqual(len(result), 2)

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
        ok, msg = validators.validate_email("test@example.com")
        self.assertTrue(ok)

    def test_invalid_email(self):
        ok, msg = validators.validate_email("invalid")
        self.assertFalse(ok)

    def test_valid_username(self):
        ok, msg = validators.validate_username("alice")
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
        ok, msg = validators.validate_date("2024-01-01")
        self.assertTrue(ok)

    def test_invalid_date(self):
        ok, msg = validators.validate_date("invalid")
        self.assertFalse(ok)

    def test_validate_tags_valid(self):
        ok, msg = validators.validate_tags(["bug", "feature"])
        self.assertTrue(ok)

    def test_validate_tags_invalid_chars(self):
        ok, msg = validators.validate_tags(["bug!", "test"])
        self.assertFalse(ok)

    def test_validate_task_create_full(self):
        ok, errors = validators.validate_task_create("Test", 1, "todo", "high", "2024-01-01", ["bug"])
        self.assertTrue(ok)

    def test_validate_task_create_invalid(self):
        ok, errors = validators.validate_task_create("", 1)
        self.assertFalse(ok)
        self.assertGreater(len(errors), 0)

# ====================================================================
# Exporter Tests
# ====================================================================

class TestExporters(BaseTestCase):

    def _make_tasks(self):
        return [
            models.Task(id=1, title="T1", project_id=1, status="todo"),
            models.Task(id=2, title="T2", project_id=1, status="done"),
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

# ====================================================================
# NEW TESTS: Recurring Tasks
# ====================================================================

class TestRecurringTasks(BaseTestCase):

    def test_recurring_rule_should_run_active_and_due(self):
        today = datetime.now().date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=today, active=True
        )
        self.assertTrue(rule.should_run())

    def test_recurring_rule_should_run_inactive(self):
        today = datetime.now().date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=today, active=False
        )
        self.assertFalse(rule.should_run())

    def test_recurring_rule_should_run_future_date(self):
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=tomorrow, active=True
        )
        self.assertFalse(rule.should_run())

    def test_recurring_rule_should_run_past_end_date(self):
        today = datetime.now().date().isoformat()
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=today, end_date=yesterday, active=True
        )
        self.assertFalse(rule.should_run())

    def test_recurring_rule_advance_daily(self):
        today = datetime.now().date()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=today.isoformat(), active=True
        )
        rule.advance()
        expected = (today + timedelta(days=1)).isoformat()
        self.assertEqual(rule.next_run, expected)
        self.assertEqual(rule.created_count, 1)

    def test_recurring_rule_advance_weekly(self):
        today = datetime.now().date()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="weekly",
            next_run=today.isoformat(), active=True
        )
        rule.advance()
        expected = (today + timedelta(weeks=1)).isoformat()
        self.assertEqual(rule.next_run, expected)

    def test_recurring_rule_advance_biweekly(self):
        today = datetime.now().date()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="biweekly",
            next_run=today.isoformat(), active=True
        )
        rule.advance()
        expected = (today + timedelta(weeks=2)).isoformat()
        self.assertEqual(rule.next_run, expected)

    def test_recurring_rule_advance_monthly(self):
        today = datetime.now().date()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="monthly",
            next_run=today.isoformat(), active=True
        )
        rule.advance()
        expected = (today + timedelta(days=30)).isoformat()
        self.assertEqual(rule.next_run, expected)

    def test_recurring_storage_round_trip(self):
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run="2024-01-01", active=True
        )
        storage.save_recurring_rules([rule])
        loaded = storage.load_recurring_rules()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].frequency, "daily")

    def test_cmd_run_recurring_creates_tasks(self):
        # Setup: create user, project, template task
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Template Task", 1)
        
        # Create recurring rule with today's date
        today = datetime.now().date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=today, active=True
        )
        storage.save_recurring_rules([rule])
        
        # Run recurring
        commands.cmd_run_recurring(1)
        
        # Check task was created
        tasks = storage.load_tasks()
        self.assertEqual(len(tasks), 2)  # template + new task
        
        # Check rule was advanced
        rules = storage.load_recurring_rules()
        self.assertNotEqual(rules[0].next_run, today)
        self.assertEqual(rules[0].created_count, 1)

    def test_cmd_run_recurring_respects_end_date(self):
        # Setup
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Template Task", 1)
        
        # Create rule with end_date in the past
        today = datetime.now().date().isoformat()
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run=today, end_date=yesterday, active=True
        )
        storage.save_recurring_rules([rule])
        
        # Run recurring
        commands.cmd_run_recurring(1)
        
        # Check no new task was created
        tasks = storage.load_tasks()
        self.assertEqual(len(tasks), 1)  # only template

    def test_cmd_cancel_recurring(self):
        rule = models.RecurringRule(
            id=1, task_template_id=1, frequency="daily",
            next_run="2024-01-01", active=True
        )
        storage.save_recurring_rules([rule])
        
        commands.cmd_cancel_recurring(1)
        
        rules = storage.load_recurring_rules()
        self.assertFalse(rules[0].active)

# ====================================================================
# NEW TESTS: Task Dependencies
# ====================================================================

class TestTaskDependencies(BaseTestCase):

    def test_dependency_storage_round_trip(self):
        dep = models.TaskDependency(id=1, task_id=2, depends_on_id=1)
        storage.save_dependencies([dep])
        loaded = storage.load_dependencies()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].task_id, 2)

    def test_cmd_add_dependency_success(self):
        # Setup
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Task 1", 1)
        commands.cmd_add_task("Task 2", 1)
        
        # Add dependency
        result = commands.cmd_add_dependency(2, 1)
        self.assertTrue(result)
        
        deps = storage.load_dependencies()
        self.assertEqual(len(deps), 1)

    def test_cmd_add_dependency_self_dependency(self):
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Task 1", 1)
        
        result = commands.cmd_add_dependency(1, 1)
        self.assertFalse(result)

    def test_cmd_add_dependency_duplicate(self):
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Task 1", 1)
        commands.cmd_add_task("Task 2", 1)
        
        commands.cmd_add_dependency(2, 1)
        result = commands.cmd_add_dependency(2, 1)
        self.assertFalse(result)

    def test_validate_circular_dependency_direct(self):
        # A depends on B
        dep1 = models.TaskDependency(id=1, task_id=2, depends_on_id=1)
        
        # Try to add B depends on A (creates cycle)
        is_valid, error = validators.validate_no_circular_dependency(1, 2, [dep1])
        self.assertFalse(is_valid)
        self.assertIn("Circular", error)

    def test_validate_circular_dependency_transitive(self):
        # A depends on B, B depends on C
        dep1 = models.TaskDependency(id=1, task_id=2, depends_on_id=1)
        dep2 = models.TaskDependency(id=2, task_id=3, depends_on_id=2)
        
        # Try to add C depends on A (creates cycle A->B->C->A)
        is_valid, error = validators.validate_no_circular_dependency(1, 3, [dep1, dep2])
        self.assertFalse(is_valid)

    def test_validate_no_circular_dependency_valid_chain(self):
        # A depends on B, B depends on C (no cycle)
        dep1 = models.TaskDependency(id=1, task_id=2, depends_on_id=1)
        dep2 = models.TaskDependency(id=2, task_id=3, depends_on_id=2)
        
        # Try to add D depends on C (no cycle)
        is_valid, error = validators.validate_no_circular_dependency(4, 3, [dep1, dep2])
        self.assertTrue(is_valid)

    def test_cmd_delete_task_removes_dependencies(self):
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Task 1", 1)
        commands.cmd_add_task("Task 2", 1)
        commands.cmd_add_task("Task 3", 1)
        
        # Add dependencies
        commands.cmd_add_dependency(2, 1)  # Task 2 depends on Task 1
        commands.cmd_add_dependency(3, 1)  # Task 3 depends on Task 1
        
        # Delete Task 1
        commands.cmd_delete_task(1, 1)
        
        # Check dependencies are removed
        deps = storage.load_dependencies()
        self.assertEqual(len(deps), 0)

    def test_cmd_update_task_warns_incomplete_dependencies(self):
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Task 1", 1)
        commands.cmd_add_task("Task 2", 1)
        
        # Task 2 depends on Task 1
        commands.cmd_add_dependency(2, 1)
        
        # Try to mark Task 2 as done (Task 1 is still todo)
        # Should warn but still allow
        result = commands.cmd_update_task(2, status="done")
        self.assertTrue(result)
        
        task = storage.get_task_by_id(2)
        self.assertEqual(task.status, "done")

# ====================================================================
# NEW TESTS: Activity Dashboard
# ====================================================================

class TestActivityDashboard(BaseTestCase):

    def test_dashboard_no_data(self):
        result = commands.cmd_dashboard(days=7)
        self.assertTrue(result)

    def test_dashboard_counts_created_tasks(self):
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Task 1", 1)
        commands.cmd_add_task("Task 2", 1)
        
        # Dashboard should count 2 created tasks
        result = commands.cmd_dashboard(days=7)
        self.assertTrue(result)

    def test_dashboard_counts_completed_tasks(self):
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Task 1", 1)
        commands.cmd_add_task("Task 2", 1)
        
        # Complete one task
        commands.cmd_update_task(1, status="done")
        
        result = commands.cmd_dashboard(days=7)
        self.assertTrue(result)

    def test_dashboard_completion_rate(self):
        commands.cmd_add_user("alice", "alice@test.com")
        commands.cmd_add_project("TestProj", 1)
        commands.cmd_add_task("Task 1", 1)
        commands.cmd_add_task("Task 2", 1)
        
        # Complete one task (50% completion rate)
        commands.cmd_update_task(1, status="done")
        
        result = commands.cmd_dashboard(days=7)
        self.assertTrue(result)

    def test_format_dashboard(self):
        data = {
            'days': 7,
            'tasks_created': 5,
            'tasks_completed': 3,
            'completion_rate': 60.0,
            'avg_completion_time': '2.5 days',
            'most_active_user': 'User #1 (alice) - 5 tasks',
            'busiest_project': 'Project #1 (TestProj) - 5 tasks',
            'overdue_count': 1,
            'by_status': {'todo': 2, 'done': 3},
        }
        output = formatters.format_dashboard(data)
        self.assertIn("ACTIVITY DASHBOARD", output)
        self.assertIn("Tasks Created:       5", output)
        self.assertIn("60.0%", output)

if __name__ == "__main__":
    unittest.main()