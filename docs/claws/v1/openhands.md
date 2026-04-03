# OpenHands Integration Analysis

**Platform:** OpenHands (formerly OpenDevin)
**Version reviewed:** v1.6.0 (March 30, 2026)
**License:** MIT
**Report date:** April 3, 2026

---

## 1. Platform Overview

OpenHands is an AI-driven software development platform that has evolved from a research project (OpenDevin) into a production-grade system with multiple deployment surfaces: a composable Python SDK, a CLI, a local GUI (React SPA backed by a REST API), a hosted cloud offering, and an enterprise tier with self-hosted Kubernetes and RBAC.

Its defining characteristic is a Docker-based runtime sandbox that provides full operating-system-level isolation for agent-driven code execution. The platform is model-agnostic and supports Claude, GPT, and any LLM backend. With 101 releases and a 77.6% SWE-bench Verified score, it represents one of the strongest autonomous software engineering platforms currently available.

From Bureau's perspective, OpenHands is interesting not as a competitor but as a complementary execution backend. Bureau orchestrates agent roles and workflows; OpenHands provides the sandboxed, instrumented runtime in which complex SWE tasks can be safely executed.

---

## 2. Memory Architecture

### OpenHands: Event Log State

OpenHands uses an **event log** as its primary memory mechanism. Every action (shell commands, file edits, browser interactions) and every observation (command output, file contents, error messages) is recorded sequentially. This log serves as the agent's working memory within a task session.

Key properties:
- **Append-only:** events accumulate chronologically, forming a complete audit trail.
- **Session-scoped:** the event log lives for the duration of a task. In production mode, logs can be persisted beyond the session.
- **Serializable:** the log is the canonical state representation, enabling replay, debugging, and handoff.
- **Context window feed:** the agent's LLM prompt is constructed from the event log, giving it full visibility into what has happened so far.

### Bureau: Fragmented Memory Stack

Bureau uses a multi-layered memory architecture:
- **Qdrant** for vector-based semantic retrieval across agent knowledge.
- **Memory MCP** for structured memory operations via MCP protocol.
- **claude-mem** for Claude-specific memory persistence.
- **Dossier system** for agent-specific profiles and context.

### Comparison

| Dimension | OpenHands | Bureau |
|---|---|---|
| Scope | Single task session | Cross-session, cross-agent |
| Structure | Linear event log | Fragmented (vector, structured, dossier) |
| Persistence | Ephemeral by default, persistent in production | Persistent by design |
| Retrieval | Sequential scan / context window | Semantic search, role-based filtering |
| Cross-agent sharing | Not native | Core design principle |

The two systems are complementary. Bureau provides long-term organizational memory; OpenHands provides detailed, auditable records of what happened during a specific execution. An integration should feed OpenHands event logs back into Bureau's memory stack for post-task analysis and knowledge retention.

---

## 3. Autonomous Learning Loop

### Microagents

OpenHands implements a `BaseGitService` abstract base class for **microagent discovery** across Git providers. Microagents are small, scoped instruction sets that can be discovered from repositories and applied to guide agent behavior on specific codebases.

This is conceptually similar to Bureau's dossier system but operates at the repository level rather than the agent level. Microagents are discovered automatically from Git repositories, meaning the agent can adapt its behavior to project-specific conventions without manual configuration.

### Bureau Comparison

Bureau's 66 agent roles and workflow skills (Assess Mode, Micro Mode) represent a more structured approach to specialization. Where OpenHands discovers project-level guidance from repositories, Bureau assigns purpose-built agent personas with pre-defined capabilities and behavioral constraints.

### Integration Opportunity

Bureau could push dossier-derived instructions into OpenHands as microagents before delegating a task. Conversely, microagents discovered by OpenHands from a target repository could be ingested into Bureau's dossier system to enrich future orchestration decisions.

---

## 4. Operational Memory Stack

OpenHands' operational memory during task execution consists of:

1. **Event stream:** the ordered sequence of action-observation pairs.
2. **Sandbox filesystem state:** the actual files within the Docker container, reflecting all edits made.
3. **Browser state:** if BrowsingAgent is active, the current page and DOM context.
4. **Plugin state:** any active plugins (Jupyter kernels, VS Code instances) maintain their own runtime state.

In production deployments, OpenHands adds:
- **Persistent event logs** that survive container teardown.
- **Resource guardrails** (CPU/RAM caps) to prevent runaway execution.
- **MCP sidecars** for external tool access.
- **HITL gateway** for human-in-the-loop approval workflows.

