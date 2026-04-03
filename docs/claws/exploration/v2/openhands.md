# OpenHands -- Bureau Integration Assessment

**Date:** 2026-04-03
**Platform:** OpenHands (formerly OpenDevin)
**Maintainer:** OpenHands Community (academic + industry)
**Repository:** [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands)
**Website:** [openhands.dev](https://openhands.dev/)
**License:** MIT
**Publication:** ICLR 2025
**Contributors:** 188+ contributors, 2,100+ contributions

---

## 1. Platform Overview

OpenHands (formerly OpenDevin) is an open-source platform for AI software developers as generalist agents, published at ICLR 2025. It enables agents to interact with the world like human developers: writing code, operating command lines, navigating web environments, collaborating in multi-agent settings, and being evaluated under standardized benchmarks.

OpenHands is distinguished by its academic rigor (ICLR publication), strong SWE-bench performance, and composable SDK architecture. It spans the full spectrum from research evaluation to production deployment.

### Architecture

OpenHands uses an **event stream architecture** -- all agent-environment interactions flow as typed, immutable events through a central hub:

```
User Message -> Agent -> LLM -> Action -> Runtime (sandbox) -> Observation -> Agent -> ...
```

This event-sourcing pattern treats all interactions as immutable events appended to a log, providing full reproducibility and auditability.

| Component | Role |
|-----------|------|
| Event Stream | Central hub for all typed events (actions + observations) |
| Agent | Reasoning engine (CodeActAgent, BrowsingAgent, etc.) |
| Runtime | Docker-based sandboxed execution environment |
| SDK | Composable Python library powering all interfaces |
| CLI | Terminal interface for local usage |
| GUI | React SPA + REST API for visual interaction |
| Microagents | Keyword-triggered modular knowledge snippets |

### Value Proposition

- **Academic foundation**: ICLR 2025 publication with rigorous evaluation
- **Strong SWE-bench performance**: Leading open-source coding agent
- **Composable SDK**: Python library for building custom agent architectures
- **Docker sandbox**: Kernel-level isolation for safe code execution
- **Multi-agent delegation**: Agents delegate subtasks to specialized agents
- **Model-agnostic**: Works with Claude, GPT, Gemini, and open models
- **MIT license**: Maximally permissive for commercial use

---

## 2. Feature Set

### Agent Types

**CodeActAgent** (Default): Generalist code-writing and debugging agent based on the CodeAct framework. At each step, the agent can:
1. **Converse**: Communicate with humans for clarification or confirmation
2. **Execute code**: Run bash commands, Python code, or browser-specific programming

**BrowsingAgent**: Specialist in web navigation and web-based task execution. Handles complex multi-step web workflows that CodeActAgent delegates to it.

### Multi-Agent Delegation

`AgentDelegateAction` enables agents to delegate subtasks to other agents. For example, CodeActAgent delegates web browsing to BrowsingAgent. This creates a natural division of labor based on agent specialization.

### Docker Sandbox Runtime

Agents execute in Docker-based isolated environments:
- Full Python and bash execution
- File system access (within sandbox)
- Web browsing capabilities
- No impact on host system
- Kernel-level isolation
- Reproducible environments

### SDK

The OpenHands SDK is a composable Python library that powers everything:
- Define agents in code
- Run locally or scale to thousands in the cloud
- Extend with custom actions, observations, and agent types
- Structured input/output for programmatic integration

### Interfaces

- **CLI**: Easiest way to start; powers with any LLM
- **Local GUI**: REST API + React SPA for visual interaction
- **Cloud deployment**: Scale to many concurrent agents

---

## 3. Memory Architecture

### Event Stream (Working Memory)

The event stream IS the memory system. All interactions are recorded as typed events in an append-only log:
- `UserMessageAction` -- user input
- `AgentMessageAction` -- agent responses
- `CmdRunAction` -- shell commands
- `CmdOutputObservation` -- command results
- `FileReadAction` / `FileWriteAction` -- file operations
- `BrowseURLAction` / `BrowserOutputObservation` -- web interactions
- `AgentDelegateAction` -- delegation to sub-agents

This event-sourced architecture provides complete reproducibility: any session can be replayed from its event log.

### Microagents (Procedural Knowledge)

Microagents are modular knowledge snippets triggered by keywords in user or agent messages. They provide context-specific information to help agents solve tasks. When a keyword match is detected, the microagent's content is injected into the agent's context.

This is a form of procedural knowledge: the system "knows how" to handle certain topics by activating relevant microagent content.

### ConversationMemory (Episodic)

The ConversationMemory component processes event history into LLM-consumable messages. It transforms the raw event stream into a structured conversation format that fits within the LLM's context window, with summarization for long histories.

### Comparison with Bureau

| Dimension | Bureau | OpenHands |
|-----------|--------|-----------|
| Architecture | Hub-and-spoke context | Event stream / event sourcing |
| Knowledge Injection | Role prompts, skills, must-read files | Microagents (keyword-triggered) |
| Agent Roles | 66 named roles with context profiles | 2 agent types + delegation |
| Sandbox | Relies on CLI backends | Docker-based kernel isolation |
| Memory Persistence | Qdrant, Memory MCP, SQLite | Event log (session-scoped) |
| Cross-Session | Fold/Unfold dossiers | Not built-in |

---

## 4. Autonomous Learning Loop

OpenHands' learning is primarily through the microagent system rather than autonomous self-improvement:

### Microagent Knowledge Retrieval

When keywords in user messages match microagent triggers, relevant knowledge is injected into the agent's context. This provides domain-specific expertise on demand -- the agent "learns" about a topic by having relevant microagent content activated.

### Event-Sourced History

The complete event stream of past sessions provides raw material for learning, though OpenHands does not currently implement automated learning from past sessions. The event log is available for analysis but is not automatically mined for patterns.

### Community Contributions

Microagents are contributed by the community, creating a shared knowledge base. When one contributor adds a microagent for a common problem, all users benefit.

### Limitations

- No autonomous skill creation
- No self-editing memory
- No cross-session learning by default
- No self-improvement feedback loop
- Microagents are static -- they don't evolve based on usage

---

## 5. Operational Memory Stack

### Working Memory (Event Stream + Context Window)

The current session's event stream, processed by ConversationMemory into LLM-consumable format. Includes recent actions, observations, and any activated microagent content. Limited by the LLM's context window; older events are summarized.

### Procedural Knowledge (Microagents)

Keyword-triggered knowledge snippets providing domain expertise. Static but curated. Analogous to Bureau's role prompts and skill instructions.

### Episodic Memory (Event Log)

Complete session event history. Append-only, immutable. Provides full audit trail and reproducibility. Session-scoped by default (no cross-session persistence built-in).

### Long-Term Memory

OpenHands does **not have a built-in long-term memory system**. There is no vector database, no persistent knowledge graph, and no cross-session memory. Each session starts fresh unless external memory is provided. This is a significant gap compared to Bureau, Hermes, Letta, and other platforms.

---

## 6. Daily Assistant Features

OpenHands is not designed as a daily assistant. It is focused on software engineering tasks:

- **No multi-channel messaging** (terminal/web only)
- **No scheduling or calendar integration**
- **No proactive outreach**
- **No persistent user model**
- **No always-on operation**

Its daily utility is confined to coding tasks: writing code, debugging, web research for development purposes, and automated testing.

---

## 7. SWE Assistant Features

This is OpenHands' primary strength and warrants detailed coverage.

### CodeAct Framework

The CodeActAgent implements the CodeAct paradigm: at each step, the agent can either converse (ask clarification) or execute code (bash, Python, browser). This code-first approach means the agent's capabilities are bounded only by what can be coded, not by a fixed set of tools.

### SWE-Bench Performance

OpenHands is one of the leading open-source agents on SWE-bench, the standard benchmark for automated software engineering. It demonstrates strong capabilities in:
- Bug fixing from issue descriptions
- Code understanding across large repositories
- Multi-file editing
- Test generation and execution
- Git workflow management

### Docker Sandbox

The Docker-based runtime provides genuine isolation:
- Agents can run arbitrary code without risking the host system
- Each session gets a clean environment (or a pre-configured one)
- File system changes are contained within the sandbox
- Network access can be controlled

This is superior to most agent frameworks that either restrict execution or run code in the host environment.

### Multi-Agent Delegation

For complex tasks, CodeActAgent can delegate to BrowsingAgent for web-based subtasks. This pattern is extensible -- custom agent types can be created and registered for delegation.

### SDK Composability

The Python SDK enables building custom agent architectures:
- Define custom agents with specialized capabilities
- Chain agents in workflows
- Integrate with external systems via Python
- Scale from single-agent local to multi-agent cloud

### Limitations

- No IDE integration (terminal/web only)
- No LSP/AST-level code understanding
- No native git-aware workflow (must be coded)
- No built-in test framework integration
- No multi-role specialization (2 agent types vs Bureau's 66)

---

## 8. Workflow Design & UX

### CLI

The simplest entry point. Run `openhands` in a terminal, provide a task description, and the agent works autonomously in a Docker sandbox. Results are displayed in the terminal.

### Local GUI

A React single-page application backed by a REST API. Provides:
- Chat interface for task description
- Real-time streaming of agent actions and outputs
- File browser for sandbox contents
- Terminal view for command execution

### SDK

For programmatic usage:
```python
from openhands import Agent
agent = Agent(model="claude-4.5-sonnet")
result = agent.run("Fix the authentication bug in auth.py")
```

### Cloud Deployment

Scale to many concurrent agents for batch processing (e.g., processing many GitHub issues simultaneously).

---

## 9. Integration Capabilities

### Python SDK

The primary integration mechanism. The SDK is composable and extensible, enabling custom agent definitions, tool registration, and workflow orchestration.

### REST API

The GUI backend exposes a REST API that can be consumed by external systems.

### Docker

The Docker-based runtime provides a standardized execution environment. Agents can be deployed in any Docker-compatible infrastructure.

### Model Agnosticism

Works with Claude, GPT, Gemini, and any OpenAI-compatible endpoint.

### Agent Templates

Custom agent types can be created by extending the base Agent class. This provides a pattern for creating specialized agents.

### Notable Absences

- **No MCP support**: OpenHands does not implement Model Context Protocol. Integration with MCP-based systems requires a bridge.
- **No multi-channel messaging**: Terminal and web GUI only.
- **No persistent memory API**: No external interface for reading/writing agent memory across sessions.

---

## 10. Bureau Integration Fit Assessment

### Synergies

**Docker Sandbox for Bureau Agents (Very High)**
Bureau's 66 agent roles currently rely on their CLI backends for execution isolation. OpenHands' Docker sandbox provides kernel-level isolation that Bureau could use for safe execution of untrusted code, MCP tools, or community-contributed skills. This is the highest-value integration point.

**Microagents Parallel Bureau's Role Prompts (High)**
OpenHands' microagents (keyword-triggered knowledge snippets) are architecturally similar to Bureau's role prompt injection. A unified format could make Bureau's 66 role prompts available as OpenHands microagents and vice versa.

**Multi-Agent Delegation Aligns with Bureau's Subagent Model (High)**
OpenHands' AgentDelegateAction maps naturally to Bureau's subagent invocation model. Bureau could delegate tasks to OpenHands agents running in Docker sandboxes, or OpenHands could delegate to Bureau's specialized CLI backends.

**SWE-Bench Performance as Bureau Backend (High)**
OpenHands' strong SWE-bench performance makes it a candidate as a fifth CLI backend for Bureau (alongside Claude Code, Gemini CLI, Codex, OpenCode). Its Docker sandbox would provide execution isolation that other backends lack.

**SDK Composability (Medium)**
OpenHands' Python SDK could be used to build custom Bureau integrations programmatically, without relying on MCP bridges.

**MIT License (Medium)**
The maximally permissive MIT license removes all legal friction from integration.

### Friction Points

**No MCP Support (High)**
Bureau's architecture is MCP-centric. OpenHands has no MCP support. Integration requires either OpenHands adding MCP or Bureau building a Python SDK bridge. This is the primary friction point.

**No Persistent Memory (High)**
OpenHands sessions start fresh each time. Bureau's agents depend on persistent memory (Qdrant, Memory MCP, SQLite dossiers). To use OpenHands as a Bureau backend, Bureau would need to inject its memory context into OpenHands sessions at startup.

**Overlapping Scope as Coding Platform (Medium)**
Both Bureau and OpenHands are coding agent platforms. The integration must clearly delineate: OpenHands provides the sandboxed execution environment; Bureau provides the multi-agent orchestration, role specialization, and persistent memory.

**Limited Agent Types (Medium)**
OpenHands has 2 agent types (CodeActAgent, BrowsingAgent) vs Bureau's 66 specialized roles. OpenHands would need to rely on Bureau's role prompts for specialization rather than its own agent types.

**No Multi-Channel (Low)**
OpenHands provides no messaging platform support. Bureau would need another system (Hermes, CoPaw, Memoh) for chat-based access.

### Overall Fit Rating: 7/10 -- Strong SWE Complement, Integration Overhead

OpenHands is a strong SWE platform that could serve as a high-performance execution backend for Bureau. Its Docker sandbox, SWE-bench performance, and composable SDK are genuine assets. However, the lack of MCP support, persistent memory, and multi-channel messaging means it fills a narrower role than platforms like Hermes or OpenClaw. It's best positioned as a **sandboxed execution engine** within Bureau's orchestration rather than a full integration partner.

### Recommended Integration Pattern

**Sandboxed Execution Backend**:
1. Use OpenHands' Docker sandbox as Bureau's execution environment for high-risk operations
2. Inject Bureau's role prompts as OpenHands microagents for specialization
3. Bridge Bureau's MCP memory servers into OpenHands sessions via SDK
4. Leverage OpenHands' SWE-bench-class code generation as a Bureau CLI backend
5. Use AgentDelegateAction for Bureau-to-OpenHands task delegation
6. Keep OpenHands focused on execution; Bureau handles orchestration and memory

---

## Sources

- [OpenHands Official Site](https://openhands.dev/)
- [OpenHands/OpenHands on GitHub](https://github.com/OpenHands/OpenHands)
- [OpenHands ICLR 2025 Paper](https://arxiv.org/abs/2407.16741)
- [OpenHands SDK Documentation](https://docs.openhands.dev/sdk)
- [OpenHands Architecture (DeepWiki)](https://deepwiki.com/OpenHands/OpenHands/6.3-agent-configuration)
- [AMD: OpenHands Local AI for Developers](https://www.amd.com/en/developer/resources/technical-articles/2025/OpenHands.html)
- [Amplifi Labs: OpenHands Analysis](https://www.amplifilabs.com/post/openhands-the-open-source-leap-for-agentic-ai-coding)
- [OpenHands SDK Paper (arXiv)](https://arxiv.org/html/2511.03690v1)

---

## 11. High-Impact Bureau x OpenHands Integration Ideas

### 11.1 "The Panopticon" -- Docker Sandbox as Bureau's Universal Execution Layer

Bureau currently inherits whatever execution environment its CLI backends provide. Claude Code runs in the user's shell, Gemini CLI runs in the user's shell, Codex runs in its own sandbox -- there is no unified, auditable, kernel-isolated execution layer across all 66 agent roles. OpenHands' Docker sandbox changes this equation entirely. By routing Bureau agent actions through OpenHands' runtime, every role -- from `security-auditor` to `chaos-engineer` -- executes inside a controlled container with filesystem snapshots, network policies, and resource limits. Bureau orchestrates; OpenHands contains.

The real power is composability: Bureau can spin up role-specific Docker images pre-loaded with the tools each role needs. The `database-admin` role gets a container with psql and migration tools. The `frontend-specialist` gets Node, Vite, and a headless browser. Each container is disposable, its event stream captured, and its filesystem diff exportable. Bureau's Concierge ML pipeline can analyze execution patterns across thousands of sandboxed runs to optimize role-container pairings.

Neither platform can do this alone. Bureau lacks a sandbox; OpenHands lacks multi-role orchestration. Together they create a system where 66 specialized agents execute safely in isolated environments, with every action recorded in an immutable event log that Bureau's MCP servers can index and query.

### 11.2 "Black Box Recorder" -- Event Stream as Bureau's Forensic Audit Trail

Bureau's hub-and-spoke context model tracks what information flows to which agent, but it does not capture a timestamped, typed, immutable record of every action an agent takes and every observation it receives. OpenHands' event stream architecture provides exactly this. By running Bureau sessions through OpenHands' event-sourcing layer, every `CmdRunAction`, `FileWriteAction`, and `AgentDelegateAction` becomes a permanent, replayable record.

This unlocks forensic debugging for Bureau's multi-agent workflows. When a Scrimmage Mode session between Claude Code and Gemini CLI produces a surprising result, Bureau can replay the complete event stream to see exactly which agent made which edit, in what order, and what observations they received. The event stream becomes the "black box recorder" of multi-agent collaboration -- not just logs, but structured, typed events that can be queried, filtered, and replayed programmatically.

For compliance-sensitive deployments, this is transformative. Bureau can prove exactly what its agents did, when, and why. The event stream can be exported to Bureau's Qdrant instance for semantic search over past sessions, or fed into the Concierge ML pipeline for pattern analysis. OpenHands provides the recording infrastructure; Bureau provides the multi-agent sessions worth recording.

### 11.3 "The Rosetta Stone" -- Microagents as a Universal Role Prompt Format

Bureau's 66 role prompts are powerful but locked inside Bureau's orchestration layer. OpenHands' microagents are keyword-triggered knowledge snippets that are powerful but limited to two agent types. Neither system can leverage the other's knowledge base -- until you create a shared format. The "Rosetta Stone" is a bidirectional compiler that converts Bureau role prompts into OpenHands microagents and vice versa, creating a universal format for agent specialization knowledge.

Bureau role prompts contain structured sections: persona, capabilities, constraints, must-read files, MCP server bindings. OpenHands microagents contain trigger keywords, content blocks, and activation conditions. A shared schema would preserve the semantic richness of both: Bureau's role constraints become microagent activation guards, and microagent keyword triggers become Bureau role-switching signals. The result is a portable agent knowledge format that works across both platforms.

The community implications are significant. Bureau's 66 roles become immediately available to the entire OpenHands community (188+ contributors, MIT license). OpenHands' community-contributed microagents become available to Bureau users. The shared format creates a marketplace effect: anyone building agent knowledge in either ecosystem automatically contributes to both. This breaks the current fragmentation where every agent platform reinvents role definitions in incompatible formats.

### 11.4 "The Thunderdome" -- Sandboxed Scrimmage Mode with Deterministic Replay

Bureau's Scrimmage Mode pits multiple CLI backends against each other on the same task, but today those backends execute in the user's environment with no isolation between them. With OpenHands' Docker sandbox, each Scrimmage contestant gets its own identical container, started from the same filesystem snapshot, with the same environment variables and tool versions. The contest is fair, isolated, and reproducible.

But the real innovation is deterministic replay. Because OpenHands captures the complete event stream for each container, Bureau can replay any Scrimmage match from the start. Analysts can watch Claude Code's approach versus Gemini CLI's approach step by step, see where they diverged, and understand why one solution was superior. The Concierge ML pipeline can consume thousands of replayed Scrimmages to learn which backend excels at which types of tasks, building a predictive model for optimal backend selection.

This creates a continuous improvement engine that neither platform can build alone. Bureau provides the multi-backend competition framework and the ML pipeline for analysis. OpenHands provides the isolated execution environments and the event-sourced replay capability. Together they produce a system that not only runs coding competitions but learns from them at scale, getting smarter about backend selection with every Scrimmage round.

### 11.5 "Mission Control" -- AgentDelegateAction as Bureau's 66-Role Dispatch Protocol

OpenHands' `AgentDelegateAction` is elegant but underutilized -- it currently just routes between CodeActAgent and BrowsingAgent. Bureau has 66 specialized roles but no standardized delegation protocol between them. By mapping Bureau's role dispatch onto OpenHands' delegation architecture, every Bureau role becomes an addressable agent that can be invoked by any other role through a typed, event-sourced delegation chain.

Consider a complex task: the `architect` role designs a system, delegates database schema work to `database-admin`, API design to `api-designer`, and frontend scaffolding to `frontend-specialist`. Each delegation is an `AgentDelegateAction` event in the stream, with the delegating agent's context, the target role, the subtask description, and the expected output format. When the subtask completes, the observation flows back through the event stream to the delegating agent. The entire delegation tree is captured, auditable, and replayable.

This transforms Bureau from a "one agent at a time" orchestrator into a genuine multi-agent workflow engine with formal delegation semantics. OpenHands provides the typed event infrastructure and the delegation protocol. Bureau provides the 66 specialized roles and the orchestration logic. The combination creates delegation chains that are deeper, more specialized, and more auditable than either platform supports today.

### 11.6 "The Gauntlet" -- SWE-Bench as Bureau's Continuous Evaluation Backend

Bureau orchestrates multiple CLI backends but has no standardized way to measure their coding performance over time. Is Claude Code getting better at Python refactoring? Is Gemini CLI improving at test generation? Bureau does not know because it has no evaluation framework. OpenHands, as a SWE-bench leader, has deep integration with standardized coding benchmarks. By connecting Bureau's orchestration layer to OpenHands' evaluation infrastructure, every Bureau backend can be continuously benchmarked.

Bureau's Concierge ML pipeline can schedule nightly evaluation runs: each CLI backend processes the same set of SWE-bench tasks inside OpenHands Docker sandboxes. Results are scored, compared, and tracked over time. When a backend's performance degrades after a model update, Bureau detects it automatically and adjusts routing weights. When a new backend is added, it runs the gauntlet before being trusted with production tasks.

The evaluation data feeds back into Bureau's Assess Mode, which currently relies on heuristics to estimate task complexity and select backends. With SWE-bench data, Assess Mode can make evidence-based routing decisions: "This task involves Django ORM migrations; based on 500 evaluation runs, Backend A resolves these 73% of the time versus Backend B's 41%." OpenHands provides the evaluation harness and sandboxed execution; Bureau provides the multi-backend routing and the ML pipeline for analysis.

### 11.7 "The Holodeck" -- Reproducible Coding Sessions via Event Replay for Onboarding and Training

When a Bureau agent produces exceptional work -- a particularly elegant refactoring, a clever debugging session, a well-orchestrated multi-file change -- that knowledge is lost the moment the session ends. Bureau's Fold/Unfold dossiers capture summaries, but not the step-by-step process. OpenHands' event stream captures everything: every command, every file read, every decision point. By combining these capabilities, Bureau can record its best sessions as replayable "holodecks" that new team members can step through.

Imagine onboarding a new developer: instead of reading documentation, they replay a recorded session where Bureau's `architect` role designed the system's authentication layer. They see every file the agent read, every command it ran, every delegation it made to sub-roles. They can pause at any decision point and ask "why did the agent choose this approach?" Bureau's Memory MCP can annotate the replay with context about the codebase state at that time.

For Bureau's own improvement, holodecks become training data. The Concierge ML pipeline can analyze hundreds of recorded sessions to identify patterns: which role prompts produce the best outcomes, which delegation chains are most efficient, which microagent activations correlate with successful task completion. OpenHands provides the event recording and replay infrastructure; Bureau provides the multi-agent sessions, the annotation layer, and the ML analysis pipeline.

### 11.8 "The Diplomat" -- SDK-Driven Programmatic Bureau Orchestration Without MCP

The biggest friction point between Bureau and OpenHands is MCP: Bureau is MCP-centric, OpenHands has no MCP support. Building an MCP bridge is complex and fragile. But OpenHands' Python SDK offers an alternative integration path that bypasses MCP entirely. Bureau can use the SDK to programmatically create, configure, and run OpenHands agents -- injecting role prompts, memory context, and task definitions through Python code rather than MCP protocol messages.

A thin Python orchestration layer sits between Bureau and OpenHands: when Bureau dispatches a task to a role that needs sandboxed execution, the orchestrator instantiates an OpenHands agent via SDK, injects the role's microagent content and relevant Qdrant memory results, starts the Docker sandbox, and streams events back to Bureau's hub. No MCP needed. The SDK handles agent lifecycle, the event stream provides observability, and Bureau's existing orchestration logic stays unchanged.

This "Diplomat" layer also enables gradual integration. Bureau can start by routing only high-risk tasks (code execution, untrusted input processing) through OpenHands sandboxes while keeping routine tasks on existing backends. As confidence grows, more roles can be migrated. The SDK's composability means each role can have a custom OpenHands agent configuration without requiring changes to OpenHands' core. Bureau controls the integration surface; OpenHands provides the execution substrate.

### 11.9 "The Blast Perimeter" -- Blast Radius Analysis Inside Sandboxed Clones

Bureau's Blast Radius skill estimates the impact of a proposed change by analyzing dependency graphs and affected files. But this analysis is static -- it predicts impact without actually executing the change. OpenHands' Docker sandbox enables dynamic blast radius analysis: clone the repository into a sandbox, apply the proposed change, run the full test suite, and observe exactly what breaks. Compare this with a control sandbox where no change was made. The diff between the two event streams IS the blast radius, measured empirically rather than estimated.

Bureau can run multiple blast radius simulations in parallel, each in its own OpenHands container. "What if we change this interface? What if we delete this deprecated module? What if we upgrade this dependency?" Each scenario executes in isolation, and Bureau's Concierge pipeline aggregates the results into a risk assessment. The `security-auditor` role can review the event streams for security implications. The `test-architect` role can identify gaps in test coverage revealed by the simulations.

This turns blast radius analysis from a heuristic into an empirical science. Bureau provides the change proposals, the multi-role analysis pipeline, and the risk aggregation logic. OpenHands provides the isolated execution environments, the event-sourced recording of what actually happened, and the ability to run many scenarios concurrently without any risk to the production codebase.

### 11.10 "The Hive Mind" -- Cross-Session Collective Intelligence via Event Stream Mining

OpenHands' biggest weakness is the lack of cross-session memory -- every session starts from zero. Bureau's biggest challenge is turning individual session outcomes into collective intelligence that improves all future sessions. By combining OpenHands' structured event streams with Bureau's persistent memory infrastructure (Qdrant, Memory MCP, SQLite dossiers), both problems are solved simultaneously.

Every OpenHands session running under Bureau generates a typed event stream. Bureau's Concierge ML pipeline ingests these streams and extracts patterns: "When working on React components, agents that read the existing component tests before writing new components succeed 84% more often." "The `database-admin` role performs better when given schema diagrams as context." "Delegation chains deeper than 3 levels have diminishing returns." These patterns are encoded as new microagents, new role prompt refinements, or new Assess Mode heuristics, and stored in Bureau's persistent memory layer.

The result is a system that gets smarter with every session. OpenHands provides the structured, typed event data that makes pattern extraction possible -- not messy logs, but formal `CmdRunAction`, `FileWriteAction`, and `AgentDelegateAction` events with metadata. Bureau provides the persistent memory to store learned patterns, the ML pipeline to discover them, and the 66-role orchestration framework to apply them. Neither platform alone can close this learning loop: OpenHands lacks persistence, and Bureau lacks structured execution telemetry. Together they create a collective intelligence that emerges from the aggregate of all coding sessions.
