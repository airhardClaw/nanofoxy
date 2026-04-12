---
name: github
description: "Interact with GitHub using the `gh` CLI. Use `gh issue`, `gh pr`, `gh run`, and `gh api` for issues, PRs, CI runs, and advanced queries."
metadata: {"nanobot":{"emoji":"🐙","requires":{"bins":["gh"]},"install":[{"id":"brew","kind":"brew","formula":"gh","bins":["gh"],"label":"Install GitHub CLI (brew)"},{"id":"apt","kind":"apt","package":"gh","bins":["gh"],"label":"Install GitHub CLI (apt)"}]}}
---

# GitHub Skill

Use the `gh` CLI to interact with GitHub repositories, issues, PRs, and CI.

## When to Use

✅ **USE this skill when:**

- Checking PR status, reviews, or merge readiness
- Viewing CI/workflow run status and logs
- Creating, closing, or commenting on issues
- Creating or merging pull requests
- Querying GitHub API for repository data
- Listing repos, releases, or collaborators

❌ **DON'T use this skill when:**

- Local git operations (commit, push, pull, branch) → use `git` directly
- Non-GitHub repos (GitLab, Bitbucket, self-hosted) → different CLIs
- Cloning repositories → use `git clone`
- Reviewing actual code changes → use read_file tool directly
- Complex multi-file diffs → use read files directly

## Setup

```bash
# Authenticate (one-time)
gh auth login

# Verify authentication
gh auth status
```

## Common Commands

### Repository Info

```bash
# View repo info
gh repo view owner/repo

# List repos (yours or organization)
gh repo list --limit 20

# Check git remote
git remote -v
```

### Pull Requests

```bash
# List PRs
gh pr list

# View PR details
gh pr view 55

# Check PR status and CI
gh pr checks 55

# Create PR from current branch
gh pr create --title "My PR" --body "Description"

# Merge PR (if allowed)
gh pr merge 55 --admin --delete-branch
```

### Issues

```bash
# List issues
gh issue list

# Create issue
gh issue create --title "Bug title" --body "Description"

# Close issue
gh issue close 123

# Comment on issue
gh issue comment 123 --body "Comment text"
```

### Workflows and CI

```bash
# List recent workflow runs
gh run list --limit 10

# View run status
gh run view <run-id>

# View failed step logs
gh run view <run-id> --log-failed

# Rerun failed job
gh run rerun <run-id> --failed
```

### GitHub API

The `gh api` command accesses the GitHub API directly for advanced queries:

```bash
# Get PR with specific fields
gh api repos/owner/repo/pulls/55 --jq '.title, .state, .user.login'

# List issues with filters
gh api repos/owner/repo/issues --jq '.[] | "\(.number): \(.title)"'

# Get branch protection rules
gh api repos/owner/repo/branches/main/protection

# Search code
gh api search/code -q '.items[] | "\(.repository.full_name): \(.path)"' \
  -F q="repo:owner/repo language:python"

# Check rate limit
gh api rate_limit
```

### JSON Output

Most commands support `--json` for structured output:

```bash
# Get issues as JSON
gh issue list --json number,title,state

# Parse with jq
gh issue list --json number,title --jq '.[] | "\(.number): \(.title)"'

# Get workflow runs as JSON
gh run list --json id,name,status,conclusion
```

## Best Practices

1. **Always specify `--repo owner/repo`** when not in a git directory
2. **Use `--jq` for filtering** to get just what you need
3. **Use `--json` for scripting** when you need structured data
4. **Check CI status** before merging PRs
5. **Use `gh api`** for data not available through subcommands