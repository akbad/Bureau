# Bureau

> *Endowing agents with the intelligence to **leverage versatile custom tools** and **orchestrate each other, autonomously.***
> 
> *Supports Gemini CLI, Claude Code, Codex, OpenCode, and Grok Build.*

> [!IMPORTANT]
> ### Shortcuts to key resources
>
> - [**Setup guide**](docs/SETUP.md)
> - [**Usage guide**](docs/USAGE.md)
> - [**Configuration reference**](docs/CONFIGURATION.md)

## What Bureau provides

- **Built-in workflow skills:** structured, multi-step protocols (like [two-phase code assessment](protocols/context/static/skills/assess-mode/SKILL.md)) that agents activate automatically when they recognise a matching task
- A **unified, cohesive set of MCP servers and plugins**
- 66 specialized agent roles that are:
    
    - spawnable as **cross-CLI subagents** with *minimal* task delegation overhead
    - usable in *every* supported CLI as both: 
        
        - **isolated subagents**
        - **interactive main agents**

- A **<ins>*near-zero* learning curve</ins>** via:
  
  1. **context injection** that ensures:

     - **agents *automatically and judiciously* use all functionality** Bureau configures them to have access to
     - *minimal/no* explicit directions are needed from the user
  
  2. sensible default settings for quick setup, accompanied by **extensive configuration options** for power users

- **<ins>Setup that takes *minutes*</ins>**, including **automated installation & configuration** of all the functionality above for each supported CLI

### Why?

Agentic coding CLIs, such as Claude Code, Gemini CLI, and Codex, are fragmented: each have unique strengths but incompatible tooling. 

Further, users often rotate between CLIs due to:
    
- their corresponding models being better suited for particular development tasks, workflows and/or styles
- new features and model releases 
- providers' capricious and scarcely-communicated model throttling and rate limit shifts

But **rotating often means losing time rebuilding and reconfiguring context, tools, and custom workflows**. 

Meanwhile, many agentic orchestration frameworks intending to help solve this problem have:

- **considerable learning curves**
- **opinionated workflows/patterns *pushed*** upon users
    
rather than adapting to users' ad-hoc workflows, permitting open-ended exploration/building, or **simply getting out of the way**.

## Feature list

### Consistent agent roles across 5 CLI platforms

- [Specialized roles](agents/role-prompts/) (architect, code-reviewer, etc.) configured for use in *all* supported CLIs
- Can choose a specific model per task (e.g. Claude for architecture, Gemini for broad code search, Grok for implementation)

### Cohesive MCP server set

Handling essential tasks like:

- **Code search** 
    - *Sourcegraph* ➔ remote, public repos
    - *Serena* ➔ local projects
- **Web search, fetch, and crawl/extraction** (*Bureau Search/SearXNG*, *Tavily*, *Brave*, *open-webSearch*, *Fetch*, *Crawl4AI*)
- **Retrieving API docs** (*Context7*)
- **Memory persistence**
    - *Qdrant* ➔ semantic memories
    - *Memory MCP* ➔ structural memories 
    - *claude-mem* ➔ automatic context storage/injection w/ progressive disclosure *(Claude Code only)*
- Security scanning (*Semgrep*)
- Browser automation (*Playwright*)

### Automatic config injection

> Enables *automatic* and *timely* use of the functionality listed above by all supported CLI agents.

All agents automatically read these files at startup:

- [`ops-hub.md`](protocols/context/static/ops-hub.md) → central routing table that directs agents to task-specific spokes
- Task-specific spokes in [`ops/`](protocols/context/static/ops/) → session start, task assessment, execution, completion
- Protocol-owned generated `code-standards` skill → detailed, customizable coding standards activated for code-writing and code-editing tasks

