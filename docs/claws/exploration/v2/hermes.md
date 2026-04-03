# Hermes Agent -- Bureau Integration Assessment

**Date:** 2026-04-03
**Platform:** Hermes Agent
**Maintainer:** NousResearch
**Repository:** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
**Website:** [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/)
**License:** Open Source
**Release Date:** February 2026
**Status:** Bureau's frontrunner integration candidate

---

## 1. Platform Overview

Hermes Agent is an open-source autonomous AI agent built by NousResearch -- the research lab behind the Hermes, Nomos, and Psyche model families. Released in February 2026, Hermes Agent tackles the two biggest bottlenecks in agentic workflows: **memory decay** and **environmental isolation**.

Unlike coding copilots tethered to an IDE or chatbot wrappers around a single API, Hermes Agent is a self-improving agent that lives on your infrastructure, remembers what it learns across sessions, and gets more capable the longer it runs. It is not a framework you code against -- it is a running system you configure and extend.

### Architecture

Hermes Agent follows a **ReAct (Reasoning and Acting) loop** architecture with a structured cycle:

| Component | Implementation |
|-----------|---------------|
| Core Agent Loop | `run_agent.py` -- main ReAct cycle (Observation -> Reasoning -> Action) |
| State Database | `hermes_state.py` -- SQLite with FTS5 full-text search (~/.hermes/state.db) |
| Tool Orchestration | `model_tools.py` -- dynamic tool discovery and dispatch |
| Memory Files | `~/.hermes/memories/MEMORY.md`, `USER.md` -- injected into system prompt |
| Skills Store | `~/.hermes/skills/` -- reusable Python-based tool definitions |
| Messaging Gateway | Multi-platform adapter (CLI, Telegram, Discord, Slack, WhatsApp) |

### Value Proposition

- **Self-improving**: Autonomously creates procedural skills from experience, improves them during use, and reuses them across sessions
- **Persistent memory**: Bounded, curated memory that survives sessions and compounds in value over time
- **Multi-platform**: Single gateway to CLI, Telegram, Discord, Slack, WhatsApp -- reach your agent from any device
- **Deployment flexible**: Runs anywhere -- $5 VPS, GPU cluster, or serverless (Daytona/Modal)
- **Open standard skills**: Compatible with agentskills.io for community-contributed, portable skills

---

## 2. Feature Set

### Core Capabilities

- **ReAct Agent Loop**: Structured Observation -> Reasoning -> Action cycle with tool use
- **Persistent Memory**: MEMORY.md and USER.md files curated by the agent itself, injected at session start
- **Autonomous Skill Creation**: When solving a hard problem, the agent writes a reusable skill document
- **Skill Self-Improvement**: Skills are refined during use based on outcomes
- **FTS5 Session Search**: All past sessions stored in SQLite with full-text search and Gemini Flash summarization
- **Multi-Platform Gateway**: CLI, Telegram, Discord, Slack, WhatsApp from one unified gateway
- **Honcho User Modeling**: Dialectic user modeling that builds a Theory of Mind for each user
- **MCP Integration**: Model Context Protocol support for tool interoperability

### Skills System

Skills are Hermes Agent's most distinctive feature. The workflow is:

1. Agent encounters a novel problem
2. Agent solves the problem through reasoning and tool use
3. Agent writes a **skill document** capturing the solution as a reusable procedure
4. Skill is stored in `~/.hermes/skills/` as a searchable, shareable document
5. On future encounters, the agent retrieves and applies the relevant skill
6. If the skill can be improved, the agent updates it

Skills are compatible with the **agentskills.io** open standard, meaning community-contributed skills are portable across Hermes Agent installations. The Skills Hub went live in mid-2025.

### Tool Creation

Beyond skill documents, Hermes Agent can create new Python-based tools and store them in the skills directory. This gives it the ability to extend its own capabilities programmatically -- writing functions, testing them, and registering them for future use.

---

## 3. Memory Architecture

Hermes Agent implements a multi-level memory system that mimics procedural learning:

### MEMORY.md (Agent Knowledge)

