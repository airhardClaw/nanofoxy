#!/usr/bin/env python3
"""Generate comprehensive SFT training data for nanofoxy tool usage.

45 examples per category (15 new × 3 = 45 total), covering:
- File operations
- System commands / Linux
- Python scripts
- Web operations
- Subagents / A2A
- Cron jobs
- Memory
- Messaging
- Combined workflows
"""

import json
import sys
from pathlib import Path


SYSTEM_PROMPT = """You are nanoFoxy, a helpful AI assistant with tools.

Available tools:
{tool_list}

Guidelines:
1. Use appropriate tools for each task
2. Use exec ONLY for system commands, NOT for file operations
3. Use read_file/write_file/edit_file for file operations
4. Check tool results before proceeding
5. Report results clearly to user"""


TOOL_SCHEMA = [
    {"name": "read_file", "params": {"path": "string", "offset": "int?", "limit": "int?"}},
    {"name": "write_file", "params": {"path": "string", "content": "string"}},
    {"name": "edit_file", "params": {"path": "string", "oldString": "string", "newString": "string"}},
    {"name": "list_dir", "params": {"path": "string"}},
    {"name": "glob", "params": {"pattern": "string", "path": "string?"}},
    {"name": "grep", "params": {"pattern": "string", "path": "string"}},
    {"name": "exec", "params": {"command": "string", "timeout": "int?"}},
    {"name": "web_search", "params": {"query": "string"}},
    {"name": "web_fetch", "params": {"url": "string"}},
    {"name": "message", "params": {"content": "string", "content_format": "string?"}},
    {"name": "spawn", "params": {"task": "string", "role": "string?", "subagent_id": "string?"}},
    {"name": "a2a", "params": {"action": "string", "target": "string?", "task": "string?"}},
    {"name": "cron", "params": {"action": "string", "name": "string?", "schedule": "string?", "task": "string?"}},
    {"name": "memory", "params": {"action": "string", "query": "string?", "content": "string?", "topic": "string?"}},
    {"name": "system", "params": {"info": "string"}},
    {"name": "speak", "params": {"text": "string", "voice": "string?"}},
]


