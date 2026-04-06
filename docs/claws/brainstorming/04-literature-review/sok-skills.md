# SoK: Agentic Skills — Beyond Tool Use in LLM Agents (2025/2026)

- **Paper**: Yanna Jiang et al., arXiv:2602.20867, published February 24, 2026
- **Verdict**: ADOPT (formalization) / CITE (security analysis) / MONITOR (composition model)
- **Relevance**: High — directly formalizes the skill layer that Bureau's SKILL-TEMPLATE.md structures

---

## 1. Paper summary

The paper is the first Systematization of Knowledge (SoK) for agentic skills. It defines skills as the layer *above* tool calls and *below* full agent autonomy: reusable, callable procedural modules that encapsulate both execution logic and applicability judgment. The paper covers the full skill lifecycle (discovery → practice → distillation → storage → composition → execution → evaluation/update), introduces a formal four-tuple definition, enumerates seven design patterns, analyzes security/governance risks through the ClawHavoc case study, and maps open research problems.

---

## 2. Four-tuple formalization: S = (C, π, T, R)

An agentic skill is formally defined as:

```
S = (C, π, T, R)
```

### Component definitions

- **C — Applicability Condition**: A predicate function `C: (observations, goals) → {0,1}` that determines whether the skill is contextually appropriate. Can be implemented as a soft score in `[0,1]` with thresholding. *Without C, policies cannot self-select.*

- **π — Executable Policy**: Maps `(observations, interaction_history) → (actions | invocations_of_other_skills)`. May be implemented as natural-language instructions, executable code, a learned controller, or a hybrid. Enables hierarchical composition when skills invoke other skills. *Without π, only metadata remains.*

- **T — Termination Condition**: A predicate over `(observations, history, goals)` that signals when the skill has completed relative to its goal. Critical for composition: *callers do not know when to resume* without explicit termination logic.

- **R — Reusable Callable Interface**: Metadata comprising the skill's name, parameter schema, and return type. Makes skills "explicitly invocable" and enables "runtime composition." Distinguishes skills from RL options, which lack programmatic invocation.

### Why all four are necessary

The paper states: "removing any component yields an incomplete abstraction." This is the key architectural insight: C + π + T + R together create a *complete, composable, governable* unit. Contrast with related abstractions:

| Abstraction | Self-selects (C) | Executes (π) | Terminates (T) | Callable (R) |
|-------------|-----------------|--------------|----------------|--------------|
| Tool | No | Yes (atomic) | No | Yes |
| Plan | No | One-time | No | No |
| Memory | No | Retrieval only | No | No |
| **Skill** | **Yes** | **Yes** | **Yes** | **Yes** |

---

## 3. Seven design patterns (P1–P7)

The paper organizes skill implementations along an autonomy spectrum from human-controlled (P1) to fully autonomous (P6), with marketplace distribution (P7) as a cross-cutting mechanism. Real systems typically combine 2–4 patterns.

### P1: Metadata-Driven Progressive Disclosure

Skills are registered with compact metadata summaries; full instructions load only upon selection. Solves the finite context window constraint by enabling agents to reason about hundreds of skills while consuming tokens only for active ones.

- **Trade-off**: Low context cost, but metadata retrieval quality directly gates skill selection quality.
- **Primary risk**: Metadata poisoning (adversarial summaries that surface wrong skills).
- **Representative systems**: Claude Code, Semantic Kernel, LangChain.

### P2: Code-as-Skill (Executable Scripts)

Policies are represented as executable programs (Python, shell scripts, domain-specific languages). Voyager generates JavaScript for Minecraft; CodeAct frames agent actions as Python.

- **Advantage**: Determinism — same inputs produce same outputs, enabling traditional software testing.
- **Limitation**: Brittleness when underlying APIs or UI elements change.
- **Representative systems**: Voyager, CodeAct, SWE-agent.

### P3: Workflow Enforcement

Hard-gated processes mandate prescribed methodologies rather than allowing agent improvisation. Skills define *how* the agent must proceed, not just *what* to do.

- **Advantage**: Clear audit trails; constrains action space to proven sequences.
- **Trade-off**: Sacrifices flexibility for reliability; may over-constrain agents.
- **Representative systems**: LATS (tree-search enforcement), TDD skills, debugging protocols.

### P4: Self-Evolving Skill Libraries

Combines execution with automated quality assessment and library maintenance. After each task, the system evaluates trajectories for distillation into new skills or refinement of existing ones.

- **Central tension**: SkillsBench reports self-generated skills average −1.3 percentage points relative to skill-free baselines, suggesting quality control remains critical.
- **Representative systems**: Voyager (in-game verification), CRADLE (episodic context linking).

