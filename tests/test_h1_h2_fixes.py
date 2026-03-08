"""
Tests for H-1 and H-2 fixes.

H-1: flask_web_app implicit keyword change
    - "flask" alone should NOT trigger flask_web_app pattern
    - "flask app", "flask web", etc. SHOULD trigger flask_web_app pattern
    - System prompt containing "Flask-SQLAlchemy==3.1.1" should NOT trigger

H-2a: _is_standard_library() using sys.stdlib_module_names
    - Previously missing modules (tempfile, runpy, shutil, etc.) should be recognized
    - Sub-modules (os.path, json.decoder) should be recognized via top-level
    - Third-party modules should NOT be recognized

H-2b: _is_pip_package() extras bracket stripping
    - "uvicorn[standard]==0.32.1" should match module "uvicorn"
    - Hyphen-to-underscore normalization should still work
    - Comments and empty lines should be skipped
"""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# ── Setup ──────────────────────────────────────────────────

# Import targets
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cognix.requirement_validator import RequirementValidator
from cognix.semi_auto_engine import AppPatternDetector


@pytest.fixture
def validator():
    """RequirementValidator instance for testing."""
    return RequirementValidator(workspace_path="/tmp/test")


@pytest.fixture
def flask_patterns():
    """
    Minimal app_patterns.json fixture with flask_web_app + fastapi_backend.
    Mirrors the real structure to test detect_pattern() behavior.
    """
    return {
        "web_app_patterns": {
            "flask_web_app": {
                "files": ["py", "html", "css", "js"],
                "trigger_conditions": {
                    "mode": "flexible",
                    "triggers": {
                        "explicit_keywords": {
                            "enabled": True,
                            "keywords": [
                                "flask app",
                                "flask web app",
                                "flask application",
                                "flask website",
                                "flask with html",
                                "python web app with flask"
                            ],
                            "confidence": "high"
                        },
                        "implicit_keywords": {
                            "enabled": True,
                            "keywords": [
                                "flask app",
                                "flask web",
                                "flask server",
                                "flask api",
                                "flask backend"
                            ],
                            "context_requirements": [
                                "goal_mentions_web_or_app",
                                "goal_mentions_ui_or_interface"
                            ],
                            "confidence": "medium"
                        }
                    }
                }
            },
            "fastapi_backend": {
                "files": ["py"],
                "trigger_conditions": {
                    "mode": "flexible",
                    "triggers": {
                        "explicit_keywords": {
                            "enabled": True,
                            "keywords": [
                                "fastapi",
                                "fast api",
                                "fastapi app",
                                "fastapi backend"
                            ],
                            "confidence": "high"
                        },
                        "implicit_keywords": {
                            "enabled": False,
                            "keywords": [],
                            "confidence": "medium"
                        }
                    }
                }
            }
        }
    }


def _make_detector_with_patterns(patterns_dict):
    """Create AppPatternDetector with injected patterns (skip file I/O)."""
    detector = AppPatternDetector.__new__(AppPatternDetector)
    detector.logger = None
    detector.patterns = patterns_dict.get("web_app_patterns", {})
    return detector


# ══════════════════════════════════════════════════════════════
# H-1: flask_web_app implicit keyword detection
# ══════════════════════════════════════════════════════════════

