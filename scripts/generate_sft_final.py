#!/usr/bin/env python3
"""Generate SFT training data for nanofoxy tool usage."""

import json
from pathlib import Path


SYSTEM_PROMPT = """You are nanoFoxy, an AI assistant with tools.

Tools available:
- read_file, write_file, edit_file
- list_dir, glob, grep
- exec (for system commands/scripts only)
- web_search, web_fetch
- message, spawn, a2a, cron
- memory, system, speak

Use appropriate tools. Use exec ONLY for shell commands and Python scripts, NOT file operations."""


def make_example(user, tool, args, result):
    return {"user": user, "tool": tool, "args": args, "result": result}


# File operations
FILE_OPS = [
    make_example("List /home", "list_dir", {"path": "/home"}, "Files listed"),
    make_example("Find .txt files", "glob", {"pattern": "**/*.txt"}, "Found files"),
    make_example("Find .py files", "glob", {"pattern": "**/*.py"}, "Found files"),
    make_example("Find .json files", "glob", {"pattern": "**/*.json"}, "Found files"),
    make_example("Find .yaml files", "glob", {"pattern": "**/*.yaml"}, "Found files"),
    make_example("Search code", "grep", {"pattern": "def ", "path": "."}, "Found"),
    make_example("Find TODOs", "grep", {"pattern": "TODO", "path": "src"}, "Found"),
    make_example("Find imports", "grep", {"pattern": "^import", "path": "."}, "Found"),
    make_example("Read README", "read_file", {"path": "README.md"}, "Content"),
    make_example("Read config", "read_file", {"path": "config.json"}, "Content"),
    make_example("Read first lines", "read_file", {"path": "file.txt", "limit": 10}, "Lines"),
    make_example("Edit file", "edit_file", {"path": "main.py", "oldString": "old", "newString": "new"}, "Edited"),
    make_example("Update version", "edit_file", {"path": "version.txt", "oldString": "1.0", "newString": "1.1"}, "Updated"),
    make_example("Create file", "write_file", {"path": "test.txt", "content": "hello"}, "Created"),
    make_example("Save config", "write_file", {"path": "config.json", "content": "{}"}, "Saved"),
    
    make_example("List current dir", "list_dir", {"path": "."}, "Listed"),
    make_example("List etc", "list_dir", {"path": "/etc"}, "Listed"),
    make_example("Glob *.py", "glob", {"pattern": "*.py"}, "Found"),
    make_example("Glob src/**", "glob", {"pattern": "src/**/*.py"}, "Found"),
    make_example("Grep pattern", "grep", {"pattern": "class ", "path": "src"}, "Found"),
    make_example("Grep function", "grep", {"pattern": "function", "path": "."}, "Found"),
    make_example("Read log", "read_file", {"path": "app.log"}, "Log content"),
    make_example("Read pyproject", "read_file", {"path": "pyproject.toml"}, "Config"),
    make_example("Add import", "edit_file", {"path": "app.py", "oldString": "import os", "newString": "import os\nimport json"}, "Added"),
    make_example("Write requirements", "write_file", {"path": "requirements.txt", "content": "requests\nflask"}, "Written"),
    make_example("Write README", "write_file", {"path": "README.md", "content": "# Project"}, "Written"),
    
    make_example("List dir", "list_dir", {"path": "data"}, "Data files"),
    make_example("Glob logs", "glob", {"pattern": "**/*.log"}, "Log files"),
    make_example("Glob csv", "glob", {"pattern": "**/*.csv"}, "CSV files"),
    make_example("Grep http", "grep", {"pattern": "http", "path": "."}, "URLs"),
    make_example("Grep email", "grep", {"pattern": "@", "path": "."}, "Emails"),
    make_example("Read dockerfile", "read_file", {"path": "Dockerfile"}, "Dockerfile"),
    make_example("Read gitignore", "read_file", {"path": ".gitignore"}, "Gitignore"),
    make_example("Change setting", "edit_file", {"path": "settings.py", "oldString": "DEBUG=False", "newString": "DEBUG=True"}, "Changed"),
    make_example("Add config", "write_file", {"path": "app.yaml", "content": "key: value"}, "Added"),
    make_example("Write env", "write_file", {"path": ".env", "content": "VAR=value"}, "Written"),
    
    make_example("Search in src", "grep", {"pattern": "TODO", "path": "src"}, "Found"),
    make_example("Find classes", "grep", {"pattern": "^class ", "path": "src"}, "Classes"),
    make_example("Find funcs", "grep", {"pattern": "^def ", "path": "src"}, "Functions"),
    make_example("Read lock", "read_file", {"path": "package-lock.json"}, "Lock"),
    make_example("Read env example", "read_file", {"path": ".env.example"}, "Example"),
    make_example("Edit port", "edit_file", {"path": "server.py", "oldString": "port=8000", "newString": "port=3000"}, "Port changed"),
    make_example("Edit host", "edit_file", {"path": "config.yaml", "oldString": "host: localhost", "newString": "host: 0.0.0.0"}, "Host changed"),
    make_example("Write dockerignore", "write_file", {".dockerignore": "", "content": "*.pyc\n__pycache__"}, "Written"),
    make_example("Write Makefile", "write_file", {"path": "Makefile", "content": "all:\n\techo done"}, "Written"),
    make_example("Write setup.py", "write_file", {"path": "setup.py", "content": "from setuptools import setup"}, "Written"),
    
    make_example("Find md files", "glob", {"pattern": "**/*.md"}, "Markdown"),
    make_example("Find sh files", "glob", {"pattern": "**/*.sh"}, "Scripts"),
    make_example("Find dockerfiles", "glob", {"pattern": "**/Dockerfile*"}, "Dockerfiles"),
    make_example("Grep print", "grep", {"pattern": "print\\(", "path": "."}, "Prints"),
    make_example("Grep query", "grep", {"pattern": "SELECT", "path": "src"}, "Queries"),
]