- **Custom Bureau skills**: structured workflow protocols (e.g. `assess-mode`) installed for all supported CLIs and activated automatically by matching prompts
- **[Superpowers](https://github.com/obra/superpowers) skills** — community-maintained skill library *(currently Claude Code and Codex only)*

Injected via:

- **Claude Code, Gemini CLI, Codex**: SessionStart hooks that `cat` the relevant protocol files into agent context at session start, plus per-prompt reminder hooks
- **OpenCode**: native `instructions` array in its config file

### Spec-driven development *(maintainer favourite)* 

> *This is provided by the [GitHub's open-source `spec-kit` CLI](https://github.com/github/spec-kit), which Bureau's setup scripting automatically installs via `uv tool install` for global availability.*

**Significantly reduces agents' mistakes, bugs and unintended implementation omissions** by providing an intuitive, painless workflow *driven by intra-CLI commands* where agents: 
    
- write a comprehensive spec for intended changes, interactively asking questions as necessary,
- turn their specs into implementation plans, which are then turned into concrete tasklists
- implement in detail based on the docs above
- can seamlessly handle on-the-fly updates, accordingly synchronize/adjust specs, plans, tasks, etc. in a cascading fashion

> [!TIP]
>
> To get started fast, **read [Bureau's 5-minute guide to `spec-kit`](docs/USAGE.md#using-github-speckit-cli)**.

### Workflow skills that actually help

> *Structured, multi-step protocols that agents activate automatically when they recognise a matching task.*

> [!NOTE]
> 
> Bureau skill names match their source and install directory names (e.g. `assess-mode`).

#### Skills installed by default

| Skill | What it does |
| :--- | :--- |
| **[Assess mode](protocols/context/static/skills/assess-mode/SKILL.md)** | **Two-phase guided review**: first builds a mental model of changes (with 4 comprehension styles to choose from), then audits every file against [configurable quality standards](docs/CONFIGURATION.md#assess_mode). Interactive tour when used as a main agent; structured report when delegated to a subagent. |
| **[Micro mode](protocols/context/static/skills/micro-mode/SKILL.md)** | **Step-gated editing with DAG-based planning:** offers maximum control over each atomic edit, with pause points after every change. |

#### Additional skills available in the catalog

The [`protocols/context/static/skills/`](protocols/context/static/skills/) directory ships several more skills that can be enabled on demand:

| Skill | What it does |
| :--- | :--- |
| [Scrimmage mode](protocols/context/static/skills/scrimmage-mode/SKILL.md) | Systematic self-attack testing after every code change: generates attack vectors across 5 categories (input validation, state, failure modes, concurrency, security) and blocks progression until vulnerabilities are fixed. |
| [Blast radius mode](protocols/context/static/skills/blast-radius-mode/SKILL.md) | Runs impact analysis before edits by enumerating callers, dependents, tests, and contracts affected, then classifying changes as *safe/needs review/breaking/blocked*. |
| [Clearance mode](protocols/context/static/skills/clearance-mode/SKILL.md) | Rigorous completion verification that defines measurable "done" criteria upfront and blocks clearance until they're satisfied, with evidence. |
| [Safeguard mode](protocols/context/static/skills/safeguard-mode/SKILL.md) | Defines system invariants (value constraints, state machines, relationships, ordering) that must never break and verifies them after all changes. |
| [Prompt engineering](protocols/context/static/skills/prompt-engineering/SKILL.md) | Guided prompt creation and refinement for system prompts, agent instructions, skill definitions, or any LLM-facing text. |
| [Shadow mode](protocols/context/static/skills/shadow-mode/SKILL.md) | Propose-only editing: the agent shows diffs without touching files, with the user applying changes manually. Ideal for learning, maximum transparency, or untrusted environments. |

To enable any of these normal catalog skills, add them to the `skills.enabled` [config setting](docs/CONFIGURATION.md#skills):

```yaml
skills:
  enabled: [micro-mode, assess-mode, shadow-mode, scrimmage-mode]
```

## Agent role usage patterns

### Spawning subagents

**Claude Code & OpenCode** *(via native subagents):*
```
"Have the architect subagent design this system"
"Use the testing agent to isolate this failing test suite"
"Spawn the security-compliance agent to audit these changes"
```

### Activating interactive main agents

#### Claude Code
  
Use Bureau-configured slash commands:

```bash
$ claude
# ... startup output ...
> /architect
# architect role activated, interactive conversation begins
```

#### Gemini CLI & Codex

> [!IMPORTANT] 
> **`~/.local/bin/` must be in your `$PATH`** to use the method.

Use Bureau-configured launch wrapper scripts:

```bash
# launch Gemini CLI w/ architect role active
$ gemini-architect

# launch Codex using GPT-5.2-Codex w/ architect role active
$ codex-architect --model gpt-5.2-codex
```
#### OpenCode

Use the built-in [primary agents mechanism](https://opencode.ai/docs/agents/#primary-agents): simply cycle through available agents using the `Tab` key.

> [!NOTE]
> Bureau-provided agents will be named/shown as `Bureau-Agents/<rolename>` in the OpenCode interface.

#### Grok Build

Use Bureau-installed slash commands or agent definitions:

```bash
$ grok
> /architect-bureau
# architect role prompt injected into the conversation
```

Bureau roles are also installed as Grok agents named `bureau-<role>` (visible in `/config-agents`).

## Configuration

| File | Purpose | Tracked? |
| :--- | :--- | :--- |
| `defaults.yml` | All git-tracked package defaults (ships with Bureau) | Yes |
| `.bureau.yml` | Optional project-level config (discovered by CWD walk-up) | Yes (in *your* project) |
| **`local.yml`** | **Personal customizations/overrides** (gitignored) | **No** (gitignored) |

Configuration loads based on the following hierarchy *(later config sources override earlier ones)*: \
**`defaults.yml` → `.bureau.yml` → `local.yml` → environment variables**

See [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) for full reference.

## Repo structure

```
bureau/
├── bin/            # CLI entry points (open-bureau, close-bureau, ensure-prereqs)
├── agents/         # Agent definitions and setup
├── protocols/      # Context/guidance files for agents
├── tools/          # MCP servers and their documentation
├── operations/     # Python modules (config loading, cleanup, etc.)
├── docs/           # Setup, configuration, usage, CI, engineering invariants
│
│   GITIGNORED:
├── .archives/      # Operational state (trash, cleanup timestamps)
└── .mcp-servers/   # Cloned MCP server repos (shared across Bureau worktrees)
```

## Documentation

| Document | Read it when |
| :--- | :--- |
| [`docs/SETUP.md`](docs/SETUP.md) | installing Bureau for the first time |
| [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) | changing MCP servers, roles, retention, or ports |
| [`docs/USAGE.md`](docs/USAGE.md) | driving Bureau day to day |
| [`docs/CI.md`](docs/CI.md) | running or changing the pipeline |
| [`docs/ENGINEERING.md`](docs/ENGINEERING.md) | **changing Bureau's own code** |

> [!IMPORTANT]
>
> Read [`docs/ENGINEERING.md`](docs/ENGINEERING.md) before contributing. It records the invariants that constrain this codebase and the defect each one was earned by: shell portability across BSD and GNU, agent identity and liveness, schema migrations, and the skill/CLI contract. Several of the rules exist because the same class of bug shipped twice.
