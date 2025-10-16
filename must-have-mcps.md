# Must-have MCPs

A practical guide to **must‑have MCP servers** and adjacent tools that *meaningfully* upgrade dev flow when using
- Gemini CLI
- Claude Code
- Codex CLI

## Prerequisites

- npm
- python3
- uv (Python package manager)
- 1 or more coding agents that you use (this guide covers Claude Code, Codex CLI, Gemini CLI)

## Useful background info 

### MCP server types

- **Official/reference** servers are developed and maintained by the creators of MCP
    
    - Are standard, primary implementations that serve as models for how to build new MCPs  

- **Community** servers are developed by the community

### Ways of running MCP servers

If you're **running multiple agents at once** (e.g. Claude Code, Gemini CLI, Codex CLI all running at the same time; they can all reuse the same server):

| Method | When to use | How it works |
| --- | --- | --- |
| **Shared instance (`http`)** | **For MCPs whose toolcalls are quick & synchronous** | Run the server once, `mcp add` command provides the server's URL; client then initiates exchanges w/ server via HTTP |
| **Server-sent events** (`sse`) | **For MCPs whose tools run for a long time**, thus making progress updates useful; Agent CLI *and* MCP server **must support SSE** | Similar to `http`, except connection remains open instead of closing after each request. Client then stays listening, and server can "push" messages (via events) to the client whenever new data is available |

When you're only using **one agent at a time** (e.g. *only launching one of* Claude Code, Codex or Gemini CLI):

| Method | How it works | Pros & cons |
| --- | --- | --- |
| **Client-managed servers (`stdio`)** | `mcp add` command includes the full command to run the server, which the client starts/stops as needed | Simple setup (no separate process) but inefficient for frequent use and stateless by default |

### Notes about adding MCPs to specific agent CLIs

> The `/mcp` command in each of the agent CLIs below will **list currently-active servers** *(useful for verifying setup was successful)*

#### Gemini CLI