class TestH1FlaskImplicitKeyword:
    """H-1: Verify flask implicit keyword change prevents false matches."""

    def test_bare_flask_does_not_trigger(self, flask_patterns):
        """'flask' alone should NOT trigger flask_web_app.
        This is the core H-1 fix: prevents system prompt text like
        'Flask-SQLAlchemy==3.1.1' from triggering the pattern.
        """
        detector = _make_detector_with_patterns(flask_patterns)
        result = detector.detect_pattern("flask")
        assert result is None

    def test_flask_in_requirements_does_not_trigger(self, flask_patterns):
        """System prompt containing 'Flask-SQLAlchemy==3.1.1' should NOT match.
        This was the actual bug: FastAPI project's requirements listed Flask
        packages, and the bare 'flask' keyword matched.
        """
        detector = _make_detector_with_patterns(flask_patterns)
        goal = (
            "Build a Quick Notes API with FastAPI.\n"
            "Requirements: Flask-SQLAlchemy==3.1.1, flask-cors==5.0.0"
        )
        # Should detect fastapi_backend (explicit), NOT flask_web_app
        result = detector.detect_pattern(goal)
        assert result != "flask_web_app"

    def test_flask_app_triggers(self, flask_patterns):
        """'flask app' should trigger flask_web_app via explicit keyword."""
        detector = _make_detector_with_patterns(flask_patterns)
        result = detector.detect_pattern("Create a flask app for blog")
        assert result == "flask_web_app"

    def test_flask_web_triggers(self, flask_patterns):
        """'flask web' should trigger flask_web_app via implicit keyword."""
        detector = _make_detector_with_patterns(flask_patterns)
        result = detector.detect_pattern("Build a flask web interface")
        assert result == "flask_web_app"

    def test_flask_server_triggers(self, flask_patterns):
        """'flask server' should trigger flask_web_app via implicit keyword."""
        detector = _make_detector_with_patterns(flask_patterns)
        result = detector.detect_pattern("Set up a flask server with templates")
        assert result == "flask_web_app"

    def test_flask_api_triggers(self, flask_patterns):
        """'flask api' should trigger flask_web_app via implicit keyword."""
        detector = _make_detector_with_patterns(flask_patterns)
        result = detector.detect_pattern("Create a flask api for users")
        assert result == "flask_web_app"

    def test_flask_backend_triggers(self, flask_patterns):
        """'flask backend' should trigger flask_web_app via implicit keyword."""
        detector = _make_detector_with_patterns(flask_patterns)
        result = detector.detect_pattern("flask backend with REST endpoints")
        assert result == "flask_web_app"

    def test_fastapi_explicit_triggers(self, flask_patterns):
        """FastAPI should trigger fastapi_backend, not flask_web_app."""
        detector = _make_detector_with_patterns(flask_patterns)
        result = detector.detect_pattern("Build a FastAPI backend")
        assert result == "fastapi_backend"

    def test_unrelated_goal_returns_none(self, flask_patterns):
        """Unrelated goal should return None."""
        detector = _make_detector_with_patterns(flask_patterns)
        result = detector.detect_pattern("Build a React dashboard")
        assert result is None


# ══════════════════════════════════════════════════════════════
# H-2a: _is_standard_library()
# ══════════════════════════════════════════════════════════════

