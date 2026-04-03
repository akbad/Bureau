# Letta / LettaBot × Bureau integration report

## Platform profile
**Research confidence:** Medium-high.

Letta is an open-source agent framework oriented around persistent memory and stateful agents (historically tied to the MemGPT lineage). Its core value proposition is long-lived agent identity and memory operations beyond short-context prompting.

## Full functionality and feature coverage

### Core capabilities
- Stateful agent runtime with persistent memory concepts.
- Memory block editing/updating as first-class behavior.
- Tools/attachments and task execution loops.
- Agent lifecycle operations (create, run, inspect, evolve).

### Likely UX/workflow shape
- Define agent persona + initial memory.
- Run interaction cycles where the agent may read/update memory.
- Observe and tune memory behavior and execution policy over time.

This contrasts with purely stateless prompt runs and aligns with Bureau’s multi-session continuity goals.

## Memory architecture deep dive and Bureau fit

### Letta strengths
- Explicit memory modeling rather than implicit “hidden context only.”
- Memory write/recall is part of normal runtime behavior.
- Better long-horizon identity coherence than stateless workflows.

### Bureau alignment
- Letta long-term memory can map to Bureau’s semantic + structural memory stack.
- Bureau dossiers (`fold`/`unfold`) can snapshot Letta agent state transitions as portable continuity artifacts.
- Bureau’s skill protocols can enforce memory hygiene on top of Letta writes.

### Integration challenges
- Prompt-cache growth from large memory blocks.
- Potential memory drift if autonomous updates are overly permissive.
- Need robust memory relevance filtering before injecting into active context.

## Autonomous learning loop assessment
Letta-like systems can support “experience accumulation” and adaptive behavior. Bureau can strengthen this via:
- quality gates before memory promotion,
- periodic retrospectives using specialized review agents,
- memory demotion/archival for low-performing behaviors.

## Operational memory stack proposal
- Working context: active prompt/task state.
- Letta short-term memory: recent interaction trail.
- Letta long-term memory: durable agent memory.
- Bureau Qdrant: semantic retrieval across agents/CLIs.
- Bureau graph memory: explicit architecture/project facts.
- Bureau dossiers: resumable workflow state.

## Practical daily assistant features + SWE features

### Daily assistant
- Habit/reminder continuity with stable personal preferences.
- Persistent user profile evolution over time.
- Multi-session personal context without re-briefing.

### SWE assistant
- Codebase conventions retained persistently.
- Reusable debugging lessons and incident patterns.
- Architecture decision recall over long implementation arcs.

## Workflow/UX design fit
The strongest combined UX is:
- Letta handles continuity-rich conversational identity.
- Bureau handles reproducible operations, tooling discipline, and cross-CLI portability.

## Recommendation
High strategic fit. Letta is one of the strongest candidates if the goal is memory-native autonomy with controllable ops.

## High-impact merge concepts (subagent brainstorm section)

### 1) Memory promotion pipeline
Three-stage promotion: `candidate -> reviewed -> canonical`, with Bureau review roles deciding whether Letta memories graduate.

### 2) Dual-memory compiler
Compile Letta freeform memories into:
- Qdrant embeddings for semantic search,
- graph triples for hard-structured retrieval.

### 3) Self-healing memory contracts
Define machine-checkable constraints (e.g., no contradictory architecture facts). Violations trigger automatic reconciliation tasks.

### 4) Persona drift monitor
A watchdog that compares current Letta behavior to baseline role expectations from Bureau prompts and flags drift.

### 5) “Replay + critique” learning lab
Replay past high-stakes episodes; specialized Bureau subagents generate counterfactual alternatives; winning policies update Letta strategy memory.