# System commands / Linux
SYSTEM_OPS = [
    make_example("Disk usage", "exec", {"command": "df -h"}, "Disk info"),
    make_example("Check memory", "exec", {"command": "free -h"}, "Memory"),
    make_example("List processes", "exec", {"command": "ps aux"}, "Processes"),
    make_example("Check CPU", "exec", {"command": "lscpu"}, "CPU info"),
    make_example("Show uptime", "exec", {"command": "uptime"}, "Uptime"),
    make_example("Current dir", "exec", {"command": "pwd"}, "Directory"),
    make_example("Who am I", "exec", {"command": "whoami"}, "User"),
    make_example("Hostname", "exec", {"command": "hostname"}, "Hostname"),
    make_example("Date/time", "exec", {"command": "date"}, "Date"),
    make_example("List services", "exec", {"command": "systemctl list-units --type=service --state=running"}, "Services"),
    
    make_example("Copy file", "exec", {"command": "cp a.txt b.txt"}, "Copied"),
    make_example("Move file", "exec", {"command": "mv a.txt b.txt"}, "Moved"),
    make_example("Remove file", "exec", {"command": "rm temp.txt"}, "Removed"),
    make_example("Make dir", "exec", {"command": "mkdir -p newdir"}, "Created"),
    make_example("Chmod", "exec", {"command": "chmod +x script.sh"}, "Permissions"),
    make_example("Check port", "exec", {"command": "ss -tuln"}, "Ports"),
    make_example("IP addr", "exec", {"command": "ip addr"}, "IP"),
    make_example("Ping test", "exec", {"command": "ping -c 1 google.com"}, "Ping"),
    make_example("Trace route", "exec", {"command": "traceroute google.com"}, "Trace"),
    make_example("DNS lookup", "exec", {"command": "nslookup example.com"}, "DNS"),
    
    make_example("Count lines", "exec", {"command": "wc -l file.txt"}, "Lines"),
    make_example("First lines", "exec", {"command": "head -5 file.txt"}, "First"),
    make_example("Last lines", "exec", {"command": "tail -5 file.txt"}, "Last"),
    make_example("Sort file", "exec", {"command": "sort file.txt"}, "Sorted"),
    make_example("Unique lines", "exec", {"command": "uniq file.txt"}, "Unique"),
    make_example("Find large files", "exec", {"command": "find / -size +100M"}, "Large files"),
    make_example("Disk inodes", "exec", {"command": "df -i"}, "Inodes"),
    make_example("Mount points", "exec", {"command": "mount"}, "Mounts"),
    make_example("Load avg", "exec", {"command": "uptime"}, "Load"),
    make_example("Kernel", "exec", {"command": "uname -r"}, "Kernel"),
    
    make_example("Top memory", "exec", {"command": "ps aux --sort=-%mem | head"}, "Top mem"),
    make_example("Top CPU", "exec", {"command": "ps aux --sort=-%cpu | head"}, "Top CPU"),
    make_example("Open files", "exec", {"command": "lsof"}, "Open files"),
    make_example("Netstat", "exec", {"command": "netstat -tuln"}, "Netstat"),
    make_example("Limits", "exec", {"command": "ulimit -a"}, "Limits"),
    
    make_example("List users", "exec", {"command": "cat /etc/passwd | cut -d: -1"}, "Users"),
    make_example("List groups", "exec", {"command": "groups"}, "Groups"),
    make_example("Permissions", "exec", {"command": "ls -la file"}, "Perms"),
    make_example("File stats", "exec", {"command": "stat file"}, "Stats"),
    make_example("File count", "exec", {"command": "ls -1 | wc -l"}, "Count"),
]