Bureau's operational memory is richer in cross-agent coordination (Qdrant vectors, Memory MCP, Telegram state) but lacks the fine-grained execution-level telemetry that OpenHands' event stream provides. An integration would give Bureau visibility into the internal reasoning and execution steps of delegated tasks.

---

## 5. Practical Assistant Features

OpenHands is narrowly focused on software development. It does not attempt to be a general-purpose assistant. Practical assistant capabilities are limited to:

- **File management:** read, write, edit files within the sandbox.
- **Shell execution:** run arbitrary commands in an isolated bash environment.
- **Web browsing:** navigate and interact with web pages (via BrowsingAgent).
- **Jupyter notebooks:** execute and iterate on notebook cells.

There is no calendar integration, no email handling, no personal productivity tooling. OpenHands does one thing -- software engineering -- and does it well.

For Bureau, this is a feature, not a limitation. Bureau already handles the practical assistant layer through its Telegram concierge, ML classification, and MCP server ecosystem. OpenHands fills the execution gap that Bureau's orchestration layer cannot safely address on its own.

---

## 6. SWE Assistant Features

This is where OpenHands excels and where the integration value is highest.

### 6.1 SWE-bench Performance

A 77.6% score on SWE-bench Verified places OpenHands among the top autonomous coding systems. This means it can resolve real-world GitHub issues from popular open-source projects -- understanding the codebase, identifying the root cause, writing a fix, and validating it -- with high reliability.

### 6.2 Docker Sandbox Runtime

The sandbox is OpenHands' most important architectural feature:

- **Custom runtime images:** OpenHands builds an "OH Runtime Image" on top of any user-specified base image. This means it can work with any tech stack, language, or toolchain.
- **Full OS environment:** the agent gets a real Linux environment with bash, not a simulated or restricted shell. It can install packages, compile code, run test suites, start services.
- **EventStream protocol:** actions are sent to the ActionExecutor inside the container; observations flow back. This clean separation means the agent backend never shares a process space with executed code.
- **Bind mounts and volumes:** `SandboxConfig` supports Docker bind mounts and named volumes. An overlay mode provides copy-on-write semantics for bind mounts, preserving the original filesystem.
- **Port allocation:** file-locked port ranges enable multiple concurrent sandboxes without conflicts.
- **Per-task isolation:** each task session gets its own container. No cross-contamination between tasks.

### 6.3 Browser Integration

BrowsingAgent can navigate web pages, fill forms, click elements, and extract content. This enables tasks that require reading documentation, checking deployed services, or interacting with web-based tools.

### 6.4 Multi-Agent Capability

OpenHands supports multiple agent types (CodeActAgent, BrowsingAgent) that can be composed for complex workflows. The agent framework is extensible via the plugin system.

### 6.5 Model Agnosticism

Any LLM backend can drive the agent. This means Bureau can pair OpenHands with whichever model is best suited for a specific task type -- Claude for nuanced reasoning, GPT for certain code generation patterns, or specialized models for domain-specific work.

---

## 7. Channel & Platform Support

| Surface | Description | Bureau Relevance |
|---|---|---|
| **Python SDK** | Composable library, core agentic engine | Primary integration point -- Bureau can import and drive OpenHands programmatically |
| **CLI** | Terminal interface, similar to Claude Code/Codex | Familiar UX for Bureau operators; can be invoked as a subprocess |
| **Local GUI** | REST API + React SPA | Useful for debugging and monitoring delegated tasks |
| **Cloud** | Hosted infrastructure | Alternative to self-hosting; reduces operational burden |
| **Enterprise** | Self-hosted Kubernetes, RBAC, fine-grained access | Production deployment path for Bureau at scale |
| **GitHub/GitLab** | Auth and repository integration | Enables Bureau to delegate repository-scoped tasks directly |
| **Slack/Jira/Linear** | Cloud/Enterprise integrations | Overlaps with Bureau's Telegram concierge; potential for unified notification routing |
| **MCP Registry** | External tool discovery | Bureau's 15+ MCP servers could be registered as OpenHands tools |

### Integration Topology

The Python SDK is the cleanest integration point. Bureau agents can instantiate an OpenHands session programmatically, pass a task specification, monitor the event stream, and collect results -- all without leaving the Python process. The CLI is a fallback for simpler delegation patterns (subprocess invocation with structured output).

The REST API backing the local GUI could also serve as an integration surface, enabling Bureau to manage OpenHands sessions over HTTP if process-level coupling is undesirable.

