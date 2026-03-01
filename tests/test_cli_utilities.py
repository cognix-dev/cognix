"""Tests for cli_utilities.py cost display fix (c4ca527)

Covers:
- Correct API method called (get_token_statistics, not get_session_stats)
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
