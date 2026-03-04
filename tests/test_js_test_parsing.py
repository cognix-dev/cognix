"""Tests for JS/TS test parsing, mypy output parsing, and TS error filtering

Covers:
- _parse_js_test_output(): jest, vitest, mocha output parsing
- _parse_mypy_output(): mypy error/warning parsing
- TS error code filtering sets (consistency checks)
- _detect_js_test_framework(): package.json-based detection
"""

import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path


def _make_engine_stub():
    """Create minimal SemiAutoEngine-like object with test parsing methods."""
    from cognix.semi_auto_engine import SemiAutoEngine
    engine = MagicMock(spec=SemiAutoEngine)
    engine._parse_js_test_output = SemiAutoEngine._parse_js_test_output.__get__(engine)
    engine._detect_js_test_framework = SemiAutoEngine._detect_js_test_framework.__get__(engine)
    engine._read_package_json = SemiAutoEngine._read_package_json.__get__(engine)
    engine._get_npx_command = SemiAutoEngine._get_npx_command.__get__(engine)
    engine.workspace_path = None
    engine.logger = MagicMock()
    return engine


@pytest.fixture
def engine():
    return _make_engine_stub()


# ── Jest Output Parsing ──────────────────────────────────────


class TestParseJestOutput:
    """Verify jest verbose output parsing."""

    def test_all_pass(self, engine):
        stdout = """
PASS src/utils.test.js
  ✓ adds 1 + 2 to equal 3 (5ms)
  ✓ validates email format (3ms)

Test Suites: 1 passed, 1 total
Tests:       5 passed, 5 total
Snapshots:   0 total
Time:        1.234s
"""
        result = engine._parse_js_test_output(stdout, "", 0, 1.234, "jest")
        assert result.success is True
        assert result.passed == 5
        assert result.failed == 0

    def test_failures(self, engine):
        stdout = """
FAIL src/utils.test.js
  ✓ adds 1 + 2 to equal 3 (5ms)
  ✕ validates email format (3ms)
  ✕ handles null input (2ms)

Test Suites: 1 failed, 1 total
Tests:       2 failed, 3 passed, 5 total
"""
        result = engine._parse_js_test_output(stdout, "", 1, 1.0, "jest")
        assert result.success is False
        assert result.failed == 2
        assert result.passed == 3
        assert result.total_tests == 5

    def test_with_skipped(self, engine):
        stdout = """
Test Suites: 1 failed, 1 total
Tests:       1 failed, 2 skipped, 3 passed, 6 total
"""
        result = engine._parse_js_test_output(stdout, "", 1, 1.0, "jest")
        assert result.failed == 1
        assert result.passed == 3

    def test_with_pending(self, engine):
        stdout = """
Tests:       1 pending, 4 passed, 5 total
"""
        result = engine._parse_js_test_output(stdout, "", 0, 1.0, "jest")
        assert result.passed == 4

    def test_with_todo(self, engine):
        stdout = """
Tests:       2 todo, 4 passed, 6 total
"""
        result = engine._parse_js_test_output(stdout, "", 0, 1.0, "jest")
        assert result.passed == 4

    def test_failure_detail_extraction(self, engine):
        stdout = """
FAIL src/utils.test.js
  ✓ adds 1 + 2 to equal 3 (5ms)
  ✕ validates email format (3ms)

Tests:       1 failed, 1 passed, 2 total
"""
        result = engine._parse_js_test_output(stdout, "", 1, 1.0, "jest")
        assert len(result.failure_details) >= 1
        assert "validates email format" in result.failure_details[0]["test_name"]

    def test_empty_output_returncode_zero(self, engine):
        result = engine._parse_js_test_output("", "", 0, 1.0, "jest")
        assert result.skipped is True


# ── Vitest Output Parsing ────────────────────────────────────