# Python scripts
PYTHON_OPS = [
    make_example("Run script", "exec", {"command": "python3 script.py"}, "Output"),
    make_example("Run with args", "exec", {"command": "python3 main.py --arg val"}, "Output"),
    make_example("Install package", "exec", {"command": "pip install requests"}, "Installed"),
    make_example("Install reqs", "exec", {"command": "pip install -r requirements.txt"}, "Installed"),
    make_example("Run pytest", "exec", {"command": "pytest tests/"}, "Tests"),
    make_example("Pytest verbose", "exec", {"command": "pytest -v"}, "Results"),
    make_example("Pytest coverage", "exec", {"command": "pytest --cov=. -v"}, "Coverage"),
    make_example("Run pylint", "exec", {"command": "pylint src/"}, "Lint"),
    make_example("Black check", "exec", {"command": "black --check src/"}, "Check"),
    make_example("Run flake8", "exec", {"command": "flake8 src/"}, "Flake8"),
    
    make_example("Pip list", "exec", {"command": "pip list"}, "Packages"),
    make_example("Pip freeze", "exec", {"command": "pip freeze"}, "Frozen"),
    make_example("Pip show", "exec", {"command": "pip show requests"}, "Show"),
    make_example("Python version", "exec", {"command": "python3 --version"}, "Version"),
    make_example("Py version", "exec", {"command": "python --version"}, "Version"),
    make_example("Create venv", "exec", {"command": "python3 -m venv .venv"}, "Created"),
    make_example("Upgrade pip", "exec", {"command": "pip install --upgrade pip"}, "Upgraded"),
    make_example("Uninstall", "exec", {"command": "pip uninstall -y pkg"}, "Uninstalled"),
    make_example("Pip audit", "exec", {"command": "pip audit"}, "Audit"),
    make_example("Wheel build", "exec", {"command": "python -m build"}, "Built"),
    
    make_example("Manage migrate", "exec", {"command": "python manage.py migrate"}, "Migrated"),
    make_example("Manage runserver", "exec", {"command": "python manage.py runserver"}, "Running"),
    make_example("Manage makemigrations", "exec", {"command": "python manage.py makemigrations"}, "Migrations"),
    make_example("Django version", "exec", {"command": "python -c 'import django; print(django.VERSION)'"}, "Version"),
    make_example("Startapp", "exec", {"command": "python manage.py startapp newapp"}, "Created"),
    make_example("Unittest", "exec", {"command": "python -m unittest discover"}, "Tests"),
    make_example("Coverage report", "exec", {"command": "coverage report"}, "Report"),
    make_example("Coverage html", "exec", {"command": "coverage html"}, "HTML"),
    make_example("Mypy check", "exec", {"command": "mypy src/"}, "Types"),
    make_example("Dev install", "exec", {"command": "pip install -e ."}, "Installed"),
    
    make_example("Parse JSON", "exec", {"command": "python3 -c 'import json; print(json.load(open(\"f.json\")))'"}, "Parsed"),
    make_example("Base64 encode", "exec", {"command": "python3 -c 'import base64; print(base64.b64encode(b\"t\"))'"}, "Encoded"),
    make_example("Hash string", "exec", {"command": "python3 -c 'import hashlib; print(hashlib.sha256(b\"t\").hexdigest())'"}, "Hash"),
    make_example("Timestamp", "exec", {"command": "python3 -c \"import time; print(int(time.time()))\""}, "Time"),
    make_example("JSON dumps", "exec", {"command": "python3 -c 'import json; print(json.dumps({\"a\":1}))'"}, "Dumped"),
    make_example("CSV read", "exec", {"command": "python3 -c 'import csv; print(list(csv.reader(open(\"f.csv\")))'"}, "CSV"),
    make_example("Datetime now", "exec", {"command": "python3 -c 'from datetime import datetime; print(datetime.now())'"}, "Now"),
    make_example("URL encode", "exec", {"command": "python3 -c 'import urllib.parse; print(urllib.parse.quote(\"a b\"))'"}, "Encoded"),
    make_example("UUID gen", "exec", {"command": "python3 -c 'import uuid; print(uuid.uuid4())'"}, "UUID"),
    make_example("Random", "exec", {"command": "python3 -c 'import random; print(random.randint(1,100))'"}, "Random"),
]