# ============ FILE OPERATIONS (45) ============
FILE_OPS = [
    {"user": "Show files in /home directory", "tool": "list_dir", "args": {"path": "/home"}, "result": "home/"},
    {"user": "Find all .txt files", "tool": "glob", "args": {"pattern": "**/*.txt"}, "result": "Found .txt files"},
    {"user": "Find all .json files in config", "tool": "glob", "args": {"pattern": "config/**/*.json"}, "result": "Found JSON files"},
    {"user": "Find all .py files in src", "tool": "glob", "args": {"pattern": "src/**/*.py"}, "result": "Found Python files"},
    {"user": "Find all YAML config files", "tool": "glob", "args": {"pattern": "**/*.yaml"}, "result": "Found YAML files"},
    {"user": "Search for 'function' in code", "tool": "grep", "args": {"pattern": "def function", "path": "."}, "result": "Found matches"},
    {"user": "Find all 'TODO' comments", "tool": "grep", "args": {"pattern": "TODO", "path": "src"}, "result": "Found TODO items"},
    {"user": "Find all imports in Python files", "tool": "grep", "args": {"pattern": "^import |^from ", "path": "."}, "result": "Found imports"},
    {"user": "Count lines in all .py files", "tool": "glob", "args": {"pattern": "**/*.py"}, "result": "Files found"},
    {"user": "Show me the README", "tool": "read_file", "args": {"path": "README.md"}, "result": "README content"},
    {"user": "Read the first 10 lines of log", "tool": "read_file", "args": {"path": "app.log", "limit": 10}, "result": "First 10 lines"},
    {"user": "Read from line 100", "tool": "read_file", "args": {"path": "file.py", "offset": 100}, "result": "Content from line 100"},
    {"user": "Check what's in the config folder", "tool": "list_dir", "args": {"path": "config"}, "result": "Config files"},
    {"user": "Find all shell scripts", "tool": "glob", "args": {"pattern": "**/*.sh"}, "result": "Shell scripts found"},
    {"user": "Find all markdown files", "tool": "glob", "args": {"pattern": "**/*.md"}, "result": "Markdown files"},

    # Edit examples
    {"user": "Rename 'old' to 'new' in code", "tool": "edit_file", "args": {"path": "main.py", "oldString": "old_value", "newString": "new_value"}, "result": "Edited file"},
    {"user": "Update the version number", "tool": "edit_file", "args": {"path": "version.txt", "oldString": "1.0.0", "newString": "1.1.0"}, "result": "Version updated"},
    {"user": "Change the import path", "tool": "edit_file", "args": {"path": "app.py", "oldString": "from old.path", "newString": "from new.path"}, "result": "Import changed"},
    {"user": "Enable debug mode", "tool": "edit_file", "args": {"path": "config.py", "oldString": "DEBUG = False", "newString": "DEBUG = True"}, "result": "Debug enabled"},
    {"user": "Add the new feature flag", "tool": "edit_file", "args": {"path": "features.py", "oldString": "# Features", "newString": "# Features\nENABLE_NEW = True"}, "result": "Feature added"},

    # Write examples
    {"user": "Create a requirements.txt", "tool": "write_file", "args": {"path": "requirements.txt", "content": "requests\nflask\ndjango"}, "result": "Created requirements.txt"},
    {"user": "Save the configuration", "tool": "write_file", "args": {"path": "config.json", "content": "{\"debug\": true}"}, "result": "Config saved"},
    {"user": "Create a .gitignore file", "tool": "write_file", "args": {"path": ".gitignore", "content": "*.pyc\n__pycache__\n.venv"}, "result": "Created .gitignore"},
    {"user": "Write the test data", "tool": "write_file", "args": {"path": "test_data.json", "content": "[]"}, "result": "Test data written"},
    {"user": "Create a simple README", "tool": "write_file", "args": {"path": "README.md", "content": "# My Project\n\nThis is my project."}, "result": "README created"},

    # Glob variations
    {"user": "Find all config files", "tool": "glob", "args": {"pattern": "**/config*"}}, "result": "Config files found"},
    {"user": "Find all test files", "tool": "glob", "args": {"pattern": "tests/**/*.py"}}, "result": "Test files"},
    {"user": "Find all Docker files", "tool": "glob", "args": {"pattern": "**/Dockerfile*"}}, "result": "Docker files"},
    {"user": "Find all .env files", "tool": "glob", "args": {"pattern": "**/.env*"}}, "result": "Env files"},
    {"user": "Find all CSV data files", "tool": "glob", "args": {"pattern": "**/*.csv"}}, "result": "CSV files"},

    # Grep variations
    {"user": "Find all function definitions", "tool": "grep", "args": {"pattern": "^def ", "path": "src"}, "result": "Functions found"},
    {"user": "Find all class definitions", "tool": "grep", "args": {"pattern": "^class ", "path": "src"}, "result": "Classes found"},
    {"user": "Find all print statements", "tool": "grep", "args": {"pattern": "print\\(", "path": "."}, "result": "Print statements"},
    {"user": "Find all URLs in code", "tool": "grep", "args": {"pattern": "https?://", "path": "."}, "result": "URLs found"},
    {"user": "Find all database queries", "tool": "grep", "args": {"pattern": "SELECT|INSERT|UPDATE", "path": "src"}, "result": "DB queries"},

    # Read variations
    {"user": "Show the package.json", "tool": "read_file", "args": {"path": "package.json"}}, "result": "package.json content"},
    {"user": "Read the lock file", "tool": "read_file", "args": {"path": "package-lock.json"}}, "result": "Lock file content"},
    {"user": "Read the Python version", "tool": "read_file", "args": {"path": "pyproject.toml"}}, "result": "Pyproject content"},
    {"user": "Read the docker compose", "tool": "read_file", "args": {"path": "docker-compose.yml"}}, "result": "Docker compose"},
    {"user": "Read the env example", "tool": "read_file", "args": {"path": ".env.example"}}, "result": "Env example"},
]