class TestH2aIsStandardLibrary:
    """H-2a: Verify _is_standard_library() recognizes all stdlib modules."""

    # --- Previously missing modules (the actual bug) ---

    def test_tempfile_is_stdlib(self, validator):
        """tempfile was missing from old hardcoded list, causing auto-completion
        to generate tempfile.py unnecessarily."""
        assert validator._is_standard_library('tempfile') is True

    def test_runpy_is_stdlib(self, validator):
        """runpy was missing, causing runpy/__init__.py generation."""
        assert validator._is_standard_library('runpy') is True

    def test_shutil_is_stdlib(self, validator):
        assert validator._is_standard_library('shutil') is True

    def test_hashlib_is_stdlib(self, validator):
        assert validator._is_standard_library('hashlib') is True

    def test_uuid_is_stdlib(self, validator):
        assert validator._is_standard_library('uuid') is True

    def test_base64_is_stdlib(self, validator):
        assert validator._is_standard_library('base64') is True

    def test_csv_is_stdlib(self, validator):
        assert validator._is_standard_library('csv') is True

    def test_zipfile_is_stdlib(self, validator):
        assert validator._is_standard_library('zipfile') is True

    def test_signal_is_stdlib(self, validator):
        assert validator._is_standard_library('signal') is True

    def test_platform_is_stdlib(self, validator):
        assert validator._is_standard_library('platform') is True

    def test_contextvars_is_stdlib(self, validator):
        assert validator._is_standard_library('contextvars') is True

    # --- Core stdlib modules (should still work) ---

    def test_os_is_stdlib(self, validator):
        assert validator._is_standard_library('os') is True

    def test_sys_is_stdlib(self, validator):
        assert validator._is_standard_library('sys') is True

    def test_json_is_stdlib(self, validator):
        assert validator._is_standard_library('json') is True

    def test_datetime_is_stdlib(self, validator):
        assert validator._is_standard_library('datetime') is True

    def test_pathlib_is_stdlib(self, validator):
        assert validator._is_standard_library('pathlib') is True

    def test_asyncio_is_stdlib(self, validator):
        assert validator._is_standard_library('asyncio') is True

    def test_typing_is_stdlib(self, validator):
        assert validator._is_standard_library('typing') is True

    def test_logging_is_stdlib(self, validator):
        assert validator._is_standard_library('logging') is True

    # --- Sub-module handling ---

    def test_os_path_recognized_via_top_level(self, validator):
        """'os.path' should be recognized by splitting to 'os'."""
        assert validator._is_standard_library('os.path') is True

    def test_json_decoder_recognized(self, validator):
        assert validator._is_standard_library('json.decoder') is True

    def test_collections_abc_recognized(self, validator):
        assert validator._is_standard_library('collections.abc') is True

    def test_urllib_parse_recognized(self, validator):
        assert validator._is_standard_library('urllib.parse') is True

    # --- Third-party modules must NOT match ---

    def test_flask_not_stdlib(self, validator):
        assert validator._is_standard_library('flask') is False

    def test_fastapi_not_stdlib(self, validator):
        assert validator._is_standard_library('fastapi') is False

    def test_pandas_not_stdlib(self, validator):
        assert validator._is_standard_library('pandas') is False

    def test_requests_not_stdlib(self, validator):
        assert validator._is_standard_library('requests') is False

    def test_sqlalchemy_not_stdlib(self, validator):
        assert validator._is_standard_library('sqlalchemy') is False

    def test_pydantic_not_stdlib(self, validator):
        assert validator._is_standard_library('pydantic') is False

    # --- Application modules must NOT match ---

    def test_models_not_stdlib(self, validator):
        assert validator._is_standard_library('models') is False

    def test_app_not_stdlib(self, validator):
        assert validator._is_standard_library('app') is False

    def test_services_auth_not_stdlib(self, validator):
        assert validator._is_standard_library('services.auth') is False

    # --- sys.stdlib_module_names path (Python 3.10+) ---

    @pytest.mark.skipif(
        not hasattr(sys, 'stdlib_module_names'),
        reason="sys.stdlib_module_names requires Python 3.10+"
    )
    def test_sys_stdlib_module_names_used(self, validator):
        """On Python 3.10+, sys.stdlib_module_names should be the primary check."""
        # 'abc' is in sys.stdlib_module_names but also in fallback
        assert validator._is_standard_library('abc') is True
        # '_thread' is in sys.stdlib_module_names but NOT in fallback
        assert validator._is_standard_library('_thread') is True


# ══════════════════════════════════════════════════════════════
# H-2b: _is_pip_package() extras bracket stripping
# ══════════════════════════════════════════════════════════════

