# Bureau skill system: proposals

- **Date**: 2026-03-30
- **Authors**: 3 synthesis agents (architect, skills designer, meta-system designer)
- **Inputs**: 3 collation reports from 9 research agents covering Superpowers analysis, Bureau inspiration docs, and the 2026 research landscape

## Part A: Architectural additions (5 proposals)

### 1. Skill lifecycle governance (SkillForge-Lite)

Triage-and-governance layer preventing skill proliferation. Three scripts: `discover-skills.py` (index builder), `triage-skill-request.py` (duplicate detection with confidence routing: USE_EXISTING >= 80%, IMPROVE_EXISTING 50-79%, CREATE_NEW < 50%, COMPOSE, CLARIFY), `validate-skill.py` (pre-admission quality gate). Plus `skill.meta.json` sidecar per skill for keywords, domains, triggers, version.

**Why first**: Foundation for everything else. Without governance, self-improvement produces noise (SkillsBench: self-generated skills = zero benefit).

**Builds on**: `operations/skills_catalog.py`, `generate-skills-config.py`, `defaults.yml` skills config.

### 2. Golden datasets and category-level measurement

`TRAINING.json` sidecar per skill with curated test cases categorized by type (basic-compliance, adversarial-pressure, rationalization-resistance, edge-case, regression). promptfoo integration for automated evaluation. Category-level regression gates (never aggregate averages — "When Better Prompts Hurt" paper).

**Why second**: The golden dataset is the bottleneck, not the optimization algorithm. Measurement enables everything else.

**Key metric**: Per-category scores, never overall averages. A skill improving one dimension while degrading another is caught.

### 3. Session-extracted skill candidates (AutoSkill-Lite)

Post-session extraction pipeline mining fold dossiers, Qdrant memories, and claude-mem for reusable patterns. Produces candidate skill drafts in a staging directory. **Never auto-deploys** — candidates enter triage (proposal 1) and must pass measurement (proposal 2) before human-approved promotion.

**Sources**: Fold dossiers, Qdrant, claude-mem (all existing).
**Builds on**: `concierge/hooks/post_session.py`, `concierge/llm.py`, `concierge/distillation/compress.py`.

### 4. Skill template with rhetorical engineering

Canonical `SKILL-TEMPLATE.md` encoding Superpowers' highest-impact compliance techniques: rationalization tables, red flag lists (naming the cognitive experience before violation), redundant mandate placement at multiple entry points, gate functions at point of risk, anti-sycophancy interrupts, `IMMUTABLE` section markers for safety-critical content, and the DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED escalation protocol.

**Why**: Superpowers' persuasion-informed design doubled compliance (33% to 72%). The template systematizes these battle-tested patterns.

### 5. Procedural memory tier (skill-aware memory)

Extend Qdrant with a `skill-execution-traces` collection capturing per-skill execution data: phases reached, gates passed/failed, rationalizations encountered, tools used, outcomes. Skill-aware fold/unfold preserves active skill state across sessions. Feeds extraction (proposal 3) and measurement (proposal 2).

**Builds on**: Qdrant (already running), Memory MCP, fold/unfold dossiers.

### Dependency graph

```
1 (Governance)  ──────────────────────────────┐
    │                                          │
    ├──> 4 (Skill Template)                    │
    │        │                                 │
    │        v                                 v
    ├──> 2 (Golden Datasets + Measurement) <── 5 (Procedural Memory)
    │        │                                 │
    │        v                                 │
    └──> 3 (Session Extraction) <──────────────┘
```

---

## Part B: Concrete new skills (8 proposals)

Priority-ordered. Each has a clear self-invocation trigger.

### 1. TDD (test-driven development)