# Web operations
WEB_OPS = [
    make_example("Search Python", "web_search", {"query": "Python tutorial 2024"}, "Results"),
    make_example("Search Docker", "web_search", {"query": "Docker compose tutorial"}, "Results"),
    make_example("Search Git", "web_search", {"query": "Git commands cheat sheet"}, "Results"),
    make_example("Search AI", "web_search", {"query": "artificial intelligence news"}, "Results"),
    make_example("Search API", "web_search", {"query": "REST API design best practices"}, "Results"),
    make_example("Fetch GitHub", "web_fetch", {"url": "https://github.com"}, "Content"),
    make_example("Fetch docs", "web_fetch", {"url": "https://docs.python.org/3/"}, "Docs"),
    make_example("Fetch example", "web_fetch", {"url": "https://example.com"}, "Page"),
    make_example("Fetch README", "web_fetch", {"url": "https://github.com/anomalyco/nanofoxy/README.md"}, "README"),
    make_example("Fetch JSON", "web_fetch", {"url": "https://api.github.com/"}, "API"),
    
    make_example("Search Postgres", "web_search", {"query": "PostgreSQL tips"}, "Tips"),
    make_example("Search Linux", "web_search", {"query": "Linux tips tricks"}, "Tips"),
    make_example("Search regex", "web_search", {"query": "regex tutorial"}, "Tutorial"),
    make_example("Search SSH", "web_search", {"query": "SSH config tips"}, "Tips"),
    make_example("Search JSON", "web_search", {"query": "JSON formatter online"}, "Tools"),
    make_example("Search VIM", "web_search", {"query": "VIM commands cheat sheet"}, "Commands"),
    make_example("Search terminal", "web_search", {"query": "terminal productivity tips"}, "Tips"),
    make_example("Search cron", "web_search", {"query": "cron job examples"}, "Examples"),
    make_example("Search shell", "web_search", {"query": "bash scripting tutorial"}, "Tutorial"),
    make_example("Search Docker", "web_search", {"query": "Dockerfile best practices"}, "Tips"),
    
    make_example("Fetch Wikipedia", "web_fetch", {"url": "https://en.wikipedia.org/wiki/Python_(programming_language)"}, "Wiki"),
    {"user": "Fetch Hacker News", "tool": "web_fetch", "args": {"url": "https://news.ycombinator.com/"}, "result": "News"},
    {"user": "Search Kubernetes", "tool": "web_search", "args": {"query": "Kubernetes tutorial beginners"}, "result": "Results"},
    {"user": "Search security", "tool": "web_search", "args": {"query": "web security best practices 2024"}, "result": "Results"},
    {"user": "Search DevOps", "tool": "web_search", "args": {"query": "DevOps pipeline tools"}, "result": "Results"},
    {"user": "Search ML", "tool": "web_search", "args": {"query": "machine learning python tutorial"}, "result": "Results"},
    {"user": "Search testing", "tool": "web_search", "args": {"query": "pytest best practices"}, "result": "Results"},
    {"user": "Search database", "tool": "web_search", "args": {"query": "PostgreSQL vs MySQL comparison"}, "result": "Results"},
    {"user": "Search microservices", "tool": "web_search", "args": {"query": "microservices architecture patterns"}, "result": "Results"},
    {"user": "Search CI/CD", "tool": "web_search", "args": {"query": "GitHub Actions workflow examples"}, "result": "Results"},
]