Located at `~/.hermes/memories/MEMORY.md`, this file contains the agent's accumulated knowledge about its environment, learned patterns, and operational context. It is injected into the system prompt as a **frozen snapshot** at session start.

- Character limits keep memory focused (~100-200 lines)
- When full, the agent **consolidates or replaces** entries to make room for new information
- The agent decides what is worth remembering and what can be deprecated
- This is analogous to curated long-term declarative memory

### USER.md (User Knowledge)

Located at `~/.hermes/memories/USER.md`, this file captures the agent's understanding of the user: preferences, working style, projects, communication patterns, and accumulated context. Combined with Honcho's dialectic user modeling, this creates a persistent Theory of Mind.

### Session Search (Episodic Recall)

All CLI and messaging sessions are stored in SQLite (`~/.hermes/state.db`) with **FTS5 full-text search**. When the agent needs to recall past interactions:

1. A search query is constructed from the current context
2. FTS5 returns relevant past conversation fragments
3. **Gemini Flash** summarizes the retrieved fragments into concise context
4. Summarized context is injected into the current session

This provides episodic memory with intelligent compression -- the agent can recall "what happened last Tuesday" without loading entire conversation histories.

### Memory Curation

A distinctive feature is that memory curation is **agent-driven with periodic nudges**. The system periodically prompts the agent to review and update its memory files, but the agent itself decides what to keep, consolidate, or discard. This creates a self-maintaining memory system that stays relevant without manual intervention.

---

## 4. Autonomous Learning Loop

Hermes Agent's learning loop operates at three levels:

### Procedural Learning (Skills)

The primary learning mechanism. When the agent solves a problem, it can:
1. **Extract** the solution pattern into a skill document
2. **Store** the skill in a searchable directory
3. **Retrieve** the skill when encountering similar problems
4. **Improve** the skill based on new outcomes

This creates a compounding capability curve: the agent becomes measurably more effective at tasks it has encountered before. After six months of operation, a Hermes Agent accumulates dozens to hundreds of skills specific to its user's domain.

### Declarative Learning (Memory Files)

MEMORY.md and USER.md accumulate knowledge over time. The agent learns facts, preferences, and patterns, consolidating them into focused entries. The character limit forces prioritization -- the agent must decide what knowledge is most valuable, creating an implicit relevance ranking.

### Episodic Learning (Session Search)

Past sessions provide experiential context. When facing a familiar situation, the agent can retrieve how it handled it before, what worked, and what didn't. The Gemini Flash summarization ensures this retrieval is efficient rather than overwhelming.

### What It Lacks

Hermes Agent does not implement:
- Parametric learning (no fine-tuning or weight updates)
- DSPy-style prompt optimization
- Reflexion-style verbal self-critique loops
- Quantified self-improvement metrics (except through skill success rates)

The learning is retrieval-based and skill-based rather than parametric or optimization-based.

---

## 5. Operational Memory Stack

### Working Memory (In-Session)

The LLM's context window during active reasoning. Populated with:
- System prompt (including frozen MEMORY.md and USER.md snapshots)
- Current conversation history
- Retrieved session search results (summarized)
- Active tool outputs and observations

### Long-Term Declarative Memory (MEMORY.md + USER.md)

Persistent knowledge curated by the agent. Survives sessions and restarts. Character-bounded to maintain focus. Updated through agent-driven curation with periodic nudges.

### Episodic Memory (Session Database)

SQLite + FTS5 store of all past sessions. Queried via full-text search, returned via LLM summarization. Provides "what happened" recall across the agent's entire operational history.

### Procedural Memory (Skills)

Reusable skill documents and Python tools in `~/.hermes/skills/`. Represent learned capabilities -- not just facts, but how to do things. Searchable and shareable via agentskills.io.

### Comparison with Bureau

| Memory Type | Bureau | Hermes Agent |
|-------------|--------|-------------|
| Vector/Semantic | Qdrant (1024-dim) | Not present (no embedding store) |
| Knowledge Graph | Memory MCP (entities/relations) | Not present |
| Declarative | claude-mem, CLAUDE.md | MEMORY.md, USER.md |
| Episodic | SQLite dossiers | SQLite + FTS5 sessions |
| Procedural | Skills directories | Skills directories |
| User Modeling | Concierge suites | Honcho + USER.md |

