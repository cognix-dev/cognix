"""Tests for deterministic auto-fix methods in semi_auto_engine.py

Covers:
- _apply_deterministic_fixes(): F401, W291, W292, W293, W391
- _apply_secret_auto_fix(): hardcoded secrets → env vars
"""

import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


def _make_engine_stub():
    """Create a minimal SemiAutoEngine-like object with the fix methods bound."""
    # Import the actual class to get the real methods
    from cognix.semi_auto_engine import SemiAutoEngine

    # Create a mock that has the real methods
    engine = MagicMock(spec=SemiAutoEngine)
    engine._apply_deterministic_fixes = SemiAutoEngine._apply_deterministic_fixes.__get__(engine)
    engine._apply_secret_auto_fix = SemiAutoEngine._apply_secret_auto_fix.__get__(engine)
    return engine


@pytest.fixture
def engine():
    return _make_engine_stub()


# ── _apply_deterministic_fixes ────────────────────────────────


class TestApplyDeterministicFixes:
    """Verify deterministic lint-error auto-fixes."""

    def test_f401_simple_import(self, engine):
        code = "import json\nimport os\n\nprint('hello')\n"
        errors = [{"code": "F401", "line": 1, "message": "'json' imported but unused"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        assert "import json" not in fixed
        assert "import os" in fixed
        assert remaining == []

    def test_f401_from_import(self, engine):
        code = "from os import path\n\nprint('hello')\n"
        errors = [{"code": "F401", "line": 1, "message": "'os.path' imported but unused"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        assert "from os import path" not in fixed
        assert remaining == []

    def test_f401_complex_import_preserved(self, engine):
        """Multi-name imports (from x import a, b) should NOT be auto-removed."""
        code = "from os import path, getcwd\n\nprint('hello')\n"
        errors = [{"code": "F401", "line": 1, "message": "'os.path' imported but unused"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        assert "from os import path, getcwd" in fixed  # preserved
        assert len(remaining) == 1  # error is in remaining

    def test_w291_trailing_spaces(self, engine):
        code = "hello = 'world'   \nnext_line\n"
        errors = [{"code": "W291", "line": 1, "message": "trailing whitespace"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        lines = fixed.split("\n")
        assert lines[0] == "hello = 'world'"
        assert remaining == []

    def test_w293_trailing_whitespace(self, engine):
        code = "hello = 'world'\t  \nnext_line\n"
        errors = [{"code": "W293", "line": 1, "message": "whitespace before a comment"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        lines = fixed.split("\n")
        assert lines[0] == "hello = 'world'"
        assert remaining == []

    def test_w292_missing_newline(self, engine):
        code = "print('hello')"  # no trailing newline
        errors = [{"code": "W292", "line": 1, "message": "no newline at end of file"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        assert fixed.endswith("\n") or fixed.split("\n")[-1] == ""
        assert remaining == []

    def test_w292_already_has_newline(self, engine):
        code = "print('hello')\n"
        errors = [{"code": "W292", "line": 1, "message": "no newline at end of file"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        # Should not add extra blank line, error should be consumed (not in remaining)
        assert remaining == []

    def test_w391_excess_blank_lines(self, engine):
        code = "print('hello')\n\n\n\n"
        errors = [{"code": "W391", "line": 4, "message": "blank line at end of file"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        # Should reduce trailing blank lines
        trailing_blanks = 0
        for line in reversed(fixed.split("\n")):
            if line.strip() == "":
                trailing_blanks += 1
            else:
                break
        assert trailing_blanks <= 2  # at most one trailing newline worth of blank
        assert remaining == []

    def test_unknown_error_in_remaining(self, engine):
        code = "print('hello')\n"
        errors = [{"code": "E302", "line": 1, "message": "expected 2 blank lines"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        assert fixed == code  # unchanged
        assert len(remaining) == 1
        assert remaining[0]["code"] == "E302"

    def test_mixed_errors(self, engine):
        code = "import json\nhello = 'world'   \nprint('hello')\n"
        errors = [
            {"code": "F401", "line": 1, "message": "unused import"},
            {"code": "W291", "line": 2, "message": "trailing whitespace"},
            {"code": "E302", "line": 3, "message": "expected 2 blank lines"},
        ]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        assert "import json" not in fixed
        assert "world'   " not in fixed
        assert "world'" in fixed
        assert len(remaining) == 1
        assert remaining[0]["code"] == "E302"

    def test_empty_errors(self, engine):
        code = "print('hello')\n"
        fixed, remaining = engine._apply_deterministic_fixes(code, [])
        assert fixed == code
        assert remaining == []

    def test_f401_line_out_of_range(self, engine):
        """Line number beyond file length should not crash."""
        code = "print('hello')\n"
        errors = [{"code": "F401", "line": 999, "message": "unused import"}]
        fixed, remaining = engine._apply_deterministic_fixes(code, errors)
        assert fixed == code
        assert len(remaining) == 1


# ── _apply_secret_auto_fix ────────────────────────────────────


class TestApplySecretAutoFix:
    """Verify hardcoded secret → env var auto-replacement."""

    def test_python_password_to_env(self, engine):
        code = 'password = "MyS3cureP@ssw0rd!"\n'
        issues = [{"line": 1, "pattern_name": "Hardcoded Password", "severity": "high"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "config.py")
        assert "os.environ.get" in fixed
        assert '"MyS3cureP@ssw0rd!"' not in fixed

    def test_python_adds_import_os(self, engine):
        code = 'password = "MyS3cureP@ssw0rd!"\n'
        issues = [{"line": 1, "pattern_name": "Hardcoded Password", "severity": "high"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "config.py")
        assert "import os" in fixed

    def test_python_no_duplicate_import_os(self, engine):
        code = 'import os\npassword = "MyS3cureP@ssw0rd!"\n'
        issues = [{"line": 2, "pattern_name": "Hardcoded Password", "severity": "high"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "config.py")
        assert fixed.count("import os") == 1

    def test_js_const_api_key(self, engine):
        code = 'const apiKey = "ABCDEFGHIJKLMNOP1234"\n'
        issues = [{"line": 1, "pattern_name": "Hardcoded API Key", "severity": "high"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "config.js")
        assert "process.env" in fixed
        assert "API_KEY" in fixed
        assert '"ABCDEFGHIJKLMNOP1234"' not in fixed

    def test_js_let_declaration(self, engine):
        code = 'let secretKey = "ABCDEFGHIJKLMNOP1234"\n'
        issues = [{"line": 1, "pattern_name": "Hardcoded API Key", "severity": "high"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "config.js")
        assert "process.env" in fixed

    def test_js_var_declaration(self, engine):
        code = 'var password = "MyS3cureP@ssw0rd!"\n'
        issues = [{"line": 1, "pattern_name": "Hardcoded Password", "severity": "high"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "app.js")
        assert "process.env" in fixed

    def test_skip_non_password_pattern(self, engine):
        """AWS Access Key pattern should NOT be auto-fixed (only Password/API Key)."""
        code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
        issues = [{"line": 1, "pattern_name": "AWS Access Key", "severity": "critical"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "config.py")
        assert fixed == code  # unchanged

    def test_no_match_preserved(self, engine):
        """Lines that don't match variable assignment pattern should be unchanged."""
        code = 'print("password = secret123")\n'
        issues = [{"line": 1, "pattern_name": "Hardcoded Password", "severity": "high"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "config.py")
        # The regex won't match print(...) format
        assert "print(" in fixed

    def test_unsupported_language(self, engine):
        """Go files should not be auto-fixed (only Python/JS supported)."""
        code = 'password := "MyS3cureP@ssw0rd!"\n'
        issues = [{"line": 1, "pattern_name": "Hardcoded Password", "severity": "high"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "config.go")
        assert fixed == code  # unchanged

    def test_empty_issues(self, engine):
        code = 'print("hello")\n'
        fixed = engine._apply_secret_auto_fix(code, [], "config.py")
        assert fixed == code

    def test_line_out_of_range(self, engine):
        """Out-of-range line number should not crash."""
        code = 'print("hello")\n'
        issues = [{"line": 999, "pattern_name": "Hardcoded Password", "severity": "high"}]
        fixed = engine._apply_secret_auto_fix(code, issues, "config.py")
        assert fixed == code