# Subagents / A2A
SUBAGENT_OPS = [
    make_example("List subagents", "a2a", {"action": "list"}, "List"),
    make_example("A2A status", "a2a", {"action": "list"}, "Status"),
    make_example("Discover code", "a2a", {"action": "discover", "capabilities": ["code"]}, "Found"),
    make_example("Discover web", "a2a", {"action": "discover", "capabilities": ["web"]}, "Found"),
    make_example("Discover files", "a2a", {"action": "discover", "capabilities": ["file"]}, "Found"),
    make_example("Call coding", "a2a", {"action": "call", "target": "coding_expert", "task": "Write test"}, "Called"),
    make_example("Call web", "a2a", {"action": "call", "target": "websearch_expert", "task": "Find info"}, "Called"),
    make_example("Call file", "a2a", {"action": "call", "target": "file_handel_expert", "task": "Organize"}, "Called"),
    make_example("Forward task", "a2a", {"action": "forward", "task": "Research this"}, "Forwarded"),
    
    make_example("Spawn coding", "spawn", {"task": "Write tests", "role": "coding-expert", "subagent_id": "coding_expert"}, "Spawned"),
    make_example("Spawn web", "spawn", {"task": "Search info", "role": "websearch-expert", "subagent_id": "websearch_expert"}, "Spawned"),
    make_example("Spawn info", "spawn", {"task": "Gather info", "role": "information-expert", "subagent_id": "information_expert"}, "Spawned"),
    make_example("Spawn file", "spawn", {"task": "Organize files", "role": "file-handel-expert", "subagent_id": "file_handel_expert"}, "Spawned"),
    make_example("Spawn bg", "spawn", {"task": "Long task"}, "Spawned"),
    
    make_example("Find writing", "a2a", {"action": "discover", "capabilities": ["writing"]}, "Found"),
    make_example("Find analysis", "a2a", {"action": "discover", "capabilities": ["analysis"]}, "Found"),
    make_example("Call info", "a2a", {"action": "call", "target": "information_expert", "task": "Summarize"}, "Called"),
    make_example("Spawn analyze", "spawn", {"task": "Analyze data", "role": "information-expert"}, "Spawned"),
    make_example("Delegate", "a2a", {"action": "delegate", "agents": ["c", "w"], "task": "Task"}, "Delegated"),
]

