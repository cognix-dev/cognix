"""
LLM Integration for Cognix
Handles communication with OpenAI and Anthropic APIs
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Generator
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    timestamp: float


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """Generate response from LLM"""
        pass
    
    @abstractmethod
    def stream_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> Generator[str, None, None]:
        """Stream response from LLM"""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    
    # Responses API専用モデルのリスト
    # 出典: platform.openai.com/docs/guides/latest-model
    # "GPT-5.2-Codex is only available in the Responses API"
    RESPONSES_API_ONLY_MODELS = [
        "gpt-5.2-codex",
        "gpt-5.1-codex",
        "gpt-5.1-codex-mini",
        "gpt-5.1-codex-max",
    ]
    
    # temperatureパラメータをサポートしないモデル
    # エラー: "Unsupported parameter: 'temperature' is not supported with this model."
    TEMPERATURE_UNSUPPORTED_MODELS = [
        "gpt-5.2-codex",
        "gpt-5.1-codex",
        "gpt-5.1-codex-mini",
        "gpt-5.1-codex-max",
        "o1",
        "o1-mini",
        "o1-preview",
    ]
    
    def __init__(self, api_key: str, model: str = "gpt-5.2", base_url: str = None):
        """Initialize OpenAI provider with optional base URL for OpenRouter support"""
        self.api_key = api_key
        self.model = model
        
        try:
            import openai
            
            # OpenRouter または他のOpenAI互換サービス対応
            if base_url:
                self.client = openai.OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    default_headers={
                        "HTTP-Referer": "https://github.com/cognix-dev/cognix",
                        "X-Title": "Cognix"
                    }
                )
            else:
                # 通常のOpenAI API
                self.client = openai.OpenAI(api_key=api_key)
                
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    def _is_responses_api_only(self, model: str = None) -> bool:
        """Check if model requires Responses API
        
        Args:
            model: Model name to check. If None, uses self.model
            
        Returns:
            True if model requires Responses API, False otherwise
            
        Note:
            OpenRouter経由（base_url設定時）の場合、Responses APIが
            サポートされない可能性があるため、この場合はFalseを返す
        """
        model_to_check = model or self.model
        is_responses_only = model_to_check.lower() in [m.lower() for m in self.RESPONSES_API_ONLY_MODELS]
        
        # OpenRouter経由の場合、Responses APIは使えない可能性が高い
        # その場合はChat Completions APIを試みる（エラーが出る可能性あり）
        if is_responses_only and hasattr(self, 'client') and hasattr(self.client, '_base_url'):
            import os
            if os.getenv("OPENAI_BASE_URL"):
                # OpenRouter等のカスタムエンドポイント経由
                # Responses APIが使えない可能性があるためFalseを返す
                # 呼び出し元でChat Completions APIを使用し、
                # "This is not a chat model"エラーが出た場合はユーザーに通知
                return False
        
        return is_responses_only
    
    def _convert_to_responses_input(self, messages: List[Dict[str, str]]) -> tuple:
        """Convert Chat Completions messages format to Responses API format
        
        Args:
            messages: List of messages in Chat Completions format
            
        Returns:
            Tuple of (instructions, input_messages) for Responses API
            
        Note:
            複数のsystemメッセージがある場合は連結してinstructionsにする
            
        出典: platform.openai.com/docs/guides/migrate-to-responses
        """
        instructions_parts = []
        input_messages = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                # systemメッセージはinstructionsに連結
                if content:
                    instructions_parts.append(content)
            elif role in ("user", "assistant"):
                # user/assistantはそのまま配列に追加
                input_messages.append({
                    "role": role,
                    "content": content
                })
        
        # 複数のsystemメッセージを改行で連結
        instructions = "\n\n".join(instructions_parts) if instructions_parts else None
        
        return instructions, input_messages
    
    def _get_params_for_model(self, max_tokens: int, temperature: float) -> dict:
        """Get appropriate parameters based on model"""
        params = {}
        
        # Token parameter
        if self.model.startswith("gpt-5") or self.model.startswith("o1"):
            params["max_completion_tokens"] = max_tokens
            # GPT-5 only supports temperature = 1
            if temperature != 1.0:
                # Silent adjustment for GPT-5
                pass
            # Don't set temperature for GPT-5 (uses default 1)
        else:
            params["max_tokens"] = max_tokens
            params["temperature"] = temperature
        
        return params
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """Generate response from OpenAI"""
        try:
            # Responses API専用モデルの場合
            if self._is_responses_api_only():
                return self._generate_response_via_responses_api(
                    messages, temperature, max_tokens
                )
            
            # 通常のChat Completions API
            return self._generate_response_via_chat_completions(
                messages, temperature, max_tokens
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")
    
    def _generate_response_via_chat_completions(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Generate response using Chat Completions API
        
        GPT-5系でfinish_reason=lengthの場合にcontentがNoneになる問題を回避するため、
        streaming modeで応答を収集する。
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Base parameters
        params = {
            "model": self.model,
            "messages": messages,
            "stream": True,  # Use streaming to avoid empty content issue
            "stream_options": {"include_usage": True}  # Get usage stats at the end
        }
        
        # Add model-specific parameters
        params.update(self._get_params_for_model(max_tokens, temperature))
        
        # Collect streamed content
        content_chunks = []
        finish_reason = None
        usage = None
        
        stream = self.client.chat.completions.create(**params)
        
        for chunk in stream:
            # Collect content
            if chunk.choices and chunk.choices[0].delta.content is not None:
                content_chunks.append(chunk.choices[0].delta.content)
            
            # Get finish_reason from final chunk
            if chunk.choices and chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason
            
            # Get usage from final chunk (when stream_options.include_usage=True)
            if hasattr(chunk, 'usage') and chunk.usage is not None:
                usage = chunk.usage
        
        content = "".join(content_chunks)
        
        # Log warning if content is empty despite streaming
        if not content:
            logger.warning(
                f"[LLM] Streaming returned empty content. "
                f"finish_reason={finish_reason}, model={self.model}"
            )
        
        # Fallback usage if not available
        if usage is None:
            usage_dict = {
                "prompt_tokens": 0,
                "completion_tokens": len(content) // 4,  # Rough estimate
                "total_tokens": len(content) // 4
            }
        else:
            usage_dict = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            }
        
        return LLMResponse(
            content=content,
            model=self.model,
            usage=usage_dict,
            finish_reason=finish_reason or "unknown",
            timestamp=time.time()
        )
    
    def _generate_response_via_responses_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Generate response using Responses API
        
        出典: platform.openai.com/docs/api-reference/responses/create
        """
        # messagesが空の場合のガード
        if not messages:
            raise ValueError("messages cannot be empty")
        
        # messagesをResponses API形式に変換
        instructions, input_messages = self._convert_to_responses_input(messages)
        
        # Base parameters
        params = {
            "model": self.model,
            "input": input_messages if input_messages else messages[-1].get("content", ""),
        }

        # instructionsがある場合は追加
        if instructions:
            params["instructions"] = instructions

        # Codexモデルはtemperatureをサポートしない
        # 出典: platform.openai.com/docs/guides/latest-model
        # "It does not support all GPT-5.2 parameters or API surfaces."
        # 代わりにreasoning.effortを使用可能（low, medium, high, xhigh）
        model_lower = self.model.lower()
        is_codex_model = "codex" in model_lower
        
        if not is_codex_model:
            # 非Codexモデル（通常のgpt-5.2等）はtemperatureをサポート
            params["temperature"] = temperature
        # Codexモデルの場合はtemperatureを設定しない
        # 必要に応じてreasoning.effortを設定可能だが、デフォルトで省略
        
        # max_output_tokensパラメータ
        # 出典: platform.openai.com/docs/guides/reasoning
        # Responses APIではmax_tokensではなくmax_output_tokensを使用
        params["max_output_tokens"] = max_tokens
        
        response = self.client.responses.create(**params)
        
        # Responses APIのレスポンス形式に対応
        # 出典: platform.openai.com/docs/libraries
        # response.output_text で集約されたテキストを取得可能
        content = ""
        if hasattr(response, 'output_text') and response.output_text:
            content = response.output_text
        elif hasattr(response, 'output') and response.output:
            # output配列からテキストを抽出
            for item in response.output:
                if hasattr(item, 'content'):
                    for content_part in item.content:
                        if hasattr(content_part, 'text'):
                            content += content_part.text
        
        # content取得失敗時の警告
        if not content:
            import sys
            print(f"Warning: Responses API returned empty content. "
                  f"Response status: {getattr(response, 'status', 'unknown')}", 
                  file=sys.stderr)
        
        # usage情報の取得
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage, 'input_tokens', 0),
                "completion_tokens": getattr(response.usage, 'output_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0)
            }
        
        # finish_reasonの取得
        finish_reason = "completed"
        if hasattr(response, 'status'):
            finish_reason = response.status
        
        return LLMResponse(
            content=content,
            model=self.model,
            usage=usage,
            finish_reason=finish_reason,
            timestamp=time.time()
        )
    
    def stream_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> Generator[str, None, None]:
        """Stream response from OpenAI"""
        try:
            # Responses API専用モデルの場合
            if self._is_responses_api_only():
                yield from self._stream_response_via_responses_api(
                    messages, temperature, max_tokens
                )
                return
            
            # 通常のChat Completions API
            yield from self._stream_response_via_chat_completions(
                messages, temperature, max_tokens
            )
                    
        except Exception as e:
            raise Exception(f"OpenAI streaming error: {e}")
    
    def _stream_response_via_chat_completions(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Generator[str, None, None]:
        """Stream response using Chat Completions API"""
        # Base parameters
        params = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        
        # Add model-specific parameters
        params.update(self._get_params_for_model(max_tokens, temperature))
        
        stream = self.client.chat.completions.create(**params)
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    
    def _stream_response_via_responses_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Generator[str, None, None]:
        """Stream response using Responses API
        
        出典: platform.openai.com/docs/guides/streaming-responses
        """
        # messagesが空の場合のガード
        if not messages:
            raise ValueError("messages cannot be empty")
        
        # messagesをResponses API形式に変換
        instructions, input_messages = self._convert_to_responses_input(messages)
        
        # Base parameters
        params = {
            "model": self.model,
            "input": input_messages if input_messages else messages[-1].get("content", ""),
            "stream": True
        }
        
        # instructionsがある場合は追加
        if instructions:
            params["instructions"] = instructions
        
        # Codexモデルはtemperatureをサポートしない
        # 出典: platform.openai.com/docs/guides/latest-model
        model_lower = self.model.lower()
        is_codex_model = "codex" in model_lower
        
        if not is_codex_model:
            # 非Codexモデル（通常のgpt-5.2等）はtemperatureをサポート
            params["temperature"] = temperature
        
        # max_output_tokensパラメータ
        # 出典: platform.openai.com/docs/guides/reasoning
        params["max_output_tokens"] = max_tokens
        
        stream = self.client.responses.create(**params)
        
        # Responses APIのストリーミングイベント処理
        # 出典: platform.openai.com/docs/guides/streaming-responses
        # イベントタイプ: response.output_text.delta
        for event in stream:
            # イベントタイプをチェック
            event_type = getattr(event, 'type', None)
            
            if event_type == "response.output_text.delta":
                # テキストの差分を取得
                delta = getattr(event, 'delta', None)
                if delta:
                    yield delta
            elif event_type == "response.completed":
                # 完了イベント
                break
            elif event_type == "error":
                # エラーイベント
                error_msg = getattr(event, 'error', 'Unknown error')
                raise Exception(f"Responses API streaming error: {error_msg}")


class AnthropicProvider(LLMProvider):
    """Anthropic API provider"""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        """Initialize Anthropic provider"""
        self.api_key = api_key
        self.model = model
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple:
        """Convert messages to Anthropic format
        
        Noneや空文字列のcontentを持つメッセージを自動的に除外します。
        """
        system_message = ""
        converted_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                content = msg.get("content")
                
                # contentが不正な場合はスキップ
                if content is None:
                    continue
                if isinstance(content, str) and not content.strip():
                    continue
                
                converted_messages.append({
                    "role": msg["role"],
                    "content": content
                })
        
        return system_message, converted_messages
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """Generate response from Anthropic (streaming-based)
        
        内部でSDKの高レベルストリーミングAPI（client.messages.stream）を使用。
        get_final_message()で完全なMessageオブジェクトを取得する。
        これにより、大きなmax_tokensでもAnthropicの
        「Streaming is required for operations that may take longer than 10 minutes」
        エラーを回避できる。呼び出し側のインターフェースは変更なし。
        
        出典: https://docs.anthropic.com/en/api/messages-streaming
        「This is especially useful for requests with large max_tokens values,
         where the SDKs require streaming to avoid HTTP timeouts.」
        """
        try:
            system_message, converted_messages = self._convert_messages(messages)
            
            kwargs = {
                "model": self.model,
                "messages": converted_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if system_message:
                kwargs["system"] = system_message
            
            # SDK高レベルストリーミングAPI
            # get_final_message()が全イベントを集約し完全なMessageオブジェクトを返す
            with self.client.messages.stream(**kwargs) as stream:
                response = stream.get_final_message()
            
            return LLMResponse(
                content=response.content[0].text if response.content else "",
                model=self.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                finish_reason=response.stop_reason,
                timestamp=time.time()
            )
            
        except Exception as e:
            raise Exception(f"Anthropic API error: {e}")
    
    def stream_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> Generator[str, None, None]:
        """Stream response from Anthropic"""
        try:
            system_message, converted_messages = self._convert_messages(messages)
            
            kwargs = {
                "model": self.model,
                "messages": converted_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            if system_message:
                kwargs["system"] = system_message
            
            stream = self.client.messages.create(**kwargs)
            
            for chunk in stream:
                if chunk.type == "content_block_delta":
                    yield chunk.delta.text
                    
        except Exception as e:
            raise Exception(f"Anthropic streaming error: {e}")


class LLMManager:
    """Manages LLM providers and interactions"""

    # OpenRouter形式のモデル名を処理する関数
    @staticmethod
    def normalize_model_name(model: str) -> str:
        """OpenRouter形式のモデル名を正規化"""
        # openai/gpt-oss-120b:free -> gpt-oss-120b
        if "/" in model:
            parts = model.split("/")
            model = parts[-1]  # プロバイダー部分を削除
        if ":" in model:
            model = model.split(":")[0]  # :free などのサフィックスを削除
        return model

    def get_provider_for_model(self, model: str) -> LLMProvider:
        """Get provider for a specific model (config-based)"""
        # OpenRouter形式のモデル名を正規化
        normalized_model = self.normalize_model_name(model)
        
        # configを使ってモデル名を解決（alias, display_name対応）
        actual_model = None
        if hasattr(self.config, 'resolve_model_name'):
            actual_model = self.config.resolve_model_name(normalized_model)
        
        if not actual_model:
            # OpenRouter経由の場合はopenaiプロバイダーを使用
            if os.getenv("OPENAI_BASE_URL"):
                provider_name = "openai"
            else:
                raise ValueError(f"Unknown model: {model}")
        else:
            # configからprovider取得
            provider_name = None
            if hasattr(self.config, 'get_model_provider'):
                provider_name = self.config.get_model_provider(actual_model)
            
            if not provider_name:
                # フォールバック: get_model_configから取得
                model_config = self.config.get_model_config(actual_model) if hasattr(self.config, 'get_model_config') else None
                if model_config:
                    provider_name = model_config.get("provider", "").lower()
        
        if not provider_name:
            # OpenRouter経由の場合はopenaiプロバイダーを使用
            if os.getenv("OPENAI_BASE_URL"):
                provider_name = "openai"
            else:
                raise ValueError(f"Unknown model: {model}")
        
        provider = self.providers.get(provider_name)
        if not provider:
            raise Exception(f"Provider {provider_name} not available for model {model}")
        
        # プロバイダーに元のモデル名を設定（OpenRouter用）
        provider.model = model  # 正規化前の元の名前を保持
        return provider

    def __init__(self, config):
        """Initialize LLM manager"""
        self.providers: Dict[str, LLMProvider] = {}
        
        # Ensure self.config is always a Config object
        from cognix.config import Config
        if isinstance(config, Config):
            self.config = config
        elif isinstance(config, dict):
            self.config = Config()  # Create new Config (loads from file)
        else:
            self.config = Config()
        
        # Get current model from config
        self.current_model = self.config.get("model", "claude-sonnet-4-5-20250929")
        
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize LLM providers based on available API keys"""
        
        # Initialize OpenAI provider
        openai_key = self.config.get_api_key("openai")
        if openai_key:
            try:
                # base_url を環境変数から取得
                base_url = os.getenv("OPENAI_BASE_URL")
                self.providers["openai"] = OpenAIProvider(
                    openai_key, 
                    base_url=base_url
                )
                
                if os.getenv('COGNIX_DEBUG') or os.getenv('DEBUG'):
                    if base_url:
                        print(f"Debug: OpenAI provider initialized with base URL: {base_url}")
                    else:
                        print(f"Debug: OpenAI provider initialized successfully")
            except ImportError as e:
                print(f"Warning: {e}")
        else:
            if os.getenv('COGNIX_DEBUG') or os.getenv('DEBUG'):
                print("Debug: No OpenAI API key found")
        
        # Initialize Anthropic provider
        anthropic_key = self.config.get_api_key("anthropic")
        if anthropic_key:
            try:
                self.providers["anthropic"] = AnthropicProvider(anthropic_key)
                if os.getenv('COGNIX_DEBUG') or os.getenv('DEBUG'):
                    print(f"Debug: Anthropic provider initialized successfully")
            except ImportError as e:
                print(f"Warning: {e}")
        else:
            if os.getenv('COGNIX_DEBUG') or os.getenv('DEBUG'):
                print("Debug: No Anthropic API key found")
        
        if not self.providers:
            # 初回起動時はrun()内のCyber Zen APIキーセットアップUIに任せるため、
            # ここではヘルプ表示せず例外のみ投げる
            from pathlib import Path
            first_run_marker = Path.home() / ".cognix" / ".first_run_complete"
            if first_run_marker.exists():
                # 2回目以降: ヘルプ表示してから例外
                self._show_immediate_setup_help()
            raise Exception("No LLM providers available. Please set API keys for OpenAI or Anthropic.")
    
    def _detect_available_models(self):
        """Auto-detect available models from OpenAI API (debug info only)"""
        # Note: Model configuration is now centralized in config.py
        # This method only logs detected models for debugging purposes
        try:
            import openai
            client = openai.OpenAI(api_key=self.providers["openai"].api_key)
            models = client.models.list()
            
            if os.getenv('COGNIX_DEBUG'):
                for model in models:
                    model_id = model.id
                    if model_id.startswith(('gpt-', 'o1-')):
                        print(f"Debug: Detected OpenAI model: {model_id}")
                        
        except Exception as e:
            if os.getenv('COGNIX_DEBUG'):
                print(f"Debug: Could not auto-detect models: {e}")

    def _show_immediate_setup_help(self):
        """Show immediate setup help with specific next steps"""
        print("\n" + "⚠️  API KEY REQUIRED")
        print("="*50)
        
        env_path = Path.home() / ".cognix" / ".env"
        env_exists = env_path.exists()
        
        if env_exists:
            print("Found .env file, but no valid API keys detected.")
            print(f"📄 Edit: {env_path}")
            print()
            print("Make sure you have one of these lines (uncommented):")
            print("   ANTHROPIC_API_KEY=sk-ant-your_key_here")
            print("   OPENAI_API_KEY=sk-your_key_here")
        else:
            print("No .env file found. Quick setup:")
            print()
            print(f"1. Create: {env_path}")
            print("2. Add one of these lines:")
            print("   ANTHROPIC_API_KEY=sk-ant-your_key_here")
            print("   OPENAI_API_KEY=sk-your_key_here")
            print()
            print("Or run 'cognix' to use the interactive setup wizard.")
        
        print()
        print("🔗 Get API keys:")
        print("   • Anthropic: https://console.anthropic.com/")
        print("   • OpenAI: https://platform.openai.com/api-keys")
        print("="*50)    
    
    def generate_response(
        self,
        prompt: str,
        context: str = "",
        conversation_history: List[Dict[str, str]] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        system_prompt: str = None
    ) -> LLMResponse:
        """Generate response using configured LLM"""
        model = model or self.current_model
        provider = self.get_provider_for_model(model)
        
        # Build messages
        messages = []
        
        # Add system prompt (修正: system_promptとcontextの両方を使用可能に)
        if system_prompt:
            system_content = system_prompt
            if context:
                # system_promptがある場合でもcontextを追加
                system_content += f"\n\nProject Context:\n{context}"
            messages.append({"role": "system", "content": system_content})
        elif context:
            system_content = f"You are Claude Code, an AI assistant helping with software development.\n\nProject Context:\n{context}"
            messages.append({"role": "system", "content": system_content})
        
        # Add conversation history
        if conversation_history:
            # content が None または空の場合はフィルタ
            filtered_history = [
                msg for msg in conversation_history
                if msg.get("content") is not None and str(msg.get("content")).strip()
            ]
            messages.extend(filtered_history)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
              
        return provider.generate_response(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def stream_response(
        self,
        prompt: str,
        context: str = "",
        conversation_history: List[Dict[str, str]] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        system_prompt: str = None
    ) -> Generator[str, None, None]:
        """Stream response using configured LLM"""
        model = model or self.current_model
        provider = self.get_provider_for_model(model)
        
        # Build messages
        messages = []
        
        # Add system prompt (修正: system_promptとcontextの両方を使用可能に)
        if system_prompt:
            system_content = system_prompt
            if context:
                # system_promptがある場合でもcontextを追加
                system_content += f"\n\nProject Context:\n{context}"
            messages.append({"role": "system", "content": system_content})
        elif context:
            system_content = f"You are Claude Code, an AI assistant helping with software development.\n\nProject Context:\n{context}"
            messages.append({"role": "system", "content": system_content})
        
        # Add conversation history
        if conversation_history:
            # content が None または空の場合はフィルタ
            filtered_history = [
                msg for msg in conversation_history
                if msg.get("content") is not None and str(msg.get("content")).strip()
            ]
            messages.extend(filtered_history)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        yield from provider.stream_response(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def get_available_models(self) -> List[str]:
        """Get list of available models (config-based)"""
        available_models = []
        
        # configから定義済みモデルを取得
        if hasattr(self.config, 'get_available_models'):
            all_models = self.config.get_available_models()
            for model in all_models:
                # providerが利用可能か確認
                provider_name = None
                if hasattr(self.config, 'get_model_provider'):
                    provider_name = self.config.get_model_provider(model)
                
                if provider_name and provider_name in self.providers:
                    available_models.append(model)
        
        # OpenRouterの場合は、設定されているが利用可能かは実行時に判断
        # ここでは何も追加しない
        
        return sorted(available_models)
    
    def set_model(self, model: str):
        """Set the current model (config-based)"""
        # Consider OpenRouter format
        if os.getenv("OPENAI_BASE_URL") and "/" in model:
            # For OpenRouter models, set as-is
            self.current_model = model
            return
        
        # configを使ってモデル名を解決（alias/display_name→完全名）
        # cli_utilities.pyで既に解決済みの場合もあるので、失敗しても続行
        actual_model = model  # デフォルトは入力そのまま
        if hasattr(self.config, 'resolve_model_name'):
            resolved = self.config.resolve_model_name(model)
            if resolved:
                actual_model = resolved
        
        # configからprovider取得
        provider_name = None
        if hasattr(self.config, 'get_model_provider'):
            provider_name = self.config.get_model_provider(actual_model)
        
        if not provider_name:
            # OpenRouter経由の場合はopenaiプロバイダーを使用
            if os.getenv("OPENAI_BASE_URL"):
                self.current_model = model
                return
            raise ValueError(f"Unknown model: {model}")
        
        if provider_name not in self.providers:
            raise Exception(f"Provider {provider_name} not available")
        
        self.current_model = actual_model  # 解決済みの完全名を使用
    
    def get_model_info(self, model: str = None) -> Dict[str, Any]:
        """Get information about a model (config-based)"""
        model = model or self.current_model
        
        # configを使ってモデル情報を取得
        provider_name = None
        if hasattr(self.config, 'get_model_provider'):
            # resolve first
            resolved = self.config.resolve_model_name(model) if hasattr(self.config, 'resolve_model_name') else model
            if resolved:
                provider_name = self.config.get_model_provider(resolved)
        
        if not provider_name:
            return {"error": f"Unknown model: {model}"}
        
        provider_available = provider_name in self.providers
        
        return {
            "model": model,
            "provider": provider_name,
            "available": provider_available,
            "current": model == self.current_model
        }


class CodeAssistant:
    """High-level code assistant interface"""
    
    def __init__(self, llm_manager: LLMManager):
        """Initialize code assistant"""
        self.llm = llm_manager
    
    def suggest_code_improvements(self, code: str, language: str = None) -> str:
        """Suggest improvements for code"""
        system_prompt = """You are an expert code reviewer. Analyze the provided code and suggest specific improvements focusing on:
1. Code quality and readability
2. Performance optimizations
3. Best practices for the language
4. Security considerations
5. Error handling

Provide concrete suggestions with explanations."""
        
        prompt = f"Review this code"
        if language:
            prompt += f" ({language})"
        prompt += f":\n\n```\n{code}\n```"
        
        response = self.llm.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        return response.content
    
    def explain_code(self, code: str, language: str = None) -> str:
        """Explain what code does"""
        system_prompt = """You are a code documentation expert. Explain code clearly and concisely, covering:
1. Overall purpose and functionality
2. Key algorithms or logic
3. Input/output behavior
4. Important implementation details
5. Potential use cases

Write explanations that are accessible to developers at different skill levels."""
        
        prompt = f"Explain this code"
        if language:
            prompt += f" ({language})"
        prompt += f":\n\n```\n{code}\n```"
        
        response = self.llm.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        return response.content
    
    def generate_diff_suggestion(
        self,
        original_code: str,
        user_request: str,
        language: str = None,
        context: str = ""
    ) -> str:
        """Generate code diff suggestion"""
        system_prompt = f"""You are Claude Code, an AI coding assistant. Generate precise code modifications based on user requests.

Rules:
1. Provide specific, actionable code changes
2. Explain the reasoning behind changes
3. Use proper diff format when showing changes
4. Consider the broader context of the codebase
5. Follow best practices for the programming language

{context}"""
        
        prompt = f"I have this code"
        if language:
            prompt += f" ({language})"
        prompt += f":\n\n```\n{original_code}\n```\n\nUser request: {user_request}\n\nPlease suggest specific changes and explain your reasoning."
        
        response = self.llm.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4
        )
        
        return response.content
    
    def generate_test_cases(self, code: str, language: str = None) -> str:
        """Generate test cases for code"""
        system_prompt = """You are a test automation expert. Generate comprehensive test cases that cover:
1. Normal/expected behavior
2. Edge cases and boundary conditions
3. Error conditions and exception handling
4. Performance considerations (if applicable)

Use appropriate testing frameworks for the language and provide runnable test code."""
        
        prompt = f"Generate test cases for this code"
        if language:
            prompt += f" ({language})"
        prompt += f":\n\n```\n{code}\n```"
        
        response = self.llm.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4
        )
        
        return response.content
    
    def refactor_code(self, code: str, refactor_type: str, language: str = None) -> str:
        """Refactor code based on specific type"""
        system_prompt = f"""You are an expert code refactoring specialist. Perform {refactor_type} refactoring while:
1. Maintaining the same functionality
2. Improving code structure and readability
3. Following language-specific best practices
4. Providing clear before/after comparisons
5. Explaining the benefits of the changes"""
        
        prompt = f"Refactor this code"
        if language:
            prompt += f" ({language})"
        prompt += f" using {refactor_type} refactoring:\n\n```\n{code}\n```"
        
        response = self.llm.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4
        )
        
        return response.content