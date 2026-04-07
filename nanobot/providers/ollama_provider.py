"""Ollama provider — native REST API."""

from __future__ import annotations

import json
import secrets
import string
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import httpx

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest

if TYPE_CHECKING:
    from nanobot.providers.registry import ProviderSpec

_ALNUM = string.ascii_letters + string.digits


def _short_tool_id() -> str:
    return "".join(secrets.choice(_ALNUM) for _ in range(9))


class OllamaProvider(LLMProvider):
    """Ollama provider with native REST API.

    Features:
    - Model discovery via GET /api/tags
    - Native chat via POST /api/chat
    - Tool calling support
    - Thinking mode (high/medium/low)
    - Streaming via ndjson
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        native_api_base: str | None = None,
        default_model: str = "llama3",
        extra_headers: dict[str, str] | None = None,
        spec: ProviderSpec | None = None,
        ollama_settings: Any = None,
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self.extra_headers = extra_headers or {}
        self._spec = spec
        self._ollama_settings = ollama_settings

        self._native_api_base = native_api_base or "http://localhost:11434/api"
        self._openai_api_base = api_base or "http://localhost:11434/v1"

        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(600.0))

    async def close(self) -> None:
        await self._http_client.aclose()

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models from Ollama."""
        try:
            response = await self._http_client.get(f"{self._native_api_base}/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception:
            return []

    def _build_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build messages for Ollama API, handling content blocks."""
        result = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            tool_call_id = msg.get("tool_call_id")
            name = msg.get("name")

            images = []
            if isinstance(content, list):
                new_content = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "image_url":
                            img = item.get("image_url", {})
                            url = img.get("url", "") if isinstance(img, dict) else str(img)
                            if url.startswith("data:"):
                                import re
                                match = re.search(r"base64,([^)]+)", url)
                                if match:
                                    images.append(match.group(1))
                            else:
                                images.append(url)
                        elif item.get("type") == "text":
                            new_content.append(item.get("text", ""))
                content = " ".join(new_content) if new_content else None

            msg_dict: dict[str, Any] = {"role": role, "content": content or ""}
            if images:
                msg_dict["images"] = images
            if tool_call_id:
                msg_dict["tool_call_id"] = tool_call_id
            if name:
                msg_dict["name"] = name
            result.append(msg_dict)
        return result

    def _build_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """Build tools for Ollama API."""
        if not tools:
            return []
        ollama_tools = []
        for tool in tools:
            if isinstance(tool, dict) and "function" in tool:
                fn = tool["function"]
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": fn.get("name"),
                        "description": fn.get("description"),
                        "parameters": fn.get("parameters"),
                    },
                })
        return ollama_tools

    async def _chat_native(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        stream: bool = False,
        on_content_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        """Use Ollama native /api/chat endpoint."""
        model_name = model or self.default_model

        options: dict[str, Any] = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        if reasoning_effort:
            options["reasoning_effort"] = reasoning_effort

        think = None
        if self._ollama_settings and self._ollama_settings.think:
            think = self._ollama_settings.think
        elif reasoning_effort:
            think = reasoning_effort

        keep_alive = "5m"
        if self._ollama_settings:
            keep_alive = self._ollama_settings.keep_alive

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": self._build_messages(messages),
            "stream": stream,
        }

        if tools:
            payload["tools"] = self._build_tools(tools)

        if think:
            payload["think"] = think

        if tool_choice and isinstance(tool_choice, dict):
            tf = tool_choice.get("function")
            if tf:
                payload["tool_choice"] = {"type": "function", "function": {"name": tf.get("name")}}

        payload["options"] = options
        payload["keep_alive"] = keep_alive

        try:
            if stream:
                return await self._stream_native(
                    payload=payload,
                    on_content_delta=on_content_delta,
                )

            response = await self._http_client.post(
                f"{self._native_api_base}/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_response(data)
        except Exception as e:
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    async def _stream_native(
        self,
        payload: dict[str, Any],
        on_content_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        """Stream using Ollama's native ndjson endpoint."""
        content_parts: list[str] = []
        tool_calls_buf: dict[int, dict[str, Any]] = {}
        thinking_parts: list[str] = []
        finish_reason = "stop"
        usage: dict[str, int] = {}

        try:
            async with self._http_client.stream(
                "POST",
                f"{self._native_api_base}/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg = chunk.get("message", {})
                    if msg.get("content"):
                        content_parts.append(msg["content"])
                        if on_content_delta:
                            await on_content_delta(msg["content"])
                    if msg.get("thinking"):
                        thinking_parts.append(msg["thinking"])
                    if msg.get("tool_calls"):
                        for tc in msg["tool_calls"]:
                            idx = tc.get("index", 0)
                            if idx not in tool_calls_buf:
                                tool_calls_buf[idx] = {"name": "", "arguments": {}}
                            fn = tc.get("function", {})
                            if fn.get("name"):
                                tool_calls_buf[idx]["name"] = fn["name"]
                            if fn.get("arguments"):
                                tool_calls_buf[idx]["arguments"].update(fn["arguments"])
                    if chunk.get("done"):
                        finish_reason = "stop"
                        usage = {
                            "prompt_tokens": chunk.get("prompt_eval_count", 0),
                            "completion_tokens": chunk.get("eval_count", 0),
                            "total_tokens": chunk.get("prompt_eval_count", 0) + chunk.get("eval_count", 0),
                        }

            parsed_tool_calls = []
            for tc_data in tool_calls_buf.values():
                args = tc_data["arguments"]
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                parsed_tool_calls.append(ToolCallRequest(
                    id=_short_tool_id(),
                    name=tc_data["name"],
                    arguments=args if isinstance(args, dict) else {},
                ))

            thinking = "".join(thinking_parts) if thinking_parts else None

            return LLMResponse(
                content="".join(content_parts) or None,
                tool_calls=parsed_tool_calls,
                finish_reason=finish_reason,
                usage=usage,
                reasoning_content=thinking,
            )
        except Exception as e:
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        """Parse Ollama chat response."""
        msg = data.get("message", {})
        content = msg.get("content", "")
        thinking = msg.get("thinking")

        tool_calls = []
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                tool_calls.append(ToolCallRequest(
                    id=_short_tool_id(),
                    name=fn.get("name"),
                    arguments=args if isinstance(args, dict) else {},
                ))

        usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        }

        return LLMResponse(
            content=content or None,
            tool_calls=tool_calls,
            finish_reason="stop",
            usage=usage,
            reasoning_content=thinking,
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
        """Send a chat completion request using native Ollama API."""
        return await self._chat_native(
            messages=messages,
            tools=tools,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            tool_choice=tool_choice,
            stream=False,
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
        """Stream a chat completion using native Ollama API."""
        return await self._chat_native(
            messages=messages,
            tools=tools,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            tool_choice=tool_choice,
            stream=True,
            on_content_delta=on_content_delta,
        )

    def get_default_model(self) -> str:
        return self.default_model