The overlap in **declarative (Markdown files)** and **procedural (skills directories)** is strikingly high, while Bureau has stronger semantic search and graph capabilities that Hermes lacks.

---

## 6. Daily Assistant Features

Hermes Agent functions as a capable daily assistant:

- **Multi-Platform Availability**: Reach the agent from CLI, Telegram, Discord, Slack, or WhatsApp -- all from one gateway with unified context
- **Persistent Context**: The agent remembers your preferences, projects, schedule, and ongoing tasks across sessions
- **Proactive Assistance**: Agent-curated memory with periodic nudges means it can surface relevant context without being asked
- **Task Execution**: Shell commands, file operations, web browsing, and API calls
- **Scheduling**: Can be deployed on Daytona or Modal serverless infrastructure that costs nearly nothing when idle
- **User Modeling**: Honcho dialectic modeling builds an increasingly accurate Theory of Mind, personalizing interactions over time

### Limitations

- No built-in calendar or email integration (must be added as skills)
- No native mobile app -- relies on messaging platforms for mobile access
- No visual interface -- purely text-based interaction
- Early-stage project; ecosystem is still developing

---

## 7. SWE Assistant Features

Hermes Agent provides solid software engineering capabilities:

- **Shell Execution**: Full terminal access for running builds, tests, git commands, and development tools
- **File Operations**: Read, write, and edit files across the filesystem
- **Code Generation**: Leverages underlying LLM (supports multiple providers) for code writing and debugging
- **Tool Creation**: Can write and register new Python tools to extend its own capabilities
- **Skill-Based Problem Solving**: Accumulated skills provide domain-specific coding patterns and solutions
- **Environment Memory**: Remembers project structures, build configurations, and development workflows across sessions
- **MCP Integration**: Can connect to external development tools via Model Context Protocol

### Comparison with Dedicated Coding Agents

Hermes Agent is a generalist autonomous agent with SWE capabilities, not a purpose-built coding agent like Claude Code or Codex. It lacks:
- Native code understanding (no AST parsing, no LSP integration)
- SWE-bench-class code repair capabilities
- IDE integration
- Git-aware workflow automation
- Built-in test runners or CI/CD integration

Its SWE strength lies in persistent skill accumulation: over time, it builds a library of coding procedures specific to its user's projects and preferences, becoming increasingly effective as a development companion.

---

## 8. Workflow Design & UX

### CLI Interaction

The primary developer interaction surface. Users type messages, the agent reasons and acts, and results are displayed in the terminal. The ReAct loop is visible -- users can observe the agent's reasoning process.

### Messaging Gateway

A single gateway process connects to multiple platforms (Telegram, Discord, Slack, WhatsApp). Messages from any platform are routed to the same agent instance with unified context. This enables a "message from your phone, continue on desktop" workflow.

### Skill Sharing

Skills are portable documents that can be shared via agentskills.io. The community skill ecosystem means users benefit from others' problem-solving experiences. Installing a skill is as simple as dropping a file into `~/.hermes/skills/`.

### Memory Transparency

MEMORY.md and USER.md are plain text files that users can read, edit, or delete. This provides full transparency into what the agent knows and believes, with the ability to correct misconceptions or remove outdated information.

### Deployment UX

- **Local**: Clone repo, configure API keys, run
- **Serverless**: Deploy on Daytona or Modal with near-zero idle cost
- **VPS**: Run on any $5+ VPS for always-on availability

---

## 9. Integration Capabilities

### MCP (Model Context Protocol)

Hermes Agent supports MCP for tool interoperability. This is the primary integration vector for Bureau, as both systems speak MCP.

### agentskills.io

The open standard for skill sharing enables cross-platform skill portability. Bureau's skills could potentially be packaged in agentskills.io format.

### Multi-Platform Gateway

The messaging gateway provides a standardized interface for reaching the agent from external systems.

### LLM Provider Agnostic

Hermes Agent works with multiple LLM providers, aligning with Bureau's model-agnostic philosophy.

### Honcho User Modeling

Honcho provides an API for user modeling data that could be consumed by external systems, including Bureau's Concierge pipeline.

