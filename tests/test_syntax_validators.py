"""Tests for multi-language syntax validators in semi_auto_engine.py

Covers: _validate_go_syntax, _validate_java_syntax, _validate_rust_syntax,
        _validate_ruby_syntax, _validate_php_syntax, _check_compiler_available,
        _validate_with_compiler

Each validator is tested for:
  - Valid syntax detection
  - Invalid syntax detection (error returned)
  - Graceful skip when compiler is unavailable
  - Temp file cleanup after validation
"""

import glob
import os
import subprocess
import sys
import tempfile

import pytest
from unittest.mock import MagicMock, patch


# ── Code Samples ────────────────────────────────────────────

VALID_GO = """\
package main

import "fmt"

func main() {
\tfmt.Println("Hello, World!")
}
"""

INVALID_GO = """\
package main

import "fmt"

func main( {
\tfmt.Println("Hello, World!")
}
"""

# Java: package-private class (no public) to avoid temp filename mismatch
VALID_JAVA = """\
class Temp {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""

INVALID_JAVA = """\
class Temp {
    public static void main(String[] args) {
        System.out.println("Hello, World!"
    }
}
"""

VALID_RUST = """\
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
"""

INVALID_RUST = """\
pub fn add(a: i32, b: i32) -> i32 {
    a +
}
"""

VALID_RUBY = """\
def greet(name)
  puts "Hello, #{name}!"
end

greet("World")
"""

INVALID_RUBY = """\
def greet(name
  puts "Hello, #{name}!"
end
"""

VALID_PHP = """\
<?php
function greet($name) {
    echo "Hello, " . $name . "!\\n";
}
greet("World");
?>
"""

INVALID_PHP = """\
<?php
function greet($name) {
    echo "Hello, " . $name . "!"
}
greet("World");
"""


# ── Engine Stub ─────────────────────────────────────────────

def _make_engine_stub():
    """Create a minimal PostGenerationValidator-like object with syntax validation methods bound.

    The multi-language syntax validators (_validate_go_syntax, etc.) belong to
    PostGenerationValidator, not SemiAutoEngine.
    """
    from cognix.semi_auto_engine import PostGenerationValidator

    engine = MagicMock(spec=PostGenerationValidator)
    engine._check_compiler_available = PostGenerationValidator._check_compiler_available.__get__(engine)
    engine._validate_with_compiler = PostGenerationValidator._validate_with_compiler.__get__(engine)
    engine._validate_go_syntax = PostGenerationValidator._validate_go_syntax.__get__(engine)
    engine._validate_java_syntax = PostGenerationValidator._validate_java_syntax.__get__(engine)
    engine._validate_rust_syntax = PostGenerationValidator._validate_rust_syntax.__get__(engine)
    engine._validate_ruby_syntax = PostGenerationValidator._validate_ruby_syntax.__get__(engine)
    engine._validate_php_syntax = PostGenerationValidator._validate_php_syntax.__get__(engine)
    engine.logger = MagicMock()
    return engine


@pytest.fixture
def engine():
    return _make_engine_stub()


# ── Helpers ─────────────────────────────────────────────────

def _compiler_available(cmd, version_flag='--version'):
    """Check if a compiler is available on the system."""
    try:
        result = subprocess.run(
            [cmd, version_flag],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


# ── Compiler Availability ───────────────────────────────────

class TestCompilerAvailability:
    """Verify _check_compiler_available returns command or None."""

    def test_nonexistent_compiler_returns_none(self, engine):
        result = engine._check_compiler_available('__nonexistent_compiler_xyz__')
        assert result is None

    @pytest.mark.skipif(not _compiler_available('go', 'version'), reason="go not installed")
    def test_go_available(self, engine):
        result = engine._check_compiler_available('go', 'version')
        assert result is not None

    @pytest.mark.skipif(not _compiler_available('javac', '-version'), reason="javac not installed")
    def test_javac_available(self, engine):
        result = engine._check_compiler_available('javac', '-version')
        assert result is not None

    @pytest.mark.skipif(not _compiler_available('rustc'), reason="rustc not installed")
    def test_rustc_available(self, engine):
        result = engine._check_compiler_available('rustc')
        assert result is not None

    @pytest.mark.skipif(not _compiler_available('ruby'), reason="ruby not installed")
    def test_ruby_available(self, engine):
        result = engine._check_compiler_available('ruby')
        assert result is not None

    @pytest.mark.skipif(not _compiler_available('php'), reason="php not installed")
    def test_php_available(self, engine):
        result = engine._check_compiler_available('php')
        assert result is not None


# ── Go Syntax Validation ───────────────────────────────────

class TestGoSyntaxValidation:

    @pytest.mark.skipif(not _compiler_available('go', 'version'), reason="go not installed")
    def test_valid_go_syntax(self, engine):
        valid, error = engine._validate_go_syntax("main.go", VALID_GO)
        assert valid is True
        assert error is None
        engine.logger.debug.assert_any_call("[Syntax Check] Valid Go syntax: main.go")

    @pytest.mark.skipif(not _compiler_available('go', 'version'), reason="go not installed")
    def test_invalid_go_syntax(self, engine):
        valid, error = engine._validate_go_syntax("main.go", INVALID_GO)
        assert valid is False
        assert error is not None
        engine.logger.debug.assert_any_call("[Syntax Check] Go syntax error in main.go")

    def test_go_unavailable_returns_true_none(self, engine):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            valid, error = engine._validate_go_syntax("main.go", VALID_GO)
            assert valid is True
            assert error is None

    @pytest.mark.skipif(not _compiler_available('go', 'version'), reason="go not installed")
    def test_go_temp_dir_cleanup(self, engine):
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
        engine._validate_go_syntax("main.go", VALID_GO)
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
        new_items = after - before
        assert len(new_items) == 0, f"Leftover temp dirs: {new_items}"

    @pytest.mark.skipif(not _compiler_available('go', 'version'), reason="go not installed")
    def test_go_temp_dir_cleanup_on_error(self, engine):
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
        engine._validate_go_syntax("main.go", INVALID_GO)
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
        new_items = after - before
        assert len(new_items) == 0, f"Leftover temp dirs after error: {new_items}"


# ── Java Syntax Validation ─────────────────────────────────

class TestJavaSyntaxValidation:

    @pytest.mark.skipif(not _compiler_available('javac', '-version'), reason="javac not installed")
    def test_valid_java_syntax(self, engine):
        valid, error = engine._validate_java_syntax("Temp.java", VALID_JAVA)
        assert valid is True
        assert error is None
        engine.logger.debug.assert_any_call("[Syntax Check] Valid syntax: Temp.java")

    @pytest.mark.skipif(not _compiler_available('javac', '-version'), reason="javac not installed")
    def test_invalid_java_syntax(self, engine):
        valid, error = engine._validate_java_syntax("Temp.java", INVALID_JAVA)
        assert valid is False
        assert error is not None
        engine.logger.debug.assert_any_call("[Syntax Check] Syntax error in Temp.java")

    def test_java_unavailable_returns_true_none(self, engine):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            valid, error = engine._validate_java_syntax("Temp.java", VALID_JAVA)
            assert valid is True
            assert error is None


# ── Rust Syntax Validation ─────────────────────────────────

class TestRustSyntaxValidation:

    @pytest.mark.skipif(not _compiler_available('rustc'), reason="rustc not installed")
    def test_valid_rust_syntax(self, engine):
        valid, error = engine._validate_rust_syntax("lib.rs", VALID_RUST)
        assert valid is True
        assert error is None
        engine.logger.debug.assert_any_call("[Syntax Check] Valid Rust syntax: lib.rs")

    @pytest.mark.skipif(not _compiler_available('rustc'), reason="rustc not installed")
    def test_invalid_rust_syntax(self, engine):
        valid, error = engine._validate_rust_syntax("lib.rs", INVALID_RUST)
        assert valid is False
        assert error is not None
        engine.logger.debug.assert_any_call("[Syntax Check] Rust syntax error in lib.rs")

    def test_rust_unavailable_returns_true_none(self, engine):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            valid, error = engine._validate_rust_syntax("lib.rs", VALID_RUST)
            assert valid is True
            assert error is None

    @pytest.mark.skipif(not _compiler_available('rustc'), reason="rustc not installed")
    def test_rust_temp_file_cleanup(self, engine):
        engine._validate_rust_syntax("lib.rs", VALID_RUST)
        engine._validate_rust_syntax("lib.rs", INVALID_RUST)
        # Rust validator uses NamedTemporaryFile with .rs suffix — check no leftover
        leftover = [f for f in glob.glob(os.path.join(tempfile.gettempdir(), 'tmp*.rs'))
                     if os.path.getmtime(f) > os.path.getmtime(__file__)]
        assert len(leftover) == 0, f"Leftover .rs temp files: {leftover}"


# ── Ruby Syntax Validation ─────────────────────────────────

class TestRubySyntaxValidation:

    @pytest.mark.skipif(not _compiler_available('ruby'), reason="ruby not installed")
    def test_valid_ruby_syntax(self, engine):
        valid, error = engine._validate_ruby_syntax("greet.rb", VALID_RUBY)
        assert valid is True
        assert error is None
        engine.logger.debug.assert_any_call("[Syntax Check] Valid syntax: greet.rb")

    @pytest.mark.skipif(not _compiler_available('ruby'), reason="ruby not installed")
    def test_invalid_ruby_syntax(self, engine):
        valid, error = engine._validate_ruby_syntax("greet.rb", INVALID_RUBY)
        assert valid is False
        assert error is not None
        engine.logger.debug.assert_any_call("[Syntax Check] Syntax error in greet.rb")

    def test_ruby_unavailable_returns_true_none(self, engine):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            valid, error = engine._validate_ruby_syntax("greet.rb", VALID_RUBY)
            assert valid is True
            assert error is None


# ── PHP Syntax Validation ──────────────────────────────────

class TestPhpSyntaxValidation:

    @pytest.mark.skipif(not _compiler_available('php'), reason="php not installed")
    def test_valid_php_syntax(self, engine):
        valid, error = engine._validate_php_syntax("index.php", VALID_PHP)
        assert valid is True
        assert error is None
        engine.logger.debug.assert_any_call("[Syntax Check] Valid syntax: index.php")

    @pytest.mark.skipif(not _compiler_available('php'), reason="php not installed")
    def test_invalid_php_syntax(self, engine):
        valid, error = engine._validate_php_syntax("index.php", INVALID_PHP)
        assert valid is False
        assert error is not None
        engine.logger.debug.assert_any_call("[Syntax Check] Syntax error in index.php")

    def test_php_unavailable_returns_true_none(self, engine):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            valid, error = engine._validate_php_syntax("index.php", VALID_PHP)
            assert valid is True
            assert error is None


# ── Graceful Skip Behavior (all languages, mocked) ─────────

class TestGracefulSkipBehavior:
    """Verify all validators return (True, None) when compiler is not found."""

    def test_all_validators_skip_gracefully(self, engine):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            validators = [
                (engine._validate_go_syntax, "main.go", VALID_GO),
                (engine._validate_java_syntax, "Temp.java", VALID_JAVA),
                (engine._validate_rust_syntax, "lib.rs", VALID_RUST),
                (engine._validate_ruby_syntax, "greet.rb", VALID_RUBY),
                (engine._validate_php_syntax, "index.php", VALID_PHP),
            ]
            for validate_fn, filepath, code in validators:
                valid, error = validate_fn(filepath, code)
                assert valid is True, f"{validate_fn.__name__} should return True when unavailable"
                assert error is None, f"{validate_fn.__name__} should return None error when unavailable"


# ── Temp File Cleanup ──────────────────────────────────────

class TestTempFileCleanup:
    """Verify no temp files are left behind after validation."""

    @pytest.mark.skipif(not _compiler_available('go', 'version'), reason="go not installed")
    def test_go_cleanup_valid(self, engine):
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
        engine._validate_go_syntax("main.go", VALID_GO)
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
        assert after - before == set()

    @pytest.mark.skipif(not _compiler_available('go', 'version'), reason="go not installed")
    def test_go_cleanup_invalid(self, engine):
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
        engine._validate_go_syntax("main.go", INVALID_GO)
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
        assert after - before == set()

    def test_cleanup_on_timeout(self, engine):
        """Verify cleanup even when subprocess times out."""
        def timeout_on_build(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('args', [])
            if isinstance(cmd, list) and 'build' in cmd:
                raise subprocess.TimeoutExpired(cmd, 30)
            # Let version check succeed
            return MagicMock(returncode=0)

        with patch('subprocess.run', side_effect=timeout_on_build):
            before = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
            valid, error = engine._validate_go_syntax("main.go", VALID_GO)
            after = set(glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*')))
            # Timeout returns (True, None) — fail-open
            assert valid is True
            assert error is None
            assert after - before == set()


# ── Standalone Runner ──────────────────────────────────────

def _run_standalone():
    """Color-coded standalone test runner for direct execution."""
    try:
        import colorama
        colorama.init()
    except ImportError:
        pass

    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    passed = 0
    failed = 0
    skipped = 0

    print(f"\n{BOLD}{'=' * 50}")
    print(f" Cognix Syntax Validator Test")
    print(f"{'=' * 50}{RESET}\n")

    # Environment check
    compilers = {
        'Go':   ('go', 'version'),
        'Java': ('javac', '-version'),
        'Rust': ('rustc', '--version'),
        'Ruby': ('ruby', '--version'),
        'PHP':  ('php', '--version'),
    }

    available = {}
    for lang, (cmd, flag) in compilers.items():
        try:
            result = subprocess.run([cmd, flag], capture_output=True, timeout=5,
                                    encoding='utf-8', errors='replace')
            if result.returncode == 0:
                ver = (result.stdout or result.stderr).strip().split('\n')[0][:30]
                print(f"[ENV] {lang + ':':8s} {ver:30s} {GREEN}AVAILABLE{RESET}")
                available[lang] = True
            else:
                print(f"[ENV] {lang + ':':8s} {'(not installed)':30s} {YELLOW}SKIP{RESET}")
                available[lang] = False
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            print(f"[ENV] {lang + ':':8s} {'(not installed)':30s} {YELLOW}SKIP{RESET}")
            available[lang] = False

    print()

    engine = _make_engine_stub()

    # Test definitions: (label, lang_key, validator, filepath, valid_code, invalid_code, log_valid, log_invalid)
    tests = [
        ("Go", "Go", engine._validate_go_syntax, "main.go", VALID_GO, INVALID_GO,
         "[Syntax Check] Valid Go syntax: main.go", "[Syntax Check] Go syntax error in main.go"),
        ("Java", "Java", engine._validate_java_syntax, "Temp.java", VALID_JAVA, INVALID_JAVA,
         "[Syntax Check] Valid syntax: Temp.java", "[Syntax Check] Syntax error in Temp.java"),
        ("Rust", "Rust", engine._validate_rust_syntax, "lib.rs", VALID_RUST, INVALID_RUST,
         "[Syntax Check] Valid Rust syntax: lib.rs", "[Syntax Check] Rust syntax error in lib.rs"),
        ("Ruby", "Ruby", engine._validate_ruby_syntax, "greet.rb", VALID_RUBY, INVALID_RUBY,
         "[Syntax Check] Valid syntax: greet.rb", "[Syntax Check] Syntax error in greet.rb"),
        ("PHP", "PHP", engine._validate_php_syntax, "index.php", VALID_PHP, INVALID_PHP,
         "[Syntax Check] Valid syntax: index.php", "[Syntax Check] Syntax error in index.php"),
    ]

    for label, lang_key, validate_fn, filepath, valid_code, invalid_code, log_valid, log_invalid in tests:
        if not available.get(lang_key):
            print(f"[TEST] {label} valid syntax:          {YELLOW}SKIP{RESET}")
            print(f"[TEST] {label} invalid syntax:        {YELLOW}SKIP{RESET}")
            skipped += 2
            continue

        # Valid syntax test
        engine.logger.reset_mock()
        try:
            valid, error = validate_fn(filepath, valid_code)
            if valid is True and error is None:
                print(f"[TEST] {label} valid syntax:          {GREEN}PASS{RESET}")
                passed += 1
            else:
                print(f"[TEST] {label} valid syntax:          {RED}FAIL{RESET} (valid={valid}, error={error})")
                failed += 1
        except Exception as e:
            print(f"[TEST] {label} valid syntax:          {RED}FAIL{RESET} ({e})")
            failed += 1

        # Invalid syntax test
        engine.logger.reset_mock()
        try:
            valid, error = validate_fn(filepath, invalid_code)
            if valid is False and error is not None:
                print(f"[TEST] {label} invalid syntax:        {GREEN}PASS{RESET} (error detected)")
                passed += 1
            else:
                print(f"[TEST] {label} invalid syntax:        {RED}FAIL{RESET} (valid={valid}, error={error})")
                failed += 1
        except Exception as e:
            print(f"[TEST] {label} invalid syntax:        {RED}FAIL{RESET} ({e})")
            failed += 1

    # Unavailable skip test (always runs, uses mock)
    print()
    engine.logger.reset_mock()
    with patch('subprocess.run', side_effect=FileNotFoundError):
        all_skip_ok = True
        for label, _, validate_fn, filepath, valid_code, *_ in tests:
            valid, error = validate_fn(filepath, valid_code)
            if not (valid is True and error is None):
                all_skip_ok = False
                break
    if all_skip_ok:
        print(f"[TEST] Unavailable skip (all langs):  {GREEN}PASS{RESET}")
        passed += 1
    else:
        print(f"[TEST] Unavailable skip (all langs):  {RED}FAIL{RESET}")
        failed += 1

    # Temp cleanup check
    leftovers = glob.glob(os.path.join(tempfile.gettempdir(), 'cognix_go_*'))
    if not leftovers:
        print(f"[CLEANUP] cognix_go_* dirs:            {GREEN}PASS{RESET} (0 leftovers)")
        passed += 1
    else:
        print(f"[CLEANUP] cognix_go_* dirs:            {RED}FAIL{RESET} ({len(leftovers)} leftovers)")
        failed += 1

    # Summary
    print(f"\n{BOLD}{'=' * 50}")
    color = GREEN if failed == 0 else RED
    print(f" Results: {color}{passed} passed{RESET}, {RED if failed else RESET}{failed} failed{RESET}, {YELLOW}{skipped} skipped{RESET}")
    print(f"{'=' * 50}{RESET}\n")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    # Ensure cognix package is importable when running standalone
    _repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    sys.exit(_run_standalone())