# ============ SYSTEM COMMANDS / LINUX (45) ============
SYSTEM_CMDS = [
    {"user": "Check disk space", "tool": "exec", "args": {"command": "df -h"}, "result": "Disk usage"},
    {"user": "Check disk usage for home", "tool": "exec", "args": {"command": "df -h /home"}, "result": "Home disk usage"},
    {"user": "Show current directory", "tool": "exec", "args": {"command": "pwd"}, "result": "/current/path"},
    {"user": "Show current date and time", "tool": "exec", "args": {"command": "date"}, "result": "Current date"},
    {"user": "Check system uptime", "tool": "exec", "args": {"command": "uptime"}, "result": "System uptime"},
    {"user": "Show memory info", "tool": "exec", "args": {"command": "free -h"}, "result": "Memory info"},
    {"user": "Check CPU info", "tool": "exec", "args": {"command": "lscpu"}, "result": "CPU details"},
    {"user": "Show hostname", "tool": "exec", "args": {"command": "hostname"}, "result": "hostname"},
    {"user": "Check current user", "tool": "exec", "args": {"command": "whoami"}, "result": "username"},
    {"user": "List running services", "tool": "exec", "args": {"command": "systemctl list-units --type=service --state=running"}, "result": "Services"},
    {"user": "Check service status", "tool": "exec", "args": {"command": "systemctl status nginx"}, "result": "Service status"},
    {"user": "Show system journal", "tool": "exec", "args": {"command": "journalctl -n 20"}, "result": "Recent logs"},
    {"user": "Check network connections", "tool": "exec", "args": {"command": "ss -tuln"}, "result": "Network ports"},
    {"user": "Show IP addresses", "tool": "exec", "args": {"command": "ip addr show"}, "result": "IP addresses"},
    {"user": "Check DNS resolution", "tool": "exec", "args": {"command": "nslookup google.com"}, "result": "DNS result"},

    {"user": "List all users", "tool": "exec", "args": {"command": "cat /etc/passwd | cut -d: -1"}, "result": "Users list"},
    {"user": "Show group memberships", "tool": "exec", "args": {"command": "groups"}, "result": "Groups"},
    {"user": "Check file permissions", "tool": "exec", "args": {"command": "ls -la script.sh"}, "result": "Permissions"},
    {"user": "Find large files", "tool": "exec", "args": {"command": "find / -size +100M"}, "result": "Large files"},
    {"user": "Check file ownership", "tool": "exec", "args": {"command": "stat file.txt"}, "result": "File stats"},
    {"user": "Count files in directory", "tool": "exec", "args": {"command": "ls -1 | wc -l"}, "result": "File count"},
    {"user": "Check disk inodes", "tool": "exec", "args": {"command": "df -i"}, "result": "Inode usage"},
    {"user": "Show mount points", "tool": "exec", "args": {"command": "mount | column -t"}, "result": "Mounts"},
    {"user": "Check load average", "tool": "exec", "args": {"command": "uptime"}, "result": "Load average"},
    {"user": "Show kernel version", "tool": "exec", "args": {"command": "uname -r"}, "result": "Kernel version"},

    # File operations via exec
    {"user": "Copy a file", "tool": "exec", "args": {"command": "cp file.txt backup.txt"}, "result": "Copied"},
    {"user": "Move a file", "tool": "exec", "args": {"command": "mv old.txt new.txt"}, "result": "Moved"},
    {"user": "Remove a file", "tool": "exec", "args": {"command": "rm temp.txt"}, "result": "Removed"},
    {"user": "Create directory", "tool": "exec", "args": {"command": "mkdir -p new_folder"}, "result": "Created"},
    {"user": "Change permissions", "tool": "exec", "args": {"command": "chmod +x script.sh"}, "result": "Permissions changed"},

    # Text processing
    {"user": "Count lines in file", "tool": "exec", "args": {"command": "wc -l file.txt"}, "result": "Line count"},
    {"user": "Show first 5 lines", "tool": "exec", "args": {"command": "head -5 file.txt"}, "result": "First 5 lines"},
    {"user": "Show last 5 lines", "tool": "exec", "args": {"command": "tail -5 file.txt"}, "result": "Last 5 lines"},
    {"user": "Sort unique lines", "tool": "exec", "args": {"command": "sort file.txt | uniq"}, "result": "Sorted unique"},
    {"user": "Count words", "tool": "exec", "args": {"command": "wc -w file.txt"}, "result": "Word count"},

    # System monitoring
    {"user": "Top processes by memory", "tool": "exec", "args": {"command": "ps aux --sort=-%mem | head -10"}, "result": "Top memory processes"},
    {"user": "Top processes by CPU", "tool": "exec", "args": {"command": "ps aux --sort=-%cpu | head -10"}, "result": "Top CPU processes"},
    {"user": "Check open files", "tool": "exec", "args": {"command": "lsof"}, "result": "Open files"},
    {"user": "Show network stats", "tool": "exec", "args": {"command": "netstat -tuln"}, "result": "Network stats"},
    {"user": "Check system limits", "tool": "exec", "args": {"command": "ulimit -a"}, "result": "System limits"},
]


