"""Test E2E Incremental: Multi-Round Feature Addition in Large Multi-Language Projects

Verifies that Cognix can perform multiple rounds of feature additions on
a large (13-file) multi-language project while maintaining code quality,
cross-file consistency, and preventing regressions.

Run with:
    pytest tests/test_e2e_incremental.py -v -s --tb=long

Requirements:
    - ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable set
    - Active internet connection
    - ~$1.50-2.50 per full test suite execution
"""

import os
import sys
import time
import tempfile
import shutil
import pytest
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Skip all tests if no API key
e2e = pytest.mark.skipif(
    not (os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY')),
    reason="No API key set. Set ANTHROPIC_API_KEY or OPENAI_API_KEY to run E2E tests."
)


# ══════════════════════════════════════════════════════════════
#  Seed Project: Multi-language web application (13 files)
# ══════════════════════════════════════════════════════════════

SEED_PROJECT: Dict[str, str] = {
    # --- Python Backend ---
    "app.py": '''"""Flask application entry point."""
from flask import Flask, jsonify, render_template
from models import db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
db.init_app(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
''',

    "models.py": '''"""Database models."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }
''',

    "utils.py": '''"""Utility functions."""
import re
from datetime import datetime

def sanitize_input(text: str) -> str:
    """Remove potentially dangerous characters."""
    return re.sub(r"[<>\\"\\']", "", text)

def format_timestamp(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M")

def validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\\\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))
''',

    "config.py": '''"""Application configuration."""
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
''',

    # --- TypeScript Frontend ---
    "static/main.ts": '''// Main application entry point
interface AppConfig {
  apiUrl: string;
  debug: boolean;
}

const config: AppConfig = {
  apiUrl: "/api",
  debug: false,
};

async function fetchHealth(): Promise<{status: string}> {
  const res = await fetch(`${config.apiUrl}/health`);
  return res.json();
}

document.addEventListener("DOMContentLoaded", () => {
  fetchHealth().then((data) => {
    console.log("Health:", data.status);
  });
});
''',

    "static/components.ts": '''// UI Components
export function createCard(title: string, body: string): HTMLElement {
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `<h3>${title}</h3><p>${body}</p>`;
  return card;
}

export function showNotification(message: string, type: string = "info"): void {
  const el = document.createElement("div");
  el.className = `notification ${type}`;
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}
''',

    "static/types.ts": '''// Shared type definitions
export interface User {
  id: number;
  name: string;
  email: string;
}

export interface Item {
  id: number;
  name: string;
  description: string;
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}
''',

    # --- HTML/CSS ---
    "templates/index.html": '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My App</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <header>
    <h1>My Application</h1>
    <nav id="main-nav">
      <a href="/">Home</a>
    </nav>
  </header>
  <main id="content">
    <p>Welcome to the application.</p>
  </main>
  <footer>
    <p>&copy; 2025 My App</p>
  </footer>
  <script src="/static/main.ts"></script>
</body>
</html>
''',

    "static/styles.css": '''/* Main stylesheet */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
header { background: #2c3e50; color: white; padding: 1rem; }
header h1 { font-size: 1.5rem; }
nav a { color: #ecf0f1; text-decoration: none; margin-right: 1rem; }
main { max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
.card { border: 1px solid #ddd; border-radius: 4px; padding: 1rem; margin-bottom: 1rem; }
.card h3 { margin-bottom: 0.5rem; }
.notification { position: fixed; top: 1rem; right: 1rem; padding: 0.75rem 1rem; border-radius: 4px; }
.notification.info { background: #3498db; color: white; }
.notification.error { background: #e74c3c; color: white; }
footer { text-align: center; padding: 1rem; color: #999; }
''',

    # --- Config/Package Files ---
    "requirements.txt": '''flask>=3.0.0
flask-sqlalchemy>=3.1.0
python-dotenv>=1.0.0
''',

    "package.json": '''{
  "name": "my-app-frontend",
  "version": "1.0.0",
  "description": "Frontend for My App",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
''',

    "README.md": '''# My Application

A multi-language web application with Flask backend and TypeScript frontend.

## Setup

```bash
pip install -r requirements.txt
npm install
python app.py
```

## Features
- Health check API
- Item management
''',

    # --- Test File ---
    "test_app.py": '''"""Tests for the Flask application."""
import pytest

def test_health_endpoint():
    """Health endpoint returns ok status."""
    assert True

def test_sanitize_input():
    """Utility function removes dangerous characters."""
    from utils import sanitize_input
    assert "<" not in sanitize_input("<script>alert('xss')</script>")

def test_validate_email():
    """Email validation works correctly."""
    from utils import validate_email
    assert validate_email("user@example.com")
    assert not validate_email("not-an-email")
''',
}


# ══════════════════════════════════════════════════════════════
#  Helper Functions
# ══════════════════════════════════════════════════════════════

def _create_engine(workspace_path: str):
    """Create a real SemiAutoEngine for E2E testing."""
    from cognix.config import Config
    from cognix.llm import LLMManager
    from cognix.semi_auto_engine import SemiAutoEngine

    config = Config()
    llm_manager = LLMManager(config)
    assert len(llm_manager.providers) > 0, (
        "LLMManager has no providers. "
        "Check that ANTHROPIC_API_KEY or OPENAI_API_KEY is correctly set."
    )

    engine = SemiAutoEngine(
        llm_manager=llm_manager,
        workspace_path=workspace_path,
    )
    assert engine.llm_manager is not None
    return engine


def _seed_workspace(workspace_path: str, seed_files: Optional[Dict[str, str]] = None):
    """Write all seed project files into workspace_path."""
    if seed_files is None:
        seed_files = SEED_PROJECT
    wp = Path(workspace_path)
    for filename, content in seed_files.items():
        filepath = wp / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")


def _run_generation_round(engine, goal: str, apply: bool = True):
    """Execute one generation round and optionally apply results.

    Returns:
        (SemiAutoResult, ApplyResult or None)
    """
    result = engine.execute_semi_auto_implementation(goal=goal)
    apply_result = None
    if apply and result.success and result.generated_code:
        apply_result = engine.apply_generated_code(result)
    return result, apply_result


def _collect_all_files(workspace_path: str) -> Dict[str, str]:
    """Read all text files in workspace into a dict."""
    files = {}
    wp = Path(workspace_path)
    text_extensions = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css',
        '.json', '.md', '.txt', '.cfg', '.toml', '.yml', '.yaml',
    }
    for f in wp.rglob("*"):
        if f.is_file() and f.suffix in text_extensions:
            try:
                rel = str(f.relative_to(wp)).replace("\\", "/")
                files[rel] = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                pass
    return files


def _assert_no_critical_lint_errors(result):
    """Assert no E999/F821/F823 critical lint errors in result."""
    if result.lint_result and result.lint_result.get("has_errors"):
        critical_codes = {"E999", "F821", "F823"}
        critical_errors = [
            e for e in result.lint_result.get("errors", [])
            if any(code in str(e) for code in critical_codes)
        ]
        assert len(critical_errors) == 0, (
            f"Critical lint errors found: {critical_errors}"
        )


def _assert_quality_above_threshold(quality_scores: Dict[str, float], threshold: float = 0.4):
    """Assert all per-file quality scores are above the threshold."""
    for filename, score in quality_scores.items():
        assert score >= threshold, (
            f"Quality score for {filename} is {score}, below threshold {threshold}"
        )


def _get_average_quality(quality_scores: Dict[str, float]) -> float:
    """Calculate average quality score."""
    if not quality_scores:
        return 0.0
    return sum(quality_scores.values()) / len(quality_scores)


# ══════════════════════════════════════════════════════════════
#  Test 1: Three-Round Incremental Feature Addition
# ══════════════════════════════════════════════════════════════

class TestIncrementalThreeRounds:
    """3 rounds of feature additions on a 13-file multi-language project."""

    @pytest.fixture(autouse=True)
    def setup_workspace(self):
        self.workspace = tempfile.mkdtemp(prefix="cognix_e2e_incr_")
        _seed_workspace(self.workspace)
        self.engine = _create_engine(self.workspace)
        yield
        shutil.rmtree(self.workspace, ignore_errors=True)

    @e2e
    def test_three_round_incremental_generation(self):
        """Run 3 rounds of feature additions and verify no quality regressions."""
        rounds = [
            {
                "goal": (
                    "Add user authentication feature to this Flask app. "
                    "Add a User model with username, email, password_hash fields. "
                    "Add /api/login and /api/register endpoints in app.py. "
                    "Add login form to the HTML. "
                    "Add auth-related TypeScript functions. "
                    "KEEP all existing functionality."
                ),
                "expect_patterns": ["login", "register", "user"],
            },
            {
                "goal": (
                    "Add search functionality to the existing app. "
                    "Add /api/search endpoint that searches items by name. "
                    "Add search bar UI in the HTML page. "
                    "Add TypeScript function for search API calls. "
                    "KEEP all existing authentication and item features."
                ),
                "expect_patterns": ["search"],
            },
            {
                "goal": (
                    "Add a dashboard page to the existing app. "
                    "Add /dashboard route that shows item count and recent items. "
                    "Add dashboard link in navigation. "
                    "Add dashboard styles in CSS. "
                    "KEEP all existing features including auth and search."
                ),
                "expect_patterns": ["dashboard"],
            },
        ]

        previous_quality_avg = None
        round_results = []

        for i, round_spec in enumerate(rounds):
            result, apply_result = _run_generation_round(
                self.engine, round_spec["goal"]
            )
            round_results.append(result)

            # Generation succeeded
            assert result.success, (
                f"Round {i+1} failed: {result.error}"
            )

            # Code was generated
            assert result.generated_code, (
                f"Round {i+1}: No code generated"
            )

            # No critical lint errors
            _assert_no_critical_lint_errors(result)

            # Quality scores exist and are above floor
            if result.quality_scores:
                _assert_quality_above_threshold(result.quality_scores, threshold=0.4)

            # Apply succeeded
            if apply_result:
                assert apply_result.success, (
                    f"Round {i+1} apply failed: {apply_result.error}"
                )

            # Expected features appear in generated code
            all_code = "\n".join(result.generated_code.values()).lower()
            for pattern in round_spec["expect_patterns"]:
                assert pattern.lower() in all_code, (
                    f"Round {i+1}: Expected pattern '{pattern}' not found "
                    f"in generated code. Files: {list(result.generated_code.keys())}"
                )

            # Regression check: quality should not drop significantly
            if result.quality_scores:
                current_avg = _get_average_quality(result.quality_scores)
                if previous_quality_avg is not None:
                    max_allowed_drop = 0.15
                    assert current_avg >= (previous_quality_avg - max_allowed_drop), (
                        f"Round {i+1}: Quality regression. "
                        f"Previous avg: {previous_quality_avg:.2f}, "
                        f"Current avg: {current_avg:.2f}"
                    )
                previous_quality_avg = current_avg

        # All 3 rounds completed
        assert len(round_results) == 3

        # Workspace still has seed-level file count
        final_files = _collect_all_files(self.workspace)
        assert len(final_files) >= 10, (
            f"Expected 10+ files after 3 rounds, got {len(final_files)}: "
            f"{sorted(final_files.keys())}"
        )


# ══════════════════════════════════════════════════════════════
#  Test 2: Requirement Spec Validation
# ══════════════════════════════════════════════════════════════

class TestRequirementSpecValidation:
    """Generate code from a formal spec and validate requirements are met."""

    SPEC_CONTENT = '''# Requirements Specification: Task Management API

## Overview
Build a task management system with the following requirements.

## Required Features
1. Task model with fields: id, title, description, status, priority, due_date
2. REST API endpoints:
   - GET /api/tasks - List all tasks
   - POST /api/tasks - Create a new task
   - GET /api/tasks/<id> - Get task by ID
   - PUT /api/tasks/<id> - Update task
   - DELETE /api/tasks/<id> - Delete task
3. Task status must be one of: todo, in_progress, done
4. Task priority must be one of: low, medium, high
5. Input validation for all endpoints

## Required Files
- app.py (Flask application with routes)
- models.py (SQLAlchemy models)
- requirements.txt (Python dependencies)

## Technical Requirements
- Use Flask and SQLAlchemy
- Return JSON responses
- Include proper error handling
'''

    @pytest.fixture(autouse=True)
    def setup_workspace(self):
        self.workspace = tempfile.mkdtemp(prefix="cognix_e2e_spec_")
        self.engine = _create_engine(self.workspace)
        yield
        shutil.rmtree(self.workspace, ignore_errors=True)

    @e2e
    def test_spec_driven_generation(self):
        """Generate code from spec content and validate requirements are met."""
        result, apply_result = _run_generation_round(
            self.engine, self.SPEC_CONTENT
        )

        # Generation succeeded
        assert result.success, f"Spec generation failed: {result.error}"
        assert result.generated_code, "No code generated from spec"

        # Required files exist
        generated_filenames = set(result.generated_code.keys())
        for required in ["app.py", "models.py", "requirements.txt"]:
            matched = any(required in fn for fn in generated_filenames)
            assert matched, (
                f"Required file '{required}' not in generated: {generated_filenames}"
            )

        # Validate using RequirementValidator
        from cognix.requirement_validator import RequirementValidator
        validator = RequirementValidator(workspace_path=self.workspace)
        validation = validator.validate_requirements(
            self.SPEC_CONTENT, result.generated_code
        )

        # Fulfillment score should be reasonable
        assert validation["fulfillment_score"] >= 0.5, (
            f"Fulfillment score too low: {validation['fulfillment_score']:.2f}. "
            f"Missing files: {validation.get('missing_files', [])}. "
            f"Missing features: {validation.get('missing_features', [])}"
        )

        # Key features detected in code
        all_code = "\n".join(result.generated_code.values()).lower()
        for keyword in ["task", "flask"]:
            assert keyword in all_code, (
                f"Expected keyword '{keyword}' not found in generated code"
            )

        # REST endpoints present
        for pattern in ["/api/tasks"]:
            assert pattern in all_code, (
                f"Expected endpoint pattern '{pattern}' not found"
            )

        # No critical lint errors
        _assert_no_critical_lint_errors(result)

        # Quality above floor
        if result.quality_scores:
            _assert_quality_above_threshold(result.quality_scores, threshold=0.4)


# ══════════════════════════════════════════════════════════════
#  Test 3: File Preservation Across Rounds
# ══════════════════════════════════════════════════════════════

class TestFilePreservation:
    """Verify that untouched files survive incremental generation."""

    @pytest.fixture(autouse=True)
    def setup_workspace(self):
        self.workspace = tempfile.mkdtemp(prefix="cognix_e2e_preserve_")
        _seed_workspace(self.workspace)
        self.engine = _create_engine(self.workspace)
        yield
        shutil.rmtree(self.workspace, ignore_errors=True)

    @e2e
    def test_unrelated_files_preserved(self):
        """After targeted generation, files not in generated_code remain unchanged."""
        # Record original content of files that should not change
        wp = Path(self.workspace)
        original_readme = (wp / "README.md").read_text(encoding="utf-8")
        original_package = (wp / "package.json").read_text(encoding="utf-8")

        # Run a targeted modification
        result, apply_result = _run_generation_round(
            self.engine,
            "Add a /api/items endpoint to app.py that returns all items as JSON. "
            "Modify ONLY app.py to add this endpoint. "
            "KEEP all other files exactly as they are."
        )

        assert result.success, f"Generation failed: {result.error}"

        if apply_result and apply_result.success:
            # Files NOT in generated_code should be untouched on disk
            assert (wp / "README.md").exists(), "README.md was deleted"
            assert (wp / "package.json").exists(), "package.json was deleted"

            if "README.md" not in result.generated_code:
                current_readme = (wp / "README.md").read_text(encoding="utf-8")
                assert current_readme == original_readme, (
                    "README.md was modified even though it was not in generated_code"
                )

            if "package.json" not in result.generated_code:
                current_package = (wp / "package.json").read_text(encoding="utf-8")
                assert current_package == original_package, (
                    "package.json was modified even though it was not in generated_code"
                )


# ══════════════════════════════════════════════════════════════
#  Standalone runner
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.path.insert(0, _repo_root)

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    print()
    print("=" * 60)
    print(" Cognix E2E Incremental Generation Tests")
    print("=" * 60)
    print()

    has_key = bool(os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY'))
    if has_key:
        print(f"[ENV] API Key:  {GREEN}SET{RESET}")
    else:
        print(f"[ENV] API Key:  {RED}NOT SET{RESET}")
        print()
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY to run E2E tests.")
        sys.exit(1)

    try:
        from cognix.config import Config
        from cognix.llm import LLMManager
        config = Config()
        llm = LLMManager(config)
        providers = list(llm.providers.keys())
        print(f"[ENV] LLM Providers: {GREEN}{', '.join(providers)}{RESET}")
        print(f"[ENV] Model: {GREEN}{llm.current_model}{RESET}")
    except Exception as e:
        print(f"[ENV] LLM Init: {RED}FAILED - {e}{RESET}")
        sys.exit(1)

    print()
    print(f"{YELLOW}WARNING: These tests make real API calls.{RESET}")
    print(f"{YELLOW}Estimated cost: ~$1.50-2.50 for full suite.{RESET}")
    print(f"{YELLOW}Estimated time: ~3-5 minutes.{RESET}")
    print()

    exit_code = pytest.main([__file__, '-v', '-s', '--tb=long', '--no-header'])
    sys.exit(exit_code)
