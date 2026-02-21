# Task G: Task Manager Feature Extension

## Existing Project

You are given an existing Task Manager CLI application with 10 files:
- `models.py` — Data classes (User, Task, Project, EventLog, Comment)
- `storage.py` — JSON file persistence
- `filters.py` — Task filtering and search
- `formatters.py` — Display formatting
- `exporters.py` — CSV/JSON/Markdown export
- `validators.py` — Input validation
- `plugins.py` — Hook-based plugin system
- `commands.py` — CLI command handlers
- `cli.py` — Main entry point (argparse)
- `test_taskmanager.py` — 61 passing tests

## CRITICAL CONSTRAINTS

1. **ALL 61 existing tests MUST continue to pass unchanged**
2. **DO NOT modify any existing function signatures** — you may add parameters with defaults
3. **DO NOT remove or rename any existing functions, classes, or methods**
4. **DO NOT change the behavior of any existing command** — existing CLI commands must work identically
5. **All existing imports in test_taskmanager.py must remain valid**
6. You may ADD new functions, classes, methods, and files
7. You may ADD new parameters to existing functions IF they have default values
8. New tests MUST be added to test_taskmanager.py (append, do not modify existing tests)

## Feature 1: Recurring Tasks

Add a recurring task system that creates tasks on a schedule.

### models.py changes:
- Add `RecurringRule` dataclass with fields:
  - `id: int`
  - `task_template_id: int` (reference to a task used as template)
  - `frequency: str` — one of: "daily", "weekly", "biweekly", "monthly"
  - `next_run: str` — ISO date of next occurrence
  - `end_date: Optional[str]` — when recurrence stops (None = never)
  - `created_count: int` — number of tasks created so far
  - `active: bool` — whether rule is active
  - `created_at: str`
  - Include a `to_dict()` method and `should_run()` method that returns True if `next_run <= now` and `active is True` and (`end_date is None or end_date >= now`)
  - Include `advance()` method that updates `next_run` based on frequency and increments `created_count`

### storage.py changes:
- Add `data/recurring.json` persistence
- Add functions: `load_recurring_rules()`, `save_recurring_rules()`, `get_recurring_rule_by_id()`, `get_next_recurring_id()`

### commands.py changes:
- Add `cmd_add_recurring(task_id, frequency, end_date=None)` — creates a recurring rule from an existing task (used as template)
- Add `cmd_list_recurring()` — list all recurring rules with status
- Add `cmd_run_recurring(user_id)` — check all active rules, create new tasks for those where `should_run()` is True, advance the rule. Print how many tasks were created.
- Add `cmd_cancel_recurring(rule_id)` — set rule.active = False

### cli.py changes:
- Add subcommands: `recurring-add`, `recurring-list`, `recurring-run`, `recurring-cancel`

### plugins.py changes:
- Add new hooks: `HOOK_RECURRING_PRE_RUN = "recurring_pre_run"` and `HOOK_RECURRING_POST_RUN = "recurring_post_run"` — registered in PluginManager.__init__

### New tests required (append to test_taskmanager.py):
- Test RecurringRule.should_run() with various conditions
- Test RecurringRule.advance() for each frequency
- Test storage round-trip for recurring rules
- Test cmd_run_recurring creates tasks correctly
- Test recurring with end_date in the past does not create tasks
- Test cmd_cancel_recurring deactivates rule

## Feature 2: Task Dependencies

Add a dependency system where tasks can block other tasks.

### models.py changes:
- Add `TaskDependency` dataclass with fields:
  - `id: int`
  - `task_id: int` — the task that is blocked
  - `depends_on_id: int` — the task that must be completed first
  - `created_at: str`
  - Include `to_dict()` method

### storage.py changes:
- Add `data/dependencies.json` persistence
- Add functions: `load_dependencies()`, `save_dependencies()`, `get_dependencies_for_task(task_id)`, `get_dependents_of_task(task_id)`, `get_next_dependency_id()`

### commands.py changes:
- Add `cmd_add_dependency(task_id, depends_on_id)` — creates a dependency. Validate:
  - Both tasks exist
  - No self-dependency (task_id != depends_on_id)
  - No duplicate dependency
  - No circular dependency (if A depends on B, B cannot depend on A — check transitively)
- Add `cmd_list_dependencies(task_id)` — show what a task depends on and what depends on it
- Add `cmd_remove_dependency(task_id, depends_on_id)` — remove a dependency
- **Modify `cmd_update_task`**: when changing status to "done", print a WARNING (not error) if any dependency is not yet done. Still allow the status change.
- **Modify `cmd_delete_task`**: when deleting a task, also remove all dependencies involving that task

### cli.py changes:
- Add subcommands: `dep-add`, `dep-list`, `dep-remove`

### validators.py changes:
- Add `validate_no_circular_dependency(task_id, depends_on_id, existing_deps)` that returns `(bool, str)`. Must detect cycles transitively.

### New tests required:
- Test dependency creation and storage round-trip
- Test self-dependency rejection
- Test duplicate dependency rejection
- Test circular dependency detection (direct: A→B→A)
- Test circular dependency detection (transitive: A→B→C→A)
- Test cmd_delete_task removes associated dependencies
- Test status change to "done" warns about incomplete dependencies

## Feature 3: Activity Dashboard

Add a dashboard command that shows activity analytics.

### commands.py changes:
- Add `cmd_dashboard(days=7, user_id=None)` that computes and prints:
  - **Tasks created** in the period
  - **Tasks completed** in the period
  - **Completion rate** (completed / total in period, as percentage)
  - **Average completion time** (for tasks completed in period: completed_at - created_at)
  - **Most active user** (who created/completed the most tasks)
  - **Busiest project** (project with most activity)
  - **Overdue tasks count**
  - **Tasks by status breakdown**

### formatters.py changes:
- Add `format_dashboard(data: dict) -> str` that formats the dashboard data as a readable text report

### cli.py changes:
- Add subcommand: `dashboard` with `--days` (default 7) and `--user` (optional)

### New tests required:
- Test dashboard with no data returns zeros
- Test dashboard correctly counts created/completed in date range
- Test dashboard completion rate calculation
- Test dashboard average completion time
- Test format_dashboard produces expected sections