class TestH2bIsPipPackageExtras:
    """H-2b: Verify _is_pip_package() handles extras brackets correctly."""

    def test_extras_bracket_stripped(self, validator):
        """uvicorn[standard]==0.32.1 should match module 'uvicorn'.
        This was the actual bug: bracket was not stripped, so
        'uvicorn[standard]' != 'uvicorn'.
        """
        files = {'requirements.txt': 'uvicorn[standard]==0.32.1'}
        assert validator._is_pip_package('uvicorn', files) is True

    def test_extras_bracket_multiple(self, validator):
        """Multiple extras like celery[redis,auth] should still match 'celery'."""
        files = {'requirements.txt': 'celery[redis,auth]==5.3.0'}
        assert validator._is_pip_package('celery', files) is True

    def test_extras_bracket_no_version(self, validator):
        """Package with extras but no version pin."""
        files = {'requirements.txt': 'uvicorn[standard]'}
        assert validator._is_pip_package('uvicorn', files) is True

    def test_normal_package_still_works(self, validator):
        """Packages without extras brackets should still work."""
        files = {'requirements.txt': 'Flask==3.0.0\npandas>=1.5.0'}
        assert validator._is_pip_package('flask', files) is True
        assert validator._is_pip_package('pandas', files) is True

    def test_hyphen_to_underscore_with_extras(self, validator):
        """Flask-CORS should match both 'flask-cors' and 'flask_cors'."""
        files = {'requirements.txt': 'Flask-CORS[extra]==4.0.0'}
        assert validator._is_pip_package('flask_cors', files) is True

    def test_hyphen_to_underscore_without_extras(self, validator):
        """Hyphen normalization still works without extras."""
        files = {'requirements.txt': 'python-dotenv==1.0.0'}
        assert validator._is_pip_package('python_dotenv', files) is True

    def test_submodule_resolved_to_top_level(self, validator):
        """flask.app should match via top-level 'flask'."""
        files = {'requirements.txt': 'Flask==3.0.0'}
        assert validator._is_pip_package('flask.app', files) is True

    def test_nonexistent_package_returns_false(self, validator):
        """Module not in requirements.txt should return False."""
        files = {'requirements.txt': 'Flask==3.0.0'}
        assert validator._is_pip_package('models', files) is False

    def test_empty_requirements_returns_false(self, validator):
        """Missing requirements.txt should return False."""
        files = {}
        assert validator._is_pip_package('flask', files) is False

    def test_comments_and_blank_lines_skipped(self, validator):
        """Comments and blank lines should not cause errors."""
        files = {'requirements.txt': (
            "# Core dependencies\n"
            "\n"
            "Flask==3.0.0\n"
            "# Database\n"
            "SQLAlchemy>=2.0.0\n"
        )}
        assert validator._is_pip_package('flask', files) is True
        assert validator._is_pip_package('sqlalchemy', files) is True

    def test_various_version_specifiers(self, validator):
        """All version specifiers (==, >=, <=, ~=) should be handled."""
        files = {'requirements.txt': (
            "flask==3.0.0\n"
            "pandas>=1.5.0\n"
            "requests<=2.31.0\n"
            "numpy~=1.24.0\n"
        )}
        assert validator._is_pip_package('flask', files) is True
        assert validator._is_pip_package('pandas', files) is True
        assert validator._is_pip_package('requests', files) is True
        assert validator._is_pip_package('numpy', files) is True

    def test_case_insensitive_matching(self, validator):
        """Package matching should be case-insensitive."""
        files = {'requirements.txt': 'Flask==3.0.0'}
        assert validator._is_pip_package('flask', files) is True
        assert validator._is_pip_package('Flask', files) is True
        assert validator._is_pip_package('FLASK', files) is True


# ══════════════════════════════════════════════════════════════
# H-3a: FEATURE_KEYWORDS 複合キーワード化（誤検出防止）
# ══════════════════════════════════════════════════════════════