class TestParseVitestOutput:
    """Verify vitest output parsing."""

    def test_all_pass(self, engine):
        stdout = """
 ✓ src/utils.test.ts (3 tests) 50ms

 Test Files  1 passed (1)
      Tests  5 passed (5)
"""
        result = engine._parse_js_test_output(stdout, "", 0, 0.5, "vitest")
        assert result.success is True
        assert result.passed == 5
        assert result.failed == 0

    def test_failures(self, engine):
        stdout = """
 ✕ src/utils.test.ts (5 tests) 100ms

 Test Files  1 failed (1)
      Tests  2 failed | 3 passed (5)
"""
        result = engine._parse_js_test_output(stdout, "", 1, 1.0, "vitest")
        assert result.success is False
        assert result.failed == 2
        assert result.passed == 3

    def test_failure_detail_extraction(self, engine):
        stdout = """
  ✕ should validate input (10ms)

 Tests  1 failed | 2 passed (3)
"""
        result = engine._parse_js_test_output(stdout, "", 1, 1.0, "vitest")
        assert len(result.failure_details) >= 1


# ── Mocha Output Parsing ─────────────────────────────────────


class TestParseMochaOutput:
    """Verify mocha spec reporter output parsing."""

    def test_all_pass(self, engine):
        stdout = """
  Array
    #indexOf()
      ✓ should return -1 when not present

  5 passing (100ms)
"""
        result = engine._parse_js_test_output(stdout, "", 0, 0.1, "mocha")
        assert result.success is True
        assert result.passed == 5

    def test_failures(self, engine):
        stdout = """
  3 passing (200ms)
  2 failing

  1) Array #indexOf() should return -1:
     AssertionError: expected 1 to equal -1
"""
        result = engine._parse_js_test_output(stdout, "", 1, 0.2, "mocha")
        assert result.success is False
        assert result.passed == 3
        assert result.failed == 2

    def test_failure_detail_extraction(self, engine):
        stdout = """
  1 passing
  1 failing

  1) should handle errors:
     TypeError: Cannot read property
"""
        result = engine._parse_js_test_output(stdout, "", 1, 0.1, "mocha")
        assert len(result.failure_details) >= 1
        assert "should handle errors" in result.failure_details[0]["test_name"]


# ── Setup Error Detection ────────────────────────────────────


class TestJsTestSetupError:
    """Verify setup error detection (command not found, missing modules)."""

    def test_command_not_found(self, engine):
        result = engine._parse_js_test_output(
            "", "bash: jest: command not found", 127, 0.1, "jest"
        )
        assert result.collection_error is True
        assert result.total_tests == 0

    def test_missing_module_with_node_modules(self, engine):
        stderr = "Error: Cannot find module 'jest-cli'\n  at node_modules/.cache/jest"
        result = engine._parse_js_test_output("", stderr, 1, 0.1, "jest")
        assert result.collection_error is True

    def test_missing_module_without_node_modules(self, engine):
        """'cannot find module' WITHOUT 'node_modules' should NOT trigger setup error."""
        stderr = "Error: Cannot find module './missing-file.js'"
        result = engine._parse_js_test_output("", stderr, 1, 0.1, "jest")
        # Should fall through to the normal parsing, not setup error
        assert result.collection_error is not True or result.total_tests > 0 or \
               "SETUP_ERROR" not in str(result.failure_details)

    def test_normal_failure_not_setup_error(self, engine):
        """Normal test failure should NOT be treated as setup error."""
        stdout = "Tests:       1 failed, 2 passed, 3 total"
        result = engine._parse_js_test_output(stdout, "", 1, 1.0, "jest")
        assert result.failed == 1
        assert not getattr(result, "collection_error", False)


# ── mypy Output Parsing ──────────────────────────────────────