# ============ PYTHON SCRIPTS (45) ============
PYTHON_OPS = [
    {"user": "Run Python script", "tool": "exec", "args": {"command": "python3 script.py"}, "result": "Script output"},
    {"user": "Run with arguments", "tool": "exec", "args": {"command": "python3 main.py --input data.json"}, "result": "Output"},
    {"user": "Install package", "tool": "exec", "args": {"command": "pip install requests"}, "result": "Installed"},
    {"user": "Install dev package", "tool": "exec", "args": {"command": "pip install -r requirements-dev.txt"}, "result": "Installed dev deps"},
    {"user": "Run pytest", "tool": "exec", "args": {"command": "python -m pytest tests/"}, "result": "Test results"},
    {"user": "Run specific test", "tool": "exec", "args": {"command": "python -m pytest tests/test_main.py -v"}, "result": "Test output"},
    {"user": "Run pytest with coverage", "tool": "exec", "args": {"command": "pytest --cov=. -v"}, "result": "Coverage report"},
    {"user": "Run pylint", "tool": "exec", "args": {"command": "pylint src/"}, "result": "Linting results"},
    {"user": "Run black formatter", "tool": "exec", "args": {"command": "black --check src/"}, "result": "Formatter check"},
    {"user": "Run flake8", "tool": "exec", "args": {"command": "flake8 src/"}, "result": "Flake8 results"},
    {"user": "Activate venv", "tool": "exec", "args": {"command": "source venv/bin/activate && pip list"}, "result": "Venv packages"},
    {"user": "Check Python version", "tool": "exec", "args": {"command": "python3 --version"}, "result": "Python version"},
    {"user": "Show installed packages", "tool": "exec", "args": {"command": "pip list"}, "result": "Packages list"},
    {"user": "Show pip freeze", "tool": "exec", "args": {"command": "pip freeze"}, "result": "Pip freeze"},
    {"user": "Check package version", "tool": "exec", "args": {"command": "pip show requests"}, "result": "Package info"},

    # Script execution
    {"user": "Run manage.py migrate", "tool": "exec", "args": {"command": "python manage.py migrate"}, "result": "Migration done"},
    {"user": "Run Django server", "tool": "exec", "args": {"command": "python manage.py runserver"}, "result": "Server running"},
    {"user": "Create Django app", "tool": "exec", "args": {"command": "python manage.py startapp newapp"}, "result": "App created"},
    {"user": "Make migrations", "tool": "exec", "args": {"command": "python manage.py makemigrations"}, "result": "Migrations made"},
    {"user": "Check Django version", "tool": "exec", "args": {"command": "python -c 'import django; print(django.VERSION)'"}, "result": "Django version"},
    
    # Virtual environments
    {"user": "Create venv", "tool": "exec", "args": {"command": "python3 -m venv .venv"}, "result": "Venv created"},
    {"user": "Upgrade pip", "tool": "exec", "args": {"command": "pip install --upgrade pip"}, "result": "Pip upgraded"},
    {"user": "List site-packages", "tool": "exec", "args": {"command": "python -c 'import site; print(site.getsitepackages())'"}, "result": "Site packages"},
    {"user": "Uninstall package", "tool": "exec", "args": {"command": "pip uninstall -y requests"}, "result": "Uninstalled"},
    
    # Testing tools
    {"user": "Run unittest", "tool": "exec", "args": {"command": "python -m unittest discover"}, "result": "Unit test results"},
    {"user": "Run coverage report", "tool": "exec", "args": {"command": "coverage report"}, "result": "Coverage report"},
    {"user": "Generate HTML coverage", "tool": "exec", "args": {"command": "coverage html"}, "result": "HTML generated"},
    {"user": "Run mypy type check", "tool": "exec", "args": {"command": "mypy src/"}, "result": "Type check results"},
    
    # Build / Package
    {"user": "Build wheel", "tool": "exec", "args": {"command": "python -m build"}, "result": "Wheel built"},
    {"user": "Install in dev mode", "tool": "exec", "args": {"command": "pip install -e ."}, "result": "Installed in dev mode"},
    {"user": "Upload to PyPI", "tool": "exec", "args": {"command": "twine upload dist/*"}, "result": "Uploaded to PyPI"},
    {"user": "Check for security issues", "tool": "exec", "args": {"command": "pip audit"}, "result": "Audit results"},
    
    # Python one-liners
    {"user": "Parse JSON", "tool": "exec", "args": {"command": "python3 -c 'import json; print(json.load(open(\"file.json\"))'"}, "result": "JSON parsed"},
    {"user": "Base64 encode", "tool": "exec", "args": {"command": "python3 -c 'import base64; print(base64.b64encode(b\"text\").decode())'"}, "result": "Base64 encoded"},
    {"user": "Hash a string", "tool": "exec", "args": {"command": "python3 -c 'import hashlib; print(hashlib.sha256(b\"text\").hexdigest())'"}, "result": "SHA256 hash"},
    {"user": "Get current timestamp", "tool": "exec", "args": {"command": "python3 -c 'import time; print(int(time.time()))'"}, "result": "Timestamp"},
]


