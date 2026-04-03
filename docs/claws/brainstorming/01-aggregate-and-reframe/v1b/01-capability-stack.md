# Capability Stack

## Inputs and method

This doc treats `docs/claws/exploration/v1`, `v2`, `v3`, and `v4` as independent research tracks, not as a progression of versions. I aggregated them by capability layer rather than by product so the analysis stays focused on Bureau's strategic question: which ingredients best support memory-native self-improving intelligence, composability into a coherent superset, and long-term differentiation.

The lens categories `deletion`, `hybrid`, and `continue` are useful only as interpretive frames. They are not binding end states, and they do not control the structure of this synthesis. The strongest recurring signal across the corpus is that no single external system wins all layers. Instead, each track contributes one or two unusually strong ingredients:

- Letta is the strongest explicit memory hierarchy. Confidence: high confidence.
- Hermes is the strongest procedural learning ingredient, but with unstable confidence and some identity ambiguity in the later passes. Confidence: mixed evidence.
- OpenHands is the strongest SWE execution ingredient. Confidence: high confidence.
- Bureau is the strongest protocol, governance, and orchestration ingredient. Confidence: high confidence.

| Major judgment | Confidence | Why it matters |
|---|---|---|
| Letta memory hierarchy | high confidence | Repeatedly explicit across all four tracks and directly tied to memory block, recall, and archival design |
| Hermes procedural learning | mixed evidence | The learning loop is strategically strong, but the later passes are more cautious about identity and maturity |
| OpenHands SWE execution | high confidence | Strong agreement across all tracks on sandboxed, auditable execution depth |
| Bureau governance/orchestration | high confidence | Existing branch docs consistently place Bureau as the policy and protocol owner |

The rest of the stack should be read through that lens: what can become a Bureau-native superset, what should remain external, and what needs a contract boundary instead of a replacement.

## Layer 1: Memory / Intelligence

### Strongest ingredients

Letta is the clearest memory-native system in the corpus. Its block hierarchy, recall store, and archival memory recur across `v1/letta-lettabot.md`, `v2/letta.md`, `v3/letta-lettabot.md`, and `v4/02-letta-integration-report.md`. Hermes is the strongest procedural learner: `v1/hermes-agent.md`, `v2/hermes.md`, `v3/hermes.md`, and `v4/01-hermes-integration-report.md` all point to self-curated memory files, FTS5 session recall, and skill creation from experience. Memoh adds the best extraction/compaction/retrieval pipeline; OpenClaw adds tiered memory plus skill discovery; OpenFang adds canonical sessions and embedded SQLite-plus-vector memory; CoPaw adds a cleaner unified API over memory backends.

### Agreements across tracks

The tracks converge on a few non-negotiables. Memory works best when it is layered, not flat. The best systems distinguish working memory, episodic recall, semantic retrieval, and some form of curated or procedural memory. Several tracks also converge on compaction and curation as first-class operations rather than afterthoughts. A second agreement is that durable user understanding matters: Hermes's USER.md, Letta's human block, CoPaw's profile layer, and Memoh's per-user memory all move in that direction.

### Conflicts across tracks

Letta's per-agent memory hierarchy is elegant, but it does not natively solve Bureau's multi-agent shared-state problem. Hermes is stronger at procedural learning than at formal knowledge structure, and the confidence around that learning loop is less stable than the memory design itself. OpenHands is mostly session-local and event-log driven, which is great for reproducibility but weak for long-horizon intelligence. OpenClaw and OpenFang show that breadth and memory can coexist, but they also show the maintenance and trust cost of trying to do everything at once.

### What Bureau-native pieces still matter

Bureau should keep the things it already does better than the field: Qdrant for semantic retrieval, Memory MCP for explicit entity-relation structure, dossiers for resumable workstreams, and protocol-level memory hygiene. Bureau's advantage is not just storage; it is controlled promotion, retrieval discipline, and cross-CLI continuity. The right lesson from the field is not "replace Bureau memory wholesale" but "add a memory compiler and better memory governance on top of what already works."

### Implications for candidate architecture formation

Current frontrunner pattern: a Bureau-owned memory governor paired with an external memory compiler that turns retrieved evidence into candidate memory updates. A memory governor is the policy layer that decides what may be promoted, retained, or retired across memory stores. A memory compiler is the transformation layer that turns raw sessions, logs, or recalls into structured candidate updates.