### Extension via Python Tools

Custom Python tools can be created and registered, providing a flexible extension mechanism for any integration need.

---

## 10. Bureau Integration Fit Assessment

### Synergies

**Skills System Alignment (Very High)**
Both Bureau and Hermes Agent use directory-based skills systems with auto-discovery and activation. Bureau's skills (Micro Mode, Assess Mode, etc.) and Hermes' auto-generated skills share architectural DNA. A unified skill format could make Bureau's 66 agent roles available as Hermes skills and vice versa.

**Markdown Memory Files (Very High)**
Both systems use Markdown files for persistent context injection (Bureau: CLAUDE.md, GEMINI.md; Hermes: MEMORY.md, USER.md). The injection pattern is nearly identical -- file content is read into the system prompt at session start.

**MCP as Shared Protocol (High)**
Both support MCP, providing a clean integration seam. Hermes Agent could connect to Bureau's MCP servers (Qdrant, Memory MCP, Serena, Sourcegraph) to gain capabilities it lacks natively (vector search, knowledge graphs, code navigation).

**Multi-Platform Gateway (High)**
Hermes' messaging gateway (Telegram, Discord, Slack, WhatsApp) could serve as Bureau's communication layer, enabling Bureau-orchestrated coding workflows to be triggered and monitored from chat platforms.

**Self-Improving Agent Model (High)**
Hermes' autonomous skill creation aligns with Bureau's vision of agents that get better over time. Bureau could leverage Hermes' skill creation loop to automatically generate and refine agent role prompts based on operational experience.

**User Modeling Synergy (Medium)**
Hermes' Honcho user modeling and Bureau's Concierge pipeline serve complementary purposes. Honcho builds a Theory of Mind; Concierge classifies messages into operational suites. Combined, they could provide deeply personalized, context-aware agent routing.

### Friction Points

**Generalist vs SWE-Focused (Medium)**
Hermes is a general-purpose autonomous agent; Bureau is specifically for coding environments. Hermes lacks the deep SWE capabilities (AST, LSP, test runners) that Bureau's CLI backends provide. However, this is complementary rather than conflicting.

**No Vector/Graph Memory (Medium)**
Hermes relies on FTS5 text search and Markdown files for memory. It lacks Bureau's Qdrant vector store and Memory MCP knowledge graph. This means Hermes cannot do semantic similarity search or entity-relationship reasoning natively. MCP integration with Bureau's memory servers would fill this gap.

**Single Agent Focus (Low)**
Hermes is designed as a single persistent agent, while Bureau orchestrates 66 specialized roles. Integrating Hermes' persistent memory and skill creation with Bureau's multi-agent model requires careful design.

**Early Maturity (Low)**
Released February 2026, Hermes Agent is young. APIs and architecture may change. However, the project has strong institutional backing from NousResearch and active development.

### Overall Fit Rating: 8.5/10 -- Strong Natural Fit (Frontrunner)

Hermes Agent is the strongest integration candidate for Bureau among the platforms assessed. The alignment across skills systems, memory architecture (Markdown files), MCP protocol, and multi-platform messaging creates a natural integration surface with minimal friction. Hermes fills gaps Bureau has (persistent user modeling, self-improving skills, messaging gateway) while Bureau fills Hermes' gaps (deep SWE capabilities, vector search, knowledge graphs, 66 specialized roles).

### Recommended Integration Pattern

**Symbiotic Pair**: Run Hermes Agent as Bureau's persistent autonomous companion:
1. Hermes provides the always-on messaging gateway and user-facing personality
2. Bureau provides the deep coding capabilities via its 4 CLI backends
3. Hermes' skills feed into Bureau's role prompts; Bureau's coding outcomes feed into Hermes' skill library
4. Share memory via MCP: Hermes reads Bureau's Qdrant/Memory MCP; Bureau reads Hermes' session search
5. Hermes' Honcho user model informs Bureau's Concierge routing decisions
6. Unified skill format on agentskills.io enables community sharing across both platforms

---

## Sources

