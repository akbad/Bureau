# Quick setup guide

Since the automated context injection enables agents to automatically and autonomously leverage Beehive's features, those who want to skip the learning curve *entirely* can follow these steps to set up as fast as possible.

> [!WARNING]
> ### Default filesystem locations Beehive uses, and how to customize them
>
> | Location | Purpose | How to customize |
> | :--- | :--- | :--- |
> | `~/Code` | Filesystem MCP whitelist path *(anything in this path can be accessed)* | Use `-f/--fsdir <path>` flag with setup script |
> | `~/Code/mcp-servers/` | Where MCP server repos are cloned | Use `-c/--clonedir <path>` flag with setup script |
>
> These directories will be created if they don't already exist. 

## Setup steps

### Selecting CLI agents to configure

Beehive automatically detects which CLIs to configure based simply on whether their corresponding user-level config directory exists. 

In particular, it looks for:

- **Claude Code:** `~/.claude/`
- **Gemini CLI:** `~/.gemini/`
- **Codex:** `~/.codex/`
- **OpenCode:** `~/.config/opencode/` (or `~/.opencode/`)

### Run the startup/bootstrap script

```bash
./bin/start-beehive
```

> [!TIP]
> Add the [root-level `bin/` directory](bin/) to your shell's `$PATH` to be able to start up (and take down) Beehive's services from anywhere on your machine.

### *If using Claude Code:* install the [`claude-mem` automatic context management](https://github.com/thedotmack/claude-mem) and the [Obra Superpowers](https://github.com/obra/superpowers) plugins

After launching Claude Code, run:

```
> /plugin marketplace add thedotmack/claude-mem
> /plugin install claude-mem

> /plugin marketplace add obra/superpowers-marketplace
> /plugin install superpowers@superpowers-marketplace
```

> [!NOTE]
> The Superpowers plugin also works for Codex. The setup script automatically installs it under `~/.codex/superpowers/` — no manual command needed.

### Verify setup

See the [verification steps in SETUP.md](SETUP.md#making-sure-it-works) to confirm everything is working correctly for each CLI.