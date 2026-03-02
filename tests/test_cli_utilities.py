"""Tests for cli_utilities.py cost display fix (c4ca527 + Fix G/H)

Covers:
- Correct API method called (get_token_statistics, not get_session_stats)
- Fix G: Startup banner reads token data from autosave_info (not current_session)
- Fix H: Sonnet 4.6 present in default model config
"""

import pytest
from unittest.mock import MagicMock, patch
from cognix.session import SessionManager


class TestCostDisplayApiCall:
    """Verify cli_utilities uses get_token_statistics() for cost display."""

    def test_source_code_uses_get_token_statistics(self):
        """Check the actual source code calls get_token_statistics, not get_session_stats."""
        import inspect
        from cognix import cli_utilities

        # Find the method/function that displays session restore info
        source = inspect.getsource(cli_utilities)

        # The cost display section should use get_token_statistics
        # Search for the pattern around the token/cost display area
        assert "get_token_statistics()" in source, \
            "cli_utilities should call get_token_statistics() for cost display"

    def test_source_code_uses_correct_keys(self):
        """Verify correct dict keys are used for token stats."""
        import inspect
        from cognix import cli_utilities

        source = inspect.getsource(cli_utilities)

        # Should use 'total_duration_seconds' (from get_token_statistics)
        # Not 'total_duration' (which doesn't exist)
        assert "total_duration_seconds" in source, \
            "Should use 'total_duration_seconds' key from get_token_statistics()"

    def test_get_token_statistics_returns_expected_keys(self):
        """Verify SessionManager.get_token_statistics() has all keys the CLI expects."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(base_dir=tmpdir)
            stats = sm.get_token_statistics()

            expected_keys = [
                'total_tokens_input', 'total_tokens_output', 'total_tokens',
                'estimated_cost', 'total_duration_seconds', 'duration_formatted',
            ]
            for key in expected_keys:
                assert key in stats, f"Missing key '{key}' in get_token_statistics()"


# ── Fix G: Startup Banner Uses autosave_info ────────────────────

class TestStartupBannerTokenSource:
    """Verify startup banner reads tokens from autosave_info, not current_session."""

    def test_banner_does_not_call_get_token_statistics(self):
        """_check_session_restoration should NOT call get_token_statistics() for token display."""
        import inspect
        from cognix.cli_utilities import UtilitiesModule

        source = inspect.getsource(UtilitiesModule._check_session_restoration)

        # Remove comments to check only actual code
        code_lines = [line for line in source.split('\n')
                       if line.strip() and not line.strip().startswith('#')]
        code_only = '\n'.join(code_lines)

        # The banner should use autosave_info directly, not call get_token_statistics()
        assert ".get_token_statistics()" not in code_only, \
            "Startup banner should read tokens from autosave_info, not call get_token_statistics()"

    def test_banner_reads_from_autosave_info(self):
        """_check_session_restoration should read total_tokens from autosave_info."""
        import inspect
        from cognix.cli_utilities import UtilitiesModule

        source = inspect.getsource(UtilitiesModule._check_session_restoration)

        assert "autosave_info.get('total_tokens'" in source, \
            "Banner should read total_tokens from autosave_info dict"


# ── Fix H: Sonnet 4.6 in Default Config ─────────────────────────

class TestSonnet46InConfig:
    """Verify Sonnet 4.6 is present in default model configuration."""

    def test_sonnet_46_in_default_models(self):
        """Sonnet 4.6 should be in DEFAULT_CONFIG models."""
        from cognix.config import Config

        models = Config.DEFAULT_CONFIG["models"]
        # Find model with display_name "Sonnet 4.6"
        sonnet46 = None
        for model_id, model_info in models.items():
            if model_info.get("display_name") == "Sonnet 4.6":
                sonnet46 = (model_id, model_info)
                break

        assert sonnet46 is not None, "Sonnet 4.6 should be in DEFAULT_CONFIG models"

    def test_sonnet_46_has_correct_provider(self):
        """Sonnet 4.6 should be an Anthropic model."""
        from cognix.config import Config

        models = Config.DEFAULT_CONFIG["models"]
        for model_id, model_info in models.items():
            if model_info.get("display_name") == "Sonnet 4.6":
                assert model_info["provider"] == "Anthropic"
                return
        pytest.fail("Sonnet 4.6 not found in models")

    def test_sonnet_46_has_aliases(self):
        """Sonnet 4.6 should have 'sonnet' as an alias."""
        from cognix.config import Config

        models = Config.DEFAULT_CONFIG["models"]
        for model_id, model_info in models.items():
            if model_info.get("display_name") == "Sonnet 4.6":
                aliases = model_info.get("aliases", [])
                assert "sonnet" in aliases, \
                    "'sonnet' alias should point to latest Sonnet (4.6)"
                return
        pytest.fail("Sonnet 4.6 not found in models")

    def test_sonnet_46_highest_priority_among_sonnets(self):
        """Sonnet 4.6 should have higher priority than Sonnet 4.5."""
        from cognix.config import Config

        models = Config.DEFAULT_CONFIG["models"]
        sonnet46_priority = None
        sonnet45_priority = None

        for model_id, model_info in models.items():
            if model_info.get("display_name") == "Sonnet 4.6":
                sonnet46_priority = model_info.get("priority", 999)
            elif model_info.get("display_name") == "Sonnet 4.5":
                sonnet45_priority = model_info.get("priority", 999)

        assert sonnet46_priority is not None, "Sonnet 4.6 not found"
        assert sonnet45_priority is not None, "Sonnet 4.5 not found"
        assert sonnet46_priority < sonnet45_priority, \
            "Sonnet 4.6 should have lower priority number (higher priority) than Sonnet 4.5"

    def test_all_providers_have_models(self):
        """Both Anthropic and OpenAI should have models defined."""
        from cognix.config import Config

        models = Config.DEFAULT_CONFIG["models"]
        providers = set()
        for model_info in models.values():
            providers.add(model_info.get("provider"))

        assert "Anthropic" in providers
        assert "OpenAI" in providers