Live alternatives: a Letta-led self-editing memory stack, a Hermes-led skill-and-memory loop, or a unified ReMe-like store with Bureau as a thin adapter.

Evidence that would decide between them: whether Bureau can keep provenance and rollback cleanly while preserving cross-agent shared state, whether memory writes improve future task quality without drift, and whether the selected layer can support both semantic recall and procedural improvement without duplicate truth sources.

## Layer 2: Assistant Surface

### Strongest ingredients

Hermes is the strongest daily-assistant surface in the more confident passes because it couples multi-channel messaging with a real gateway and background scheduling. Confidence: high confidence. LettaBot adds a clean multiplexer model on top of Letta. Confidence: high confidence. OpenClaw is the maximal breadth option, with broad channel coverage and companion apps. Confidence: high confidence. CoPaw is the strongest iMessage/macOS and Asia-platform option. Confidence: mixed evidence. Memoh gives a compelling multi-bot assistant shell with web UI and nine channels. Confidence: high confidence. OpenFang pushes breadth furthest, but its security and maturity tradeoffs are larger. Confidence: high confidence.

### Agreements across tracks

Across the corpus, assistant surfaces are best when they normalize transport and preserve a single conversational identity across channels. The best examples are Hermes's single gateway, LettaBot's single-agent routing, OpenClaw's common adapter layer, Memoh's per-bot containers with unified chat, and OpenFang's canonical sessions. Several tracks also converge on the value of scheduling, reminders, briefings, and voice or media handling as real differentiators for a non-dev assistant surface.

### Conflicts across tracks

Breadth competes with security. OpenClaw and OpenFang show how a wide channel footprint expands attack surface and governance burden. LettaBot's single-agent routing is clean, but it can underserve Bureau's multi-role architecture unless Bureau stays in charge of task interpretation. CoPaw and Memoh are much more assistant-first than Bureau, which makes them valuable front ends but weak as the system of record. Hermes is balanced, but it does not fully solve the iMessage/macOS problem.

### What Bureau-native pieces still matter

Bureau already has the right shape for the control plane: a channel-agnostic concierge pipeline, a Telegram transport, session state, background runner, and a normalized message envelope. Those pieces matter because they let Bureau preserve policy and role selection while swapping transports underneath. The assistant surface should be treated as a transport layer, not the owner of memory or governance.

### Implications for candidate architecture formation

Current frontrunner pattern: a swappable front door where Bureau owns policy and the assistant surface is a transport/gateway layer. Hermes-like and LettaBot-like gateways are the clearest candidates because they preserve continuity without re-homing the policy brain.

Live alternatives: OpenClaw for maximum breadth, Memoh for multi-bot always-on UI, or CoPaw for macOS/iMessage-heavy environments.

Evidence that would decide between them: channel mix demanded by Bureau users, whether the transport layer must also own memory, and whether the front door can preserve a single task identity without creating a second source of truth.

## Layer 3: SWE Orchestration / Execution

### Strongest ingredients

OpenHands is the strongest execution backend by a wide margin: its Docker sandbox, event stream, and SWE-focused loop recur across `v1/openhands.md`, `v2/openhands.md`, `v3/openhands.md`, and `v4/06-openhands-integration-report.md`. Confidence: high confidence. Bureau is the strongest orchestration layer because it already combines cross-CLI delegation, a large role catalog, Assess Mode, Micro Mode, and a dense MCP stack. Confidence: high confidence. Memoh contributes the strongest general-purpose container-isolated execution substrate. Confidence: high confidence. OpenFang contributes a WASM and security-heavy execution model, while Hermes contributes flexible terminal backends. Confidence: mixed evidence.

### Agreements across tracks

The common pattern is clear: execution should be isolated, auditable, and replayable. Strong systems separate reasoning from action, record an event trail, and support subagents or delegated workers. They also treat tests, review, and rollback as part of execution rather than as a later manual step. OpenHands and Bureau are the clearest articulation of that principle in the corpus.

### Conflicts across tracks

OpenHands is excellent at execution but is not trying to be Bureau's orchestration system. Memoh gives hard isolation but adds a containerization and licensing burden. Hermes's execution backends are flexible, but that flexibility is not the same thing as SWE depth. OpenClaw and OpenFang can execute code, but their breadth-first design is not the same as Bureau's protocolized engineering workflow. The conflict is not "can it run code?" but "who owns the workflow contract?"