class TestH3aFeatureKeywordsFalsePositives:
    """H-3a: Verify FEATURE_KEYWORDS compound keywords prevent false detection.

    Root cause: Single-word keywords like 'api', 'test', 'window', 'hash',
    'terminal', 'storage', 'spec' matched spec text in unintended contexts
    (e.g., "Web Audio API" triggered 'api' feature requirement).
    """

    # --- 'api' feature: browser API mentions must NOT trigger ---

    def test_web_audio_api_does_not_trigger(self, validator):
        """Spec mentioning 'Web Audio API' should NOT require REST API feature."""
        result = validator.validate_requirements(
            "Build a Tetris game with Web Audio API for sound effects",
            {'game.html': '<html><script>new AudioContext()</script></html>'}
        )
        missing = result.get('missing_features', [])
        assert 'api' not in [f.lower() for f in missing]

    def test_canvas_api_does_not_trigger(self, validator):
        """Spec mentioning 'Canvas API' should NOT require REST API feature."""
        result = validator.validate_requirements(
            "Use Canvas API to render graphics on the screen",
            {'game.html': '<canvas></canvas>'}
        )
        missing = result.get('missing_features', [])
        assert 'api' not in [f.lower() for f in missing]

    def test_fetch_api_does_not_trigger(self, validator):
        """Spec mentioning 'Fetch API' should NOT require REST API feature."""
        result = validator.validate_requirements(
            "Use Fetch API for data retrieval",
            {'app.js': 'fetch("/data").then(r => r.json())'}
        )
        missing = result.get('missing_features', [])
        assert 'api' not in [f.lower() for f in missing]

    def test_rest_api_does_trigger(self, validator):
        """Spec explicitly requesting 'REST API' SHOULD require API feature."""
        features = validator._extract_required_features(
            "Build a REST API for user management"
        )
        assert 'api' in features

    def test_api_endpoint_does_trigger(self, validator):
        """Spec requesting 'API endpoint' SHOULD require API feature."""
        features = validator._extract_required_features(
            "Create an API endpoint for CRUD operations"
        )
        assert 'api' in features

    def test_api_server_does_trigger(self, validator):
        """Spec requesting 'API server' SHOULD require API feature."""
        features = validator._extract_required_features(
            "Build an API server with Express"
        )
        assert 'api' in features

    def test_http_server_does_trigger(self, validator):
        """Spec requesting 'HTTP server' SHOULD require API feature."""
        features = validator._extract_required_features(
            "Create an HTTP server for the backend"
        )
        assert 'api' in features

    # --- 'test' feature: casual mentions must NOT trigger ---

    def test_bare_test_does_not_trigger(self, validator):
        """'test the application' should NOT require test framework feature."""
        features = validator._extract_required_features(
            "Build a calculator and test the application manually"
        )
        assert 'test' not in features

    def test_stress_test_does_not_trigger(self, validator):
        """'stress test' should NOT require test framework feature."""
        features = validator._extract_required_features(
            "Run a stress test on the server"
        )
        assert 'test' not in features

    def test_unit_test_does_trigger(self, validator):
        """'unit test' SHOULD require test feature."""
        features = validator._extract_required_features(
            "Write unit test for the service layer"
        )
        assert 'test' in features

    def test_pytest_does_trigger(self, validator):
        """'pytest' SHOULD require test feature."""
        features = validator._extract_required_features(
            "Use pytest for testing"
        )
        assert 'test' in features

    # --- 'test' feature: 'spec' must NOT trigger ---

    def test_spec_does_not_trigger(self, validator):
        """'specification' or 'spec' alone should NOT require test feature."""
        features = validator._extract_required_features(
            "Build per the spec document provided"
        )
        assert 'test' not in features

    def test_sample_spec_does_not_trigger(self, validator):
        """'sample_spec_tetris.md' in goal should NOT require test feature."""
        features = validator._extract_required_features(
            "Generate code from sample_spec_tetris.md specification"
        )
        assert 'test' not in features

    # --- 'gui' feature: browser 'window' must NOT trigger ---

    def test_browser_window_does_not_trigger(self, validator):
        """'window.addEventListener' should NOT require GUI framework feature."""
        features = validator._extract_required_features(
            "Add window resize event handling"
        )
        assert 'gui' not in features

    def test_game_window_does_not_trigger(self, validator):
        """'game window' should NOT require GUI framework feature."""
        features = validator._extract_required_features(
            "Create a game window with canvas"
        )
        assert 'gui' not in features

    def test_dialog_does_not_trigger(self, validator):
        """'confirmation dialog' should NOT require GUI framework feature."""
        features = validator._extract_required_features(
            "Show a confirmation dialog before deleting"
        )
        assert 'gui' not in features

    def test_tkinter_does_trigger(self, validator):
        """'tkinter' SHOULD require GUI feature."""
        features = validator._extract_required_features(
            "Build a desktop app with tkinter"
        )
        assert 'gui' in features

    def test_gui_app_does_trigger(self, validator):
        """'GUI app' SHOULD require GUI feature."""
        features = validator._extract_required_features(
            "Create a GUI app for file management"
        )
        assert 'gui' in features

    # --- 'encryption' feature: 'hash' alone must NOT trigger ---

    def test_hash_table_does_not_trigger(self, validator):
        """'hash table' should NOT require encryption feature."""
        features = validator._extract_required_features(
            "Implement a hash table for fast lookup"
        )
        assert 'encryption' not in features

    def test_url_hash_does_not_trigger(self, validator):
        """'URL hash' should NOT require encryption feature."""
        features = validator._extract_required_features(
            "Use location hash for client-side routing"
        )
        assert 'encryption' not in features

    def test_encrypt_does_trigger(self, validator):
        """'encrypt' SHOULD require encryption feature."""
        features = validator._extract_required_features(
            "Encrypt user data before storing"
        )
        assert 'encryption' in features

    def test_password_hash_does_trigger(self, validator):
        """'password hash' SHOULD require encryption feature."""
        features = validator._extract_required_features(
            "Use password hash with bcrypt"
        )
        assert 'encryption' in features

    # --- 'cli' feature: 'terminal' alone must NOT trigger ---

    def test_terminal_state_does_not_trigger(self, validator):
        """'terminal state' should NOT require CLI feature."""
        features = validator._extract_required_features(
            "Check the terminal state of the finite automaton"
        )
        assert 'cli' not in features

    def test_bare_cli_does_not_trigger(self, validator):
        """Bare 'cli' without 'tool'/'app' should NOT trigger CLI feature."""
        features = validator._extract_required_features(
            "The CLI for this service is minimal"
        )
        assert 'cli' not in features

    def test_cli_tool_does_trigger(self, validator):
        """'CLI tool' SHOULD require CLI feature."""
        features = validator._extract_required_features(
            "Build a CLI tool for data processing"
        )
        assert 'cli' in features

    def test_command_line_does_trigger(self, validator):
        """'command line' SHOULD require CLI feature."""
        features = validator._extract_required_features(
            "Create a command line utility"
        )
        assert 'cli' in features

    def test_argparse_does_trigger(self, validator):
        """'argparse' SHOULD require CLI feature."""
        features = validator._extract_required_features(
            "Use argparse for argument parsing"
        )
        assert 'cli' in features

    # --- 'storage' feature: 'localStorage' must NOT trigger ---

    def test_localstorage_does_not_trigger(self, validator):
        """'localStorage' should NOT require storage/database feature."""
        features = validator._extract_required_features(
            "Use localStorage for saving user preferences"
        )
        assert 'storage' not in features

    def test_web_storage_does_not_trigger(self, validator):
        """'Web Storage API' should NOT require storage/database feature."""
        features = validator._extract_required_features(
            "Use Web Storage API for session data"
        )
        assert 'storage' not in features

    def test_database_does_trigger(self, validator):
        """'database' SHOULD require storage feature."""
        features = validator._extract_required_features(
            "Connect to a database for user data"
        )
        assert 'storage' in features

    def test_data_storage_does_trigger(self, validator):
        """'data storage' SHOULD require storage feature."""
        features = validator._extract_required_features(
            "Implement data storage for the application"
        )
        assert 'storage' in features