---

## 8. Security Model

### Docker Sandbox Isolation

OpenHands' security model is built on container isolation:

- **No host access:** agent-executed code runs exclusively inside Docker containers. The host filesystem, network, and process space are protected by container boundaries.
- **Per-session containers:** each task gets its own container. A compromised agent in one session cannot affect another.
- **Resource caps:** CPU and RAM guardrails prevent denial-of-service from runaway processes.
- **Overlay mounts:** copy-on-write semantics for bind mounts mean the agent can read host-provided files without being able to modify the originals.
- **Port isolation:** file-locked port ranges prevent port conflicts and unauthorized access between concurrent sessions.

### Enterprise Security

The enterprise tier adds:
- **RBAC:** role-based access control for multi-user environments.
- **Fine-grained permissions:** control which operations agents can perform.
- **HITL gateway:** human approval required for sensitive operations.

### Bureau Security Implications

Bureau currently runs agents (Claude Code, Gemini CLI, Codex, OpenCode) with varying degrees of host access. Delegating execution-heavy tasks to OpenHands sandboxes would materially improve Bureau's security posture:

1. **Code execution isolation:** Bureau agents could reason about code changes without executing them locally. Execution happens in OpenHands containers.
2. **Blast radius containment:** a hallucinated `rm -rf` or a malicious dependency runs inside a disposable container, not on the host.
3. **Audit trail:** the event log provides a complete record of everything the agent did, enabling post-hoc security review.
4. **Resource protection:** CPU/RAM caps prevent a single task from degrading the host system.

