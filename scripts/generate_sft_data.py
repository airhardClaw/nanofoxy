#!/usr/bin/env python3
"""Generate SFT training data for nanofoxy tool usage with tool calls.

This script creates training data in the OpenAI function calling format,
suitable for fine-tuning models like LFM, LLaMA, or DeepSeek.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Any


SYSTEM_PROMPT = """You are nanoFoxy, a helpful AI assistant with access to tools.

Available tools:
{tool_list}

Instructions:
1. Analyze the user's request to determine which tools are needed
2. Use tool_calls to execute actions (NOT exec/shell for file operations)
3. Use exec only for system commands (ls, cat, ps, etc.) or running scripts
4. For file operations, use read_file/write_file/edit_file tools
5. Always check tool results before proceeding
6. Report results to the user in a helpful way"""


def get_tool_schema() -> list[dict]:
    """Get tool schemas in OpenAI function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file. Returns numbered lines.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The file path to read"},
                        "offset": {"type": "integer", "description": "Line number to start from (1-indexed)"},
                        "limit": {"type": "integer", "description": "Maximum lines to read"}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file. Creates the file if it doesn't exist.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The file path to write"},
                        "content": {"type": "string", "description": "Content to write"}
                    },
                    "required": ["path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Edit specific parts of a file using exact string replacement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The file path to edit"},
                        "oldString": {"type": "string", "description": "Text to find"},
                        "newString": {"type": "string", "description": "Text to replace with"}
                    },
                    "required": ["path", "oldString", "newString"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List directory contents with details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to list"}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "glob",
                "description": "Find files matching a pattern.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Glob pattern (e.g., **/*.py)"},
                        "path": {"type": "string", "description": "Base directory to search"}
                    },
                    "required": ["pattern"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "grep",
                "description": "Search for patterns in files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Regex pattern to search"},
                        "path": {"type": "string", "description": "Directory to search"}
                    },
                    "required": ["pattern", "path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "exec",
                "description": "Execute shell commands. Use ONLY for system commands or running scripts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to execute"},
                        "timeout": {"type": "integer", "description": "Timeout in seconds"}
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "web_fetch",
                "description": "Fetch and parse web page content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"}
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "message",
                "description": "Send a message to the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Message content"},
                        "content_format": {"type": "string", "description": "Format: markdown, html, text"}
                    },
                    "required": ["content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "spawn",
                "description": "Create a background subagent to handle tasks.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task for subagent"},
                        "role": {"type": "string", "description": "Role: coding-expert, websearch-expert, etc."},
                        "subagent_id": {"type": "string", "description": "Subagent identifier"}
                    },
                    "required": ["task"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "a2a",
                "description": "Communicate with subagents via A2A protocol.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "Action: list, discover, call, forward, delegate"},
                        "target": {"type": "string", "description": "Target subagent ID"},
                        "capabilities": {"type": "array", "items": {"type": "string"}},
                        "task": {"type": "string", "description": "Task description"}
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cron",
                "description": "Manage scheduled jobs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "Action: list, add, remove, enable, disable"},
                        "name": {"type": "string", "description": "Job name"},
                        "schedule": {"type": "string", "description": "Cron expression"},
                        "task": {"type": "string", "description": "Task to execute"}
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "memory",
                "description": "Manage persistent memory and knowledge.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "Action: read, write, search, recall"},
                        "query": {"type": "string", "description": "Query or content"},
                        "topic": {"type": "string", "description": "Topic for memory"}
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "system",
                "description": "Get system information (CPU, memory, disk, processes).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "info": {"type": "string", "description": "What to check: cpu, memory, disk, processes"}
                    },
                    "required": ["info"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "speak",
                "description": "Convert text to speech using TTS.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to speak"},
                        "voice": {"type": "string", "description": "Voice: us_male, us_female, uk_male, uk_female"}
                    },
                    "required": ["text"]
                }
            }
        }
    ]