**Trigger**: Agent is about to implement a feature, fix a bug, or add functionality.
**Workflow**: RED (write one failing test, verify it fails for the right reason) → GREEN (minimal implementation, all tests pass) → REFACTOR (improve with tests green, revert on any failure). Repeat.
**Why**: Replaces Superpowers dependency. Highest-impact rigid skill. The rationalization table (10+ entries from Superpowers' 6 RED-GREEN-REFACTOR iterations) is the core defense.
**Companion files**: `rationalization-table.md`, `testing-anti-patterns.md`, `test-design-guide.md`.

### 2. Research

**Trigger**: Agent needs to make a consequential technology choice and is relying on training data rather than current sources. Or user asks to investigate/compare/evaluate.
**Workflow**: Scope into 3-5 sub-questions → multi-source sweep (Context7, Brave/Tavily, Grep/Serena, Qdrant) → triangulate with confidence scoring (HIGH/MEDIUM/LOW) → anti-hallucination gate → deliver with citations, store in Qdrant.
**Why**: Owner's top priority (5 inspiration slots in brainstorm). Fills the most dangerous gap: unverified claims entering memory.
**Companion files**: `source-priority.md`, `anti-hallucination-gates.md`.

### 3. Reflect

**Trigger**: Agent considers a deliverable "done" (implementation, plan, review, research).
**Workflow**: Snapshot deliverable → apply three lenses (completeness, correctness, fitness) → generate specific objections → revise or confirm → track convergence (stop if same objections repeat).
**Why**: Operationalizes Reflexion pattern (production-ready, immediate value, lowest barrier). Prevents the common failure of presenting unreviewed work as final.
**Companion files**: `anti-sycophancy-gates.md`.

### 4. Pressure test

**Trigger**: Agent is about to finalize a plan, architecture decision, or skill draft.
**Workflow**: Frame artifact → apply 4 combined pressures (time, sunk cost, authority, scope creep) → surface rationalizations with rebuttals → verdict (SURVIVES / SURVIVES_WITH_PATCHES / RETHINK) → log to memory.
**Why**: Generalizes Superpowers' adversarial skill testing into a reusable pattern. Combined pressures expose fragility that individual pressures miss.
**Companion files**: `pressure-catalog.md`, `rationalization-library.md`.

### 5. Dispatch

**Trigger**: Agent identifies 2+ independent work units with no shared mutable state.
**Workflow**: Decompose and verify independence → calibrate subagent prompts (task, skills, acceptance criteria, SUBAGENT-STOP, model recommendation) → define reconciliation plan → execute → reconcile and verify.
**Why**: Owner's second priority. Unlocks parallel execution with structural safeguards against conflicts.
**Companion files**: `independence-checklist.md`, `model-dispatch-guide.md`, `reconciliation-patterns.md`.

### 6. Distill

**Trigger**: End of session where agent solved a non-trivial problem using a repeatable approach not captured by existing skills.
**Workflow**: Identify candidate pattern → triage against skill index (USE_EXISTING/IMPROVE_EXISTING/CREATE_NEW) → draft SKILL.md following template → pressure-test the draft → store as candidate for human review.
**Why**: The meta-skill that makes Bureau self-improving. Depends on pressure-test and governance infrastructure.
**Companion files**: `skill-template.md`, `triage-decision-tree.md`.

### 7. Schema evolution

**Trigger**: Agent is about to modify a database schema, API contract, config format, or data model.
**Workflow**: Map blast radius (all consumers) → classify change (ADDITIVE/TRANSFORM/DESTRUCTIVE) → design multi-phase migration path → generate safety artifacts (migration + rollback + integrity check) → execute with verification gates between phases.
**Why**: Cleared the self-invocation bar in role evaluation. Models natively write unsafe single-phase migrations. This forces expand/migrate/contract.
**Companion files**: `migration-patterns.md`, `rollback-checklist.md`.

### 8. Incident response

**Trigger**: Production incident, system outage, data corruption, cascading failure.
**Workflow**: Stabilize first (gate: do not investigate until confirmed stable) → reconstruct timeline (FACT vs INFERENCE) → isolate root cause (5 Whys with rationalization check) → propose remediation (immediate + systemic) → draft blameless postmortem.
**Why**: Cleared the role evaluation bar. The stabilize-first gate is the critical differentiator — prevents investigating while the system burns.
**Companion files**: `stabilization-playbook.md`, `postmortem-template.md`.

---

## Part C: Skill lifecycle meta-system

### Creation pipeline

1. **Triage** (`triage_skill_request.py`): keyword-based duplicate detection against `skill-index.json`. Routes to USE_EXISTING, IMPROVE_EXISTING, CREATE_NEW, COMPOSE, or CLARIFY.
2. **Scaffold** (`scaffold_skill.py`): generates directory with SKILL.md (from template), `skill.meta.json`, `TRAINING.json`, `CHANGELOG.md`.
3. **RED-GREEN-REFACTOR**: TDD for skills. RED = observe agent failure without skill. GREEN = minimal skill addressing failures. REFACTOR = pressure test with multi-pressure scenarios, plug rationalization loopholes. Loop until no new rationalizations emerge (Superpowers needed 6 iterations for TDD).

### Quality measurement

- `TRAINING.json` per skill: categorized test cases (basic-compliance, adversarial-pressure, rationalization-resistance, edge-case, regression).
- Three grader types: code-based (structural checks), LLM-as-judge (behavioral assessment), human review (promotion gates).
- promptfoo integration: `generate_promptfoo_config.py` → `run_skill_evals.sh` → `check_regression.py` with **category-level tracking** (never overall averages).
- CI gating: PRs modifying skills must pass eval suite.

### Self-improvement loop

**Observe** (automated): `extract_improvement_candidates.py` mines Qdrant/dossiers/claude-mem for skill-relevant patterns (failures despite following skill, uncovered rationalizations, skipped phases).

**Propose** (human + LLM): Review candidates, add failing test cases (RED), draft skill modification (GREEN), pressure test (REFACTOR). Reflexion mode for drafting (max 3 iterations).

**Eval** (automated): Run skill evals, verify no category-level regression.

**Approve** (human): Git diff review, explicit sign-off.

**Deploy** (automated): Commit, PR, merge. `set-up-skills.sh` propagates via symlinks.

**Cadence**: Monthly, or when 5+ candidates accumulate for a single skill.

### Versioning and safety

- Semver in `skill.meta.json`: PATCH (no behavior change), MINOR (new rationalizations/red flags, requires eval), MAJOR (workflow restructure, requires full eval + human review).
- Git-based: skills are text files in the repo. `git revert` for rollback.
- `IMMUTABLE` section markers: safety-critical content that cannot be modified during improvement. CI lint enforces.
- Rollback triggers: post-deploy regression, operator report, zero invocations for 30 days post-major-bump.

### Skill discovery

- Progressive disclosure (existing): metadata at startup, full load on activation.
- Keyword indexing (starting point): `skill-index.json` with keyword/domain matching.
- Activation modes per skill: `auto` (exact trigger match), `suggest` (above keyword threshold), `manual` (below threshold).
- Future: embedding-based retrieval via Qdrant when skill count exceeds 20.

### Skill retirement

- **Triggers**: declining quality scores, zero invocations for 60 days, model capability surpassing the skill (quarterly review running TRAINING.json without skill).
- **Process**: deprecate (1 month, move to `disabled`) → archive (move to `_archived/`) → delete (3 months later, git preserves history).

### Implementation roadmap

| Phase | Weeks | What |
|-------|-------|------|
| 1. Foundation | 1-2 | `skill.meta.json` sidecars, `generate-skill-index.py`, `scaffold_skill.py` with template |
| 2. Quality measurement | 3-4 | `TRAINING.json` format, golden test cases for pilot skill, promptfoo integration, regression gates |
| 3. Triage and governance | 5-6 | `triage_skill_request.py`, `lint_immutable.py`, convert first 2-3 role prompts via RED-GREEN-REFACTOR |
| 4. Improvement loop | 7-8 | `extract_improvement_candidates.py`, `CANDIDATES.md` sidecar, first refinement cycle |
| 5. Scale | ongoing | Convert remaining roles, first quarterly review, evaluate embedding retrieval |

### Deferred capabilities

| Capability | Trigger to revisit |
|------------|-------------------|
| Embedding-based retrieval | Skill count > 20 or keyword recall < 70% |
| DSPy prompt compilation | 50+ golden test cases accumulated |
| Autonomous session extraction | Curation infrastructure mature and battle-tested |
| A/B testing skill variants | Any skill > 100 invocations/month |
| MCP Skills primitive | MCP publishes specification |