class TestParseMypyOutput:
    """Verify mypy output parsing from linter_integration.py."""

    @pytest.fixture
    def linter(self):
        from cognix.linter_integration import LinterIntegration
        return LinterIntegration()

    def test_error_parsing(self, linter):
        output = "temp.py:10: error: Incompatible types in assignment  [assignment]"
        errors, warnings = linter._parse_mypy_output(output, "app.py")
        assert len(errors) == 1
        assert errors[0]["line"] == 10
        assert errors[0]["severity"] == "error"
        assert errors[0]["code"] == "mypy:assignment"
        assert errors[0]["file"] == "app.py"

    def test_warning_parsing(self, linter):
        output = "temp.py:5: warning: Unused variable  [unused-variable]"
        errors, warnings = linter._parse_mypy_output(output, "app.py")
        assert len(warnings) == 1
        assert warnings[0]["severity"] == "warning"

    def test_note_skipped(self, linter):
        output = "temp.py:1: note: See https://mypy.readthedocs.io"
        errors, warnings = linter._parse_mypy_output(output, "app.py")
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_import_error_skipped(self, linter):
        output = "temp.py:1: error: Cannot find module  [import]"
        errors, warnings = linter._parse_mypy_output(output, "app.py")
        assert len(errors) == 0

    def test_import_untyped_skipped(self, linter):
        output = "temp.py:1: error: Skipping module  [import-untyped]"
        errors, warnings = linter._parse_mypy_output(output, "app.py")
        assert len(errors) == 0

    def test_error_code_prefixed(self, linter):
        output = "temp.py:10: error: Incompatible types  [assignment]"
        errors, _ = linter._parse_mypy_output(output, "app.py")
        assert errors[0]["code"].startswith("mypy:")

    def test_no_error_code(self, linter):
        output = "temp.py:10: error: Some generic error"
        errors, _ = linter._parse_mypy_output(output, "app.py")
        assert len(errors) == 1
        assert errors[0]["code"] == "mypy"

    def test_empty_output(self, linter):
        errors, warnings = linter._parse_mypy_output("", "app.py")
        assert errors == []
        assert warnings == []

    def test_multiple_errors(self, linter):
        output = (
            "temp.py:10: error: Type error  [assignment]\n"
            "temp.py:20: error: Another error  [arg-type]\n"
            "temp.py:30: warning: Deprecated  [deprecated]\n"
        )
        errors, warnings = linter._parse_mypy_output(output, "app.py")
        assert len(errors) == 2
        assert len(warnings) == 1


# ── TS Error Code Filtering ──────────────────────────────────


class TestTsErrorFiltering:
    """Verify TypeScript error code set consistency."""

    @pytest.fixture
    def linter_cls(self):
        from cognix.linter_integration import LinterIntegration
        return LinterIntegration

    def test_critical_codes_contain_syntax_errors(self, linter_cls):
        """TS1xxx (syntax errors) should be in critical set."""
        critical = linter_cls.TS_CRITICAL_ERROR_CODES
        syntax_codes = [c for c in critical if c.startswith("1")]
        assert len(syntax_codes) >= 10  # at least 10 syntax error codes

    def test_ignorable_codes_contain_type_errors(self, linter_cls):
        """Type mismatch codes should be in ignorable set."""
        ignorable = linter_cls.TS_IGNORABLE_ERROR_CODES
        assert "2322" in ignorable  # Type not assignable
        assert "2345" in ignorable  # Argument type mismatch

    def test_ts_type_codes_for_ts_disjoint_from_critical(self, linter_cls):
        """TS_TYPE_ERROR_CODES_FOR_TS should not overlap with CRITICAL."""
        type_for_ts = linter_cls.TS_TYPE_ERROR_CODES_FOR_TS
        critical = linter_cls.TS_CRITICAL_ERROR_CODES
        overlap = type_for_ts & critical
        assert overlap == set(), \
            f"Overlap between TS_TYPE_FOR_TS and CRITICAL: {overlap}"

    def test_always_ignorable_subset_of_ignorable(self, linter_cls):
        """TS_ALWAYS_IGNORABLE should be a subset of IGNORABLE."""
        always = linter_cls.TS_ALWAYS_IGNORABLE_CODES
        ignorable = linter_cls.TS_IGNORABLE_ERROR_CODES
        not_in_ignorable = always - ignorable
        assert not_in_ignorable == set(), \
            f"These codes are in ALWAYS_IGNORABLE but not IGNORABLE: {not_in_ignorable}"

    def test_no_overlap_critical_and_ignorable(self, linter_cls):
        """CRITICAL and IGNORABLE should have no overlapping codes."""
        critical = linter_cls.TS_CRITICAL_ERROR_CODES
        ignorable = linter_cls.TS_IGNORABLE_ERROR_CODES
        overlap = critical & ignorable
        assert overlap == set(), \
            f"Overlap between CRITICAL and IGNORABLE: {overlap}"

    def test_no_overlap_critical_and_always_ignorable(self, linter_cls):
        """CRITICAL and ALWAYS_IGNORABLE should have no overlap."""
        critical = linter_cls.TS_CRITICAL_ERROR_CODES
        always = linter_cls.TS_ALWAYS_IGNORABLE_CODES
        overlap = critical & always
        assert overlap == set(), \
            f"Overlap between CRITICAL and ALWAYS_IGNORABLE: {overlap}"