LINUX_EXAMPLES = [
    # File operations
    {
        "user": "List the files in the current directory",
        "assistant_tool_calls": [
            {"name": "list_dir", "arguments": {"path": "."}}
        ],
        "assistant_response": "Here are the files in the current directory:\n- file1.txt\n- file2.py\n- directory/"
    },
    {
        "user": "List all Python files in the project",
        "assistant_tool_calls": [
            {"name": "glob", "arguments": {"pattern": "**/*.py"}}
        ],
        "assistant_response": "Found 15 Python files in the project."
    },
    {
        "user": "Read the config file",
        "assistant_tool_calls": [
            {"name": "read_file", "arguments": {"path": "/home/user/config.json"}}
        ],
        "assistant_response": "The config file contains: {\"key\": \"value\"}"
    },
    {
        "user": "Find all files containing 'TODO'",
        "assistant_tool_calls": [
            {"name": "grep", "arguments": {"pattern": "TODO", "path": "."}}
        ],
        "assistant_response": "Found 5 files with TODO comments."
    },
    
    # Writing files
    {
        "user": "Create a simple hello.py script",
        "assistant_tool_calls": [
            {"name": "write_file", "arguments": {"path": "hello.py", "content": "#!/usr/bin/env python3\nprint('Hello, World!')\n"}}
        ],
        "assistant_response": "Created hello.py with the following content:\n```python\n#!/usr/bin/env python3\nprint('Hello, World!')\n```"
    },
    {
        "user": "Add a comment to the start of main.py",
        "assistant_tool_calls": [
            {"name": "edit_file", "arguments": {"path": "main.py", "oldString": "#!/usr/bin/env python3", "newString": "#!/usr/bin/env python3\n# Created by nanoFoxy\n"}}
        ],
        "assistant_response": "Added the comment to main.py"
    },
    
    # System commands via exec
    {
        "user": "Check disk usage",
        "assistant_tool_calls": [
            {"name": "exec", "arguments": {"command": "df -h"}}
        ],
        "assistant_response": "Disk usage:\nFilesystem  Size  Used Avail Use% Mounted on\n/dev/sda1    100G   50G   50G  50% /"
    },
    {
        "user": "Check running processes",
        "assistant_tool_calls": [
            {"name": "exec", "arguments": {"command": "ps aux | head -20"}}
        ],
        "assistant_response": "Running processes: ..."
    },
    {
        "user": "Check system memory",
        "assistant_tool_calls": [
            {"name": "exec", "arguments": {"command": "free -h"}}
        ],
        "assistant_response": "Memory:\n              total    used    free\nMem:           16Gi   8Gi   8Gi"
    },
    {
        "user": "Show system info",
        "assistant_tool_calls": [
            {"name": "system", "arguments": {"info": "cpu"}}
        ],
        "assistant_response": "CPU: 4 cores at 2.4GHz"
    },
    
    # Python script execution
    {
        "user": "Run the main.py script",
        "assistant_tool_calls": [
            {"name": "exec", "arguments": {"command": "python3 main.py"}}
        ],
        "assistant_response": "Script output: Hello World!"
    },
    {
        "user": "Run a Python script with arguments",
        "assistant_tool_calls": [
            {"name": "exec", "arguments": {"command": "python3 script.py --arg1 value1 --arg2 value2"}}
        ],
        "assistant_response": "Script executed successfully"
    },
    {
        "user": "Run a pip install command",
        "assistant_tool_calls": [
            {"name": "exec", "arguments": {"command": "pip install requests"}}
        ],
        "assistant_response": "Successfully installed requests"
    },
    {
        "user": "Run a Python virtual environment",
        "assistant_tool_calls": [
            {"name": "exec", "arguments": {"command": "source venv/bin/activate && python main.py"}}
        ],
        "assistant_response": "Running in virtual environment..."
    },
    {
        "user": "Run pytest tests",
        "assistant_tool_calls": [
            {"name": "exec", "arguments": {"command": "python -m pytest tests/ -v"}}
        ],
        "assistant_response": "Tests passed: 15 passed, 0 failed"
    },
    
    # Web operations
    {
        "user": "Search for the latest Python news",
        "assistant_tool_calls": [
            {"name": "web_search", "arguments": {"query": "Python programming language latest news 2024"}}
        ],
        "assistant_response": "Found 5 results about Python..."
    },
    {
        "user": "Fetch the nanopy documentation",
        "assistant_tool_calls": [
            {"name": "web_fetch", "arguments": {"url": "https://github.com/anomalyco/nanofoxy"}}
        ],
        "assistant_response": "Fetched the documentation page..."
    },
    
    # Subagents and A2A
    {
        "user": "What subagents are available?",
        "assistant_tool_calls": [
            {"name": "a2a", "arguments": {"action": "list"}}
        ],
        "assistant_response": "Available subagents:\n- coding_expert\n- websearch_expert\n- file_expert"
    },
    {
        "user": "Have the coding expert fix the bug",
        "assistant_tool_calls": [
            {"name": "a2a", "arguments": {"action": "call", "target": "coding_expert", "task": "Fix the bug in parser.py"}}
        ],
        "assistant_response": "Spawned coding_expert to fix the bug..."
    },
    {
        "user": "Spawn a coding expert to write a test",
        "assistant_tool_calls": [
            {"name": "spawn", "arguments": {"task": "Write unit tests for auth.py", "role": "coding-expert", "subagent_id": "coding_expert"}}
        ],
        "assistant_response": "Created background subagent to write tests..."
    },
    
    # Cron jobs
    {
        "user": "Show me the scheduled jobs",
        "assistant_tool_calls": [
            {"name": "cron", "arguments": {"action": "list"}}
        ],
        "assistant_response": "Scheduled jobs:\n- heartbeat (every 30 min)\n- daily_report (every 6 hours)"
    },
    {
        "user": "Add a new cron job to backup files every hour",
        "assistant_tool_calls": [
            {"name": "cron", "arguments": {"action": "add", "name": "backup", "schedule": "0 * * * *", "task": "Backup important files"}}
        ],
        "assistant_response": "Added cron job 'backup' to run every hour"
    },
    
    # Memory
    {
        "user": "Remember that I prefer dark mode",
        "assistant_tool_calls": [
            {"name": "memory", "arguments": {"action": "write", "content": "User prefers dark mode for UI", "topic": "preferences"}}
        ],
        "assistant_response": "Saved to memory: User prefers dark mode"
    },
    {
        "user": "What do you know about my preferences?",
        "assistant_tool_calls": [
            {"name": "memory", "arguments": {"action": "search", "query": "preferences"}}
        ],
        "assistant_response": "Found: User prefers dark mode"
    },
    
    # Messaging
    {
        "user": "Send a message to the user",
        "assistant_tool_calls": [
            {"name": "message", "arguments": {"content": "Task completed successfully!", "content_format": "markdown"}}
        ],
        "assistant_response": "Message sent to user"
    },
    
    # TTS
    {
        "user": "Speak this message",
        "assistant_tool_calls": [
            {"name": "speak", "arguments": {"text": "Hello, I am nanoFoxy!", "voice": "us_male"}}
        ],
        "assistant_response": "Converting text to speech..."
    },
    
    # Complex workflows
    {
        "user": "Find all Python files, then count lines in each",
        "assistant_tool_calls": [
            {"name": "glob", "arguments": {"pattern": "**/*.py"}},
        ],
        "assistant_response": "Found 15 files. Let me count the lines...",
        "expected_followup": [
            {"name": "exec", "arguments": {"command": "wc -l *.py"}}
        ]
    },
    {
        "user": "Read config, check if database is configured, then test connection",
        "assistant_tool_calls": [
            {"name": "read_file", "arguments": {"path": "config.json"}},
        ],
        "assistant_response": "Config shows database: postgres://localhost/db",
        "expected_followup": [
            {"name": "exec", "arguments": {"command": "python -c \"from db import test; test()\""}}
        ]
    }
]