### P5: Hybrid NL+Code Macros

Single skill packages combine natural-language descriptions with executable components. NL sections explain purpose and handle edge cases; code sections provide determinism for well-understood steps.

- **Advantage**: Flexibility via NL reasoning + determinism via code.
- **Risk**: Boundary ambiguity when NL instructions conflict with code components.
- **Representative systems**: Bureau SKILL.md format implicitly (NL workflow + optional scripts).

### P6: Meta-Skills

Skills whose purpose is to create, modify, or compose other skills. Analyze task history to identify patterns, generate candidate skills, and test them.

- **Advantage**: Scalability — a small seed library can grow without matching human labor investment.
- **Risk**: Recursive error amplification if early-generation flaws propagate through subsequent generations.
- **Representative systems**: Self-Instruct, CREATOR, Eureka, Bureau's proposed "Distill" skill.

### P7: Plugin/Marketplace Distribution

Skills are versioned, distributable packages with explicit metadata for dependencies and governance. Enables community-driven ecosystems.

- **Advantage**: Community growth and skill reuse at scale.
- **Critical risk**: Supply-chain vulnerability — a malicious or compromised skill package can execute arbitrary actions within the agent's permission scope (see ClawHavoc, Section 4).
- **Representative systems**: OpenClaw/ClawHub, Claude Code plugin marketplace, MCP skill ecosystem.

---

## 4. Skill lifecycle model

Seven stages, non-linear with feedback loops:

1. **Discovery**: Identifying recurring task patterns justifying encapsulation. Methods: curriculum-driven exploration (Voyager), plan decomposition, user demonstrations.
2. **Practice/Refinement**: Iterative improvement through trial-and-error. Reflexion implements verbal RL loops.
3. **Distillation**: Extracting stable, generalizable procedures from trajectories and packaging into the (C,π,T,R) tuple with descriptive metadata.
4. **Storage**: Persisting with indexing, versioning, and metadata for retrieval and governance.
5. **Retrieval/Composition**: Selecting relevant skills at runtime and composing into higher-level workflows.
6. **Execution**: Running skill policies under sandboxing, permission controls, and resource constraints.
7. **Evaluation/Update**: Monitoring post-deployment performance, detecting drift, revising or retiring.

Feedback loops: evaluation → practice (underperformance triggers refinement), retrieval → storage (indexing failures trigger reindexing), execution → discovery (runtime failures reveal capability gaps).

---

## 5. Skill composition model

### Hierarchical structure

Skills organize into hierarchies mirroring the RL options framework: high-level skills invoke mid-level skills, which invoke low-level skills. Composition is hierarchical, DAG-based, and potentially recursive.

### Runtime routing strategies

Two primary strategies:
- **Embedding-based retrieval**: Task descriptions matched against skill embeddings; top-k candidates loaded.
- **LLM-mediated routing**: Agent reasons about skill selection using metadata. Hybrid approaches combine both.

### Failure recovery as a first-class skill

When T signals failure, recovery skills diagnose causes and decide between retry, backtrack, or escalation. Governance implication: *the recovery skill must be at least as trusted as the skill it is recovering.*

### Multi-agent skill sharing

Skills can be shared through common repositories in multi-agent systems. Cross-agent security concern: a compromised skill in a shared repository affects all consuming agents.

### No formal algebra (notable gap)

The SoK does not define a formal composition algebra with operators (no ⊕, ∥, →, or similar notation). Composition is described qualitatively and via the T component (which enables callers to sequence skills). This is a gap relative to Bureau's composition algebra proposal.

---

## 6. Security and governance findings

### The ClawHavoc supply-chain attack

ClawHavoc is the defining real-world case for skill marketplace security. It targeted OpenClaw's ClawHub marketplace:

**Scale**: 1,184 confirmed malicious skills uploaded by 12 coordinated attacker accounts. Single attacker "hightower6eu" uploaded 677 packages. Peak: 386 malicious skills deployed within 24 hours on January 31, 2026.

**Weaponization vectors** (three types):
1. *Download-Execute Trojans*: Skills lured users into downloading encrypted packages and executing malware under the guise of required helper tools.
2. *Reverse Shell RATs*: Python scripts with `os.system()` calls establishing remote access.
3. *Information Stealers*: JavaScript components exfiltrating `~/.clawdbot/.env` (API credentials for Claude, OpenAI).

**Payload delivery**: ClickFix 2.0 social engineering — attackers embedded malicious instructions in SKILL.md "Prerequisites" sections, disguised as legitimate setup steps. AI-generated 500–700 line documents added credibility. macOS users got Atomic macOS Stealer (AMOS) via clipboard-hosted terminal commands; Windows users got password-protected ZIP archives.