# ============ WEB OPERATIONS (30) ============
WEB_OPS = [
    {"user": "Search for Python tutorials", "tool": "web_search", "args": {"query": "Python programming tutorial 2024"}, "result": "Search results"},
    {"user": "Search for Docker documentation", "tool": "web_search", "args": {"query": "Docker compose documentation"}, "result": "Docs found"},
    {"user": "Search for Git commands", "tool": "web_search", "args": {"query": "Git command line cheat sheet"}, "result": "Commands found"},
    {"user": "Find latest tech news", "tool": "web_search", "args": {"query": "latest technology news 2024"}, "result": "Tech news"},
    {"user": "Search for API design best practices", "tool": "web_search", "args": {"query": "REST API design best practices"}, "result": "Best practices"},
    {"user": "Find the nanofoxy GitHub", "tool": "web_fetch", "args": {"url": "https://github.com/anomalyco/nanofoxy"}, "result": "Page content"},
    {"user": "Fetch Python documentation", "tool": "web_fetch", "args": {"url": "https://docs.python.org/3/"}, "result": "Python docs"},
    {"user": "Fetch Docker docs", "tool": "web_fetch", "args": {"url": "https://docs.docker.com/"}, "result": "Docker docs"},
    {"user": "Fetch the README", "tool": "web_fetch", "args": {"url": "https://github.com/anomalyco/nanofoxy/README.md"}, "result": "README content"},
    {"user": "Check a webpage", "tool": "web_fetch", "args": {"url": "https://example.com"}, "result": "Webpage content"},
    
    # More search examples
    {"user": "Search for PostgreSQL tips", "tool": "web_search", "args": {"query": "PostgreSQL performance tips"}}, "result": "Postgres tips"},
    {"user": "Search for Linux commands", "tool": "web_search", "args": {"query": "Linux command line tips tricks"}}, "result": "Linux tips"},
    {"user": "Search for regex guide", "tool": "web_search", "args": {"query": "regex tutorial regular expressions guide"}}, "result": "Regex guide"},
    {"user": "Search for SSH config", "tool": "web_search", "args": {"query": "SSH config best practices"}}, "result": "SSH tips"},
    {"user": "Search for JSON tools", "tool": "web_search", "args": {"query": "JSON formatter validator online"}}, "result": "JSON tools"},
    {"user": "Search for VIM commands", "tool": "web_search", "args": {"query": "VIM cheat sheet commands"}}, "result": "VIM commands"},
    {"user": "Search for terminal tips", "tool": "web_search", "args": {"query": "Linux terminal productivity tips"}}, "result": "Terminal tips"},
    {"user": "Search for environment variables", "tool": "web_search", "args": {"query": "environment variables tutorial"}}, "result": "Env var guide"},
    {"user": "Search for cron guide", "tool": "web_search", "args": {"query": "cron job tutorial examples"}}, "result": "Cron guide"},
    {"user": "Search for shell scripting", "tool": "web_search", "args": {"query": "bash shell scripting tutorial"}}, "result": "Shell scripting"},
    
    # More fetch examples
    {"user": "Fetch news article", "tool": "web_fetch", "args": {"url": "https://news.ycombinator.com/"}}, "result": "News content"},
    {"user": "Fetch Wikipedia page", "tool": "web_fetch", "args": {"url": "https://en.wikipedia.org/wiki/Python_(programming_language)"}}, "result": "Wikipedia"},
    {"user": "Fetch JSON API", "tool": "web_fetch", "args": {"url": "https://api.github.com/"}}, "result": "GitHub API"},
    {"user": "Fetch documentation", "tool": "web_fetch", "args": {"url": "https://docs.python.org/3/library/index.html"}}, "result": "Docs"},
    {"user": "Check website status", "tool": "web_fetch", "args": {"url": "https://httpbin.org/get"}}, "result": "HTTP response"},
]


