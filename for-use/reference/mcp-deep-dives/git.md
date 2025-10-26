# Git MCP: Deep Dive

## Critical Requirement

**Parent agent MUST run at Git repo root** - All Git operations assume working directory is repo root.

## Overview

Handles all Git operations (status, diff, log, add, commit, branch, etc.). Unlimited local usage.

## Available Tools

Comprehensive Git operations available through MCP interface. Common operations include:

### Status & Inspection
- `git status` - View working tree status
- `git diff` - See changes (staged/unstaged)
- `git log` - View commit history
- `git show` - Display commits, objects

### Staging & Committing
- `git add` - Stage files
- `git commit` - Create commits
- `git reset` - Unstage changes

### Branching & Merging
- `git branch` - List/create/delete branches
- `git checkout` - Switch branches
- `git merge` - Merge branches

### Comparison
- `git diff` with refs - Compare branches/commits
- Targeted comparisons

**Note:** Tools available depend on MCP implementation. Check documentation for complete list.

## Tradeoffs

### Advantages
✅ **All Git operations** in one MCP
✅ **Unlimited usage** (local)
✅ **Safer than CLI** (MCP validation)
✅ **Consistent interface** across agents
✅ **No rate limits**

### Disadvantages
❌ **Requires repo root** (parent must be at root)
❌ **No GitHub features** (use gh CLI or Sourcegraph)
❌ **No Git LFS** (large file support)
❌ **Local repos only** (not for remote operations)

## Common Pitfalls: When NOT to Use

### ❌ Parent Not at Repo Root
**Problem:** Git operations fail if not at root
**Alternative:** Change directory first or use Bash with cd

**Example:**
```
Bad:  Run from /path/to/repo/subdir
      → Git MCP operations fail

Good: Run from /path/to/repo
      → Git MCP operations work
```

### ❌ GitHub-Specific Operations
**Problem:** Git MCP doesn't handle GitHub features
**Alternative:** gh CLI via Bash

**Example:**
```
Bad:  Git MCP for creating pull requests
Good: gh pr create via Bash
```

### ❌ Large File Operations
**Problem:** No Git LFS support
**Alternative:** Git LFS CLI via Bash

**Example:**
```
Bad:  Git MCP for LFS files
Good: git lfs commands via Bash
```

### ❌ Remote Repository Cloning
**Problem:** Git MCP works with existing repos
**Alternative:** git clone via Bash first

**Example:**
```
Bad:  Git MCP to clone repo
Good: git clone via Bash → then use Git MCP
```

### ❌ Interactive Operations
**Problem:** Interactive rebase/add not supported
**Alternative:** Non-interactive alternatives or Bash

**Example:**
```
Bad:  git rebase -i via Git MCP
Good: git rebase (non-interactive) or use Bash carefully
```

## When Git MCP IS the Right Choice

✅ **Status/diff/log** operations
✅ **Staging and committing**
✅ **Branch operations**
✅ **History inspection**
✅ **Comparisons** between refs
✅ **Local repo operations**

**Decision rule:** "Am I doing standard Git operations at repo root?"

## Usage Patterns

**Check status:**
```
git status
→ See modified, staged, untracked files
```

**View changes:**
```
git diff
→ Unstaged changes

git diff --staged
→ Staged changes
```

**Stage and commit:**
```
git add file.js
git commit -m "Fix bug in authentication"
```

**Branch operations:**
```
git branch feature-x
git checkout feature-x
git branch -d old-feature
```

**View history:**
```
git log --oneline -10
→ Last 10 commits

git show commit-hash
→ View specific commit
```

**Compare branches:**
```
git diff main...feature-branch
→ Changes in feature branch since diverging from main
```

## Integration with Other Tools

**Common workflows:**

**1. Code review workflow:**
```
1. git diff → See changes
2. Read files → Review code
3. git add → Stage changes
4. git commit → Create commit
```

**2. Exploration workflow:**
```
1. git log → See history
2. git show → View specific commits
3. Read files → Understand changes
4. git diff → Compare versions
```

**3. Feature branch workflow:**
```
1. git branch feature
2. git checkout feature
3. [Make changes]
4. git add & git commit
5. git checkout main
6. git merge feature
```

## Best Practices

**Always verify location:**
- Ensure parent agent at repo root
- Check with pwd if uncertain
- Git operations assume root context

**Safe commit workflow:**
```
1. git status → See what changed
2. git diff → Review changes
3. git add specific files → Stage selectively
4. git commit with message → Create commit
5. git status → Verify clean state
```

**Avoid destructive operations:**
- Be careful with `git reset --hard`
- Avoid force push to shared branches
- Use `git diff` before committing

**Use descriptive commits:**
- Clear, concise messages
- Explain why, not just what
- Follow project conventions

## GitHub Operations via gh CLI

**For GitHub-specific tasks, use Bash with gh:**

```
Create PR: gh pr create --title "..." --body "..."
View issues: gh issue list
Create issue: gh issue create --title "..." --body "..."
View PR checks: gh pr checks
```

## Alternatives Summary

| Task | Instead of Git MCP | Use This |
|------|--------------------|----------|
| Not at repo root | Git MCP | cd to root first (Bash) |
| GitHub features | Git MCP | gh CLI (Bash) |
| Git LFS | Git MCP | git lfs (Bash) |
| Clone repos | Git MCP | git clone (Bash) |
| Interactive ops | Git MCP | git -i commands (Bash) |

## Quick Reference

**Requirement:** Parent at repo root
**Rate limits:** None (local)
**Best for:** Standard Git operations
**Avoid for:** GitHub features, LFS, interactive ops, cloning

**Common operations:**
- Status: `git status`
- Diff: `git diff` / `git diff --staged`
- Stage: `git add`
- Commit: `git commit -m "message"`
- Branch: `git branch` / `git checkout`
- Log: `git log`

**Links:**
- [Full decision guide](../../../mcps/tools-decision-guide.md)