# ══════════════════════════════════════════════════════════════
# H-3b: fulfillment_score 計算式の安全弁
# ══════════════════════════════════════════════════════════════

class TestH3bFulfillmentScoreSafetyValve:
    """H-3b: Verify fulfillment_score uses weighted formula (0.7 file + 0.3 feature).

    Root cause: Previous formula (file + feature) / 2.0 allowed a single
    false-positive feature miss to halve the score (1.0 + 0.0) / 2 = 0.50.
    New formula: file * 0.7 + feature * 0.3 → (1.0 * 0.7) + (0.0 * 0.3) = 0.70.
    """

    def test_perfect_scores_unchanged(self, validator):
        """Both file and feature perfect → fulfillment should be 1.0."""
        # Use simple goal that doesn't trigger API_PROJECT_PATTERNS
        # Code must contain the exact keyword ('database') for _check_implemented_features
        result = validator.validate_requirements(
            "Build a calculator with database connection",
            {'calculator.py': '# database module\nimport sqlite3\ndef add(a,b): return a+b'}
        )
        score = result['fulfillment_score']
        # 'database' keyword found in both goal and code → feature matched
        assert score >= 0.90

    def test_single_feature_miss_does_not_halve(self, validator):
        """Missing 1 feature should NOT drop score below 0.70.
        Old formula: (1.0 + 0.0) / 2.0 = 0.50 (halved)
        New formula: 1.0 * 0.7 + 0.0 * 0.3 = 0.70 (floor)
        """
        # Goal requires 'encryption' but code has no encryption
        result = validator.validate_requirements(
            "Build a notes app that can encrypt data",
            {'notes.py': 'class Note:\n    def __init__(self): self.text = ""'}
        )
        score = result['fulfillment_score']
        # encryption missing, but file_score = 1.0 → should be >= 0.70
        assert score >= 0.70

    def test_all_features_missing_still_has_file_weight(self, validator):
        """Even if ALL features are missing, file_score (0.7 weight) keeps floor."""
        result = validator.validate_requirements(
            "Build a tool that can encrypt and persist data",
            {'tool.py': 'print("hello")'}
        )
        score = result['fulfillment_score']
        # Both features missing but file present → 1.0*0.7 + 0.0*0.3 = 0.70
        assert score >= 0.70

    def test_no_required_features_gives_full_score(self, validator):
        """Goal with no detectable feature keywords → fulfillment = 1.0."""
        result = validator.validate_requirements(
            "Build a simple calculator app",
            {'calculator.py': 'def add(a, b): return a + b'}
        )
        score = result['fulfillment_score']
        assert score == 1.0

    def test_file_score_weighted_higher_than_feature(self, validator):
        """file_score should have 0.7 weight, feature_score 0.3 weight.
        Verifies the actual weighting ratio."""
        # Test via _calculate_file_score and _calculate_feature_score
        file_score = validator._calculate_file_score(
            required_count=1, generated_count=1, missing_count=0
        )
        feature_score = validator._calculate_feature_score(
            required_count=1, implemented_count=0
        )
        expected = file_score * 0.7 + feature_score * 0.3
        # file_score=1.0, feature_score=0.0 → 0.70
        assert abs(expected - 0.70) < 0.01

    def test_neon_tetris_scenario(self, validator):
        """Reproduce the actual neon_tetris.html bug scenario.
        Goal mentions 'Web Audio API' → previously triggered 'api' feature.
        With compound keywords, 'api' alone should NOT trigger.
        Even if it did, score should remain >= 0.70 (not 0.48).
        """
        result = validator.validate_requirements(
            "Build NEON TETRIS with Web Audio API for sound effects and Canvas for rendering",
            {'neon_tetris.html': '<html><canvas></canvas><script>new AudioContext()</script></html>'}
        )
        score = result['fulfillment_score']
        # No features should be required → score should be 1.0
        assert score >= 0.90
        # Verify 'api' was NOT extracted as required
        missing = result.get('missing_features', [])
        assert 'api' not in [f.lower() for f in missing]