**Governance failures exploited**:
- "Virtually no security review mechanisms" on ClawHub.
- Only requirement: GitHub account registered for one week.
- No automated code analysis, sandbox testing, or manual review.
- Default open-upload policy prioritized growth over vetting.
- Brand confusion from platform renamings (ClawdBot → Moltbot → OpenClaw) severed user trust chains.

**Impact**: ~300,000 OpenClaw users at risk. 60 packages by one account accumulated 14,285 downloads before removal.

### Six threat categories (from SoK paper)

1. Poisoned metadata causing retrieval of malicious skills
2. Malicious payloads in skill policies (code injection or prompt injection)
3. Cross-tenant data leakage in shared repositories
4. Environmental manipulation exploiting skill brittleness
5. Confused deputy attacks via adversarial observations
6. Applicability condition poisoning triggering unintended skill activation

### Four trust tiers (SoK framework)

- **Tier 1 (Metadata only)**: No execution risk; discovery phase.
- **Tier 2 (Instruction access)**: Loaded into context; read-only if architecture separates reasoning from action.
- **Tier 3 (Supervised execution)**: Per-action approval or sandboxed constraints.
- **Tier 4 (Autonomous execution)**: Unrestricted within pre-configured permissions.

### Proposed mitigations

**For platform operators** (from Antiy CERT / SoK):
- Mandatory static code analysis + LLM-based semantic review before skill publication.
- Sandbox testing for all uploaded packages.
- Dedicated security response team.
- Automated detection analogous to mobile app store models.
- Provenance requirements: mandatory tracking of skill origins, dependencies, modification history.
- Permission boundaries: granular capability specifications rather than broad API access.

**For skill consumers**:
- Verify skill provenance before installation.
- Review skill files before loading.
- Apply principle of least privilege to skill execution contexts.
- Avoid loading skills with executable scripts in untrusted contexts.

---

## 7. Mapping to Bureau's SKILL-TEMPLATE.md

### The 12 sections mapped to the four-tuple

| Bureau section | SoK component | Notes |
|----------------|---------------|-------|
| 1. YAML frontmatter (name, description) | R (callable interface metadata) | Partial match: Bureau's R includes name and trigger description but lacks formal parameter schema and return type |
| 2. Title + goal statement | C (applicability condition, informally) | Goal statement implies when the skill applies; not a formal predicate |
| 3. Non-negotiable directive notice | Not in SoK | Bureau addition for compliance engineering |
| 4. Activation / deactivation | C (applicability condition) | Trigger phrases ≈ informal C; SUBAGENT-STOP ≈ negative C predicate |
| 5. Definitions | π (policy context) | Supports accurate execution |
| 6. Workflow phases | π (executable policy) | Core of the skill; phases with gates approximate T at each transition |
| 7. Rationalization table | Not in SoK | Bureau addition for compliance engineering |
| 8. Red flags | Not in SoK | Bureau addition for compliance engineering |
| 9. Verification checklist | T (termination condition) | Checklist operationalizes T; "declare workflow complete" = T satisfied |
| 10. Companion file references | R (reusable interface, extended) | Resource boundary beyond SoK's minimal R definition |
| 11. Hook declarations | T (programmatic termination/gate) | Phase-boundary hooks are a concrete T implementation |
| 12. Final rule restatement | Not in SoK | Bureau addition for compliance engineering |

### Key findings from the mapping

**Bureau fully covers SoK's π and T.** The workflow phases section is a richer π than most SoK systems describe: it adds gate functions, escalation paths, and explicit sequencing. The verification checklist + hook declarations provide a more concrete T than most SoK systems implement.

**Bureau's C is informal.** The SoK defines C as a formal predicate. Bureau's activation section describes trigger phrases and conditions in prose, which the skill loading mechanism interprets. This is functionally equivalent for Bureau's current scale but would need to be formalized for programmatic composition.

**Bureau's R is minimal.** The SoK's R includes name, parameter schema, and return type. Bureau's `skill.meta.json` covers name, triggers, and keywords — but lacks formal parameter typing and return-type declarations. This gap matters for composition: callers cannot type-check interfaces at the boundary.

**Bureau adds three compliance engineering layers not in SoK.** The non-negotiable directive notice, rationalization table, and red flags address a problem the SoK does not treat: agent *willingness* to follow the skill policy. The SoK assumes agents execute π faithfully; Bureau has empirical evidence they do not (33% → 72% compliance improvement). This is Bureau's primary contribution beyond the SoK framework.

