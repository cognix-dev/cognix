"""Tests for llm.py bug fixes (c4ca527 + Fix B/C/D)

Covers:
- Streaming empty choices guard
- Anthropic empty response guard
- Responses API safe dict access
- Default model names
- Fix B: Fallback token estimation uses 0 (not len//4)
- Fix C: Temperature override logs warning
- Fix D: Empty message validation in Anthropic _convert_messages
"""

import logging
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace


# ── Default Model Tests ──────────────────────────────────────────

class TestDefaultModels:
    """Verify default model names match config.py."""

    @patch("openai.OpenAI")
    def test_openai_default_model(self, mock_openai_cls):
        from cognix.llm import OpenAIProvider
        provider = OpenAIProvider(api_key="fake-key")
        assert provider.model == "gpt-5.2"

    @patch("anthropic.Anthropic")
    def test_anthropic_default_model(self, mock_anthropic_cls):
        from cognix.llm import AnthropicProvider
        provider = AnthropicProvider(api_key="fake-key")
        assert provider.model == "claude-sonnet-4-6"


# ── Streaming Empty Choices Guard ────────────────────────────────

class TestStreamingEmptyChoices:
    """chunk.choices が空配列の場合に IndexError にならないこと。"""

    @patch("openai.OpenAI")
    def test_stream_with_empty_choices_chunk(self, mock_openai_cls):
        from cognix.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="fake-key", model="gpt-5.2")

        # chunk with empty choices (e.g. heartbeat or metadata chunk)
        chunk_empty = SimpleNamespace(choices=[])
        # chunk with actual content
        chunk_content = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="hello"))]
        )
        # final chunk (content=None signals end)
        chunk_end = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]
        )

        mock_stream = [chunk_empty, chunk_content, chunk_end]
        provider.client.chat.completions.create.return_value = mock_stream

        messages = [{"role": "user", "content": "test"}]
        result = list(provider._stream_response_via_chat_completions(
            messages, temperature=0.7, max_tokens=100
        ))
        assert result == ["hello"]

    @patch("openai.OpenAI")
    def test_stream_with_all_empty_choices(self, mock_openai_cls):
        from cognix.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="fake-key", model="gpt-5.2")

        # All chunks have empty choices
        mock_stream = [
            SimpleNamespace(choices=[]),
            SimpleNamespace(choices=[]),
        ]
        provider.client.chat.completions.create.return_value = mock_stream

        messages = [{"role": "user", "content": "test"}]
        result = list(provider._stream_response_via_chat_completions(
            messages, temperature=0.7, max_tokens=100
        ))
        assert result == []


# ── Anthropic Empty Response Guard ───────────────────────────────

class TestAnthropicEmptyResponse:
    """response.content が空の場合に空文字を返すこと。"""

    @patch("anthropic.Anthropic")
    def test_empty_content_returns_empty_string(self, mock_anthropic_cls):
        from cognix.llm import AnthropicProvider

        provider = AnthropicProvider(api_key="fake-key")

        # Mock the streaming context manager
        mock_response = SimpleNamespace(
            content=[],  # empty content
            usage=SimpleNamespace(input_tokens=10, output_tokens=0),
            stop_reason="end_turn",
        )
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=MagicMock(
            get_final_message=MagicMock(return_value=mock_response)
        ))
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        provider.client.messages.stream.return_value = mock_stream_ctx

        messages = [{"role": "user", "content": "test"}]
        result = provider.generate_response(messages)
        assert result.content == ""

    @patch("anthropic.Anthropic")
    def test_normal_content_returns_text(self, mock_anthropic_cls):
        from cognix.llm import AnthropicProvider

        provider = AnthropicProvider(api_key="fake-key")

        mock_response = SimpleNamespace(
            content=[SimpleNamespace(text="Hello from Claude")],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            stop_reason="end_turn",
        )
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=MagicMock(
            get_final_message=MagicMock(return_value=mock_response)
        ))
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        provider.client.messages.stream.return_value = mock_stream_ctx

        messages = [{"role": "user", "content": "test"}]
        result = provider.generate_response(messages)
        assert result.content == "Hello from Claude"


# ── Responses API Safe Dict Access ───────────────────────────────