# Cron jobs
CRON_OPS = [
    make_example("List jobs", "cron", {"action": "list"}, "Jobs"),
    make_example("Show jobs", "cron", {"action": "list"}, "Jobs"),
    make_example("Add backup", "cron", {"action": "add", "name": "backup", "schedule": "0 2 * * *", "task": "Backup"}, "Added"),
    make_example("Add report", "cron", {"action": "add", "name": "report", "schedule": "0 9 * * *", "task": "Report"}, "Added"),
    make_example("Add check", "cron", {"action": "add", "name": "check", "schedule": "0 * * * *", "task": "Check"}, "Added"),
    make_example("Disable job", "cron", {"action": "disable", "name": "backup"}, "Disabled"),
    make_example("Enable job", "cron", {"action": "enable", "name": "backup"}, "Enabled"),
    make_example("Remove job", "cron", {"action": "remove", "name": "old"}, "Removed"),
    make_example("Add cleanup", "cron", {"action": "add", "name": "cleanup", "schedule": "0 3 * * 0", "task": "Clean"}, "Added"),
    make_example("Add monitor", "cron", {"action": "add", "name": "monitor", "schedule": "*/15 * * * *", "task": "Monitor"}, "Added"),
    
    make_example("Add archive", "cron", {"action": "add", "name": "archive", "schedule": "0 2 1 * *", "task": "Archive"}, "Added"),
    make_example("Add sync", "cron", {"action": "add", "name": "sync", "schedule": "0 */6 * * *", "task": "Sync"}, "Added"),
    make_example("Add notify", "cron", {"action": "add", "name": "notify", "schedule": "0 9,17 * * *", "task": "Notify"}, "Added"),
    make_example("Add rotate", "cron", {"action": "add", "name": "rotate", "schedule": "0 0 * * *", "task": "Rotate"}, "Added"),
    make_example("Add disk check", "cron", {"action": "add", "name": "disk", "schedule": "0 * * * *", "task": "Disk check"}, "Added"),
]

# Memory
MEMORY_OPS = [
    make_example("Save preference", "memory", {"action": "write", "content": "Dark mode", "topic": "preferences"}, "Saved"),
    make_example("Save fact", "memory", {"action": "write", "content": "Uses Python 3.12", "topic": "project"}, "Saved"),
    make_example("Save name", "memory", {"action": "write", "content": "Name is John", "topic": "user"}, "Saved"),
    make_example("Search project", "memory", {"action": "search", "query": "project"}, "Found"),
    make_example("Search prefs", "memory", {"action": "search", "query": "preferences"}, "Found"),
    make_example("Search work", "memory", {"action": "search", "query": "work"}, "Found"),
    make_example("Recall project", "memory", {"action": "recall", "topic": "project"}, "Recall"),
    make_example("Recall user", "memory", {"action": "recall", "topic": "user"}, "Recall"),
    make_example("Write note", "memory", {"action": "write", "content": "Complete by Friday", "topic": "tasks"}, "Saved"),
    make_example("Write learning", "memory", {"action": "write", "content": "New pattern", "topic": "learning"}, "Saved"),
    
    make_example("Search notes", "memory", {"action": "search", "query": "notes"}, "Found"),
    make_example("Search meetings", "memory", {"action": "search", "query": "meeting"}, "Found"),
    make_example("Search knowledge", "memory", {"action": "search", "query": "knowledge"}, "Found"),
    make_example("Save contact", "memory", {"action": "write", "content": "john@email.com", "topic": "contacts"}, "Saved"),
    make_example("Save meeting", "memory", {"action": "write", "content": "Meeting at 3pm", "topic": "meetings"}, "Saved"),
]

# Messaging
MESSAGING = [
    make_example("Send message", "message", {"content": "Done!", "content_format": "markdown"}, "Sent"),
    make_example("Notify", "message", {"content": "Finished"}, "Sent"),
    make_example("Format msg", "message", {"content": "**Important**", "content_format": "markdown"}, "Sent"),
    make_example("Plain text", "message", {"content": "Simple message", "content_format": "text"}, "Sent"),
    make_example("HTML msg", "message", {"content": "<b>Bold</b>", "content_format": "html"}, "Sent"),
    make_example("Status", "message", {"content": "Status: OK"}, "Sent"),
    make_example("Alert", "message", {"content": "Warning: Issue"}, "Sent"),
    make_example("Success", "message", {"content": "Success!"}, "Sent"),
    make_example("Emoji", "message", {"content": "✅ Complete"}, "Sent"),
    make_example("List", "message", {"content": "- Item 1\n- Item 2"}, "Sent"),
    make_example("Code", "message", {"content": "```python\nx=1\n```"}, "Sent"),
    make_example("Link", "message", {"content": "Check [this](url)"}, "Sent"),
    make_example("Confirm", "message", {"content": "Confirmed ✓"}, "Sent"),
    make_example("Remind", "message", {"content": "Reminder: Meeting"}, "Sent"),
    make_example("Summary", "message", {"content": "Summary:\n- Done\n- Done"}, "Sent"),
]