**Bureau's IMMUTABLE markers partially implement security governance.** The SoK's trust-tier framework separates skills by execution risk. Bureau's IMMUTABLE sections prevent self-modification of safety-critical content — a weaker but complementary mechanism at the content level rather than the permission level.

---

## 8. Which of the 7 patterns Bureau implements

| Pattern | Bureau status | Evidence |
|---------|---------------|---------|
| P1: Metadata-Driven Progressive Disclosure | Implemented | YAML frontmatter + `skill.meta.json` loaded at startup; full SKILL.md loaded on activation |
| P2: Code-as-Skill | Partially | Companion scripts exist but are secondary to NL instructions; Bureau is primarily NL-first |
| P3: Workflow Enforcement | Implemented (primary pattern) | Phases + gates + escalation paths are Bureau's core structural pattern |
| P4: Self-Evolving Skill Libraries | Proposed, not implemented | `AutoSkill-Lite` + `extract_improvement_candidates.py` in 04-proposals.md; deferred |
| P5: Hybrid NL+Code Macros | Implemented | SKILL.md is NL + optional companion scripts; hook declarations bridge to code |
| P6: Meta-Skills | Proposed, not implemented | "Distill" skill in 04-proposals.md; the meta-skill for Bureau self-improvement |
| P7: Plugin/Marketplace Distribution | Not applicable (private) | Bureau is a private, local system; ClawHavoc security concerns do not apply currently |

---

## 9. Design implications for Bureau

### Implication 1: Formalize C as a predicate

Bureau's current C (activation triggers) is prose-based and interpreted by the skill loading mechanism. To support future programmatic composition, C should be expressible as a structured predicate with:
- Typed preconditions (e.g., "conversation state = writing code", "user action = about to implement")
- Negative conditions (SUBAGENT-STOP is already one; generalize it)
- Soft-score fallback for fuzzy matching

This is low priority for current scale but is the prerequisite for any composition algebra.

### Implication 2: Extend R with parameter schema

Bureau's `skill.meta.json` covers name, triggers, keywords, and domains. Adding a formal parameter schema (input types, required/optional) and a return-type declaration would:
- Enable the proposed composition algebra to type-check skill boundaries
- Make the `COMPOSE` triage route in SkillForge-Lite tractable
- Align with the SoK's minimal interface requirement

### Implication 3: The compliance engineering gap is Bureau's moat

The SoK has no framework for agent rationalization or compliance failure. Bureau's rationalization tables, red flags, IMMUTABLE markers, and redundant mandate placement address a real empirical gap. This is Bureau's strongest differentiator relative to the academic literature. The implication: document this as Bureau's formal contribution, not just an implementation detail.

### Implication 4: Adopt the six-threat taxonomy for skill security analysis

When Bureau eventually implements P7 (marketplace distribution) or shares skills across agents, the SoK's six threat categories should be the checklist:
1. Metadata poisoning resistance
2. Policy payload validation
3. Cross-agent data isolation
4. Brittleness/environmental manipulation resistance
5. Confused deputy protection
6. Applicability condition poisoning protection

Bureau currently has none of these as explicit controls, but the threat surface is low for a private local system.

### Implication 5: Recovery skills must be first-class

The SoK's finding that "recovery skills must be at least as trusted as the skills they recover" has an implication for Bureau's escalation paths. Currently, BLOCKED/NEEDS_CONTEXT paths in skill workflows route to implicit human escalation. A formal recovery skill (Bureau equivalent: "incident response" or a generic "recovery" skill) would make this explicit and governable.

### Implication 6: The SoK's composition model confirms Bureau's DAG approach

The SoK describes skill composition as hierarchical and DAG-based. Bureau's proposed composition algebra (implicit in the COMPOSE triage route and meta-skill proposals) is consistent with this. However, Bureau needs to formalize the composition operators. The SoK does not provide a formal algebra — this is an open problem in the literature, and Bureau could contribute one.

### Implication 7: Self-evolving skills (P4/P6) require verification gates before deployment

The SoK cites SkillsBench showing −1.3pp average for self-generated skills without curation. Bureau's proposed AutoSkill-Lite correctly defers autonomous deployment and requires human approval. This design decision is validated by the academic consensus.

---

## 10. Related work and further reading

### Primary references from the SoK