class TestResponsesAPISafeDictAccess:
    """messages[-1] に content キーがなくても KeyError にならないこと。"""

    @patch("openai.OpenAI")
    def test_missing_content_key_in_generate(self, mock_openai_cls):
        from cognix.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="fake-key", model="gpt-5.2-codex")

        # Message without "content" key
        messages = [{"role": "user"}]

        # _convert_to_responses_input returns empty when no valid messages
        # The fallback should use .get("content", "") instead of ["content"]
        mock_response = SimpleNamespace(
            output_text="result",
            usage=SimpleNamespace(
                input_tokens=5,
                output_tokens=10,
                total_tokens=15,
            ),
            status="completed",
        )
        provider.client.responses.create.return_value = mock_response

        # This should NOT raise KeyError
        result = provider._generate_response_via_responses_api(
            messages, temperature=0.7, max_tokens=100
        )
        assert result.content == "result"

    @patch("openai.OpenAI")
    def test_missing_content_key_in_stream(self, mock_openai_cls):
        from cognix.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="fake-key", model="gpt-5.2-codex")

        messages = [{"role": "user"}]

        # Mock streaming events
        event1 = SimpleNamespace(type="response.output_text.delta", delta="hello")
        event2 = SimpleNamespace(type="response.completed")
        provider.client.responses.create.return_value = [event1, event2]

        # This should NOT raise KeyError
        result = list(provider._stream_response_via_responses_api(
            messages, temperature=0.7, max_tokens=100
        ))
        assert "hello" in result


# ── Fix B: Fallback Token Estimation ─────────────────────────────

class TestFallbackTokenEstimation:
    """Fallback usage should be all zeros, not len(content)//4."""

    @patch("openai.OpenAI")
    def test_fallback_usage_is_zero(self, mock_openai_cls):
        from cognix.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="fake-key", model="gpt-5.2")

        # Simulate a stream that yields content but no usage object
        chunk1 = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="hello world"))]
        )
        chunk2 = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]
        )
        provider.client.chat.completions.create.return_value = [chunk1, chunk2]

        messages = [{"role": "user", "content": "test"}]
        # Consume the stream to trigger the fallback path
        result = list(provider._stream_response_via_chat_completions(
            messages, temperature=0.7, max_tokens=100
        ))
        assert result == ["hello world"]

    @patch("openai.OpenAI")
    def test_source_code_no_len_div_4(self, mock_openai_cls):
        """Verify len(content) // 4 pattern is NOT in the fallback."""
        import inspect
        from cognix.llm import OpenAIProvider
        source = inspect.getsource(OpenAIProvider)
        assert "len(content) // 4" not in source, \
            "Fallback should use 0, not len(content) // 4"


# ── Fix C: Temperature Warning ───────────────────────────────────

class TestTemperatureWarning:
    """GPT-5 temperature override should log a warning."""

    @patch("openai.OpenAI")
    def test_temperature_override_logs_warning(self, mock_openai_cls):
        from cognix.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="fake-key", model="gpt-5.2")

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            params = provider._get_params_for_model(max_tokens=100, temperature=0.5)

        mock_logger.warning.assert_called_once()
        assert "temperature" in mock_logger.warning.call_args[0][0].lower(), \
            "Warning message should mention temperature"
        # Temperature should NOT be in the params (GPT-5 uses default 1)
        assert "temperature" not in params

    @patch("openai.OpenAI")
    def test_temperature_1_no_warning(self, mock_openai_cls, caplog):
        from cognix.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="fake-key", model="gpt-5.2")

        with caplog.at_level(logging.WARNING, logger="cognix.llm"):
            params = provider._get_params_for_model(max_tokens=100, temperature=1.0)

        assert not any("temperature" in record.message.lower() for record in caplog.records), \
            "Should NOT log a warning when temperature is 1.0"


# ── Fix D: Empty Message Validation ──────────────────────────────