# ============ SUBAGENTS / A2A (30) ============
SUBAGENT_OPS = [
    {"user": "List all subagents", "tool": "a2a", "args": {"action": "list"}}, "result": "Subagents list"},
    {"user": "Show A2A server status", "tool": "a2a", "args": {"action": "list"}}, "result": "Server status"},
    {"user": "Discover coding agents", "tool": "a2a", "args": {"action": "discover", "capabilities": ["code"]}}, "result": "Coding agents"},
    {"user": "Discover web search agents", "tool": "a2a", "args": {"action": "discover", "capabilities": ["web"]}}, "result": "Web agents"},
    {"user": "Find agents with file capability", "tool": "a2a", "args": {"action": "discover", "capabilities": ["file"]}}, "result": "File agents"},
    {"user": "Call coding expert", "tool": "a2a", "args": {"action": "call", "target": "coding_expert", "task": "Write a test"}}, "result": "Coding expert called"},
    {"user": "Call web search expert", "tool": "a2a", "args": {"action": "call", "target": "websearch_expert", "task": "Find info"}}, "result": "Web expert called"},
    {"user": "Call file expert", "tool": "a2a", "args": {"action": "call", "target": "file_handel_expert", "task": "Organize files"}}, "result": "File expert called"},
    {"user": "Forward task to expert", "tool": "a2a", "args": {"action": "forward", "task": "Research this"}}, "result": "Task forwarded"},
    
    # Spawn new subagents
    {"user": "Spawn a coding expert", "tool": "spawn", "args": {"task": "Write unit tests", "role": "coding-expert", "subagent_id": "coding_expert"}}, "result": "Coding expert spawned"},
    {"user": "Spawn a web searcher", "tool": "spawn", "args": {"task": "Search for information", "role": "websearch-expert", "subagent_id": "websearch_expert"}}, "result": "Web searcher spawned"},
    {"user": "Spawn an information gatherer", "tool": "spawn", "args": {"task": "Gather info on topic", "role": "information-expert", "subagent_id": "information_expert"}}, "result": "Info gatherer spawned"},
    {"user": "Spawn a file handler", "tool": "spawn", "args": {"task": "Organize downloads", "role": "file-handel-expert", "subagent_id": "file_handel_expert"}}, "result": "File handler spawned"},
    {"user": "Spawn a background agent", "tool": "spawn", "args": {"task": "Long-running task"}}, "result": "Background agent spawned"},
    
    # More A2A operations
    {"user": "Delegate to multiple agents", "tool": "a2a", "args": {"action": "delegate", "agents": ["coding_expert", "websearch_expert"], "task": "Complete project"}}, "result": "Delegated"},
    {"user": "Find writing agents", "tool": "a2a", "args": {"action": "discover", "capabilities": ["writing"]}}, "result": "Writing agents"},
    {"user": "Find analysis agents", "tool": "a2a", "args": {"action": "discover", "capabilities": ["analysis"]}}, "result": "Analysis agents"},
    {"user": "Call information expert", "tool": "a2a", "args": {"action": "call", "target": "information_expert", "task": "Summarize this document"}}, "result": "Info expert called"},
    {"user": "Spawn for data analysis", "tool": "spawn", "args": {"task": "Analyze this data", "role": "information-expert"}}, "result": "Data analyst spawned"},
]


# ============ CRON JOBS (30) ============
CRON_OPS = [
    {"user": "List scheduled jobs", "tool": "cron", "args": {"action": "list"}}, "result": "Jobs list"},
    {"user": "Show all cron jobs", "tool": "cron", "args": {"action": "list"}}, "result": "All jobs"},
    {"user": "Add backup job", "tool": "cron", "args": {"action": "add", "name": "backup", "schedule": "0 2 * * *", "task": "Backup files"}}, "result": "Backup job added"},
    {"user": "Add daily report", "tool": "cron", "args": {"action": "add", "name": "daily_report", "schedule": "0 9 * * *", "task": "Send daily report"}}, "result": "Daily report added"},
    {"user": "Add hourly check", "tool": "cron", "args": {"action": "add", "name": "health_check", "schedule": "0 * * * *", "task": "Check health"}}, "result": "Health check added"},
    {"user": "Disable a job", "tool": "cron", "args": {"action": "disable", "name": "backup"}}, "result": "Job disabled"},
    {"user": "Enable a job", "tool": "cron", "args": {"action": "enable", "name": "backup"}}, "result": "Job enabled"},
    {"user": "Remove old job", "tool": "cron", "args": {"action": "remove", "name": "old_task"}}, "result": "Job removed"},
    {"user": "Add weekly cleanup", "tool": "cron", "args": {"action": "add", "name": "cleanup", "schedule": "0 3 * * 0", "task": "Clean up files"}}, "result": "Cleanup added"},
    {"user": "Add monitoring job", "tool": "cron", "args": {"action": "add", "name": "monitor", "schedule": "*/15 * * * *", "task": "Monitor system"}}, "result": "Monitor added"},
    
    # More cron operations
    {"user": "Add monthly archive", "tool": "cron", "args": {"action": "add", "name": "archive", "schedule": "0 2 1 * *", "task": "Archive data"}}, "result": "Archive added"},
    {"user": "Add sync job", "tool": "cron", "args": {"action": "add", "name": "sync", "schedule": "0 */6 * * *", "task": "Sync data"}}, "result": "Sync job added"},
    {"user": "Add notification job", "tool": "cron", "args": {"action": "add", "name": "notify", "schedule": "0 9,17 * * *", "task": "Send notification"}}, "result": "Notify added"},
    {"user": "Add log rotation", "tool": "cron", "args": {"action": "add", "name": "logrotate", "schedule": "0 0 * * *", "task": "Rotate logs"}}, "result": "Log rotate added"},
    {"user": "Add disk check", "tool": "cron", "args": {"action": "add", "name": "disk_check", "schedule": "0 * * * *", "task": "Check disk space"}}, "result": "Disk check added"},
]


