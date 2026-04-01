# Debate synthesis: three lenses on the skill system proposals

- **Date**: 2026-03-31
- **Method**: 3 parallel debate agents (skeptic, advocate, contrarian) each read all 5 documents in `docs/features/skills/` and argued from assigned positions
- **Input**: `04-proposals.md` (the proposals under debate), plus `evaluate-role-prompts.md`, `reports/01-superpowers-analysis.md`, `reports/02-bureau-inspiration.md`, `reports/03-research-landscape.md`

## Where all three agree

| Point | Skeptic | Advocate | Contrarian |
|-------|---------|----------|------------|
| **A.3 (AutoSkill-Lite) is premature** | "SkillsBench says zero benefit from self-generated skills" | "Temporally premature... defer until governance validated" | Agrees, but for different reason: extraction quality is unmeasurable for behavioral skills |
| **A.5 (Procedural Memory) is premature** | "Exists only to feed A.3" | "Most willing to defer... instrumenting a system that doesn't exist" | "You don't need a separate tier -- state machines produce traces natively" |
| **A.4 (Skill Template) is the highest-leverage single item** | "Costs one file, zero scripts, zero databases" | "33%->72% compliance is the evidence" | Agrees template matters, but argues prose is the wrong layer for phase enforcement |
| **Retirement system is premature** | "Enterprise governance for a personal tool" | Third weakest proposal | Not addressed (bigger problems exist) |

## The three fundamental disagreements

### 1. How many skills before infrastructure?

- **Skeptic**: Template + 3 skills immediately. Let usage tell you what governance you need. "The best extraction pipeline is noticing things and writing them down."
- **Advocate**: 2-3 skills with full governance + measurement. "If in 3 months Bureau has 8 skills and no measurement, it has recreated the 66-role-prompt problem."
- **Verdict**: Both agree on ~3 skills. They disagree on whether governance/measurement should precede or follow the first skills.

### 2. Should TDD be first?

- **Skeptic**: No. The owner's priority stack is Research #1, Dispatch #2. TDD is already covered by Superpowers. Bureau-native TDD is a lateral move.
- **Advocate**: Yes. TDD has the most evidence (6 iterations, 10+ rationalizations), lowest risk because it can be directly compared against Superpowers.
- **Contrarian**: TDD first, but as a state machine, not a prose skill -- it's the best test case because it has the clearest phase boundaries and verifiable gates.

### 3. Prose persuasion vs. programmatic enforcement

This is the most consequential disagreement. The contrarian's alternative architecture challenges the entire proposal set:

- **The proposals**: skills are prose documents relying on rhetorical engineering (rationalization tables, gate functions, red flag lists) to achieve compliance.
- **The contrarian**: 72% compliance = 28% failure. Bureau already has hooks (`post_session.py`), a pipeline orchestrator, and MCP servers. Why not enforce phase transitions programmatically? A `SkillMachine` (YAML-defined state machine) could verify a test fails before allowing implementation code, verify tests pass before allowing refactor. Prose handles within-phase quality; code handles between-phase ordering.
- **Bonus**: state machines make composition tractable (product automata), produce execution traces natively (eliminating A.5), and make measurement objective even for behavioral skills (did it reach state X before transitioning?).

## Contrarian's unanswered questions (the sharpest ones)

1. **Composition**: What happens when TDD + schema-evolution + reflect are all active? No conflict resolution model exists.
2. **Context budget**: Each skill adds thousands of tokens. With 3+ skills + protocols + task context, does skill loading degrade performance by consuming context?
3. **Cross-model transfer**: 33%->72% was measured on Claude. Codex and Gemini rationalize differently. Are model-specific variants needed?
4. **Subjective measurement**: How do you write TRAINING.json for `reflect`? What does "correct reflection" look like? Inter-rater reliability may be too low.
5. **Longevity**: Applying the same lens that killed 37 roles -- which of these 8 skills will models subsume in 12 months? Research, Reflect, Distill, and Incident Response are candidates.

## Resolved decisions

### From debate consensus

- **A.4 (Skill Template) first** -- all three agree, different reasons.
- **Defer A.3 (AutoSkill-Lite), A.5 (Procedural Memory), and Part C's retirement system** -- unanimous.
- **Distill (B.6) drops to "someday"** -- depends on infrastructure no one thinks should be built yet.

### From owner decisions (2026-04-01)

**Q1: Enforcement model → Hybrid.**
Prose skills with targeted programmatic hooks where gates are verifiable. Not a full state machine runtime — just hooks at high-value checkpoints. Prose handles within-phase quality and subjective skills; code enforces phase transitions where verification is possible (e.g., `pytest` for TDD gates). This avoids building a new runtime while meaningfully exceeding the ~72% prose-only compliance ceiling on gateable skills.

**Q2: Skill ordering → Dispatch + Reflect simultaneously.**
Neither retreads Superpowers ground (unlike TDD) nor bets on something models may soon subsume (unlike Research). Dispatch is the owner's #2 priority and a structural coordination problem models won't natively solve. Reflect applies universally and composes naturally with Dispatch — it can validate Dispatch's reconciliation results. Together they cover coordination and quality assurance.

**Q3: Governance timing → Interleaved (during skill authoring).**
Write the skill template (A.4) first. Then author Dispatch and Reflect using it, writing `TRAINING.json` entries as failure modes are discovered during the RED-GREEN-REFACTOR creation process. promptfoo integration comes at the end as a regression gate. Skills and golden datasets co-evolve — no idle infrastructure, no unmeasured gap.

### Strategic priority: self-reflection over measurement tooling

The owner values honing the agent's self-reflection process — and its ability to effectively and tastefully update its own skills — more than measurement infrastructure. This elevates Reflect from "co-equal first skill" to the strategic centerpiece of the entire system. Reflect is not just "a skill that checks work"; it is the foundation for Bureau's self-improvement loop. An agent that can genuinely self-critique its own skills is more valuable than any amount of promptfoo infrastructure. The measurement tooling (A.2) serves Reflect, not the other way around.

### Skill segregation: static vs. evolving

The existing Bureau skills — **fold**, **unfold**, **micro-mode**, and **assess-mode** — are static operational skills. They are not to be touched by this effort. The new evolving/dynamic skills (Reflect, Dispatch, and future skills built through the template) must be segregated from them in a separate directory. This prevents the skill improvement loop from accidentally modifying operational infrastructure.

### Implementation sequence

1. **A.4**: Write the skill template (`SKILL-TEMPLATE.md`) encoding Superpowers' rhetorical techniques
2. **Reflect + Dispatch**: Author simultaneously using the template, with `TRAINING.json` entries accumulating during creation
3. **A.1 (Governance-lite)**: `skill-index.json` + `skill.meta.json` sidecars — lightweight, no triage scripts yet
4. **A.2 (Measurement)**: promptfoo integration with category-level tracking, once golden datasets exist from step 2
5. **Hooks**: Targeted programmatic gates for skills with verifiable phase transitions (Dispatch has some; future skills like TDD and Schema Evolution have more)

### Deferred (revisit triggers noted)

| Proposal | Revisit when |
|----------|-------------|
| A.3 (AutoSkill-Lite) | Governance + measurement validated on 3+ skills |
| A.5 (Procedural Memory) | Ad-hoc Qdrant queries become insufficient for execution trace analysis |
| Part C retirement system | Any skill reaches 60 days of operation |
| TDD skill | Superpowers replacement becomes necessary or hybrid enforcement needs a proof of concept |
| Research skill | After Dispatch + Reflect are operational; reassess model-native citation capabilities at that time |
| Distill (B.6) | Governance infrastructure is battle-tested |