class TestEmptyMessageValidation:
    """_convert_messages should raise ValueError when all messages are empty."""

    @patch("anthropic.Anthropic")
    def test_all_empty_messages_raises(self, mock_anthropic_cls):
        from cognix.llm import AnthropicProvider

        provider = AnthropicProvider(api_key="fake-key")

        # All messages have empty content
        messages = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": ""},
        ]

        with pytest.raises(ValueError, match="No valid messages"):
            provider._convert_messages(messages)

    @patch("anthropic.Anthropic")
    def test_valid_messages_pass(self, mock_anthropic_cls):
        from cognix.llm import AnthropicProvider

        provider = AnthropicProvider(api_key="fake-key")

        messages = [
            {"role": "user", "content": "hello"},
        ]

        system_msg, converted = provider._convert_messages(messages)
        assert len(converted) == 1
        assert converted[0]["content"] == "hello"

    @patch("anthropic.Anthropic")
    def test_system_only_messages_pass(self, mock_anthropic_cls):
        """System-only conversations should NOT raise ValueError."""
        from cognix.llm import AnthropicProvider

        provider = AnthropicProvider(api_key="fake-key")

        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
        ]

        system_msg, converted = provider._convert_messages(messages)
        assert system_msg == "You are a helpful assistant"
        assert converted == []

    @patch("anthropic.Anthropic")
    def test_empty_system_and_empty_user_raises(self, mock_anthropic_cls):
        """Empty system + empty user should raise ValueError."""
        from cognix.llm import AnthropicProvider

        provider = AnthropicProvider(api_key="fake-key")

        messages = [
            {"role": "system", "content": ""},
            {"role": "user", "content": ""},
        ]

        with pytest.raises(ValueError, match="No valid messages"):
            provider._convert_messages(messages)


# ── Fix F: Streaming Usage Capture ────────────────────────────────

class TestStreamingUsageCapture:
    """stream_response should capture token usage in _last_stream_usage."""

    @patch("anthropic.Anthropic")
    def test_anthropic_stream_captures_usage(self, mock_anthropic_cls):
        from cognix.llm import AnthropicProvider

        provider = AnthropicProvider(api_key="fake-key")

        # Simulate Anthropic streaming events
        events = [
            SimpleNamespace(
                type="message_start",
                message=SimpleNamespace(
                    usage=SimpleNamespace(input_tokens=150)
                )
            ),
            SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text="Hello")
            ),
            SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text=" world")
            ),
            SimpleNamespace(
                type="message_delta",
                usage=SimpleNamespace(output_tokens=42)
            ),
        ]
        provider.client.messages.create.return_value = events

        messages = [{"role": "user", "content": "test"}]
        result = list(provider.stream_response(messages))

        assert result == ["Hello", " world"]
        assert provider._last_stream_usage is not None
        assert provider._last_stream_usage["prompt_tokens"] == 150
        assert provider._last_stream_usage["completion_tokens"] == 42
        assert provider._last_stream_usage["total_tokens"] == 192

    @patch("openai.OpenAI")
    def test_openai_chat_stream_captures_usage(self, mock_openai_cls):
        from cognix.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="fake-key", model="gpt-5.2")

        # Simulate OpenAI streaming chunks with usage in final chunk
        chunks = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="Hi"))],
                usage=None
            ),
            SimpleNamespace(
                choices=[],
                usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120)
            ),
        ]
        provider.client.chat.completions.create.return_value = chunks

        messages = [{"role": "user", "content": "test"}]
        result = list(provider.stream_response(messages))

        assert result == ["Hi"]
        assert provider._last_stream_usage is not None
        assert provider._last_stream_usage["prompt_tokens"] == 100
        assert provider._last_stream_usage["completion_tokens"] == 20
        assert provider._last_stream_usage["total_tokens"] == 120

    @patch("anthropic.Anthropic")
    def test_stream_usage_zeros_on_no_events(self, mock_anthropic_cls):
        """If no usage events arrive, _last_stream_usage should still be a dict with zeros."""
        from cognix.llm import AnthropicProvider

        provider = AnthropicProvider(api_key="fake-key")

        # Only content events, no message_start or message_delta
        events = [
            SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text="test")
            ),
        ]
        provider.client.messages.create.return_value = events

        messages = [{"role": "user", "content": "test"}]
        list(provider.stream_response(messages))

        # Should still have a dict, but with zeros
        assert provider._last_stream_usage is not None
        assert provider._last_stream_usage["total_tokens"] == 0

    @patch("openai.OpenAI")
    def test_openai_stream_options_fallback(self, mock_openai_cls):
        """If stream_options is unsupported, should fallback without it."""
        from cognix.llm import OpenAIProvider

        provider = OpenAIProvider(api_key="fake-key", model="gpt-5.2")

        # First call raises error (stream_options unsupported), second succeeds
        chunk = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))],
            usage=None
        )
        provider.client.chat.completions.create.side_effect = [
            Exception("stream_options not supported"),
            [chunk]
        ]

        messages = [{"role": "user", "content": "test"}]
        result = list(provider.stream_response(messages))
        assert result == ["ok"]
        # Usage not captured in fallback path (no stream_options)
        assert provider._last_stream_usage is None