# ============ MEMORY OPERATIONS (30) ============
MEMORY_OPS = [
    {"user": "Remember this preference", "tool": "memory", "args": {"action": "write", "content": "User prefers dark mode", "topic": "preferences"}}, "result": "Saved to memory"},
    {"user": "Save this fact", "tool": "memory", "args": {"action": "write", "content": "Project uses Python 3.12", "topic": "project"}}, "result": "Saved"},
    {"user": "Remember my name", "tool": "memory", "args": {"action": "write", "content": "User's name is John", "topic": "user"}}, "result": "Name saved"},
    {"user": "Search memory for project info", "tool": "memory", "args": {"action": "search", "query": "project"}}, "result": "Project info found"},
    {"user": "Search memory for preferences", "tool": "memory", "args": {"action": "search", "query": "preferences"}}, "result": "Preferences found"},
    {"user": "Search memory for work", "tool": "memory", "args": {"action": "search", "query": "work"}}, "result": "Work info found"},
    {"user": "Read memory about topics", "tool": "memory", "args": {"action": "recall", "topic": "project"}}, "result": "Project recall"},
    {"user": "Recall user info", "tool": "memory", "args": {"action": "recall", "topic": "user"}}, "result": "User recall"},
    {"user": "Write important note", "tool": "memory", "args": {"action": "write", "content": "Complete the API by Friday", "topic": "tasks"}}, "result": "Note saved"},
    {"user": "Write learning", "tool": "memory", "args": {"action": "write", "content": "Learned new Python pattern", "topic": "learning"}}, "result": "Learning saved"},
    
    # More memory operations
    {"user": "Search project notes", "tool": "memory", "args": {"action": "search", "query": "notes"}}, "result": "Notes found"},
    {"user": "Search for meetings", "tool": "memory", "args": {"action": "search", "query": "meeting"}}, "result": "Meetings found"},
    {"user": "Search knowledge base", "tool": "memory", "args": {"action": "search", "query": "knowledge"}}, "result": "Knowledge found"},
    {"user": "Save contact info", "tool": "memory", "args": {"action": "write", "content": "Contact: john@email.com", "topic": "contacts"}}, "result": "Contact saved"},
    {"user": "Save meeting notes", "tool": "memory", "args": {"action": "write", "content": "Meeting at 3pm", "topic": "meetings"}}, "result": "Meeting saved"},
]


# ============ MESSAGING (15) ============
MESSAGING = [
    {"user": "Send message to user", "tool": "message", "args": {"content": "Task completed!", "content_format": "markdown"}}, "result": "Message sent"},
    {"user": "Send notification", "tool": "message", "args": {"content": "Backup finished successfully"}}, "result": "Notification sent"},
    {"user": "Send with formatting", "tool": "message", "args": {"content": "**Important**: Task done!", "content_format": "markdown"}}, "result": "Formatted message sent"},
    {"user": "Send plain text", "tool": "message", "args": {"content": "System check completed", "content_format": "text"}}, "result": "Plain text sent"},
    {"user": "Send HTML message", "tool": "message", "args": {"content": "<b>Bold</b> message", "content_format": "html"}}, "result": "HTML sent"},
    {"user": "Send status update", "tool": "message", "args": {"content": "Status: All systems operational"}}, "result": "Status sent"},
    {"user": "Send error alert", "tool": "message", "args": {"content": "Error: Something went wrong"}}, "result": "Alert sent"},
    {"user": "Send success message", "tool": "message", "args": {"content": "Success! The task completed."}}, "result": "Success message sent"},
    {"user": "Send with emoji", "tool": "message", "args": {"content": "✅ Task complete!"}}, "result": "Emoji message sent"},
    {"user": "Send list", "tool": "message", "args": {"content": "- Item 1\n- Item 2\n- Item 3"}}, "result": "List sent"},
    {"user": "Send code block", "tool": "message", "args": {"content": "```python\nprint('hello')\n```"}}, "result": "Code block sent"},
    {"user": "Send link", "tool": "message", "args": "Check [this](https://example.com) out!"}, "result": "Link sent"},
    {"user": "Send confirmation", "tool": "message", "args": {"content": "Confirmed ✓"}}, "result": "Confirmation sent"},
    {"user": "Send reminder", "tool": "message", "args": {"content": "Reminder: Meeting in 5 minutes"}}, "result": "Reminder sent"},
    {"user": "Send summary", "tool": "message", "args": {"content": "Summary:\n- Task 1: Done\n- Task 2: Done"}}, "result": "Summary sent"},
]