### What Bureau-native pieces still matter

Bureau should keep the parts that make execution meaningful: role specialization, Assess Mode, Micro Mode, dossier replay, and the MCP tool mesh. Those are the pieces that turn raw execution into a controlled engineering system. Bureau also needs to keep ownership of high-level task decomposition and review policy, because that is where its strongest differentiation already sits.

### Implications for candidate architecture formation

Current frontrunner pattern: Bureau stays planner/reviewer/policy governor while OpenHands serves as the primary SWE executor. Memoh-like isolation remains a live secondary pattern for higher-risk or less trusted execution.

Live alternatives: a Memoh-first sandbox layer for risky work, or a more generalized Hermes/OpenFang execution fabric for broader but less SWE-specific runtime coverage.

Evidence that would decide between them: whether the task mix is dominated by code repair and repository work, whether the runtime must isolate untrusted code more aggressively than OpenHands does by default, and whether Bureau can preserve a clean evidence trail across task lifecycles.

## Layer 4: Autonomy / Evolution

### Strongest ingredients

Hermes is the strongest procedural evolution engine: skill creation from experience, user-model deepening, and session search recur across `v1/hermes-agent.md`, `v2/hermes.md`, `v3/hermes.md`, and `v4/01-hermes-integration-report.md`. Confidence: mixed evidence. Letta contributes sleep-time style memory updates and self-editing memory. Confidence: high confidence. OpenFang contributes schedule-driven Hands plus calibrated feedback loops like Brier scoring and CRAAP-style research evaluation. Confidence: mixed evidence. CoPaw and Memoh both add heartbeat or cron-based proactive loops. Confidence: high confidence. OpenClaw adds community skill discovery and injection, which is a weaker but still relevant form of evolution. Confidence: mixed evidence.

### Agreements across tracks

The best autonomous systems do not just respond; they schedule, revisit, and improve. They either learn from outcomes or at least remember enough to avoid repeating the same work. There is also broad agreement that evolution should be selective: not every observation deserves to become a permanent policy or memory update. The stronger systems either curate their own memory or gate their own improvement loop.

### Conflicts across tracks

Hermes has the strongest learning story, but the confidence around its procedural learning is less stable than the strength of its memory and channel stories. Letta's learning is powerful but mostly memory-based, not behavior-changing. OpenFang and CoPaw are more schedule-driven than self-improving. OpenClaw's skill ecosystem is broad, but much of it is community-curated rather than autonomously learned. The gap is between "more continuity" and "better self-improvement."

### What Bureau-native pieces still matter

Bureau already has the raw material for evolution: background checks, dispatch-like task loops, skill protocols, and dossier snapshots. What it lacks is a disciplined promotion pipeline for lessons learned. That means Bureau should remain the place where outcomes are judged, lessons are distilled, and behavior changes are approved. The field supports a proposal-first, gate-kept evolution model, not a free-form self-modifying one.

### Implications for candidate architecture formation

Current frontrunner pattern: a gate-kept observe → propose → promote loop where external systems can suggest memory, skill, or policy changes but Bureau decides what graduates into core behavior.

Live alternatives: a Hermes-led self-improving loop that emphasizes skill growth, or a Letta-led memory-first loop that improves continuity more than behavior.

Evidence that would decide between them: whether candidate improvements measurably reduce repeated mistakes, whether the system can prevent bad self-reinforcement, and whether the loop can operate without burying Bureau under maintenance noise.

## Layer 5: Governance / Composability

### Strongest ingredients

Bureau is strongest here by design. Confidence: high confidence. CoPaw contributes tool guards, file guards, and skill scanning. Confidence: high confidence. OpenFang contributes capability gates, audit trails, SSRF protection, prompt-injection defenses, and loop guards. Confidence: mixed evidence. OpenHands contributes Docker isolation and RBAC. Confidence: high confidence. Memoh contributes per-bot container isolation and ACLs. Confidence: high confidence. OpenClaw contributes pairing/approval flows and explicit warnings about trust boundaries. Confidence: mixed evidence. Letta contributes the need for memory auditing and rollback, even where the docs are less prescriptive. Confidence: high confidence.

### Agreements across tracks

Every serious candidate converges on the same governance principles: least privilege, explicit approval points, auditability, and rollback. Broad assistant surfaces are risky unless transport, memory, and action are separated. Composability only works when interfaces are explicit and state ownership is clear. The systems that are strongest in one layer tend to become weaker if they try to own every layer without those boundaries.