| System | Key contribution | SoK pattern | Bureau relevance |
|--------|-----------------|-------------|-----------------|
| Voyager (Wang et al., 2023) | First self-evolving code skill library; embedding-indexed retrieval | P2, P4 | Foundational for AutoSkill-Lite design |
| Reflexion (Shinn et al., 2023) | Verbal self-critique loop as skill refinement | P3, P4 | Bureau's reflect skill directly implements this |
| LATS (Zhou et al., 2023) | Tree-search with failure recovery as first-class skills | P3 | Bureau's phase-escalation model analogous |
| MetaGPT (Hong et al., 2023) | Role-specific skills in multi-agent systems | P7 | Relevant when Bureau scales to multi-agent |
| CREATOR (Qian et al., 2023) | LLM creates tools on demand | P6 | Relevant for meta-skill design |
| Eureka (Ma et al., 2023) | Reward function generation as meta-skill | P6 | Parallel to Bureau's distill meta-skill |
| Self-Instruct (Wang et al., 2023) | Bootstrapping skill libraries from seed sets | P6 | Relevant for AutoSkill-Lite |
| CRADLE (Tan et al., 2024) | Retrieve/judge/update/create lifecycle | P4 | Closest prior art to Bureau's SkillForge-Lite |

### Adjacent papers to read

- **arXiv:2602.12430** — "Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward" (Xu & Yan, Zhejiang U). A complementary survey with detailed security governance framework (four verification gates G1–G4, trust tiers T1–T4). Also documents that 26.1% of 42,447 community skills contain vulnerabilities, 13.3% show data exfiltration patterns.

- **arXiv:2603.00195** — "Formal Analysis and Supply Chain Security for Agentic AI Skills" (Bhardwaj). Applies Dolev-Yao threat model + abstract interpretation to skill capability analysis. Proposes mandatory provenance tracking, capability auditing, permission models, and dependency analysis.

- **arXiv:2603.22928** — "SoK: The Attack Surface of Agentic AI — Tools and Autonomy." Companion SoK covering the broader agentic attack surface beyond skills.

- **arXiv:2601.19752** — "Agentic Design Patterns: A System-Theoretic Framework." System-theoretic treatment of agent design patterns; complementary perspective to SoK's empirical taxonomy.

- **SkillsBench (Feb 2026)** — First benchmark specifically measuring skill effectiveness (as distinct from raw model capability). Key results: curated skills +16.2pp, self-generated skills ≈ 0, misapplied skills degradation in 16/84 tasks. Critical empirical validation for Bureau's anti-auto-deploy stance.

---

## 11. Classification

| Classification | Item | Rationale |
|---------------|------|-----------|
| **ADOPT** | S = (C, π, T, R) four-tuple as formal reference model | Bureau's 12 sections map cleanly; provides vocabulary for spec writing and composition algebra |
| **ADOPT** | Six threat category taxonomy | Concrete checklist for future security analysis; currently low priority but should be documented |
| **ADOPT** | Seven design pattern vocabulary | P1–P7 labels give Bureau a shared vocabulary for describing its architecture |
| **ADOPT** | Trust-tier model (T1–T4) | Relevant when Bureau implements skill sharing or marketplace distribution |
| **CITE** | ClawHavoc case study | Strongest empirical evidence for Bureau's conservative skill governance stance; cite in security rationale docs |
| **CITE** | SkillsBench −1.3pp self-generated finding | Validates AutoSkill-Lite's human-approval requirement; cite in proposals |
| **CITE** | Reflexion and LATS for failure recovery | Bureau's escalation model aligns; citing validates the design |
| **MONITOR** | Formal composition algebra research | SoK identifies this as an open problem; Bureau's composition algebra work is novel; watch for competing formalizations |
| **MONITOR** | Programmatic C (applicability condition) | Academic trend toward formal predicates; relevant when Bureau hits composition at scale |
| **MONITOR** | MCP Skills primitive (2026 roadmap) | If MCP formalizes a Skills primitive, Bureau's `skill.meta.json` should align |

---

## 12. Open questions for synthesis

1. **Does Bureau's composition algebra proposal (implicit in COMPOSE triage route) correspond to any formalization in the adjacent papers?** None of the surveyed papers provide a formal algebra — this may be Bureau's opportunity to define the vocabulary.

2. **How do the other literature agents' papers (ISP, DSPy, ELEPHANT, Arbiter, EvoFSM) interact with the SoK's compliance gap?** The SoK assumes agents follow π faithfully; Bureau's empirical finding (compliance failure) is the bridge to those papers' domains.

3. **Should Bureau explicitly declare which SoK trust tier each skill operates at?** Adding `trust_tier: 1|2|3|4` to `skill.meta.json` would be a low-cost, high-signal governance improvement.

4. **Does the SoK's T (termination condition) map cleanly to Bureau's DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED escalation protocol?** The four escalation states are richer than a binary T predicate — potentially a Bureau contribution to the SoK framework.