The main security concern is the Docker socket. OpenHands requires Docker access to create containers, and the Docker socket is a privileged resource. On macOS (Bureau's primary platform), Docker Desktop provides adequate isolation for development use, but production deployments should use rootless Docker or a dedicated container runtime.

---

## 9. Integration Architecture

### Primary Pattern: Bureau Orchestrates, OpenHands Executes

The highest-value integration pattern positions OpenHands as a sandboxed execution backend for Bureau's SWE workflows.

```
Bureau Agent (orchestrator)
    |
    |-- Assess Mode: analyze task, determine complexity
    |-- Micro Mode: break into sub-tasks if needed
    |
    v
OpenHands SDK (execution)
    |
    |-- Spawn Docker sandbox
    |-- Execute code changes
    |-- Run tests
    |-- Return event log + results
    |
    v
Bureau Agent (review + commit)
    |
    |-- Review event log
    |-- Validate results
    |-- Commit / report back
```

### Implementation Approach

1. **SDK integration layer:** A Bureau MCP server or skill that wraps the OpenHands Python SDK. Bureau agents invoke it like any other tool.

2. **Task specification format:** Bureau constructs a structured task description (repository URL, branch, issue description, acceptance criteria) and passes it to OpenHands.

3. **Event stream monitoring:** Bureau subscribes to the OpenHands event stream during execution. This enables:
   - Progress reporting to the Telegram concierge.
   - Early termination if the agent goes off-track.
   - HITL intervention via Bureau's existing approval workflows.

4. **Result ingestion:** On task completion, Bureau:
   - Extracts the final diff from the sandbox filesystem.
   - Ingests the event log into the fragmented memory stack (Qdrant) for future reference.
   - Updates the relevant dossier with lessons learned.

5. **MCP bridge:** Bureau's 15+ MCP servers could be exposed to OpenHands via its MCP Registry, giving the sandboxed agent access to Bureau's tool ecosystem without breaking isolation.

### Concrete Use Cases

- **Complex bug fixes:** Bureau's Assess Mode identifies a multi-file bug. Instead of running Claude Code directly on the host, Bureau delegates to OpenHands, which can safely run the test suite, iterate on fixes, and return a validated patch.
- **Dependency upgrades:** OpenHands spins up a sandbox with the target dependency version, runs the full test suite, and reports compatibility issues.
- **Code generation from specs:** Bureau agents write specifications; OpenHands generates, tests, and refines the implementation in isolation.
- **Repository exploration:** For unfamiliar codebases, OpenHands can clone, build, and explore a repository in a sandbox without polluting the host environment.

---

## 10. Fit Assessment

### Strengths for Bureau Integration

| Factor | Rating | Notes |
|---|---|---|
| Execution isolation | Strong | Docker sandbox is exactly what Bureau lacks |
| SWE capability | Strong | 77.6% SWE-bench; best-in-class autonomous coding |
| Python SDK | Strong | Native integration with Bureau's Python codebase |
| Model agnosticism | Strong | Bureau can use its preferred LLM backends |
| MIT license | Strong | No licensing friction |
| MCP support | Moderate | MCP Registry exists; bridge to Bureau's servers is feasible |
| Event log auditability | Strong | Complete execution telemetry feeds Bureau's memory stack |

### Weaknesses / Gaps

| Factor | Rating | Notes |
|---|---|---|
| macOS Docker overhead | Moderate | Docker Desktop on macOS adds latency and resource consumption |
| No cross-session memory | Weak | OpenHands forgets between tasks; Bureau must manage continuity |
| Limited assistant features | N/A | Not a gap -- Bureau handles this layer |
| Enterprise cost | Unknown | Cloud/Enterprise pricing not evaluated |
| Container startup time | Moderate | Building custom OH Runtime Images adds cold-start latency |

### Overall Fit: High

OpenHands fills Bureau's most significant architectural gap: safe, isolated, instrumented code execution. Bureau's orchestration, memory, and multi-agent coordination capabilities complement OpenHands' execution engine. The integration is natural -- both are Python-based, both support MCP, and the SDK provides a clean programmatic interface.

---

## 11. Risks & Tradeoffs

### Operational Risks

1. **Docker dependency:** Bureau gains a hard dependency on Docker. On macOS, this means Docker Desktop must be running, consuming resources even when idle. Mitigation: lazy container startup, aggressive cleanup of completed sandboxes.

2. **Cold start latency:** Building the OH Runtime Image on first use for a given base image takes time. Subsequent runs use cached images, but the first invocation for a new tech stack will be slow. Mitigation: pre-build images for common stacks (Python, Node, Go, Rust).

3. **Resource consumption:** Each sandbox is a full Docker container. Running multiple concurrent tasks consumes significant memory and CPU. Mitigation: use OpenHands' resource guardrails; limit concurrent sandboxes based on host capacity.

4. **Complexity budget:** Adding OpenHands to Bureau's stack increases operational complexity. There are now two systems to update, configure, and debug. Mitigation: encapsulate OpenHands behind a single MCP server or skill; keep the integration surface minimal.

### Architectural Risks

5. **State synchronization:** Bureau and OpenHands have independent state models. Keeping them consistent (e.g., ensuring Bureau's memory reflects what OpenHands actually did) requires careful event log parsing and error handling.

6. **Version coupling:** OpenHands releases frequently (101 releases). Breaking changes in the SDK could disrupt Bureau's integration. Mitigation: pin SDK versions; test upgrades in isolation.

7. **Security surface:** The Docker socket is a privileged resource. A bug in OpenHands' container management could expose the host. Mitigation: use rootless Docker in production; audit OpenHands' container lifecycle code.

### Strategic Tradeoffs

8. **Build vs. integrate:** Bureau could build its own sandboxed execution layer instead of depending on OpenHands. However, replicating OpenHands' 77.6% SWE-bench performance, battle-tested sandbox, and active development community would be a massive engineering investment. Integration is the pragmatic choice.

9. **Tight vs. loose coupling:** The SDK integration (tight coupling) gives the best UX and performance but creates a hard dependency. A REST API integration (loose coupling) is more resilient but adds network overhead and complexity. Recommendation: start with SDK integration, add REST API as a fallback.

10. **Cloud vs. self-hosted:** OpenHands Cloud eliminates Docker management overhead but introduces network latency and data sovereignty concerns. For development and personal use, local Docker is preferred. For team/production use, evaluate the enterprise self-hosted Kubernetes option.

---

*This analysis is based on OpenHands v1.6.0 architecture and Bureau's current multi-agent orchestration design. Reassess if either system undergoes significant architectural changes.*

---

## 12. High-Impact Feature Merges & Extensions

The following ideas represent high-differentiation capabilities that become possible only when Bureau's orchestration layer and OpenHands' sandboxed execution runtime are combined. Each targets a gap that neither system can fill alone.

---

### 12.1 Assess Mode with Live Verdict Verification

Bureau's Assess Mode currently builds a mental model and audits files against quality standards, but its findings are static -- it reasons about code without executing it. With OpenHands integration, Assess Mode's second phase (the audit pass) spawns a transient sandbox per finding: if the reviewer suspects a race condition, it writes a targeted concurrency stress test and runs it; if it flags a missing null check, it crafts an input that triggers the crash. Each audit finding gets an attached "verified" or "unverified" tag based on actual execution evidence, and the concrete reproducer is included in the report.

**Why it matters:** Review tools that can prove their own findings collapse the feedback loop from "the reviewer thinks this is a bug" to "here is a failing test," eliminating an entire round-trip of developer triage.

---

### 12.2 Micro Mode with Sandboxed Step Gates

Micro Mode's DAG-based planning already pauses after each atomic edit for user approval. By wiring each step gate to an OpenHands sandbox checkpoint, the system can run the project's test suite (or a targeted subset) after every single edit, presenting the user with a green/red signal alongside the diff. If a step breaks tests, Micro Mode can automatically roll back the sandbox to the previous checkpoint and re-attempt with a corrected approach -- all before the user even sees the failed attempt. The sandbox filesystem is snapshotted via Docker commit at each gate, making rollback instantaneous.

**Why it matters:** Step-gated editing becomes step-gated-and-verified editing. Users gain proof that each atomic change is independently correct, not just syntactically plausible, turning Micro Mode into a formally progressive construction process.

---

### 12.3 Role-Isolated Sandboxes (Per-Agent Security Domains)

Each of Bureau's 66 agent roles executes inside its own OpenHands Docker container with a tailored security profile. The `security-compliance` role gets a sandbox with Semgrep, Trivy, and network access to vulnerability databases but no write access to source files. The `debugger` role gets a sandbox with GDB, strace, and the failing test harness but no network egress. The `architect` role gets read-only access to the full codebase plus a scratchpad volume for design documents. Bureau's orchestration layer enforces these profiles declaratively via a new `sandbox_profile` field in role definitions, mapping each role to an OpenHands `SandboxConfig` with specific bind mounts, resource caps, and network policies.

**Why it matters:** No existing agent framework enforces least-privilege execution at the role level. This makes Bureau the first system where "the debugger agent literally cannot modify production code" is an architectural guarantee, not a prompt-level suggestion.

---

### 12.4 Dossier Snapshots with Full Sandbox State

Bureau's dossier system currently stores agent profiles and textual context. With OpenHands integration, a dossier snapshot expands to include the full sandbox state at a meaningful checkpoint: filesystem tarball, installed packages, environment variables, running services, and the event log up to that point. When a future task resembles a previous one, Bureau can restore the snapshot as an OpenHands sandbox base image, giving the agent a warm start with the exact environment and partial progress from the prior session. Snapshots are indexed in Qdrant by task description embedding, enabling semantic retrieval of "the closest prior working state."

**Why it matters:** This creates resumable, transferable execution contexts. An agent working on a React upgrade can pick up exactly where a previous session left off -- dependencies installed, test suite configured, half the migration complete -- instead of rebuilding from scratch.

---

### 12.5 Spec-Kit to Sandbox Pipeline (Spec-Driven Execution)

Bureau's spec-kit workflow already produces specs, implementation plans, and tasklists. The integration adds an "execute" phase: each tasklist item is dispatched to OpenHands as an independent, sandboxed coding task with acceptance criteria derived from the spec. OpenHands generates the implementation, runs the spec's test criteria, and returns a validated patch. Bureau's orchestrator sequences the tasks respecting the dependency graph from the spec, merges validated patches incrementally, and runs integration tests in a final sandbox after all tasks complete. If any task fails its acceptance criteria after N retries, the pipeline halts and surfaces the failure with the full event log for human intervention.

**Why it matters:** This closes the loop from "agent writes a plan" to "agent executes the plan with proof of correctness" entirely within one system. Spec-kit becomes not just a planning tool but an end-to-end delivery pipeline where every deliverable is sandbox-verified before it touches the real codebase.

---

### 12.6 Cross-CLI Competitive Execution (Tournament Mode)

Bureau's multi-CLI orchestration (Claude Code, Gemini CLI, Codex, OpenCode) gains a new capability: for high-stakes tasks, Bureau dispatches the same task specification to multiple OpenHands sandboxes, each driven by a different LLM backend. Claude, GPT, and Gemini each produce an independent solution in isolated containers. Bureau's Assess Mode then evaluates all solutions against the same criteria -- test pass rate, code quality metrics, diff size, execution time -- and selects the best one (or synthesizes a hybrid). The losing solutions are discarded but their event logs are ingested into Qdrant to inform future model-routing decisions, building a corpus of "which model does best on which task type."

**Why it matters:** No agent framework currently supports competitive multi-model execution with automated adjudication. This turns Bureau into a meta-optimizer that empirically learns per-task model strengths rather than relying on static heuristics or user intuition.

---

### 12.7 Scrimmage Mode with Real Attack Execution

Bureau's Scrimmage Mode currently generates attack vectors across five categories (input validation, state, failure modes, concurrency, security) but relies on the agent reasoning about whether they would succeed. With OpenHands, every generated attack vector is actually executed in an isolated sandbox: malformed inputs are sent to running services, concurrent requests are fired in parallel, and the sandbox captures whether the service crashes, leaks data, or deadlocks. Scrimmage Mode's report transforms from "these attack vectors might work" to "these 3 out of 12 attacks caused observable failures, here are the stack traces and reproduction steps."

**Why it matters:** This converts a theoretical security review into an automated penetration test. The agent doesn't just hypothesize vulnerabilities -- it demonstrates them with evidence, producing output comparable to a human security engineer's findings.

---

### 12.8 Event Log Memory Distillation

After every OpenHands task completes, Bureau's memory pipeline processes the full event log (which can contain hundreds of action-observation pairs) through a distillation step: an LLM summarizes the event log into structured lessons -- "this library requires flag X when running on ARM," "the test suite needs Redis running before integration tests," "module Y has an undocumented circular import with Z." These distilled facts are stored in Qdrant with embeddings tied to the repository, tech stack, and task type. On future tasks in the same codebase, Bureau injects relevant distilled knowledge as microagent instructions before OpenHands begins, so the agent never repeats the same discovery process twice.

**Why it matters:** OpenHands forgets between sessions by design. This feature gives Bureau the ability to accumulate institutional knowledge from sandboxed execution and feed it forward, creating an organizational memory that makes every subsequent task in a codebase faster than the last.

---

### 12.9 Blast Radius Mode with Dependency Graph Execution

Bureau's Blast Radius Mode currently performs static impact analysis -- enumerating callers, dependents, and affected tests. With OpenHands, the analysis becomes dynamic: for each identified dependency, the sandbox checks out the dependent module, applies the proposed change, and runs its tests. The blast radius report then includes not just "these 14 modules depend on the changed function" but "of those 14, 11 still pass, 2 fail with type errors, and 1 has a subtle behavioral change where the return value shifted from `None` to an empty list." Each failure includes the exact test output and a suggested fix generated in the sandbox.

**Why it matters:** Static dependency analysis misses runtime behavioral changes. This feature provides empirical blast radius measurement -- the kind of confidence that currently requires a human engineer to manually check each downstream consumer.

---

### 12.10 Hot-Swappable Sandbox Environments for Polyglot Monorepos

Bureau gains awareness of per-directory tech stacks within monorepos by reading workspace configuration files (package.json, Cargo.toml, go.mod, pyproject.toml). When a task spans multiple stack boundaries -- say, a gRPC schema change that affects a Rust service, a TypeScript client, and a Python ML pipeline -- Bureau decomposes the task and spins up a dedicated OpenHands sandbox per stack segment, each with the correct runtime image (Rust nightly, Node 22, Python 3.12). The orchestrator coordinates cross-sandbox communication via shared volumes for generated artifacts (protobuf outputs, compiled binaries), running each segment's test suite in its native environment. Integration validation happens in a final "composition sandbox" that runs the end-to-end test suite.

**Why it matters:** Current coding agents treat monorepos as flat codebases and stumble when a task requires compiling Rust, running npm, and executing pytest in the same session. This decomposes polyglot tasks into properly isolated, natively-tooled execution environments while preserving cross-boundary coordination.

---

### 12.11 Safeguard Mode with Continuous Invariant Monitoring

Bureau's Safeguard Mode defines system invariants (value constraints, state machines, ordering guarantees) that must hold after changes. With OpenHands, these invariants become runtime assertions executed continuously in a background sandbox. While the primary coding agent makes changes, a parallel OpenHands container runs the invariant suite against each intermediate state of the codebase -- not just the final result. If an intermediate edit violates an invariant, the monitoring sandbox signals Bureau's orchestrator, which can pause the primary agent before further damage compounds. The invariant violations are reported with the exact commit (or edit) that caused the breach and the specific assertion that failed.

**Why it matters:** Current invariant checking is post-hoc: you verify after all changes are complete. Continuous sandboxed monitoring catches violations at the moment of introduction, preventing the common failure mode where an early mistake is buried under subsequent changes that make it harder to diagnose and fix.