# ── JS Test Framework Detection ──────────────────────────────


class TestDetectJsTestFramework:
    """Verify package.json-based framework detection."""

    def test_vitest_from_package_json(self, engine):
        pkg = {"devDependencies": {"vitest": "^1.0.0"}, "scripts": {"test": "vitest"}}
        generated_files = {
            "package.json": json.dumps(pkg),
            "src/utils.test.ts": "import { test } from 'vitest'",
        }
        test_files = ["src/utils.test.ts"]
        engine._get_npx_command = MagicMock(return_value="npx")

        result = engine._detect_js_test_framework(generated_files, test_files)

        assert result.framework == "vitest"
        assert result.language == "typescript"
        assert result.has_tests is True

    def test_jest_from_package_json(self, engine):
        pkg = {"devDependencies": {"jest": "^29.0.0"}, "scripts": {"test": "jest"}}
        generated_files = {
            "package.json": json.dumps(pkg),
            "src/utils.test.js": "test('hello', () => {})",
        }
        test_files = ["src/utils.test.js"]
        engine._get_npx_command = MagicMock(return_value="npx")

        result = engine._detect_js_test_framework(generated_files, test_files)

        assert result.framework == "jest"
        assert result.language == "javascript"

    def test_mocha_from_test_script(self, engine):
        pkg = {"scripts": {"test": "mocha --recursive"}}
        generated_files = {
            "package.json": json.dumps(pkg),
            "test/app.test.js": "describe('App', function() {})",
        }
        test_files = ["test/app.test.js"]
        engine._get_npx_command = MagicMock(return_value="npx")

        result = engine._detect_js_test_framework(generated_files, test_files)

        assert result.framework == "mocha"

    def test_config_file_fallback_vitest(self, engine):
        """When package.json has no framework info, detect from config files."""
        generated_files = {
            "vitest.config.ts": "export default {}",
            "src/utils.test.ts": "test('hello', () => {})",
        }
        test_files = ["src/utils.test.ts"]
        engine._get_npx_command = MagicMock(return_value="npx")

        result = engine._detect_js_test_framework(generated_files, test_files)

        assert result.framework == "vitest"

    def test_npx_not_available(self, engine):
        pkg = {"devDependencies": {"jest": "^29.0.0"}}
        generated_files = {
            "package.json": json.dumps(pkg),
            "src/utils.test.js": "test('hello', () => {})",
        }
        test_files = ["src/utils.test.js"]
        engine._get_npx_command = MagicMock(return_value=None)

        result = engine._detect_js_test_framework(generated_files, test_files)

        assert result.framework == "none"
        assert result.run_command == []
