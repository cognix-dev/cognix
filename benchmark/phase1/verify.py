#!/usr/bin/env python3
"""
Verify script for Task G: Task Manager Feature Extension.
Tests that existing 61 tests still pass AND new features work correctly.
"""

import json
import os
import sys
import ast
import subprocess
import importlib.util
import shutil
import tempfile
from pathlib import Path


def find_python_files(workdir: Path):
    return [p for p in workdir.rglob("*.py") if "_bench" not in p.name]


def count_code_lines(workdir: Path) -> int:
    total = 0
    for p in find_python_files(workdir):
        try:
            total += len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            pass
    return total


# =================================================================
# Axis 1: Execution
# =================================================================

def test_execution(workdir: Path) -> dict:
    """Test existing tests still pass + new features work."""
    python = sys.executable
    passed = 0
    total = 8
    details = []

    # --- Test 1: All existing 61 tests still pass ---
    try:
        result = subprocess.run(
            [python, "-m", "unittest", "test_taskmanager", "-v"],
            cwd=str(workdir), capture_output=True, text=True, timeout=60,
        )
        # Count passes vs total
        lines = result.stderr.strip().splitlines() if result.stderr else []
        ok_count = sum(1 for l in lines if "... ok" in l.lower())
        # FIX: "... FAIL" と "... ERROR" のみカウント（行末パターン）
        # コマンド出力の "Error: ..." にマッチしないよう、テスト結果行のパターンに限定
        fail_count = sum(1 for l in lines if l.rstrip().endswith("... FAIL") or l.rstrip().endswith("... ERROR"))

        # Must have AT LEAST 61 passing (original) + some new
        if ok_count >= 61 and fail_count == 0 and result.returncode == 0:
            passed += 1
            details.append(f"Existing tests: OK ({ok_count} passed, 0 failed)")
        elif ok_count >= 61 and fail_count > 0:
            details.append(f"Existing tests: PARTIAL ({ok_count} passed, {fail_count} failed)")
        else:
            details.append(f"Existing tests: FAIL ({ok_count} passed, {fail_count} failed, rc={result.returncode})")
            # Show errors
            for l in lines[-10:]:
                if "error" in l.lower() or "fail" in l.lower():
                    details.append(f"  {l.strip()}")
    except subprocess.TimeoutExpired:
        details.append("Existing tests: TIMEOUT")
    except Exception as e:
        details.append(f"Existing tests: {e}")

    # --- Test 2: New tests were added (>61 total) ---
    try:
        result = subprocess.run(
            [python, "-m", "unittest", "test_taskmanager", "-v"],
            cwd=str(workdir), capture_output=True, text=True, timeout=60,
        )
        lines = result.stderr.strip().splitlines() if result.stderr else []
        test_count = sum(1 for l in lines if "... ok" in l.lower() or l.rstrip().endswith("... FAIL") or l.rstrip().endswith("... ERROR"))
        if test_count > 61:
            passed += 1
            details.append(f"New tests added: OK ({test_count} total, {test_count - 61} new)")
        else:
            details.append(f"New tests added: FAIL (only {test_count} tests, expected >61)")
    except Exception as e:
        details.append(f"New tests check: {e}")

    # --- Test 3: RecurringRule model exists and works ---
    try:
        result = subprocess.run(
            [python, "-c", """
import sys; sys.path.insert(0, '.')
from models import RecurringRule
r = RecurringRule(id=1, task_template_id=1, frequency='daily',
                  next_run='2020-01-01T00:00:00', active=True)
assert r.should_run() == True, f"should_run expected True, got {r.should_run()}"
old_next = r.next_run
r.advance()
assert r.next_run != old_next, "advance() did not change next_run"
assert r.created_count == 1, f"created_count expected 1, got {r.created_count}"
print("OK")
"""],
            cwd=str(workdir), capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            passed += 1
            details.append("RecurringRule model: OK")
        else:
            err = (result.stderr or result.stdout)[:200]
            details.append(f"RecurringRule model: FAIL ({err})")
    except Exception as e:
        details.append(f"RecurringRule model: {e}")

    # --- Test 4: Recurring storage works ---
    try:
        result = subprocess.run(
            [python, "-c", """
import sys, os, tempfile, shutil; sys.path.insert(0, '.')
from pathlib import Path
import storage
td = tempfile.mkdtemp()
storage.DATA_DIR = Path(td) / "data"
storage.TASKS_FILE = storage.DATA_DIR / "tasks.json"
storage.RECURRING_FILE = storage.DATA_DIR / "recurring.json"
storage.ensure_data_dir()

# Check recurring functions exist
from storage import load_recurring_rules, save_recurring_rules, get_next_recurring_id
from models import RecurringRule
rules = load_recurring_rules()
assert isinstance(rules, list)
r = RecurringRule(id=1, task_template_id=1, frequency='weekly',
                  next_run='2025-01-01', active=True)
save_recurring_rules([r])
loaded = load_recurring_rules()
assert len(loaded) == 1
shutil.rmtree(td)
print("OK")
"""],
            cwd=str(workdir), capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            passed += 1
            details.append("Recurring storage: OK")
        else:
            err = (result.stderr or result.stdout)[:200]
            details.append(f"Recurring storage: FAIL ({err})")
    except Exception as e:
        details.append(f"Recurring storage: {e}")

    # --- Test 5: TaskDependency model and circular detection ---
    try:
        result = subprocess.run(
            [python, "-c", """
import sys; sys.path.insert(0, '.')
from models import TaskDependency
d = TaskDependency(id=1, task_id=2, depends_on_id=1)
assert d.task_id == 2
assert d.depends_on_id == 1
dct = d.to_dict()
assert 'task_id' in dct

# Check circular dependency validation
from validators import validate_no_circular_dependency
# No cycle: A depends on B
ok, msg = validate_no_circular_dependency(2, 1, [])
assert ok == True, f"Expected True for no-cycle, got {ok}: {msg}"

# Direct cycle: A depends on B, now B depends on A
from models import TaskDependency
existing = [TaskDependency(id=1, task_id=2, depends_on_id=1)]
ok, msg = validate_no_circular_dependency(1, 2, existing)
assert ok == False, f"Expected False for direct cycle, got {ok}"

print("OK")
"""],
            cwd=str(workdir), capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            passed += 1
            details.append("Dependencies + circular detection: OK")
        else:
            err = (result.stderr or result.stdout)[:200]
            details.append(f"Dependencies + circular detection: FAIL ({err})")
    except Exception as e:
        details.append(f"Dependencies: {e}")

    # --- Test 6: Dependency storage works ---
    try:
        result = subprocess.run(
            [python, "-c", """
import sys, tempfile, shutil; sys.path.insert(0, '.')
from pathlib import Path
import storage
td = tempfile.mkdtemp()
storage.DATA_DIR = Path(td) / "data"
storage.TASKS_FILE = storage.DATA_DIR / "tasks.json"
storage.DEPENDENCIES_FILE = storage.DATA_DIR / "dependencies.json"
storage.ensure_data_dir()

from storage import load_dependencies, save_dependencies, get_next_dependency_id
from models import TaskDependency
deps = load_dependencies()
assert isinstance(deps, list)
d = TaskDependency(id=1, task_id=2, depends_on_id=1)
save_dependencies([d])
loaded = load_dependencies()
assert len(loaded) == 1
assert loaded[0].task_id == 2
shutil.rmtree(td)
print("OK")
"""],
            cwd=str(workdir), capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            passed += 1
            details.append("Dependency storage: OK")
        else:
            err = (result.stderr or result.stdout)[:200]
            details.append(f"Dependency storage: FAIL ({err})")
    except Exception as e:
        details.append(f"Dependency storage: {e}")

    # --- Test 7: Dashboard command ---
    try:
        result = subprocess.run(
            [python, "-c", """
import sys; sys.path.insert(0, '.')
from commands import cmd_dashboard
from formatters import format_dashboard
# format_dashboard should exist
assert callable(format_dashboard)
# cmd_dashboard should accept days and user_id
import inspect
sig = inspect.signature(cmd_dashboard)
params = list(sig.parameters.keys())
assert 'days' in params or len(params) >= 1
print("OK")
"""],
            cwd=str(workdir), capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            passed += 1
            details.append("Dashboard command: OK")
        else:
            err = (result.stderr or result.stdout)[:200]
            details.append(f"Dashboard command: FAIL ({err})")
    except Exception as e:
        details.append(f"Dashboard command: {e}")

    # --- Test 8: CLI subcommands exist ---
    try:
        result = subprocess.run(
            [python, "cli.py", "--help"],
            cwd=str(workdir), capture_output=True, text=True, timeout=10,
        )
        help_text = result.stdout.lower()
        found = []
        missing = []
        for cmd in ["recurring-add", "recurring-list", "recurring-run",
                     "dep-add", "dep-list", "dashboard"]:
            if cmd in help_text:
                found.append(cmd)
            else:
                missing.append(cmd)
        if len(found) >= 5:  # Allow 1 missing
            passed += 1
            details.append(f"CLI subcommands: OK ({len(found)}/6 found)")
        else:
            details.append(f"CLI subcommands: FAIL (found: {found}, missing: {missing})")
    except Exception as e:
        details.append(f"CLI subcommands: {e}")

    return {"passed": passed, "total": total, "details": details}


# =================================================================
# Axis 2: Dependency
# =================================================================

def check_dependency(workdir: Path) -> dict:
    py_files = find_python_files(workdir)
    if not py_files:
        return {"resolved": 0, "total": 0, "details": []}

    total_imports = 0
    resolved_imports = 0
    details = []

    for pyfile in py_files:
        try:
            source = pyfile.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    total_imports += 1
                    if _can_import(alias.name, workdir):
                        resolved_imports += 1
                    else:
                        details.append(f"{pyfile.name}: unresolved import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                total_imports += 1
                if _can_import(node.module, workdir):
                    resolved_imports += 1
                else:
                    details.append(f"{pyfile.name}: unresolved from {node.module}")

    return {"resolved": resolved_imports, "total": total_imports, "details": details}


def _can_import(module_name: str, workdir: Path) -> bool:
    root = module_name.split(".")[0]
    local_py = workdir / (root + ".py")
    local_dir = workdir / root
    if local_py.exists() or (local_dir.exists() and local_dir.is_dir()):
        return True
    try:
        spec = importlib.util.find_spec(root)
        return spec is not None
    except (ModuleNotFoundError, ValueError):
        return False


# =================================================================
# Axis 3: Lint
# =================================================================

def run_lint(workdir: Path) -> dict:
    py_files = find_python_files(workdir)
    if not py_files:
        return {"errors": 0, "lines": 0, "details": []}
    try:
        result = subprocess.run(
            ["ruff", "check", "--select", "E,F", "--no-fix",
             "--exclude", "_bench_runner.py", str(workdir)],
            capture_output=True, text=True, timeout=30,
        )
        error_lines = [
            line for line in result.stdout.strip().splitlines()
            if line and ":" in line and not line.startswith("Found")
        ]
        errors = len(error_lines)
    except FileNotFoundError:
        return {"errors": 0, "lines": count_code_lines(workdir),
                "details": ["ruff not installed"]}
    except Exception as e:
        return {"errors": 0, "lines": count_code_lines(workdir),
                "details": [f"ruff error: {e}"]}

    return {"errors": errors, "lines": count_code_lines(workdir),
            "details": error_lines[:20]}


# =================================================================
# Axis 4: Scope
# =================================================================

def check_scope(workdir: Path) -> dict:
    """Check that required files, features, and tests exist."""
    passed = 0
    total = 12
    details = []

    # 1. Required existing files still present
    required_files = [
        "models.py", "storage.py", "filters.py", "formatters.py",
        "exporters.py", "validators.py", "plugins.py", "commands.py",
        "cli.py", "test_taskmanager.py",
    ]
    all_exist = True
    for f in required_files:
        if not (workdir / f).exists():
            all_exist = False
            details.append(f"{f}: MISSING")
    if all_exist:
        passed += 1
        details.append(f"Required files: PASS ({len(required_files)}/{len(required_files)})")
    else:
        details.append("Required files: FAIL")

    # 2. RecurringRule class exists in models.py
    models_text = _read_file(workdir / "models.py")
    if "class RecurringRule" in models_text:
        passed += 1
        details.append("RecurringRule class: PASS")
    else:
        details.append("RecurringRule class: MISSING in models.py")

    # 3. TaskDependency class exists in models.py
    if "class TaskDependency" in models_text:
        passed += 1
        details.append("TaskDependency class: PASS")
    else:
        details.append("TaskDependency class: MISSING in models.py")

    # 4. Recurring storage functions
    storage_text = _read_file(workdir / "storage.py")
    recurring_fns = ["load_recurring_rules", "save_recurring_rules"]
    if all(fn in storage_text for fn in recurring_fns):
        passed += 1
        details.append("Recurring storage functions: PASS")
    else:
        details.append("Recurring storage functions: MISSING")

    # 5. Dependency storage functions
    dep_fns = ["load_dependencies", "save_dependencies"]
    if all(fn in storage_text for fn in dep_fns):
        passed += 1
        details.append("Dependency storage functions: PASS")
    else:
        details.append("Dependency storage functions: MISSING")

    # 6. Circular dependency validator
    validators_text = _read_file(workdir / "validators.py")
    if "validate_no_circular_dependency" in validators_text:
        passed += 1
        details.append("Circular dependency validator: PASS")
    else:
        details.append("Circular dependency validator: MISSING")

    # 7. Recurring commands
    commands_text = _read_file(workdir / "commands.py")
    recurring_cmds = ["cmd_add_recurring", "cmd_run_recurring", "cmd_list_recurring"]
    found = [c for c in recurring_cmds if c in commands_text]
    if len(found) >= 2:
        passed += 1
        details.append(f"Recurring commands: PASS ({len(found)}/{len(recurring_cmds)})")
    else:
        details.append(f"Recurring commands: FAIL ({len(found)}/{len(recurring_cmds)})")

    # 8. Dependency commands
    dep_cmds = ["cmd_add_dependency", "cmd_list_dependencies", "cmd_remove_dependency"]
    found = [c for c in dep_cmds if c in commands_text]
    if len(found) >= 2:
        passed += 1
        details.append(f"Dependency commands: PASS ({len(found)}/{len(dep_cmds)})")
    else:
        details.append(f"Dependency commands: FAIL ({len(found)}/{len(dep_cmds)})")

    # 9. Dashboard command
    if "cmd_dashboard" in commands_text:
        passed += 1
        details.append("Dashboard command: PASS")
    else:
        details.append("Dashboard command: MISSING")

    # 10. format_dashboard in formatters
    formatters_text = _read_file(workdir / "formatters.py")
    if "format_dashboard" in formatters_text:
        passed += 1
        details.append("format_dashboard: PASS")
    else:
        details.append("format_dashboard: MISSING")

    # 11. Plugin hooks for recurring
    plugins_text = _read_file(workdir / "plugins.py")
    if "recurring" in plugins_text.lower():
        passed += 1
        details.append("Recurring plugin hooks: PASS")
    else:
        details.append("Recurring plugin hooks: MISSING")

    # 12. Existing functions preserved (spot check)
    preserved_fns = [
        ("commands.py", "cmd_add_task"),
        ("commands.py", "cmd_export"),
        ("storage.py", "load_tasks"),
        ("storage.py", "add_event"),
        ("filters.py", "apply_filters"),
        ("formatters.py", "format_task_line"),
    ]
    all_preserved = True
    for fname, fn_name in preserved_fns:
        ftxt = _read_file(workdir / fname)
        if fn_name not in ftxt:
            all_preserved = False
            details.append(f"REMOVED: {fn_name} from {fname}")
    if all_preserved:
        passed += 1
        details.append("Existing functions preserved: PASS")
    else:
        details.append("Existing functions preserved: FAIL")

    return {"passed": passed, "total": total, "details": details}


def _read_file(filepath: Path) -> str:
    try:
        return filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# =================================================================
# Main
# =================================================================

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <workdir>")
        sys.exit(1)

    workdir = Path(sys.argv[1]).resolve()
    if not workdir.exists():
        print(f"Error: {workdir} does not exist")
        sys.exit(1)

    results = {}
    results["axis1_execution"] = test_execution(workdir)
    results["axis2_dependency"] = check_dependency(workdir)
    results["axis3_lint"] = run_lint(workdir)
    results["axis4_scope"] = check_scope(workdir)

    # Collect raw details
    results["raw_details"] = {
        "execution": results["axis1_execution"].pop("details", []),
        "dependency": results["axis2_dependency"].pop("details", []),
        "lint": results["axis3_lint"].pop("details", []),
        "scope": results["axis4_scope"].pop("details", []),
    }

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()