"""Tests for llm.py bug fixes (c4ca527)

Covers:
- Streaming empty choices guard
- Anthropic empty response guard
- Responses API safe dict access
- Default model names
"""

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
        assert provider.model == "claude-sonnet-4-5-20250929"


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
