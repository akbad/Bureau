# Research landscape: agentic skill development (March 2026)

> Collation of findings from five parallel research agents covering frameworks, self-improving patterns, platforms/standards, autonomous skill creation, and skill quality/improvement loops. Organized by theme for cross-cutting reference.

***Contents***

- [1. Standards and interoperability](#1-standards-and-interoperability)
  - [SKILL.md as universal format](#skillmd-as-universal-format)
  - [MCP (Model Context Protocol)](#mcp-model-context-protocol)
  - [Agent-to-Agent (A2A)](#agent-to-agent-a2a)
  - [AAIF consolidation](#aaif-consolidation)
- [2. Frameworks for skill learning](#2-frameworks-for-skill-learning)
  - [Research-origin systems](#research-origin-systems)
  - [Production-bridging systems (March 2026)](#production-bridging-systems-march-2026)
  - [Multi-agent orchestration frameworks](#multi-agent-orchestration-frameworks)
  - [Coding tools](#coding-tools)
- [3. Self-improving agent patterns](#3-self-improving-agent-patterns)
  - [Reflexion (verbal self-critique)](#reflexion-verbal-self-critique)
  - [Skill distillation](#skill-distillation)
  - [Prompt evolution (DSPy)](#prompt-evolution-dspy)
  - [Memory-augmented learning](#memory-augmented-learning)
  - [A/B testing for skills](#ab-testing-for-skills)
  - [Self-modification guardrails](#self-modification-guardrails)
  - [Recommended adoption order](#recommended-adoption-order)
- [4. Autonomous skill creation pipeline](#4-autonomous-skill-creation-pipeline)
  - [Key systems compared](#key-systems-compared)
  - [Meta-prompting and optimization](#meta-prompting-and-optimization)
  - [Production path for a skill forge](#production-path-for-a-skill-forge)
- [5. Skill quality and improvement loops](#5-skill-quality-and-improvement-loops)
  - [Measurement](#measurement)
  - [Refinement loops](#refinement-loops)
  - [Regression prevention](#regression-prevention)
  - [Practical patterns (increasing automation)](#practical-patterns-increasing-automation)
- [6. Platforms and marketplaces](#6-platforms-and-marketplaces)
  - [Claude Code plugin system](#claude-code-plugin-system)
  - [OpenAI skills catalog](#openai-skills-catalog)
  - [AgentSkillOS](#agentos)
  - [Memory platforms](#memory-platforms)
  - [Workflow engines](#workflow-engines)
- [7. Benchmarking and evaluation](#7-benchmarking-and-evaluation)
  - [SkillsBench (critical finding)](#skillsbench-critical-finding)
  - [SWE-bench](#swe-bench)
- [8. Key takeaways for Bureau](#8-key-takeaways-for-bureau)

---

## 1. Standards and interoperability

### SKILL.md as universal format

SKILL.md has emerged as the **de facto cross-platform standard** for agent skill definitions. The Agent Skills spec (`agentskills.io`) was adopted by 30+ tools within 90 days of publication. Bureau already uses SKILL.md as its skill format, which places it on the right side of the convergence happening across the ecosystem.

Cross-platform portability is real and validated: skills authored in SKILL.md format work across Claude Code, Codex, and other tools that have adopted the standard. EvoSkill (see below) produces standard SKILL.md output, further reinforcing the format as a lingua franca.

### MCP (Model Context Protocol)

MCP has reached **97 million monthly SDK downloads** as of early 2026. The 2026 roadmap includes investigation of a dedicated **Skills primitive**, which could formalize skill discovery and invocation at the protocol level. MCP is now under AAIF governance.

### Agent-to-Agent (A2A)

A2A provides **Agent Cards** for service discovery and is positioned as complementary to MCP (MCP handles tool invocation; A2A handles inter-agent communication and capability advertisement).

### AAIF consolidation

The Linux Foundation's AAIF initiative is consolidating MCP, AGENTS.md, and Goose under a single governance umbrella. This signals that the fragmented agent standards landscape is beginning to cohere around a small number of interoperable specifications.

---

## 2. Frameworks for skill learning

### Research-origin systems

| System | Core pattern | Key innovation | Limitations |
|:-------|:-------------|:---------------|:------------|
| **Voyager** | Code-as-skill library | Embedding retrieval + self-verification gate + curriculum-driven exploration | Research only; no versioning; foundational but not production-ready |
| **CRADLE** | General computer control | Retrieve, judge, update/create lifecycle for skill curation | Screenshot-based interaction model; less applicable to CLI/code agents |

These systems established the theoretical foundations (skill libraries, self-verification, curation lifecycles) that newer production-oriented systems build on.

### Production-bridging systems (March 2026)

Two systems published in March 2026 bridge the gap between research and production:

**EvoSkill** -- Self-evolving skill framework using three specialized agents (Executor, Proposer, Skill-Builder). Maintains a Pareto frontier of agent programs and produces standard SKILL.md output. Demonstrated **+7.3-12.1%** improvement on benchmarks. Notable for directly outputting the industry-standard skill format.

**AutoSkill** -- Experience-driven skill evolution with both online extraction (from live dialogues) and offline extraction (from archived sessions). Uses an **add/merge/discard judge** for skill curation and supports versioned merging. Ships with an OpenAI-compatible proxy, making it the most production-ready system. Most directly applicable to Bureau's architecture.

### Multi-agent orchestration frameworks

LangGraph, CrewAI, AutoGen, and OpenAI Agents SDK treat skills as orchestration nodes rather than standalone learnable units. These frameworks coordinate skill execution but do not implement skill learning or self-improvement. They are complementary to, not competitive with, skill development systems.

### Coding tools

Cursor, Windsurf, and Aider are converging toward the SKILL.md standard, migrating from simpler rules files. This trend validates the direction Bureau has already taken.

---

## 3. Self-improving agent patterns

### Reflexion (verbal self-critique)

A verbal self-critique loop where the agent reviews its own output and iterates. **Production-ready** today.

- Results: 80% to 91% on HumanEval
- Cost: approximately 4x per iteration loop
- Failure mode: non-convergence (the loop can cycle without improving)

### Skill distillation

Extracting reusable patterns from successful task trajectories. AutoSkill is the most practical implementation, with its add/merge/discard judge and versioned skill management. SkillRL provides a reinforcement-learning variant.

- Failure modes: skill overwrite (losing a good version), noise accumulation from weak trajectories

### Prompt evolution (DSPy)

Treats prompts as compiled programs. MIPROv2 optimizer demonstrated **12.5 percentage point improvement** on target benchmarks.

- Barrier: requires well-defined metrics and training data to compile against
- Relevant later in maturity curve, not as a starting point

### Memory-augmented learning

**MUSE** introduces a 3-tier memory architecture (strategic, procedural, tool memory) achieving **+8.6 percentage points** improvement. **MAGMA** uses multi-graph memory structures.

Bureau already has Qdrant + Memory MCP, providing a foundation. The key gap is the procedural memory tier (capturing *how* tasks were completed, not just *what* was learned).

### A/B testing for skills

Parloa uses a **hierarchical Bayesian model** for skill variant testing. Maxim AI provides a platform for this.

Critical insight: measure skill effectiveness **by task category**, not by overall averages. A skill that improves performance on one category can silently degrade another.

### Self-modification guardrails

Essential for any system where agents modify their own skills or prompts.

- **Darwin Godel Machine**: non-degradation gate (changes must prove they do not make things worse before deployment)
- Recommended safeguards: dual-audit, versioning with rollback, scope limits (restrict what an agent can modify), immutable sections (core safety behaviors are never self-modifiable)

### Recommended adoption order

Based on maturity, risk, and incremental value:

1. **Reflexion** -- lowest barrier, immediate value, well-understood failure modes
2. **Memory enhancement** -- Bureau already has infrastructure; extend to procedural tier
3. **Guardrails** -- must precede any automated self-modification
4. **A/B testing** -- category-level measurement before deploying variants
5. **Distillation** -- requires guardrails and measurement to be safe
6. **DSPy optimization** -- highest barrier (metrics + training data), highest ceiling

---

## 4. Autonomous skill creation pipeline

### Key systems compared

| System | Extraction method | Curation | Versioning | Output format | Applicability to Bureau |
|:-------|:------------------|:---------|:-----------|:--------------|:------------------------|
| Voyager | Self-verification from exploration | Embedding-based retrieval | None | Code functions | Low (research) |
| CRADLE | Screenshot-based interaction | Retrieve, judge, update/create | Implicit | Internal format | Low (UI-focused) |
| AutoSkill | Dialogue extraction (online + offline) | Add/merge/discard judge | Explicit versioned merging | OpenAI-compatible | **High** |
| EvoSkill | Multi-agent (Executor/Proposer/Builder) | Pareto frontier selection | Implicit (frontier) | **SKILL.md** | **High** |
| SkillGen | Synthetic amplification from few demos | - | - | Robotics-specific | Low (robotics) |

### Meta-prompting and optimization

**OPRO** and **GEPA** use the LLM itself as an optimizer for prompt/skill content. GEPA maintains a Pareto frontier of diverse prompt candidates and demonstrated improvement from **66.7% to 93.3%** on a compilation benchmark. These techniques are applicable as a refinement step after initial skill creation.

### Production path for a skill forge

Drawing from the strongest elements across systems, a practical skill creation pipeline would follow this sequence:

1. **Extract** candidate skills from successful sessions (AutoSkill's dialogue extraction)
2. **Judge** each candidate: add as new skill, merge with existing skill, or discard (AutoSkill's curation model)
3. **Verify** in sandbox with test cases (Voyager's self-verification gate)
4. **Version** and track with git (AutoSkill's versioning + standard VCS)
5. **Refine** via GEPA-style optimization against golden datasets
6. **Curriculum** planning: track task gaps and propose targeted skill creation (Voyager's curriculum concept)

---

## 5. Skill quality and improvement loops

### Measurement

**Golden datasets with ablation testing** form the foundation: measure task performance with and without a skill, broken down by task category.

Three grader types, in order of cost and coverage:

| Grader | Strengths | Limitations |
|:-------|:----------|:------------|
| Code-based | Deterministic, fast, cheap | Only works for objectively measurable outcomes |
| LLM-as-judge | Flexible, scales to subjective quality | Requires calibration; can drift |
| Human review | Highest fidelity | Does not scale |

Key metrics for coding skills: task completion rate, test pass rate, tool selection accuracy, efficiency (tokens/steps), and code quality.

Tools: **promptfoo** (best open-source option), DeepEval, Braintrust, Langfuse.

### Refinement loops

Three validated approaches:

- **OpenAI Self-Evolving Agents cookbook**: baseline, evaluate, meta-prompt revision, re-evaluate, loop
- **AGENTS.md accretion**: append learnings to the skill file after each task (simple but accumulates noise)
- **SICA (Bristol)**: agent edits its own codebase including prompts, achieving **17% to 53% on SWE-Bench**

### Regression prevention

This is the hardest unsolved problem in skill self-improvement.

- **Category-level tracking**: never use overall averages. A skill that improves one task type can silently degrade another ("When Better Prompts Hurt" paper confirms this).
- **Separate capability evals from regression evals**: "climbing" metrics (is the skill getting better?) are distinct from "maintaining" metrics (has the skill broken anything?).
- **CI/CD integration**: promptfoo config with fail-on-regression gates, run as part of the standard pipeline.
- **Version skills with quality scores**: every skill version carries its measured performance per category.

### Practical patterns (increasing automation)

| Pattern | Description | Automation level |
|:--------|:------------|:-----------------|
| **A (minimal)** | Golden dataset + promptfoo + human-in-the-loop editing | Manual |
| **B (semi-auto)** | LLM proposes skill revision, human reviews, regression suite gates deployment | Semi-automated |
| **C (DSPy-compiled)** | Parse SKILL.md into DSPy signature, optimize, extract back to SKILL.md | Fully automated |

**Recommended starting point**: TRAINING.json sidecar per skill (golden dataset), promptfoo config for measurement, CI integration for regression gates, LLM-as-judge for scaling evaluation, DSPy compilation as a later stage.

**Key insight: the golden dataset is the bottleneck, not the optimization algorithm.** Investing in curating high-quality training/evaluation examples yields more improvement than investing in more sophisticated optimization techniques.

---

## 6. Platforms and marketplaces

### Claude Code plugin system

Claude Code now supports full plugin packaging with `marketplace.json`, versioning, namespacing, and permission scopes. Bureau should consider packaging itself (or individual skill bundles) as a Claude Code plugin for broader distribution.

### OpenAI skills catalog

Available at `github.com/openai/skills`. Together with 6,000+ publicly indexed skills on community registries, this creates a large surface area of reusable skill definitions.

### AgentSkillOS

Provides DAG-based skill composition and a Capability Tree for organizing skill hierarchies. Key finding: **"structured composition > mere availability"** -- having skills is less valuable than having a principled way to compose and select them.

### Memory platforms

Mem0, Zep, and Letta are the leading commercial memory platforms. Bureau's fold/unfold mechanism solves the **instance identity problem** (maintaining agent state across sessions) better than these commercial offerings, which focus primarily on memory retrieval rather than full context restoration.

### Workflow engines

Temporal and Inngest provide durable execution guarantees. These are overkill for Bureau's CLI-local architecture but may become relevant if Bureau expands to long-running distributed workflows.

---

## 7. Benchmarking and evaluation

### SkillsBench (critical finding)

Published February 2026, SkillsBench is the **first benchmark specifically designed to measure skill effectiveness** (as distinct from raw model capability).

Key results:

| Condition | Effect |
|:----------|:-------|
| Curated skills | **+16.2 percentage points** improvement |
| Self-generated skills | **No measurable benefit** |
| Skills applied to wrong task type | **Degradation in 16 of 84 tasks** |

**Implications**: never auto-deploy self-generated skills. Curation (human or rigorous automated judge) is mandatory. Skills can actively harm performance when misapplied.

### SWE-bench

Measures raw model capability on software engineering tasks but does not isolate skill effectiveness. Useful as a baseline but insufficient for evaluating skill development systems.

---

## 8. Key takeaways for Bureau

**What Bureau already has right:**

- SKILL.md format (aligned with emerging universal standard)
- Qdrant + Memory MCP (foundation for memory-augmented learning)
- Fold/unfold (superior instance identity vs. commercial memory platforms)
- CLI-local architecture (avoids workflow engine complexity)

**Highest-value next steps:**

1. **Golden datasets per skill** -- the single biggest bottleneck to skill quality improvement. Start with TRAINING.json sidecars.
2. **Category-level measurement** -- promptfoo integration with per-task-type tracking and regression gates.
3. **Skill extraction from sessions** -- AutoSkill-style dialogue extraction, feeding an add/merge/discard judge.
4. **Non-degradation gate** -- any automated skill modification must prove it does not make things worse before deployment.
5. **Claude Code plugin packaging** -- explore distributing Bureau or skill bundles via the plugin marketplace.

**What to avoid:**

- Auto-deploying self-generated skills without curation (SkillsBench shows zero benefit, real risk of degradation)
- Overall-average metrics (masks category-level regression)
- Premature DSPy optimization (high barrier; invest in golden datasets first)
- Workflow engines (Temporal/Inngest are overkill for current architecture)

**Emerging trends to monitor:**

- AAIF consolidation of standards under Linux Foundation governance
- MCP Skills primitive investigation (2026 roadmap)
- Claude Code plugin ecosystem growth
- SkillsBench adoption as a standard evaluation methodology
