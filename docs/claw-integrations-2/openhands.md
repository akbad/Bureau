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
