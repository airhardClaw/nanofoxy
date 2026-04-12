"""LM Studio provider — native REST API + OpenAI-compatible endpoints."""

from __future__ import annotations

import secrets
import string
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import httpx
import json_repair
from openai import AsyncOpenAI

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest

if TYPE_CHECKING:
    from nanobot.providers.registry import ProviderSpec

_ALNUM = string.ascii_letters + string.digits


def _short_tool_id() -> str:
    return "".join(secrets.choice(_ALNUM) for _ in range(9))


class LMStudioProvider(LLMProvider):
    """LM Studio provider with native REST API and OpenAI-compatible fallback.

    Features:
    - Model discovery via GET /api/v1/models
    - Programmatic model loading/unloading
    - Stateful chat sessions via POST /api/v1/chat
    - OpenAI-compatible endpoint fallback
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        native_api_base: str | None = None,
        default_model: str = "gpt-4o",
        extra_headers: dict[str, str] | None = None,
        spec: ProviderSpec | None = None,
        lmstudio_settings: Any = None,
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self.extra_headers = extra_headers or {}
        self._spec = spec
        self._lmstudio_settings = lmstudio_settings

        self._native_api_base = native_api_base or "http://localhost:1234/api/v1"
        self._openai_api_base = api_base or "http://localhost:1234/v1"

        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(600.0))

        self._openai_client = AsyncOpenAI(
            api_key=api_key or "no-key",
            base_url=self._openai_api_base,
            timeout=httpx.Timeout(600.0),
        )

        self._loaded_models: dict[str, str] = {}
        self._loaded_instance_id: str | None = None
        self._chat_response_id: str | None = None

    async def close(self) -> None:
        await self._http_client.aclose()
        await self._openai_client.close()

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models from LM Studio."""
        try:
            response = await self._http_client.get(f"{self._native_api_base}/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception:
            return []

    async def load_model(
        self,
        model_id: str,
        context_length: int = 32768,
        flash_attention: bool = True,
        eval_batch_size: int = 512,
        offload_kv_cache_to_gpu: bool = True,
        llama_k_cache_quantization_type: str = "Q8_0",
        llama_v_cache_quantization_type: str = "Q4_0",
    ) -> dict[str, Any]:
        """Load a model into LM Studio."""
        payload = {
            "model": model_id,
            "context_length": context_length,
            "flash_attention": flash_attention,
            "eval_batch_size": eval_batch_size,
            "offload_kv_cache_to_gpu": offload_kv_cache_to_gpu,
            "llama_k_cache_quantization_type": llama_k_cache_quantization_type,
            "llama_v_cache_quantization_type": llama_v_cache_quantization_type,
            "echo_load_config": True,
        }
        response = await self._http_client.post(
            f"{self._native_api_base}/models/load",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
        self._loaded_models[model_id] = result.get("instance_id", "")
        self._loaded_instance_id = result.get("instance_id")
        return result

    async def unload_model(self, instance_id: str | None = None) -> None:
        """Unload a model from LM Studio."""
        if instance_id is None:
            instance_id = self._loaded_instance_id
        if not instance_id:
            return
        try:
            await self._http_client.post(
                f"{self._native_api_base}/models/unload",
                json={"instance_id": instance_id},
            )
        except Exception:
            pass
        self._loaded_instance_id = None
        self._loaded_models.clear()

    async def _ensure_model_loaded(self, model: str) -> str | None:
        """Ensure model is loaded, auto-load if enabled."""
        if not self._lmstudio_settings or not self._lmstudio_settings.auto_load:
            return None

        available_models = await self.list_models()
        loaded_models = [m for m in available_models if m.get("ready")]

        model_id = model
        if "/" in model:
            model_id = model.split("/")[-1]

        for m in loaded_models:
            m_id = m.get("id", "")
            if model_id in m_id or m_id in model:
                self._loaded_instance_id = m.get("instance_id")
                return self._loaded_instance_id

        try:
            result = await self.load_model(
                model_id=model,
                context_length=self._lmstudio_settings.context_length,
                flash_attention=self._lmstudio_settings.flash_attention,
                eval_batch_size=self._lmstudio_settings.eval_batch_size,
                offload_kv_cache_to_gpu=self._lmstudio_settings.offload_kv_cache_to_gpu,
                llama_k_cache_quantization_type=self._lmstudio_settings.llama_k_cache_quantization_type,
                llama_v_cache_quantization_type=self._lmstudio_settings.llama_v_cache_quantization_type,
            )
            return result.get("instance_id")
        except Exception:
            return None

    def _build_messages_for_stateful(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract user input from messages for stateful chat."""
        user_inputs: list[str] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                if isinstance(content, str):
                    user_inputs.append(content)
                elif isinstance(content, list):
                    text_parts = []
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            text_parts.append(c.get("text", ""))
                    if text_parts:
                        user_inputs.append(" ".join(text_parts))
        return [{"type": "input", "text": inp} for inp in user_inputs]

    async def _chat_stateful(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Use LM Studio's stateful chat API."""
        model_name = model or self.default_model
        await self._ensure_model_loaded(model_name)

        inputs = self._build_messages_for_stateful(messages)
        if not inputs:
            return LLMResponse(content="Error: No user input found", finish_reason="error")

        payload: dict[str, Any] = {
            "model": model_name,
            "inputs": inputs,
            "options": {
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        }

        if self._lmstudio_settings and self._lmstudio_settings.use_stateful_chat:
            if self._chat_response_id:
                payload["previous_response_id"] = self._chat_response_id

        try:
            response = await self._http_client.post(
                f"{self._native_api_base}/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            self._chat_response_id = data.get("response_id")

            output = data.get("output", [])
            content = ""
            for item in output:
                if item.get("type") == "message":
                    content = item.get("content", "")
                    break

            return LLMResponse(content=content, finish_reason="stop")
        except Exception as e:
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    async def _chat_stateless(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        on_content_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        """Use OpenAI-compatible chat completions endpoint."""
        if on_content_delta:
            return await self.chat_stream(
                messages=messages,
                tools=tools,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                tool_choice=tool_choice,
                on_content_delta=on_content_delta,
            )

        try:
            kwargs: dict[str, Any] = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice or "auto"
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

            response = await self._openai_client.chat.completions.create(**kwargs)
            return self._parse_openai_response(response)
        except Exception as e:
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    @staticmethod
    def _parse_openai_response(response: Any) -> LLMResponse:
        """Parse OpenAI-compatible response."""
        if not response.choices:
            return LLMResponse(content="Error: No choices returned", finish_reason="error")

        choice = response.choices[0]
        content = choice.message.content or ""
        finish_reason = choice.finish_reason or "stop"

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json_repair.loads(args)
                tool_calls.append(ToolCallRequest(
                    id=tc.id or _short_tool_id(),
                    name=tc.function.name,
                    arguments=args if isinstance(args, dict) else {},
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage={"prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                   "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                   "total_tokens": response.usage.total_tokens if response.usage else 0},
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request."""
        if tools:
            return await self._chat_stateless(
                messages=messages,
                tools=tools,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                tool_choice=tool_choice,
            )

        if self._lmstudio_settings and self._lmstudio_settings.use_stateful_chat:
            return await self._chat_stateful(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        return await self._chat_stateless(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        on_content_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        """Stream a chat completion."""
        model_name = model or self.default_model

        try:
            kwargs: dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice or "auto"
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

            stream = await self._openai_client.chat.completions.create(**kwargs)
            content_parts: list[str] = []
            tool_calls_buf: dict[int, dict[str, Any]] = {}
            finish_reason = "stop"
            usage: dict[str, int] = {}

            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content_parts.append(delta.content)
                        if on_content_delta:
                            await on_content_delta(delta.content)
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index or 0
                            if idx not in tool_calls_buf:
                                tool_calls_buf[idx] = {"id": "", "name": "", "arguments": ""}
                            if tc.id:
                                tool_calls_buf[idx]["id"] = tc.id
                            if tc.function and tc.function.name:
                                tool_calls_buf[idx]["name"] = tc.function.name
                            if tc.function and tc.function.arguments:
                                tool_calls_buf[idx]["arguments"] += tc.function.arguments
                    if chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                if chunk.usage:
                    usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens or 0,
                        "completion_tokens": chunk.usage.completion_tokens or 0,
                        "total_tokens": chunk.usage.total_tokens or 0,
                    }

            parsed_tool_calls = []
            for tc_data in tool_calls_buf.values():
                args = tc_data["arguments"]
                if isinstance(args, str):
                    args = json_repair.loads(args) if args else {}
                parsed_tool_calls.append(ToolCallRequest(
                    id=tc_data["id"] or _short_tool_id(),
                    name=tc_data["name"],
                    arguments=args if isinstance(args, dict) else {},
                ))

            return LLMResponse(
                content="".join(content_parts) or None,
                tool_calls=parsed_tool_calls,
                finish_reason=finish_reason,
                usage=usage,
            )
        except Exception as e:
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    def get_default_model(self) -> str:
        return self.default_model