# System monitoring
SYSTEM_MON = [
    {"user": "CPU info", "tool": "system", "args": {"info": "cpu"}, "result": "CPU"},
    {"user": "Memory info", "tool": "system", "args": {"info": "memory"}, "result": "Memory"},
    {"user": "Disk info", "tool": "system", "args": {"info": "disk"}, "result": "Disk"},
    {"user": "Processes", "tool": "system", "args": {"info": "processes"}, "result": "Processes"},
    {"user": "Network", "tool": "system", "args": {"info": "network"}, "result": "Network"},
    {"user": "CPU usage", "tool": "system", "args": {"info": "cpu"}, "result": "CPU"},
    {"user": "RAM usage", "tool": "system", "args": {"info": "memory"}, "result": "RAM"},
    {"user": "Storage", "tool": "system", "args": {"info": "disk"}, "result": "Storage"},
    {"user": "Running tasks", "tool": "system", "args": {"info": "processes"}, "result": "Tasks"},
    {"user": "Network status", "tool": "system", "args": {"info": "network"}, "result": "Status"},
    {"user": "Health check", "tool": "system", "args": {"info": "cpu"}, "result": "Health"},
    {"user": "System load", "tool": "system", "args": {"info": "cpu"}, "result": "Load"},
    {"user": "Memory status", "tool": "system", "args": {"info": "memory"}, "result": "Status"},
    {"user": "Disk status", "tool": "system", "args": {"info": "disk"}, "result": "Status"},
    {"user": "Full overview", "tool": "system", "args": {"info": "cpu"}, "result": "Overview"},
]


def generate():
    """Generate the dataset."""
    categories = [
        ("file_operations", FILE_OPS),
        ("system_commands", SYSTEM_OPS),
        ("python_scripts", PYTHON_OPS),
        ("web_operations", WEB_OPS),
        ("subagents", SUBAGENT_OPS),
        ("cron_jobs", CRON_OPS),
        ("memory", MEMORY_OPS),
        ("messaging", MESSAGING),
        ("system_monitoring", SYSTEM_MON),
    ]
    
    total = sum(len(ex) for _, ex in categories)
    print(f"Generating {total} examples...")
    
    for name, examples in categories:
        print(f"  {name}: {len(examples)}")
    
    # Generate JSONL
    output = "/home/sir-airhard/.nanobot/workspace/sft_data_v3.jsonl"
    with open(output, 'w') as f:
        for category, examples in categories:
            for ex in examples:
                if isinstance(ex, dict):
                    user = ex.get("user", "")
                    tool = ex.get("tool", "")
                    args = ex.get("args", {})
                    result = ex.get("result", "")
                else:
                    user = ex.user
                    tool = ex.tool
                    args = ex.args
                    result = ex.result
                
                conv = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": None, "tool_calls": [{
                        "type": "function",
                        "id": "call_xxx",
                        "function": {"name": tool, "arguments": json.dumps(args)}
                    }]},
                    {"role": "tool", "tool_call_id": "call_xxx", "content": result},
                    {"role": "assistant", "content": result}
                ]
                f.write(json.dumps(conv, ensure_ascii=False) + "\n")
    
    print(f"\nWritten to {output}")
    
    # Summary
    print("\nSummary:")
    for name, examples in categories:
        print(f"  {name}: {len(examples)}")
    print(f"  TOTAL: {total}")


if __name__ == "__main__":
    generate()