def generate_conversation(user_msg: str, tool_calls: list, assistant_msg: str, tools: list = None) -> dict:
    """Generate a single conversation in SFT format."""
    conv = [
        {"role": "system", "content": SYSTEM_PROMPT.format(tool_list="- " + "\n- ".join([t["function"]["name"] for t in tools]))},
        {"role": "user", "content": user_msg},
    ]
    
    # Add tool calls if present
    for tc in tool_calls:
        conv.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "type": "function",
                    "id": f"call_{tc['name'][:8]}",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["arguments"])
                    }
                }
            ]
        })
        # Add tool result
        conv.append({
            "role": "tool",
            "tool_call_id": f"call_{tc['name'][:8]}",
            "content": assistant_msg if tool_calls.index(tc) == len(tool_calls) - 1 else "[Tool executed]"
        })
    
    # Add final response
    conv.append({"role": "assistant", "content": assistant_msg})
    
    return conv


def generate_sft_dataset(output_path: str = "/home/sir-airhard/.nanobot/workspace/sft_data_v2.jsonl"):
    """Generate the enhanced SFT dataset."""
    
    print("Generating enhanced SFT training dataset...")
    
    tools = get_tool_schema()
    print(f"  - Loaded {len(tools)} tool definitions")
    
    # Generate conversations
    conversations = []
    
    for example in LINUX_EXAMPLES:
        conv = generate_conversation(
            user_msg=example["user"],
            tool_calls=example["assistant_tool_calls"],
            assistant_msg=example["assistant_response"],
            tools=tools
        )
        conversations.append(conv)
        
        # Add follow-up if expected
        if "expected_followup" in example:
            for fu in example["expected_followup"]:
                conversations.append([
                    {"role": "system", "content": SYSTEM_PROMPT.format(tool_list="- " + "\n- ".join([t["function"]["name"] for t in tools]))},
                    {"role": "user", "content": example["user"]},
                    {"role": "assistant", "content": None, "tool_calls": [{"type": "function", "id": "call_xxx", "function": {"name": fu["name"], "arguments": json.dumps(fu["arguments"])}}]},
                    {"role": "tool", "tool_call_id": "call_xxx", "content": fu.get("result", "[Executed]")},
                    {"role": "assistant", "content": fu.get("final_response", "Done.")}
                ])
    
    # Write to JSONL
    print(f"  - Writing {len(conversations)} conversations...")
    with open(output_path, 'w') as f:
        for conv in conversations:
            f.write(json.dumps(conv, ensure_ascii=False) + '\n')
    
    # Also create a training-ready format with tools
    tools_path = output_path.replace('.jsonl', '_with_tools.jsonl')
    with open(tools_path, 'w') as f:
        for conv in conversations:
            record = {
                "conversations": conv
            }
            # Add tools to first message
            record["tools"] = tools
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"\nDataset generated successfully!")
    print(f"  - Total conversations: {len(conversations)}")
    print(f"  - Output: {output_path}")
    print(f"  - With tools: {tools_path}")
    
    return conversations


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    
    output = args.output or "/home/sir-airhard/.nanobot/workspace/sft_data_v2.jsonl"
    generate_sft_dataset(output)