# ============ SYSTEM MONITORING (15) ============
SYSTEM_MON = [
    {"user": "Get CPU info", "tool": "system", "args": {"info": "cpu"}}, "result": "CPU details"},
    {"user": "Get memory info", "tool": "system", "args": {"info": "memory"}}, "result": "Memory details"},
    {"user": "Get disk info", "tool": "system", "args": {"info": "disk"}}, "result": "Disk details"},
    {"user": "Get process list", "tool": "system", "args": {"info": "processes"}}, "result": "Process list"},
    {"user": "Get network info", "tool": "system", "args": {"info": "network"}}, "result": "Network info"},
    {"user": "Get system overview", "tool": "system", "args": {"info": "cpu"}}, "result": "System CPU info"},
    {"user": "Check memory usage", "tool": "system", "args": {"info": "memory"}}, "result": "Memory usage"},
    {"user": "Check disk space", "tool": "system", "args": {"info": "disk"}}, "result": "Disk space"},
    {"user": "View processes", "tool": "system", "args": {"info": "processes"}}, "result": "Running processes"},
    {"user": "Network status", "tool": "system", "args": {"info": "network"}}, "result": "Network status"},
    {"user": "System health", "tool": "system", "args": {"info": "cpu"}}, "result": "Health check CPU"},
    {"user": "Memory status", "tool": "system", "args": {"info": "memory"}}, "result": "Memory status"},
    {"user": "Storage status", "tool": "system", "args": {"info": "disk"}}, "result": "Storage status"},
    {"user": "Process status", "tool": "system", "args": {"info": "processes"}}, "result": "Process status"},
    {"user": "Full status", "tool": "system", "args": {"info": "cpu"}}, "result": "Full status"},
]


def generate_all_examples():
    """Generate all training examples."""
    all_examples = []
    
    categories = [
        ("file_operations", FILE_OPS),
        ("system_commands", SYSTEM_CMDS),
        ("python_scripts", PYTHON_OPS),
        ("web_operations", WEB_OPS),
        ("subagents", SUBAGENT_OPS),
        ("cron_jobs", CRON_OPS),
        ("memory", MEMORY_OPS),
        ("messaging", MESSAGING),
        ("system_monitoring", SYSTEM_MON),
    ]
    
    for category, examples in categories:
        print(f"  - {category}: {len(examples)} examples")
        for ex in examples:
            all_examples.append({
                "category": category,
                "user": ex["user"],
                "tool": ex["tool"],
                "args": ex["args"],
                "result": ex["result"]
            })
    
    return all_examples


def create_conversations():
    """Create training conversations."""
    examples = generate_all_examples()
    print(f"\nTotal examples: {len(examples)}")
    
    conversations = []
    tool_list_str = "\n- ".join([t["name"] for t in TOOL_SCHEMA])
    
    for ex in examples:
        conv = [
            {"role": "system", "content": SYSTEM_PROMPT.format(tool_list=tool_list_str)},
            {"role": "user", "content": ex["user"]},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "type": "function",
                    "id": f"call_{ex['tool'][:8]}",
                    "function": {
                        "name": ex["tool"],
                        "arguments": json.dumps(ex["args"])
                    }
                }]
            },
            {"role": "tool", "tool_call_id": f"call_{ex['tool'][:8]}", "content": ex["result"]},
            {"role": "assistant", "content": ex["result"]}
        ]
        conversations.append(conv)
    
    return conversations


def main():
    """Main function."""
    output_path = "/home/sir-airhard/.nanobot/workspace/sft_data_v3.jsonl"
    
    print("Generating comprehensive SFT training dataset...")
    print("Categories:")
    
    conversations = create_conversations()
    
    print(f"\n  - Writing {len(conversations)} conversations...")
    with open(output_path, 'w') as f:
        for conv in conversations:
            f.write(json.dumps(conv, ensure_ascii=False) + '\n')
    
    print(f"\nDataset complete!")
    print(f"  - Total: {len(conversations)} conversations")
    print(f"  - Output: {output_path}")
    
    # Also create by category
    by_category_path = output_path.replace('.jsonl', '_by_category.json')
    examples = generate_all_examples()
    
    by_category = {}
    for ex in examples:
        cat = ex["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(ex)
    
    with open(by_category_path, 'w') as f:
        json.dump(by_category, f, indent=2)
    
    print(f"  - By category: {by_category_path}")
    
    for cat, exs in by_category.items():
        print(f"    - {cat}: {len(exs)} examples")
    
    return conversations


if __name__ == "__main__":
    main()