- [Hermes Agent Official Site](https://hermes-agent.nousresearch.com/)
- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs/)
- [NousResearch/hermes-agent on GitHub](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture/)
- [Persistent Memory Documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/)
- [NousResearch Blog: Hermes Agent](https://nousresearch.com/hermes-agent/)
- [MarkTechPost: Hermes Agent Release](https://www.marktechpost.com/2026/02/26/nous-research-releases-hermes-agent-to-fix-ai-forgetfulness-with-multi-level-memory-and-dedicated-remote-terminal-access-support/)
- [YUV.AI: Hermes Agent Deep Dive](https://yuv.ai/blog/hermes-agent)
- [DeepWiki: NousResearch/hermes-agent](https://deepwiki.com/NousResearch/hermes-agent)
- [AIToolly: Hermes Agent Launch](https://aitoolly.com/ai-news/article/2026-03-25-nousresearch-launches-hermes-agent-a-new-intelligent-agent-framework-designed-to-grow-with-users)

---

## 11. High-Impact Bureau x Hermes Integration Ideas

The following ideas focus on capabilities that emerge only from the combination of both platforms -- things neither Bureau nor Hermes Agent can achieve alone.

---

### 11.1 The Phantom Limb -- Hermes as Bureau's Persistent Nervous System

Bureau's multi-agent coding sessions are powerful but ephemeral. When a session ends, the orchestration graph dissolves. Hermes Agent, by contrast, is always on -- a persistent process with curated memory and session continuity. The Phantom Limb pattern makes Hermes the persistent nervous system that survives between Bureau coding sessions.

Between Bureau sessions, Hermes monitors the codebase, messaging channels, and CI/CD pipelines. It accumulates context in MEMORY.md and its FTS5 session store. When a new Bureau session starts, Hermes injects a "since you were gone" briefing: PRs merged, tests broken, Slack discussions about the codebase, dependency updates, and any issues that came in overnight. Bureau's Concierge pipeline uses this briefing to pre-route to the right agent roles before the user even types a command.

The multiplicative value: Bureau gets temporal continuity it fundamentally cannot have as a session-based orchestrator. Hermes gets deep SWE capabilities it fundamentally cannot have as a generalist agent. The combination is an always-aware, surgically precise coding companion -- a developer's nervous system that never sleeps and never forgets, but can summon 66 specialist roles the moment precision work is needed.

---

### 11.2 Skill Alchemy -- Bidirectional Skill Transmutation Engine

Bureau has 66 hand-crafted agent roles and curated workflow skills (Micro Mode, Assess Mode, Fold/Unfold, Scrimmage, Blast Radius). Hermes has autonomous skill creation -- it writes, tests, and refines skill documents through operational experience. Skill Alchemy connects these two skill ecosystems into a transmutation loop.

Direction 1 (Bureau -> Hermes): Bureau's curated workflow skills are packaged in agentskills.io format and published to Hermes' skill directory. Hermes can now invoke Micro Mode or Blast Radius analysis from a Telegram message. But more importantly, Hermes applies its self-improvement loop to these skills -- tracking success rates, identifying edge cases Bureau's authors never encountered, and proposing refinements back to Bureau.

Direction 2 (Hermes -> Bureau): When Hermes autonomously creates a coding skill through its ReAct loop -- say, a procedure for migrating a specific ORM pattern, or a debugging workflow for a particular error class -- that skill is evaluated against Bureau's quality gates and, if it passes, promoted into a new Bureau agent role prompt or added to an existing role's skill repertoire. Over months, Hermes essentially writes new Bureau roles from operational experience. Neither platform can close this loop alone: Bureau cannot self-author roles, and Hermes cannot orchestrate 66 specialists. Together, the skill ecosystem self-evolves.

---

### 11.3 Honcho-Concierge Fusion -- Theory of Mind Meets Task Routing

Bureau's Concierge ML pipeline classifies incoming messages and routes them to the appropriate agent suite. It is fast and accurate for task classification, but it knows nothing about the user as a person -- their skill level, communication style, risk tolerance, or current cognitive load. Hermes' Honcho integration builds a dialectic Theory of Mind: a structured, evolving model of who the user is and how they think.

Honcho-Concierge Fusion feeds Honcho's user model into the Concierge routing decision. A junior developer asking "fix the auth bug" gets routed differently than a senior architect asking the same thing -- the junior gets Assess Mode with explanations and guardrails, the senior gets Micro Mode with minimal commentary and maximum autonomy. A user who Honcho models as "risk-averse" gets Blast Radius analysis by default; a "move fast" user skips it unless the change touches critical paths.

The fusion also flows in reverse: Bureau's operational outcomes feed back into Honcho's model. If Bureau observes that a user frequently rejects suggestions from a particular agent role, Honcho updates the user model to route around that role in the future. The result is a coding orchestrator that genuinely adapts to the human it serves -- not just to the task, but to the person. Concierge alone cannot build a user model. Honcho alone cannot orchestrate specialist agents. The fusion is deeply multiplicative.

---

### 11.4 The Codex Whisperer -- Autonomous Coding Skill Distillation

Bureau runs complex multi-agent coding sessions that produce rich intermediate artifacts: reasoning chains, code diffs, test results, error traces, and resolution paths. Today, these artifacts disappear when the session ends. The Codex Whisperer makes Hermes a silent observer of Bureau sessions, distilling operational patterns into reusable coding skills.

Hermes watches Bureau sessions through a read-only MCP tap on Bureau's context bus. When Bureau's agents solve a non-trivial problem -- a complex refactor, a subtle bug fix, a tricky migration -- Hermes' skill creation loop activates. It extracts the problem signature, the solution pattern, the tools used, and the verification steps, then writes a skill document. Over time, Hermes builds a "codex" -- a searchable library of every hard problem Bureau has solved, indexed by problem type, language, framework, and codebase.

When a similar problem appears in the future, Hermes surfaces the relevant skill before Bureau even spins up agents. Bureau's Concierge can route directly to the right agent with the right skill pre-loaded, turning what was previously a 20-minute multi-agent reasoning session into a 2-minute pattern application. This is autonomous institutional knowledge capture -- the coding team's tribal knowledge, distilled into machine-executable skills. Bureau generates the knowledge through deep SWE work; Hermes captures, curates, and retrieves it. Neither can do both.

---

### 11.5 The Memory Bridge -- Qdrant/Memory MCP <-> FTS5/MEMORY.md Bidirectional Sync

Bureau's memory stack is semantically rich: Qdrant provides 1024-dimensional vector similarity search, Memory MCP provides entity-relationship graph traversal, and Serena provides code-structural awareness. Hermes' memory stack is textually rich: FTS5 provides blazing-fast full-text search across all past sessions, and MEMORY.md provides curated declarative knowledge. These are complementary, not competing, memory modalities.

The Memory Bridge creates a bidirectional sync layer. Hermes' FTS5 session transcripts are periodically embedded and indexed in Bureau's Qdrant store, making conversational history from Telegram, Discord, and Slack semantically searchable alongside code artifacts. Bureau's Memory MCP entity graph is serialized into structured entries in Hermes' MEMORY.md, giving Hermes awareness of codebase entities (modules, classes, APIs, dependencies) and their relationships without needing its own graph database.

The bridge also enables cross-modal retrieval: a user can ask Hermes on Slack "what was that function we refactored last week?" and Hermes queries both its FTS5 sessions and Bureau's Qdrant vectors to find the answer, combining textual recall with semantic similarity. Bureau gains access to months of conversational context from messaging platforms it has never touched. Hermes gains semantic and structural awareness of codebases it has never deeply analyzed. The unified memory surface is strictly more powerful than either memory stack alone.

---

### 11.6 Scrimmage Evolved -- Cross-Agent Adversarial Skill Tournaments

Bureau's Scrimmage mode pits multiple CLI backends (Claude Code, Gemini CLI, Codex, OpenCode) against each other on the same coding task, then selects the best solution. This is powerful but static -- the agents do not learn from losing. Scrimmage Evolved closes the learning loop by feeding tournament outcomes into Hermes' skill creation engine.

After each Scrimmage, Hermes analyzes the winning and losing solutions. It identifies what made the winner succeed: was it a better algorithm choice, cleaner error handling, more idiomatic code, better test coverage? Hermes distills these patterns into comparative skill documents -- skills that encode not just "how to solve X" but "why approach A beats approach B for problem type X." These comparative skills are then injected into the system prompts of the agents that lost, making them more competitive in future Scrimmages.

Over dozens of Scrimmage rounds, the agents converge toward best practices while maintaining diversity in approach. Hermes acts as the tournament's historian and coach -- roles that require both persistent memory (to track performance trends) and skill creation (to encode lessons). Bureau provides the competitive arena and the diverse agent roster. The result is a self-improving competitive ecosystem where each coding challenge permanently raises the floor for all agents.

---

### 11.7 The Gateway Dispatch -- Chat-Platform-Initiated Bureau Workflows

Today, Bureau is a CLI tool. You must be at a terminal to invoke it. Hermes' multi-platform gateway (Telegram, Discord, Slack, WhatsApp) opens a radical new interaction surface: developers can trigger, monitor, and steer Bureau coding sessions from their phone.

A developer messages Hermes on Slack: "Run Blast Radius analysis on the payment module changes in PR #437." Hermes receives the message through its gateway, constructs the appropriate Bureau invocation (selecting the right agent roles, loading the right context from the Memory Bridge, applying the right Honcho-informed routing), and kicks off a Bureau session in the background. As Bureau works, Hermes streams progress summaries back to Slack. The developer can reply with steering commands: "focus on the database migrations" or "skip the frontend tests."

This is not just a notification layer -- it is a full bidirectional command channel. Hermes' persistent context means it understands abbreviated commands ("do the usual on the auth PR") because it remembers what "the usual" means for this user. Bureau provides the actual SWE firepower. The combination turns Bureau from a terminal-bound tool into an omnipresent coding assistant accessible from any device, any platform, at any time. The gateway becomes the universal developer remote control.

---

### 11.8 Self-Improving Agent Roles -- Hermes as Bureau's Role Optimization Engine

Bureau's 66 agent roles are defined by hand-crafted system prompts and skill configurations. They are powerful but static -- a role defined six months ago operates exactly the same today, regardless of accumulated operational data. Hermes' self-improvement loop can change this fundamentally.

Hermes is given read access to Bureau's role definitions and write access to propose modifications. It monitors the outcomes of each role's activations: which roles produce accepted code, which get their output rejected, which consistently need human correction, and which are rarely invoked. Using its skill self-improvement mechanism, Hermes generates proposed role prompt modifications -- sharpening instructions that are too vague, adding edge case handling that is frequently needed, deprecating capabilities that are never used, and tuning temperature/model selection based on observed performance.

Proposed modifications go through a review queue (surfaced via the Gateway Dispatch to the team lead's Slack). Approved modifications are applied to the role definitions. Over quarters, Bureau's 66 roles are continuously refined by operational reality rather than author intuition. Hermes provides the self-improvement loop and memory infrastructure. Bureau provides the role architecture and the operational data. This is DSPy-style prompt optimization without DSPy -- driven by a persistent agent with a Theory of Mind rather than by gradient-free search.

---

### 11.9 The Dossier Weaver -- Unified Cross-Platform Project Intelligence

Bureau builds per-project "dossiers" -- SQLite databases that accumulate metadata about a codebase. Hermes accumulates project context in MEMORY.md and session histories from conversations across five platforms. The Dossier Weaver merges these into a unified project intelligence layer that draws from both structured analysis and unstructured conversation.

When a developer discusses architectural decisions on Discord, files a bug on Slack, debates API design on Telegram, and codes the implementation through Bureau's CLI -- all of that context is currently siloed. The Dossier Weaver feeds Hermes' cross-platform conversation transcripts into Bureau's project dossier, tagged by topic, author, and timestamp. Bureau's structural code analysis (via Serena and Sourcegraph) is fed into Hermes' MEMORY.md as project context.

The result is a project intelligence system that can answer questions like "Why did we choose PostgreSQL over DynamoDB for the auth service?" by retrieving the Slack discussion from three months ago, linking it to the commit that implemented the decision, and noting that the same developer later wrote a Bureau Assess Mode analysis confirming the choice. Neither Bureau's code-centric dossiers nor Hermes' conversation-centric sessions can answer such questions alone. The Dossier Weaver creates organizational memory that spans code and conversation.

---

### 11.10 Reflexion-by-Proxy -- Hermes as Bureau's External Self-Critic

Bureau's agents operate in a forward pass: they receive a task, reason about it, produce output, and terminate. They do not reflect on their own performance across sessions. Hermes, with its persistent memory and ReAct loop, can serve as Bureau's external reflection layer -- implementing Reflexion-style verbal self-critique without modifying Bureau's core agent loop.

After each Bureau session, Hermes reviews the session transcript, the code produced, and any test results or human feedback. It generates a structured reflection: What went well? What failed? Were the right agent roles selected? Was the Concierge routing optimal? Did any agent produce code that was later rejected or heavily modified? These reflections are stored in Hermes' session database and distilled into MEMORY.md entries that inform future session briefings.

The next time a similar task appears, Hermes' pre-session briefing includes relevant reflections: "Last time we tried to refactor the auth module, the initial approach of splitting the middleware failed because of circular dependencies. The successful approach was to introduce a facade pattern first." Bureau's agents receive this reflection as context, avoiding past mistakes without having been architecturally modified. Hermes provides the persistent reflection capacity. Bureau provides the operational surface that generates experiences worth reflecting on. This adds a learning-from-failure capability to Bureau that it structurally cannot implement as a stateless orchestrator.

---

### 11.11 The Skill Marketplace Bridge -- agentskills.io as Bureau's Public Interface

Bureau's skills are powerful but insular -- they live in a private repository and serve only Bureau users. Hermes' agentskills.io provides a public, standardized skill marketplace with community contributions. The Skill Marketplace Bridge makes Bureau the largest single contributor to agentskills.io while simultaneously importing community-created skills into Bureau's role system.

Bureau's workflow skills (Micro Mode, Assess Mode, Fold/Unfold, Blast Radius) are packaged into agentskills.io format with standardized metadata: required capabilities, input/output schemas, difficulty ratings, and usage examples. They become available to every Hermes Agent installation worldwide. In return, community skills from agentskills.io -- created by thousands of Hermes users solving real problems -- are continuously evaluated for Bureau compatibility. Skills that pass quality gates are auto-imported into Bureau's skill directories, tagged with their community provenance and success metrics.

This creates a network effect: Bureau's curated excellence seeds the marketplace, attracting contributors. Community contributions flow back, expanding Bureau's capabilities beyond what any single team could author. Hermes users who have never heard of Bureau benefit from its workflow innovations. Bureau users who have never used Hermes benefit from the global skill commons. The agentskills.io standard becomes the IETF RFC of agent skills -- and Bureau and Hermes are its founding contributors.

---

### 11.12 Nightwatch -- Autonomous Codebase Health Monitoring

Developers sleep. CI breaks. Dependencies release security patches. APIs deprecate endpoints. Pull requests go stale. Today, these problems wait until a human notices them. Nightwatch makes Hermes an autonomous codebase health monitor that uses Bureau's SWE capabilities to not just detect problems, but fix them.

Hermes runs on a cron schedule (or serverlessly on Daytona/Modal), periodically scanning the codebase for health signals: dependency vulnerabilities (via `npm audit`, `pip-audit`, `cargo audit`), test suite drift, code coverage regressions, stale branches, TODO/FIXME accumulation, and configuration drift. When it detects an issue, it evaluates severity using its accumulated project knowledge from MEMORY.md and the Dossier Weaver's project intelligence.

For low-severity issues, Hermes fixes them directly by invoking Bureau in headless mode -- spinning up the appropriate agent roles to create a fix, running the test suite, and opening a PR. For high-severity issues, Hermes alerts the developer via the Gateway Dispatch (Slack, Telegram, etc.) with a structured briefing and a proposed action plan. The developer can reply "fix it" from their phone and Hermes triggers Bureau to execute the plan. This is autonomous codebase maintenance -- a night shift of AI agents that keeps the codebase healthy while the team sleeps. Hermes provides the persistence, scheduling, and alerting. Bureau provides the surgical coding capability. Together, they create a self-healing codebase.
