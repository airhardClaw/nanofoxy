---
name: code-reviewer
description: Analyze code logs, identify improvements, optimize code, and restart the service. Use after dreaming phases or on-demand to reflect on and improve the codebase.
---

# Code Reviewer

This skill analyzes nanobot logs to identify bottlenecks and improvements, then optimizes the codebase.

## Log Files Reference

### Primary Log Locations
- **Runtime logs**: `~/.nanofoxy/agents/{agent_id}/logs/` or stdout stderr
- **Session logs**: `{workspace}/sessions/*.jsonl`
- **Memory files**: `{workspace}/memory/MEMORY.md`, `{workspace}/memory/HISTORY.md`
- **Config files**: `{workspace}/.nanofoxy/config.yaml`

### Key Metrics in Logs

1. **Agent Runner Metrics** (logged at end of each run):
   ```
   Agent run completed: iterations=N, llm_time=X.XXXs, tool_time=X.XXXs, 
   prompt_tokens=N, completion_tokens=N, stop_reason=XXX
   ```
   - High `llm_time` → provider latency issue
   - High `tool_time` → slow tool execution
   - High `iterations` → complex task or loop issue

2. **Message Processing Metrics**:
   ```
   Message processed in X.XXXs for channel:chat_id - N chars in, N chars out
   ```
   - High processing time → bottleneck in agent loop

3. **Context Building Metrics**:
   ```
   Context built in X.XXXs, N messages, N chars
   ```

4. **Tool Execution Metrics**:
   ```
   Tool X executed in X.XXXs
   Tool X failed after X.XXXs: error
   ```

## Using the Skill

### 1. Find and Analyze Logs

Use these commands to locate logs:
```bash
# Find log files
ls -la ~/.nanofoxy/agents/*/logs/ 2>/dev/null || echo "No agent logs"
ls -la {workspace}/sessions/ 2>/dev/null

# Search for performance metrics
grep -r "Agent run completed" {workspace}/sessions/ ~/.nanofoxy/ 2>/dev/null | tail -20
grep -r "Message processed in" {workspace}/ 2>/dev/null | tail -20

# Find errors and warnings
grep -r "ERROR\|WARNING\|Exception" {workspace}/sessions/ 2>/dev/null | tail -30
```

### 2. Identify Bottlenecks

Look for patterns:
- **High LLM time**: Check provider configuration, network latency
- **High tool time**: Optimize slow tools or add caching
- **High iterations**: Check for loops or unnecessary tool calls
- **Memory issues**: Check consolidation settings

### 3. Apply Improvements

Common optimization areas:
- **Provider settings**: Adjust temperature, max_tokens
- **Tool optimization**: Cache results, optimize implementations
- **Context optimization**: Adjust memory consolidation thresholds
- **Code improvements**: Fix bugs, improve algorithms

### 4. Restart Service

After making improvements, restart nanobot:
```bash
# Find the nanobot process
ps aux | grep -E "nanobot|python.*nanobot" | grep -v grep

# Restart (depending on how it was started)
# If running as service:
sudo systemctl restart nanobot
# Or via CLI:
pkill -f nanobot && cd {workspace} && source .venv/bin/activate && python -m nanobot agent
```

## Integration with Dreaming

After dreaming phases complete, the agent should:

1. **Read recent logs** from the agent's log directory
2. **Analyze metrics** for performance trends
3. **Identify patterns** of issues or slowdowns
4. **Make targeted improvements** to code
5. **Verify fixes** by running tests
6. **Restart service** to apply changes

The dreaming process triggers this skill automatically when configured in the dreaming phase callbacks.

## Example Workflow

```bash
# Step 1: Find logs
LOGS=$(ls -t ~/.nanofoxy/agents/*/logs/*.log 2>/dev/null | head -1)
[ -z "$LOGS" ] && LOGS="{workspace}/nanobot.log"

# Step 2: Analyze recent performance
echo "=== Recent Agent Runs ==="
grep "Agent run completed" "$LOGS" | tail -10

echo "=== Slow Tools ==="
grep "executed in" "$LOGS" | tail -10

echo "=== Errors ==="
grep -i "error\|exception\|failed" "$LOGS" | tail -20

# Step 3: Make improvements based on findings
# ... edit code ...

# Step 4: Run tests
cd /home/sir-airhard/nanofoxy
.venv/bin/pytest -x

# Step 5: Restart
pkill -f "python.*nanobot" || true
cd /home/sir-airhard/nanofoxy && .venv/bin/python -m nanobot agent
```

## Key Metrics to Watch

| Metric | Good | Needs Attention |
|--------|------|------------------|
| llm_time | < 2s | > 5s |
| tool_time | < 0.5s | > 2s |
| iterations | 1-5 | > 10 |
| prompt_tokens | < 32000 | > 60000 |
| completion_tokens | < 2000 | > 4000 |

Track these over time to identify degradation or improvements.