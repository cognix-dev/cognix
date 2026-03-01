"""Tests for session.py token restoration fix (c4ca527)

Covers:
- Token fields in add_entry()
- JSON round-trip preservation
- Backward compatibility with old session files
- Cost calculation in get_token_statistics()
- Duration formatting
"""

import json
import pytest
import tempfile
from pathlib import Path
from cognix.session import SessionManager, SessionEntry, SessionData


@pytest.fixture
def session_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def session_manager(session_dir):
    return SessionManager(base_dir=session_dir)


# ── SessionEntry Token Fields ────────────────────────────────────

class TestSessionEntryTokenFields:
    def test_default_token_values(self):
        entry = SessionEntry(
            timestamp="2026-03-01T00:00:00",
            user_input="test",
            ai_response="response",
            model_used="test-model",
        )
        assert entry.tokens_input == 0
        assert entry.tokens_output == 0
        assert entry.tokens_total == 0
        assert entry.duration_seconds == 0.0

    def test_explicit_token_values(self):
        entry = SessionEntry(
            timestamp="2026-03-01T00:00:00",
            user_input="test",
            ai_response="response",
            model_used="test-model",
            tokens_input=100,
            tokens_output=200,
            tokens_total=300,
            duration_seconds=1.5,
        )
        assert entry.tokens_input == 100
        assert entry.tokens_output == 200
        assert entry.tokens_total == 300
        assert entry.duration_seconds == 1.5


# ── add_entry Token Accumulation ─────────────────────────────────

class TestAddEntryTokenAccumulation:
    def test_add_entry_with_tokens(self, session_manager):
        session_manager.add_entry(
            user_input="hello",
            ai_response="world",
            model_used="test-model",
            tokens_used={
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
            duration_seconds=1.0,
        )
        assert session_manager.current_session.total_tokens_input == 10
        assert session_manager.current_session.total_tokens_output == 20
        assert session_manager.current_session.total_tokens == 30
        assert session_manager.current_session.total_duration_seconds == 1.0

    def test_add_entry_without_tokens(self, session_manager):
        session_manager.add_entry(
            user_input="hello",
            ai_response="world",
            model_used="test-model",
        )
        assert session_manager.current_session.total_tokens_input == 0
        assert session_manager.current_session.total_tokens_output == 0
        assert session_manager.current_session.total_tokens == 0

    def test_multiple_entries_accumulate(self, session_manager):
        for i in range(3):
            session_manager.add_entry(
                user_input=f"input {i}",
                ai_response=f"output {i}",
                model_used="test-model",
                tokens_used={
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
                duration_seconds=0.5,
            )
        assert session_manager.current_session.total_tokens_input == 30
        assert session_manager.current_session.total_tokens_output == 60
        assert session_manager.current_session.total_tokens == 90
        assert session_manager.current_session.total_duration_seconds == pytest.approx(1.5)


# ── JSON Round-Trip ──────────────────────────────────────────────

class TestSessionJsonRoundTrip:
    def test_save_and_load_preserves_tokens(self, session_manager):
        session_manager.add_entry(
            user_input="hello",
            ai_response="world",
            model_used="test-model",
            tokens_used={
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
            duration_seconds=5.0,
        )
        session_manager.save_session("test_session")

        # Load into a new manager
        new_manager = SessionManager(base_dir=session_manager.base_dir)
        loaded = new_manager.load_session("test_session")

        assert loaded is not None
        assert loaded.total_tokens_input == 100
        assert loaded.total_tokens_output == 200
        assert loaded.total_tokens == 300
        assert loaded.total_duration_seconds == 5.0

        # Verify entry-level tokens
        assert len(loaded.entries) == 1
        assert loaded.entries[0].tokens_input == 100
        assert loaded.entries[0].tokens_output == 200
        assert loaded.entries[0].tokens_total == 300
        assert loaded.entries[0].duration_seconds == 5.0


# ── Backward Compatibility ───────────────────────────────────────

class TestBackwardCompatibility:
    def test_load_old_session_without_token_fields(self, session_dir):
        """Old session files without token fields should load with defaults."""
        sessions_dir = Path(session_dir) / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        old_session = {
            "session_id": "old-session",
            "created_at": "2025-01-01T00:00:00",
            "last_updated": "2025-01-01T00:00:00",
            "current_model": "claude-sonnet-4-5-20250929",
            "current_directory": "/tmp",
            "entries": [
                {
                    "timestamp": "2025-01-01T00:00:00",
                    "user_input": "old input",
                    "ai_response": "old response",
                    "model_used": "claude-sonnet-4-5-20250929",
                }
            ],
            "total_entries": 1,
        }

        session_file = sessions_dir / "old-session.json"
        with open(session_file, "w") as f:
            json.dump(old_session, f)

        manager = SessionManager(base_dir=session_dir)
        loaded = manager.load_session("old-session")

        assert loaded is not None
        # Token fields should default to 0
        assert loaded.total_tokens_input == 0
        assert loaded.total_tokens_output == 0
        assert loaded.total_tokens == 0
        assert loaded.total_duration_seconds == 0.0
        # Entry-level too
        assert loaded.entries[0].tokens_input == 0
        assert loaded.entries[0].tokens_output == 0
        assert loaded.entries[0].duration_seconds == 0.0


# ── get_token_statistics ─────────────────────────────────────────

class TestTokenStatistics:
    def test_empty_session_returns_zeros(self, session_manager):
        stats = session_manager.get_token_statistics()
        assert stats["total_tokens"] == 0
        assert stats["estimated_cost"] == 0.0
        assert stats["duration_formatted"] == "0.0s"

    def test_cost_calculation(self, session_manager):
        session_manager.add_entry(
            user_input="test",
            ai_response="response",
            model_used="test-model",
            tokens_used={
                "prompt_tokens": 1_000_000,  # $3.00
                "completion_tokens": 1_000_000,  # $15.00
                "total_tokens": 2_000_000,
            },
        )
        stats = session_manager.get_token_statistics()
        assert stats["total_tokens"] == 2_000_000
        assert stats["input_cost"] == pytest.approx(3.0, abs=0.01)
        assert stats["output_cost"] == pytest.approx(15.0, abs=0.01)
        assert stats["estimated_cost"] == pytest.approx(18.0, abs=0.01)

    def test_duration_format_seconds(self, session_manager):
        session_manager.add_entry(
            user_input="test", ai_response="r", model_used="m",
            duration_seconds=45.0,
        )
        stats = session_manager.get_token_statistics()
        assert stats["duration_formatted"] == "45.0s"

    def test_duration_format_minutes(self, session_manager):
        session_manager.add_entry(
            user_input="test", ai_response="r", model_used="m",
            duration_seconds=150.0,
        )
        stats = session_manager.get_token_statistics()
        assert stats["duration_formatted"] == "2m 30s"

    def test_duration_format_hours(self, session_manager):
        session_manager.add_entry(
            user_input="test", ai_response="r", model_used="m",
            duration_seconds=3900.0,
        )
        stats = session_manager.get_token_statistics()
        assert stats["duration_formatted"] == "1h 5m"
