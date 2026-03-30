# Utils

The utils module provides utility functions for nanobot.

## Files

| File | Description |
|------|-------------|
| `utils/__init__.py` | Module initialization |
| `utils/helpers.py` | General helper functions |
| `utils/evaluator.py` | Expression evaluation |

---

## Helpers

**File:** `utils/helpers.py`

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `strip_think` | text | str | Remove think blocks from model output |
| `detect_image_mime` | data | str \| None | Detect image MIME type from magic bytes |
| `build_image_content_blocks` | raw, mime, path, label | list | Create content blocks for images |
| `ensure_dir` | path | Path | Create directory if it doesn't exist |
| `timestamp` | - | str | Get current ISO timestamp |
| `current_time_str` | timezone | str | Get human-readable current time |
| `safe_filename` | name | str | Replace unsafe filename characters |
| `split_message` | content, max_len | list | Split text into chunks |
| `build_assistant_message` | ... | dict | Build provider-safe assistant message |
| `estimate_prompt_tokens` | messages, tools | int | Estimate token count |
| `estimate_message_tokens` | message | int | Estimate tokens for one message |
| `estimate_prompt_tokens_chain` | provider, model, messages, tools | tuple | Estimate via provider or tiktoken |
| `build_status_content` | ... | str | Build runtime status string |
| `sync_workspace_templates` | workspace, silent | None | Sync bundled templates to workspace |

### strip_think

Removes think blocks from text using regex.

### detect_image_mime

Detects image MIME type from magic bytes.

| Supported Types |
|-----------------|
| PNG |
| JPEG |
| GIF |
| WEBP |

### split_message

Splits text into chunks within max_len, preferring line breaks.

Used for Discord messages (2000 char limit).

---

## Evaluator

**File:** `utils/evaluator.py`

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `evaluate_expression` | expr, context | Any | Evaluate a Python expression safely |
| `safe_eval` | expr | Any | Safe expression evaluation |

Used for evaluating dynamic expressions in configuration or agent context.