> [***Full Gemini MCP guide***](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md)
> 
> → [*Shortcut: guide to `gemini mcp` commands*](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md#managing-mcp-servers-with-gemini-mcp)

- Add servers with `gemini mcp add <name> <commandOrUrl> [args...]` 
    
    - Scope used determines which config file is changed: 

        - **Project scope *(default)*** → `~/.gemini/settings.json`
        - **User scope** → `~/.gemini/settings.json`
            
            - Use via `-s user` option

#### Claude Code

> [***Full Claude Code MCP guide***](https://docs.claude.com/en/docs/claude-code/mcp)

- **Support for SSE servers is deprecated**; prefer HTTP servers instead 
- Can add MCP servers at these scopes (with `--scope <local|project|user>`):

    - **Local (*default*)**: for current repo
    - **Project**: changes current repo's `.mcp.json` so collaborators can reuse the same MCP setup
    - **User**: for Claude Code anywhere on your device (changes config in `~/.claude`)

- Listing and using available MCPs:

    - Type `@` to see available resources from all connected MCP servers (alongside files)
    - Use the format **`@server:protocol://resource/path`** to reference a resource, for example:

        > `Compare @postgres:schema://users with @docs:file://database/user-model`

#### Codex

> [***Full Codex MCP guide***](https://developers.openai.com/codex/mcp)

- Adding MCP servers:
    
    - Options for `stdio` servers:

        1. **Edit `~/.codex/config.toml` config file** with this format:

            ```toml
            [mcp_servers.<server-name>]
            command = <server launch command>  # required
            args = <args for launch command>   # optional
            env = { "ENV_VAR" = "VALUE" }      # optional: env vars for server to use

            # alternate way of adding any env vars for server to use
            [mcp_servers.<server-name>.env]
            ENV_VAR = "VALUE"                 
            # ... repeat for each variable
            ```

            - Example:

                ```toml
                [mcp_servers.context7]
                command = "npx"
                args = ["-y", "@upstash/context7-mcp"]

                [mcp_servers.context7.env]
                SUNRISE_DIRECTION = "EAST"
                ```
            
        2. **Use shortcut command** (creates config entry for you): 

            ```bash
            codex mcp add <server-name> [--env <VAR=VALUE>]... -- <server launch command>
            ```
    
    - For `http` servers: **must edit `~/.codex/config.toml`** config file with this format:

        ```toml
        # optional: add this line if you want to use RMCP client to connect to server
        #           enables auth via OAuth for HTTP servers
        experimental_use_rmcp_client = true 

        [mcp_servers.<server-name>]
        url = <server URL>      # required
        bearer_token = <token>  # optional: bearer token to use in an `Authorization` header 
                                #           (if not using OAuth via RMCP above)
        ``` 

    - **Doesn't support SSE**; use HTTP servers instead

## Prerequisites

- npm
- python3
- uv (Python package manager)
- 1 or more coding agents that you use (this guide covers Claude Code, Codex CLI, Gemini CLI)

## MCP servers

**Cost:** Free / open source.

### Why use over vanilla agents

- **Enhanced security and control:** The server operates only within pre-approved, "allow-listed" directories; prevents accessing sensitive system files or directories outside project scope
- **Reliable and structured ops:** agent receives structured data (like JSON) (instead of parsing the unpredictable text output of commands like `ls` or `find`)
    
    - *Makes file discovery, reading, and writing far less error-prone*
    - Eliminates brittleness from platform differences (e.g., macOS vs. Linux shell tools)

- **Predictable error handling:** 
    
    - Server provides typed, machine-readable errors (e.g., `FileNotFound`, `AccessDenied`)
    - Allows the agent to intelligently handle failures, retry operations, or ask for clarification, rather than failing silently or misinterpreting a generic `bash` error message.

### Running the server

#### Via `http` (when using many agents together)

1. Set the port you want the server to use (best if in `.bashrc`/`.zshrc`):

    ```bash
    export FS_MCP_PORT=8081
    ```

2. Start the central server:

    ```bash
    npx -y @modelcontextprotocol/server-filesystem --port $FS_MCP_PORT [your-allowed-directory]
    ```

3. Connect agents:

    - Gemini CLI: `gemini mcp add fs http --url http://localhost:8081/mcp/`
    - Claude Code: `claude mcp add --transport http fs http://localhost:8081/mcp/`
    - Codex CLI add to `~/.codex/config.toml`:

        ```toml
        [mcp_servers.fs]
        url = "http://localhost:8081/mcp/"
        transport = "http"
        ``` 

#### Via `stdio` (if only using one agent at a time)

The agent client will start and stop the server automatically as needed.

| Agent | Command |
| :--- | :--- |
| Gemini CLI | `gemini mcp add fs npx -- -y @modelcontextprotocol/server-filesystem [your-allowed-directory]` |
| Codex CLI | `codex mcp add fs -- npx -y @modelcontextprotocol/server-filesystem [your-allowed-directory]` |
| Claude Code | `claude mcp add fs -s user -- npx -y @modelcontextprotocol/server-filesystem [your-allowed-directory]` |

### Examples to try

> “Read `server/**/*.go` and propose a patch adding retries with exponential backoff; write diffs but do not commit.”
<p></p>

**Git (choose one implementation)**  
- **Gemini (Python server via uvx):**  
  ```bash
  gemini mcp add git uvx -- mcp-server-git
  ```
  *(alt Node)* `gemini mcp add git npx -- -y @cyanheads/git-mcp-server`
- **Codex:**  
  ```bash
  codex mcp add git -- npx -y @cyanheads/git-mcp-server
  ```
- **Claude Code:**  
  ```bash
  claude mcp add git -s user -- npx -y @cyanheads/git-mcp-server
  ```

**Fetch (web → Markdown)**  
- **Gemini (Python server):**  
  ```bash
  gemini mcp add fetch uvx -- mcp-server-fetch
  ```
- **Codex:**  
  ```bash
  codex mcp add fetch -- uvx mcp-server-fetch
  ```
- **Claude Code:**  
  ```bash
  claude mcp add fetch -s user -- uvx mcp-server-fetch
  ```

### B. Planning & Research (Context7, Tavily, Firecrawl)

**Context7 (API docs into context)**  
- **Gemini:**  
  ```bash
  gemini mcp add context7 npx -- -y @upstash/context7-mcp --api-key $CONTEXT7_API_KEY
  ```
- **Codex:**  
  ```bash
  codex mcp add context7 -- npx -y @upstash/context7-mcp
  ```
- **Claude Code:**  
  ```bash
  claude mcp add context7 -s user -- npx -y @upstash/context7-mcp
  ```

**Tavily (search / extract / map / crawl)**  
- **Gemini (remote HTTP):**  
  ```bash
  gemini mcp add tavily https://mcp.tavily.com/mcp/?tavilyApiKey=$TAVILY_API_KEY
  ```
- **Codex (remote HTTP via config)** — add to `~/.codex/config.toml`:
  ```toml
  [mcp_servers.tavily]
  url = "https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_API_KEY}"
  ```
  *(or run locally with)* `codex mcp add tavily -- npx -y @mcptools/mcp-tavily`
- **Claude Code (HTTP):**  
  ```bash
  claude mcp add --transport http tavily https://mcp.tavily.com/mcp/?tavilyApiKey=$TAVILY_API_KEY
  ```

**Firecrawl (robust crawl/scrape; JS pages)**  
- **Gemini (npx):**  
  ```bash
  gemini mcp add firecrawl npx -- -y firecrawl-mcp
  ```
- **Codex:**  
  ```bash
  codex mcp add firecrawl -- npx -y firecrawl-mcp
  ```
- **Claude Code:**  
  ```bash
  claude mcp add firecrawl -s user -- npx -y firecrawl-mcp
  ```

### C. Memory / Token‑efficiency

**Memory (reference knowledge‑graph)**  
- **Gemini:** `gemini mcp add memory npx -- -y @modelcontextprotocol/server-memory`  
- **Codex:** `codex mcp add memory -- npx -y @modelcontextprotocol/server-memory`  
- **Claude Code:** `claude mcp add memory -s user -- npx -y @modelcontextprotocol/server-memory`

**Postgres + pgvector (community servers)**  
- Add your server command where indicated:  
  - **Gemini:** `gemini mcp add pgmem <your-pgvector-server-cmd>`  
  - **Codex:** `codex mcp add pgmem -- <your-pgvector-server-cmd>`  
  - **Claude Code:** `claude mcp add pgmem -s user -- <your-pgvector-server-cmd>`

### D. Quality & Security Rails

**Semgrep (SAST)**  
- **Gemini (local stdio):**  
  ```bash
  gemini mcp add semgrep uvx -- semgrep-mcp
  ```
  *(or connect to remote SSE when applicable)*
- **Codex:**  
  ```bash
  codex mcp add semgrep -- uvx semgrep-mcp
  ```
- **Claude Code:**  
  ```bash
  # Remote SSE (hosted by Semgrep)
  claude mcp add --transport sse semgrep https://mcp.semgrep.ai/sse
  # OR local:
  claude mcp add semgrep -s user -- uvx semgrep-mcp
  ```

**Snyk (deps/IaC/containers)**  
- **Gemini:** `gemini mcp add snyk <your-snyk-mcp-cmd>`  
- **Codex:** `codex mcp add snyk -- <your-snyk-mcp-cmd>`  
- **Claude Code:** `claude mcp add snyk -s user -- <your-snyk-mcp-cmd>`

### E. Workflow Glue

**Composio / Rube (GitHub/Jira/Slack/Notion…)**  
- **Gemini:** `gemini mcp add rube npx -- @composiohq/rube`  
- **Codex:** `codex mcp add rube -- npx @composiohq/rube`  
- **Claude Code:** `claude mcp add rube -s user -- npx @composiohq/rube`

---

### Verify & manage

- **Gemini CLI:** run `/mcp` to see active servers/tools.  
- **Codex CLI:** run `/mcp` inside the TUI; edit `~/.codex/config.toml` for finer control.  
- **Claude Code:** run `/mcp` to list; supports `.mcp.json` (project), user & enterprise‑managed configs; transports: **http**, **sse**, **stdio**.

> **Security tip:** Prefer least‑privilege (path allow‑lists, read‑only where possible). For remote HTTP/SSE servers, review auth scopes and rotate tokens regularly.

---

## Appendix — User vs Project Config (Claude Code, Codex CLI, Gemini CLI)

Use **user/global config** to “set & forget” shared servers, and **project config** for path‑scoped tools (Filesystem), policies (Semgrep/Snyk), or per‑repo memory namespaces.

> **Verify fast:** in any client session, type **`/mcp`** to list active servers & tools.

### A) Gemini CLI

**Where config lives**
- **User:** `~/.gemini/settings.json` (default for `gemini mcp add …`)
- **Project:** `.gemini/settings.json` in the repo (use `-s project` after `gemini mcp add`)

**User config (one root for many repos)**
```jsonc
{
  "mcpServers": {
    "fs": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/Projects"],
      "transport": "stdio",
      "enabled": true
    },
    "tavily": {
      "url": "https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_API_KEY}",
      "transport": "http",
      "enabled": true
    }
  }
}
```

**Project config (safer: repo‑local root)**
```jsonc
// .gemini/settings.json (checked into the repo if you wish)
{
  "mcpServers": {
    "fs": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "transport": "stdio",
      "enabled": true
    },
    "semgrep": {
      "command": "uvx",
      "args": ["semgrep-mcp"],
      "transport": "stdio",
      "env": { "SEMGREP_RULES": "./.semgrep/rules" }
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": { "MEMORY_NAMESPACE": "locker" }
    }
  }
}
```

**Switch scope via commands**
```bash
# User/global
gemini mcp add fs npx -- -y @modelcontextprotocol/server-filesystem ~/Projects

# Project‑scoped (writes .gemini/settings.json in the repo)
gemini mcp add -s project fs npx -- -y @modelcontextprotocol/server-filesystem .
```

---

### B) OpenAI Codex CLI

**Where config lives**
- **Global:** `~/.codex/config.toml`
- **Profiles:** define named profiles in the same file and launch with `codex --profile <name>`

**Global config (one root for many repos)**
```toml
[mcp_servers.fs]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "~/Projects"]
transport = "stdio"
enabled = true

[mcp_servers.tavily]
url = "https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_API_KEY}"
transport = "http"
enabled = true
```

**Profile for a specific repo (safer root)**
```toml
[profiles.locker.mcp_servers.fs]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "."]
transport = "stdio"
enabled = true

[profiles.locker.env]
MEMORY_NAMESPACE = "locker"
SEMGREP_RULES = "./.semgrep/rules"
```

**Launch with a profile**
```bash
codex --profile locker
```

---

### C) Claude Code (CLI + VS Code)

**Where config lives**
- **User:** stored by `claude mcp add …` at user scope
- **Project:** `.mcp.json` (checked into the repo if you like)

**Project config (`.mcp.json`) — per‑repo root & policies**
```jsonc
{
  "mcpServers": {
    "fs": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "transport": "stdio",
      "enabled": true
    },
    "tavily": {
      "url": "https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_API_KEY}",
      "transport": "http",
      "enabled": true
    },
    "semgrep": {
      "command": "uvx",
      "args": ["semgrep-mcp"],
      "transport": "stdio",
      "env": { "SEMGREP_RULES": "./.semgrep/rules" }
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": { "MEMORY_NAMESPACE": "locker" }
    }
  }
}
```

**User scope via commands**
```bash
# Broad root for many repos (least friction)
claude mcp add fs -s user -- npx -y @modelcontextprotocol/server-filesystem ~/Projects

# Repo‑local root (least privilege) — run inside the repo
claude mcp add fs -s project -- npx -y @modelcontextprotocol/server-filesystem .
```

---

### One‑root vs Many‑roots (Filesystem)

- **One root** (e.g., `~/Projects`): simplest — works across all repos inside that path.  
  *Trade‑off:* broader access; rely on allow‑lists and human‑in‑the‑loop for safety.
- **Many roots** (per‑repo `.`): most secure — each repo declares its own filesystem server in **project config**.  
  *Trade‑off:* a bit more setup when creating a new repo.

**Tip:** For monorepos, prefer **project config** at the workspace root and specify additional allow‑listed subpaths via server args if your filesystem server supports them.
