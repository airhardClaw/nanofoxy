# Tool Usage Notes

Tool signatures are provided automatically via function calling.
This file documents non-obvious constraints and usage patterns.

## exec — Safety Limits

- Commands have a configurable timeout (default 60s)
- Dangerous commands are blocked (rm -rf, format, dd, shutdown, etc.)
- Output is truncated at 10,000 characters
- `restrictToWorkspace` config can limit file access to the workspace

## cron — Scheduled Reminders

- Please refer to cron skill for usage.

## Liquid AI Models (LFM2/LFM2.5) — Tool Calling

When using Liquid AI models, tools work differently:

### Tool Call Format

Output tool calls between `<|tool_call_start|>` and `<|tool_call_end|>` tokens.

**JSON format (recommended):**
```
<|tool_call_start|>
{"name": "read_file", "arguments": {"path": "/home/user/file.txt"}}
<|tool_call_end|>
```

**Python-like format:**
```
<|tool_call_start|>[read_file(path="/home/user/file.txt")]<|tool_call_end|>
```

### Important

- Output only the JSON, no additional text before or after the tool call tokens
- Always use the exact tool name from the available tools list
- If no tool is needed, reply with text normally

### Best Practices

- Include only tools relevant to the current request
- Write clear, concise tool descriptions in your requests