### Conflicts across tracks

The main conflict is breadth versus control. OpenClaw and OpenFang show what happens when the surface area grows faster than the trust model. Memoh's container isolation is strong but operationally heavy. Letta's self-editing memory is elegant but needs governance to avoid drift. Hermes's gateway power and OpenHands's execution power both become liabilities if Bureau does not own the contract. Composability is also limited by implementation boundaries: Rust/Python splits, hosted dependencies, and project maturity all matter.

### What Bureau-native pieces still matter

Bureau's role prompts, skills, config hierarchy, MCP routing, dossier workflow, and task-assessment guidance are the governance substrate. This is where Bureau can define what a permitted action looks like, how much autonomy a role gets, and what evidence is required before a change is accepted. If Bureau gives away that layer, it stops being the superset and becomes just another client.

### Implications for candidate architecture formation

Current frontrunner pattern: Bureau as the contract owner that defines composition, approval, and rollback semantics for every external subsystem.

Live alternatives: a more platform-led contract model where an external system owns the gateway or execution boundary, or a federated model where Bureau and one attachment point share governance contracts.

Evidence that would decide between them: whether Bureau can remain the single source of policy truth without bottlenecking iteration, whether external systems can expose trustworthy guardrails, and whether auditability survives multi-layer composition.

## Cross-layer tensions

The major tension is not product choice; it is how to combine the best ingredients without breaking coherence.

- Memory richness versus operational simplicity: Letta, Memoh, and Hermes all push toward deeper memory, but each does so differently, and not all of them map cleanly onto Bureau's multi-agent structure.
- Assistant breadth versus security: OpenClaw, Memoh, and OpenFang widen the surface area, but breadth increases governance burden faster than it increases intelligence.
- Procedural learning versus memory correctness: Hermes-style skill growth is powerful, but without strict provenance and confidence handling it can entrench bad habits.
- Execution sandbox versus orchestration control: OpenHands wants to execute; Bureau wants to govern. That split is good if explicit and dangerous if blurred.
- Multi-channel convenience versus single source of truth: the more channels that can talk to the system, the more important it becomes that Bureau owns state, identity, and decision history.

Another recurring tension is evidence quality. The v1 and v3 passes lean harder toward Hermes because its learning loop feels strategically distinct, while v4 is more conservative and ranks OpenHands and Letta higher because their technical surfaces are more explicit and confidence-limited ambiguity is lower. That divergence is useful: it says the architecture should be modular enough to absorb several candidates, not locked to one option too early.

## Early architecture implications

The combined signal is that Bureau should not be rebuilt around a single external platform. The candidate space now looks more like a set of testable attachment-point variables than a single predetermined end-state: memory compiler behavior, assistant front-door shape, execution boundary, and evolution gate.

That mapping still needs a few hard rules:

- Bureau keeps policy, role governance, and promotion rights.
- External systems may contribute memories, tasks, or candidate skills, but they do not directly rewrite the core without review.
- Channels are transports, not authorities.
- Execution is delegated behind an observable contract.
- Learning is proposal-driven until evidence clears a promotion gate.

This is not the final recommendation. It is the normalized candidate space after the capability stack pass, and it should feed the matrix and narrative rather than pre-decide them.

## Handoff

### Stable inputs for the matrix

- Letta remains the strongest explicit memory hierarchy.
- Hermes remains the strongest procedural learning signal, but with mixed evidence on maturity and canonical identity.
- OpenHands remains the strongest SWE execution ingredient.
- Bureau remains the strongest governance and orchestration ingredient.
- Breadth-heavy assistant surfaces consistently trade convenience for security and composability pressure.

### Questions for the narrative assessment

- Where does the real tension sit: memory unification, assistant breadth, or execution governance?
- Which evidence is strongest enough to treat as a stable ingredient versus a speculative one?
- How much should Bureau absorb directly versus mediate through adapters and contracts?

### Architecture variables to test in candidate formation

- Whether Bureau owns the memory promotion policy or delegates part of it.
- Whether the assistant front door is a gateway, a multiplexer, or a peer system.
- Whether execution is OpenHands-first, Memoh-first, or split by risk tier.
- Whether autonomy is skill-driven, memory-driven, or gate-kept by proposal review.
