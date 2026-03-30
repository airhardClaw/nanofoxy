# Providers

The providers module provides the LLM provider abstraction layer for nanobot. It supports multiple LLM backends through a consistent interface.

## Files

| File | Description |
|------|-------------|
| `providers/__init__.py` | Module exports with lazy-loading |
| `providers/base.py` | Abstract base class for all LLM providers |
| `providers/registry.py` | Provider registry with metadata |
| `providers/anthropic_provider.py` | Native Anthropic/Claude SDK implementation |
| `providers/openai_compat_provider.py` | OpenAI-compatible API provider |
| `providers/openai_codex_provider.py` | OpenAI Codex OAuth-based provider |
| `providers/azure_openai_provider.py` | Azure OpenAI specific implementation |
| `providers/transcription.py` | Voice transcription using Groq Whisper |

---

## Base Classes

### ToolCallRequest

**File:** `providers/base.py`

Dataclass representing a tool call from the LLM.

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier for the tool call |
| `name` | str | Name of the tool to call |
| `arguments` | dict[str, Any] | Arguments to pass to the tool |
| `extra_content` | list | Additional content blocks |
| `provider_specific_fields` | dict | Provider-specific extra fields |
| `function_provider_specific_fields` | dict | Function-specific provider fields |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_openai_tool_call` | dict | Serializes to OpenAI-style format |

---

### LLMResponse

**File:** `providers/base.py`

Dataclass representing an LLM response.

| Field | Type | Description |
|-------|------|-------------|
| `content` | str | Response content |
| `tool_calls` | list[ToolCallRequest] | Tool calls requested by the LLM |
| `finish_reason` | str | Why the response finished |
| `usage` | dict | Token usage statistics |
| `reasoning_content` | str | Reasoning content (if any) |
| `thinking_blocks` | list | Thinking blocks (for models that support it) |

| Property | Type | Description |
|----------|------|-------------|
| `has_tool_calls` | bool | Boolean check for tool call presence |

---

### GenerationSettings

**File:** `providers/base.py`

Dataclass for default generation parameters.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `temperature` | float | 0.7 | Sampling temperature |
| `max_tokens` | int | 4096 | Maximum tokens to generate |
| `reasoning_effort` | str | None | Reasoning effort level |

---

### LLMProvider (Abstract Base Class)

**File:** `providers/base.py`

Abstract base class that all LLM providers inherit from.

#### Abstract Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `chat` | messages, tools, ... | LLMResponse | Send chat completion request |
| `get_default_model` | - | str | Get default model name |

#### Key Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `_sanitize_empty_content` | messages | list | Fix empty message blocks, strip internal `_meta` fields |
| `_sanitize_request_messages` | messages | list | Keep only provider-safe message keys |
| `_strip_image_content` | messages | list | Replace image_url blocks with text placeholders |
| `_is_transient_error` | error | bool | Check if error is transient (rate limits, timeouts) |
| `_safe_chat` | ... | LLMResponse | Wrapper that converts exceptions to error responses |
| `chat_stream` | messages, tools, ... | AsyncIterator | Streaming version (default falls back to non-streaming) |
| `_safe_chat_stream` | ... | AsyncIterator | Safe wrapper for streaming |
| `chat_stream_with_retry` | ... | LLMResponse | Streaming with retry logic |
| `chat_with_retry` | ... | LLMResponse | Non-streaming with retry logic |

---

## Provider Implementations

### AnthropicProvider

**File:** `providers/anthropic_provider.py`

Native Anthropic SDK implementation for Claude models.

#### Key Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `_gen_tool_id` | - | str | Generate 22-char alphanumeric tool call ID |
| `_strip_prefix` | model | str | Strip "anthropic/" from model names |

#### Message Conversion Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `_convert_messages` | messages | list | Convert OpenAI format to Anthropic Messages API format |
| `_tool_result_block` | tool_call_id, content | dict | Convert tool result messages to Anthropic blocks |
| `_assistant_blocks` | message | list | Convert assistant messages including thinking blocks and tool calls |
| `_convert_user_content` | content | list | Convert user content, translating image_url blocks |
| `_convert_image_block` | block | dict | Convert OpenAI image_url to Anthropic base64/URL format |
| `_merge_consecutive` | messages | list | Merge consecutive messages with same role |

#### Tool Handling

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `_convert_tools` | tools | list | Convert OpenAI function schema to Anthropic tool format |
| `_convert_tool_choice` | choice | dict | Convert tool_choice to Anthropic format |

#### Prompt Caching

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `_apply_cache_control` | messages, provider | list | Inject cache_control markers for Anthropic prompt caching |

#### Response Parsing

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `_parse_response` | response | LLMResponse | Parse Anthropic response handling text, tool_use, and thinking blocks |

#### API Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `chat` | messages, tools, ... | LLMResponse | Non-streaming chat (lines 395-413) |
| `chat_stream` | messages, tools, callback, ... | None | Streaming chat with callback support |
| `get_default_model` | - | str | Returns "claude-sonnet-4-20250514" |

#### Features
- Native Anthropic SDK integration
- Extended thinking/reasoning support
- Prompt caching
- Image/vision support

---

### OpenAICompatProvider

**File:** `providers/openai_compat_provider.py`

Unified provider for all OpenAI-compatible APIs.

#### Key Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `_short_tool_id` | - | str | Generate 9-char alphanumeric tool ID |
| `_get` | obj, key, default | Any | Safely get dict value or object attribute |
| `_coerce_dict` | val | dict | Coerce value to dict |
| `_extract_tc_extras` | tool_calls | dict | Extract provider-specific fields from tool calls |
| `_uses_openrouter_attribution` | - | bool | Check if OpenRouter attribution headers needed |

#### Key Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `_setup_env` | - | None | Set environment variables based on provider spec |
| `_apply_cache_control` | messages, provider | list | Inject cache_control markers |
| `_normalize_tool_call_id` | tool_call_id | str | Normalize tool call IDs to 9-char alphanumeric |
| `_sanitize_messages` | messages | list | Strip non-standard keys, normalize tool call IDs |
| `_build_kwargs` | ... | dict | Build API request parameters |
| `_parse` | response | LLMResponse | Parse non-streaming response |
| `_parse_chunks` | response | list | Parse streaming response chunks |
| `_handle_error` | error | LLMResponse | Convert exceptions to error responses |
| `_extract_text_content` | response | str | Extract text from various response formats |
| `_extract_usage` | response | dict | Extract token usage from response |

#### API Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `chat` | messages, tools, ... | LLMResponse | Non-streaming chat |
| `chat_stream` | messages, tools, callback, ... | None | Streaming chat |
| `get_default_model` | - | str | Returns "gpt-4o" |

#### Supported Providers
- OpenAI
- DeepSeek
- Gemini
- DashScope
- Moonshot
- Mistral
- vLLM
- Ollama
- And many more via OpenAI-compatible API

#### Features
- Prompt caching support
- OpenRouter attribution headers
- Model prefix stripping for gateways

---

### OpenAICodexProvider

**File:** `providers/openai_codex_provider.py`

OAuth-based OpenAI Codex provider using the Responses API.

#### Key Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `_strip_model_prefix` | model | str | Strip "openai-codex/" or "openai_codex/" prefixes |
| `_build_headers` | - | dict | Build OAuth-based headers |
| `_convert_tools` | tools | list | Convert OpenAI function schema to Codex flat format |
| `_convert_messages` | messages | list | Convert messages to Codex input format |
| `_convert_user_message` | message | dict | Convert user messages including images |
| `_split_tool_call_id` | tool_call_id | tuple | Split tool call ID into call_id and item_id |
| `_prompt_cache_key` | messages | str | Generate SHA256 cache key |
| `_iter_sse` | response | Iterator | Iterate over Server-Sent Events |
| `_consume_sse` | response | dict | Parse SSE stream into response |
| `_map_finish_reason` | status | str | Map Codex status to finish reason |
| `_friendly_error` | error | str | Convert HTTP errors to user-friendly messages |

#### API Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `_call_codex` | ... | dict | Shared request logic for both chat() and chat_stream() |
| `chat` | messages, tools, ... | LLMResponse | Non-streaming |
| `chat_stream` | messages, tools, callback, ... | None | Streaming |
| `get_default_model` | - | str | Returns "openai-codex/gpt-5.1-codex" |

#### Features
- OAuth-based authentication (uses `oauth_cli_kit`)
- Uses Codex Responses API
- SSE streaming
- Handles SSL verification failures gracefully

---

### AzureOpenAIProvider

**File:** `providers/azure_openai_provider.py`

Azure OpenAI specific implementation.

#### Key Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `_build_chat_url` | - | str | Build Azure OpenAI chat completions URL |
| `_build_headers` | - | dict | Build headers with api-key header |
| `_supports_temperature` | model | bool | Check if deployment supports temperature parameter |
| `_prepare_request_payload` | ... | dict | Prepare Azure 2024-10-21 compliant payload |
| `_parse_response` | response | LLMResponse | Parse Azure OpenAI response |
| `_consume_stream` | response | Iterator | Parse Azure SSE stream |

#### API Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `chat` | messages, tools, ... | LLMResponse | Non-streaming chat |
| `chat_stream` | messages, tools, callback, ... | None | Streaming chat |
| `get_default_model` | - | str | Returns "gpt-5.2-chat" |

#### Features
- API version 2024-10-21 compliance
- Uses model as deployment name in URL path
- Uses api-key header instead of Authorization
- Uses max_completion_tokens instead of max_tokens
- Direct HTTP calls (bypasses LiteLLM)
- Temperature not supported for GPT-5, O1, O3, O4 models

---

## Provider Registry

**File:** `providers/registry.py`

### ProviderSpec Dataclass

Metadata for each provider.

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Config field name (e.g., "dashscope") |
| `keywords` | list[str] | Model name keywords for matching |
| `env_key` | str | Environment variable for API key |
| `display_name` | str | Display name in status |
| `backend` | str | Implementation type: "openai_compat", "anthropic", "azure_openai", "openai_codex" |
| `env_extras` | dict | Extra env vars |
| `is_gateway` | bool | Routes any model (OpenRouter, AiHubMix) |
| `is_local` | bool | Local deployment (vLLM, Ollama) |
| `detect_by_key_prefix` | str | Match api_key prefix (e.g., "sk-or-" for OpenRouter) |
| `detect_by_base_keyword` | str | Match substring in api_base URL |
| `default_api_base` | str | Default OpenAI-compatible base URL |
| `strip_model_prefix` | bool | Strip "provider/" before sending |
| `supports_max_completion_tokens` | bool | Provider supports max_completion_tokens |
| `model_overrides` | dict | Per-model parameter overrides |
| `is_oauth` | bool | OAuth-based (no API key) |
| `is_direct` | bool | Direct provider (user supplies everything) |
| `supports_prompt_caching` | bool | Supports cache_control on content blocks |

### Registered Providers

#### Gateways (detected by api_key/api_base)
- `openrouter` - Global gateway, keys start with "sk-or-"
- `aihubmix` - Global gateway, strips model prefix
- `siliconflow` - Chinese gateway (硅基流动)
- `volcengine` - ByteDance VolcEngine
- `volcengine_coding_plan` - VolcEngine Coding Plan
- `byteplus` - BytePlus international
- `byteplus_coding_plan` - BytePlus Coding Plan

#### Standard Providers (matched by model keywords)
- `anthropic` - Claude models
- `openai` - OpenAI GPT models
- `openai_codex` - OAuth-based Codex
- `github_copilot` - GitHub Copilot OAuth
- `deepseek` - DeepSeek models
- `gemini` - Google Gemini
- `zhipu` - Chinese Zhipu AI (智谱)
- `dashscope` - Alibaba Qwen models
- `moonshot` - Kimi models (Moonshot AI)
- `minimax` - MiniMax models
- `mistral` - Mistral AI models
- `stepfun` - StepFun (阶跃星辰)

#### Local Deployments
- `vllm` - vLLM local server
- `ollama` - Ollama local
- `ovms` - OpenVINO Model Server

#### Auxiliary
- `groq` - Groq (mainly for Whisper transcription)

#### Direct
- `custom` - Custom OpenAI-compatible endpoint
- `azure_openai` - Azure OpenAI

### Lookup Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `find_by_name` | name | ProviderSpec | Find provider spec by config field name |

---

## Transcription

**File:** `providers/transcription.py`

### GroqTranscriptionProvider

Voice transcription using Groq's Whisper API.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | api_key: str \| None = None | - | Initialize, accepts API key or reads from GROQ_API_KEY env var |
| `transcribe` | file_path: str \| Path | str | Transcribe audio file using whisper-large-v3 model |

#### API Endpoint

```
https://api.groq.com/openai/v1/audio/transcriptions
```

#### Features
- Uses `whisper-large-v3` model
- Returns transcribed text or empty string on error
- 60-second timeout

---

## Lazy Loading

**File:** `providers/__init__.py`

Uses `_LAZY_IMPORTS` dict to defer imports until needed.

```python
__all__ = [
    "LLMProvider",
    "LLMResponse",
    "AnthropicProvider",
    "OpenAICompatProvider",
    "OpenAICodexProvider",
    "AzureOpenAIProvider",
]
```

---

## Summary

The nanobot providers system provides:

1. **Consistent Interface**: All providers implement `chat()`, `chat_stream()`, and `get_default_model()` from the abstract `LLMProvider` base class

2. **Retry Logic**: Built-in retry with exponential backoff for transient errors (rate limits, server errors)

3. **Message Sanitization**: Utilities to clean messages for provider compatibility

4. **Tool Calling**: Unified tool call representation across all providers

5. **Multiple Backends**: Support for 25+ providers including Anthropic, OpenAI, DeepSeek, Gemini, and local deployments
