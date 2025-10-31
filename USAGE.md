# Usage guide

> [!IMPORTANT]
> This guide assumes the setup steps in [`SETUP.md`](SETUP.md) have been completed and doesn't restate information/guidance available there.

**<ins>Contents</ins>**
- [Overview](#overview)
  - [Features](#features)
  - [Repo-specific definitions](#repo-specific-definitions)
- [Using agents](#using-agents)
  - [Direct use](#direct-use)
  - [As subagents](#as-subagents)
- [MCPs available](#mcps-available)

---

## Overview

### Features

- Provides a **harmonized** ecosystem for developing using **any or all** of the following agentic coding CLIs, <ins>**together**</ins>:

    - **Claude Code**
    - **Codex CLI**
    - **Gemini CLI**

- A **suite of specialized coding agent roles** with consistent behaviour on any platform, with **flexible ways of invoking them:**

    - **Direct use:** use an agent at any time in your current conversation *(Claude Code)* or launch instances of the CLI with the chosen agent *(Codex & Gemini CLIs)*
    - **As subagents:** delegate specific, isolated tasks to specialized agents that run in the background, <ins>automatically</ins> using [Zen MCP's `clink`](https://github.com/BeehiveInnovations/zen-mcp-server/blob/main/docs/tools/clink.md) to **enable cross-CLI subagent spawning & collaboration**

- A set of **open-source/free/freemium MCP servers** *(i.e. you won't pay a cent)* that make tasks (such as `git`, web browsing and static code analysis) **reliable and token-efficient**
- **Automatic setup scripts** for:
    
    - MCP server configuration
    - Agent role prompt installs
    - CLI configuration files for the 3 agentic coding CLIs
    - Config files for all 3 CLIs, ensuring **your CLIs automatically use the tools and agent roles set up in this repo** (and not only when explicitly prompted to)

> [!NOTE]
> #### CLI-specific restrictions
> 
> Some features are limited upstream to specific CLIs:
> 
> | Feature | Restricted to |
> | --- | --- |
> | [*claude-mem* plugin](https://github.com/thedotmack/claude-mem) | Claude Code |
> | [*Superpowers* plugin](https://github.com/obra/superpowers) | Claude Code, Codex CLI (beta) |

### Repo-specific definitions

| Concept | Definition |
| :------ | :--------- |
| **Skill** | *Superpowers* workflow (e.g., `superpowers:test-driven-development`) + any extra Claude/Codex skills files you define |
| **Agent** |  Roles (e.g., `debugger`, `architect`) usable as agents, either [directly in your main chat](#direct-use) or [as **subagents**](#as-subagents) |
| **Subagent** | A child **agent**, isolated from the main chat, spawned to complete a particular task by *either* (1) Claude Code first-party "subagents" feature or (2) `clink` |
| **MCP** | MCP servers available for CLIs to use |

## Using agents

>  [!TIP]
> **Role prompts** for agents/subagents can be found in the following directories.
> | Location | Used when? |
> | :--- | :--- |
> | [`agents/claude-subagents`](agents/claude-subagents/) | (1) Spawning **subagents via Claude Code**'s first-party "subagents" feature or (2) spawning agents for **direct use in chat via slash commands** |
> | [`agents/clink-role-prompts`](agents/clink-role-prompts/) | (1) Spawning **subagents via `clink`** (from *any* CLI, including Claude Code) or (2) spawning agents for **direct use in Codex/Gemini CLIs via wrapper scripts** |
>
> - **Read through the files to see the full list of roles available for use.**
> - Prompts for the <ins>same role</ins> have the <ins>same body across both locations</ins> *(the `claude-subagents` files simply have some extra header YAML that makes them smoother to use with Claude Code)*

> [!TIP] 
> Read [`handoff-guidelines.md`](agents/reference/handoff-guidelines.md) to see the guidance that the CLIs will read at startup that will teach them:
> - when to delegate tasks to subagents
> - which CLIs/models to use for specific subagent tasks

There are 2 primary ways to use agents, depending on the CLI.

### Direct use

→ For using an agent <ins>interactively</ins> in the main/current chat.

#### Claude Code

Activate an agent <ins>within a Claude Code session</ins> using its **corresponding slash command** (injects the role prompt into the current conversation).

> <ins>Example</ins>: to load the [*Architect*](agents/claude-subagents/architect.md) agent in Claude Code:
> ```bash
> $ claude
> > /architect
> # you are now interacting w/ the Architect agent  
> ```

#### Codex & Gemini CLIs

Launch the CLI using the **generated wrapper scripts**, named in the format **`<codex|gemini>-<rolename>`** (e.g. `gemini-architect`, `codex-debugger`)

> <ins>Example</ins>:
>
> - Starting Gemini CLI to interact with the [*Explainer*](agents/clink-role-prompts/explainer.md) agent in the main conversation:
>   ```bash
>   $ gemini-explainer
>   # Gemini CLI is now running w/ the Explainer agent active
>   # Ask it to clarify code and docs
>   ```
> - Starting Codex CLI to interact with the [*Debugger*](agents/clink-role-prompts/debugger.md) agent in the main conversation:
>   ```bash
>   $ codex-debugger
>   # Codex CLI is now running w/ the Debugger agent active
>   # Give it error logs or code snippets to analyze
>   ```

### As subagents

→ When you need to delegate a <ins>specific, isolated task</ins> without interrupting your main workflow or polluting your current chat's context. \
→ Subagents work in the background and report back their findings/results.

> [!IMPORTANT]
> You should **not** need to explicitly follow the steps below; after reading startup guidance, **agents will know when to spawn subagents <ins>automatically</ins>** (assuming you've set up the global config files).

#### Spawning subagents using any CLI, from any CLI (via `clink`)

For cross-CLI subagent spawning and collaboration, use Zen MCP's `clink` tool. It allows specifying:

- the agent role
- the CLI to use to spawn the agent
- the task prompt

> <ins>Example</ins>:
> ```bash
> # within any of Claude Code, Codex or Gemini CLIs
> > clink with gemini with architect role to map out how to 
>   migrate from our monorepo to a microservices architecture

#### Within Claude Code (via Task tool)

> [!NOTE]
> This is only for spawning Claude Code subagents from within Claude Code.

Simply explicitly mention the subagent you want to use and it will automatically be invoked to handle the task.

> <ins>Example</ins>:
> ```bash
> # in Claude Code
> > Have the `code-reviewer` subagent review the changes 
>   in `src/main.py` for best practices and potential bugs.

## MCPs available

> [!IMPORTANT]
> You should **not** need to explicitly use these tools most of the time; after reading the startup guidance provided by the config files, **agents will automatically select and use the appropriate MCP tools** based on the task.

- **Code & security**:

    - **Sourcegraph**: For searching and navigating large, 
      public, open-source codebases.
    - **Serena**: For deep semantic code understanding, 
      analysis, and refactoring within your local codebase
      using LSPs.
    - **Semgrep**: For running fast, local static analysis and
      security scans with a vast library of rules.

- **Web research & documentation**:
    - **Tavily**: A comprehensive search API built for AI 
      agents, capable of searching, crawling, and 
      extracting web content.
    - **Brave**: A privacy-focused web search engine for 
      general queries.
    - **Firecrawl**: A high-performance web scraping and 
      crawling service for reliably extracting content 
      from websites.
    - **Exa**: A "neural search" engine that understands 
      concepts, assisting with finding relevant information 
      even if exact keywords aren't known.
    - **Context7**: For fetching up-to-date, versioned 
      documentation for a wide range of libraries and 
      APIs.
    - **Fetch**: A simple, reliable tool for fetching the 
      content of a single URL and converting it to 
      Markdown.

- **Memory & knowledge**:
    - **Qdrant**: A vector database that provides agents with
      long-term semantic memory, allowing them to recall 
      concepts and context from past interactions.
    - **Memory**: A knowledge graph for storing structured 
      information as entities and relations, giving agents
      a persistent, queryable understanding of your 
      project.
    - **claude-mem *(Claude Code only)***: For automatic 
      context management and conversation memory.

- **Local dev tools**:
    - **Git**: For performing version control operations like
      status, diff, commit, and branch directly within 
      your repository.
    - **Filesystem**: For efficient batch file 
      operations, directory analysis, and other filesystem
      interactions.

- **Orchestration**:
    - **Zen (`clink` tool only)**: enables cross-CLI collaboration/subagent spawning, [as discussed above](#spawning-subagents-using-any-cli-from-any-cli-via-clink)

> [!TIP]
> To learn more about the available MCPs and the specific guidance agents receive on how to use them, read:
>
> - [`compact-mcp-list.md`](agents/reference/compact-mcp-list.md): quick decision guide for selecting the best tool for a given task.
> - [`mcp-deep-dives/`](agents/reference/mcp-deep-dives/): 
> 
>     - Collection of in-depth guides for each MCP, detailing their capabilities and advanced usage patterns. Only read by agents when necessary to preserve context
