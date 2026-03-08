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
