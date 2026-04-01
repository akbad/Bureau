# Bureau skill system proposals

- **Date**: `2026-03-30`
- **Authors**: 3 synthesis agents

    - architect
    - skills designer
    - meta-system designer

- **Inputs**: 3 collation reports from 9 research agents

    - Superpowers analysis
    - Bureau inspiration docs
    - 2026 research landscape

## Architectural additions

> [!IMPORTANT]
>
> <ins>Priority order matters</ins> because governance and measurement are prerequisites for most downstream automation.

- **1. Skill lifecycle governance (`SkillForge-Lite`)**

    - **Add** a triage-and-governance layer that prevents skill proliferation.
    - **Include** 3 scripts.

        - `discover-skills.py` builds the index.
        - `triage-skill-request.py` routes by duplicate-detection confidence.
        - `validate-skill.py` runs the pre-admission quality gate.

    - **Add** a `skill.meta.json` sidecar per skill.

        - `keywords`
        - `domains`
        - `triggers`
        - `version`

    - **Set routing thresholds**.

        - `USE_EXISTING`: `>= 80%`
        - `IMPROVE_EXISTING`: `50-79%`
        - `CREATE_NEW`: `< 50%`
        - Additional routes: `COMPOSE`, `CLARIFY`

    - **Why first**: it is the foundation for everything else.
    - **Key rationale**: self-improvement without governance produces noise.
    - **Builds on**.

        - `operations/skills_catalog.py`
        - `generate-skills-config.py`
        - `defaults.yml` skills config

- **2. Golden datasets and category-level measurement**

    - **Add** a `TRAINING.json` sidecar per skill with curated test cases.

        - `basic-compliance`
        - `adversarial-pressure`
        - `rationalization-resistance`
        - `edge-case`
        - `regression`

    - **Integrate** `promptfoo` for automated evaluation.
    - **Gate** regressions at the category level.
    - **Never rely** on aggregate averages.
    - **Why second**: the golden dataset is the bottleneck, not the optimization algorithm.
    - **Key metric**: track per-category scores only.
    - **Failure mode caught**: a skill that improves one dimension while degrading another.

- **3. Session-extracted skill candidates (`AutoSkill-Lite`)**

    - **Add** a post-session extraction pipeline that mines reusable patterns.
    - **Pull from** existing sources.

        - fold dossiers
        - Qdrant memories
        - claude-mem

    - **Produce** candidate skill drafts in a staging directory.
    - **Route** every candidate through proposal 1.
    - **Require** proposal 2 before promotion.
    - **Require** human approval before deployment.
    - **Builds on**.

        - `concierge/hooks/post_session.py`
        - `concierge/llm.py`
        - `concierge/distillation/compress.py`

> [!NOTE]
>
> `AutoSkill-Lite` never auto-deploys candidates.

- **4. Skill template with rhetorical engineering**

    - **Add** a canonical `SKILL-TEMPLATE.md`.
    - **Encode** Superpowers' highest-impact compliance techniques.

        - rationalization tables
        - red-flag lists
        - redundant mandate placement
        - gate functions at the point of risk
        - anti-sycophancy interrupts
        - `IMMUTABLE` section markers
        - `DONE` / `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED` escalation

    - **Why**: Superpowers' persuasion-informed design doubled compliance.
    - **Target gain**: systematize battle-tested compliance patterns.

- **5. Procedural memory tier**

    - **Extend** Qdrant with a `skill-execution-traces` collection.
    - **Capture** per-skill execution data.

        - phases reached
        - gates passed or failed
        - rationalizations encountered
        - tools used
        - outcomes

    - **Preserve** active skill state across `fold` and `unfold`.
    - **Feed** proposal 3.
    - **Feed** proposal 2.
    - **Builds on**.

        - Qdrant
        - Memory MCP
        - fold and unfold dossiers

### Dependencies

- **Governance (1)** enables downstream structure.

    - feeds **Skill template (4)**
    - feeds **Golden datasets and measurement (2)**
    - feeds **Session extraction (3)**

- **Skill template (4)** strengthens **Golden datasets and measurement (2)**.
- **Procedural memory (5)** feeds downstream learning.

    - feeds **Golden datasets and measurement (2)**
    - feeds **Session extraction (3)**

## Concrete new skills

> [!IMPORTANT]
>
> These proposals are ordered by expected impact and by how cleanly they self-invoke.

- **1. TDD**

    - **Trigger**: the agent is about to implement a feature, fix a bug, or add functionality.
    - **Workflow**.

        - `RED`: write one failing test and verify it fails for the right reason.
        - `GREEN`: add the minimal implementation and get all tests passing.
        - `REFACTOR`: improve while tests stay green and revert on any failure.
        - repeat the loop

    - **Why**.

        - it replaces the Superpowers dependency.
        - it is the highest-impact rigid skill.

    - **Core defense**: the rationalization table from Superpowers' 6 `RED-GREEN-REFACTOR` iterations.
    - **Companion files**.

        - `rationalization-table.md`
        - `testing-anti-patterns.md`
        - `test-design-guide.md`

- **2. Research**

    - **Triggers**.

        - the agent must make a consequential technology choice using current sources.
        - the user asks to investigate, compare, or evaluate.

    - **Workflow**.

        - scope into 3-5 sub-questions
        - run a multi-source sweep

            - Context7
            - Brave or Tavily
            - Grep or Serena
            - Qdrant

        - triangulate with `HIGH` / `MEDIUM` / `LOW` confidence
        - pass an anti-hallucination gate
        - deliver with citations
        - store the result in Qdrant

    - **Why**: it fills the most dangerous gap.
    - **Risk addressed**: unverified claims entering memory.
    - **Companion files**.

        - `source-priority.md`
        - `anti-hallucination-gates.md`

- **3. Reflect**

    - **Trigger**: the agent considers a deliverable done.
    - **Applicable deliverables**.

        - implementation
        - plan
        - review
        - research

    - **Workflow**.

        - snapshot the deliverable
        - apply 3 lenses

            - completeness
            - correctness
            - fitness

        - generate specific objections
        - revise or confirm
        - stop if the same objections repeat

    - **Why**.

        - it operationalizes the Reflexion pattern.
        - it is production-ready and immediately useful.

    - **Failure mode addressed**: presenting unreviewed work as final.
    - **Companion files**.

        - `anti-sycophancy-gates.md`

- **4. Pressure test**

    - **Trigger**: the agent is about to finalize a plan, architecture decision, or skill draft.
    - **Workflow**.

        - frame the artifact
        - apply 4 combined pressures

            - time
            - sunk cost
            - authority
            - scope creep

        - surface rationalizations with rebuttals
        - produce a verdict

            - `SURVIVES`
            - `SURVIVES_WITH_PATCHES`
            - `RETHINK`

        - log the result to memory

    - **Why**: it generalizes Superpowers' adversarial skill testing.
    - **Key insight**: combined pressures expose fragility better than isolated pressures.
    - **Companion files**.

        - `pressure-catalog.md`
        - `rationalization-library.md`

- **5. Dispatch**

    - **Trigger**: the agent identifies 2 or more independent work units with no shared mutable state.
    - **Workflow**.

        - decompose and verify independence
        - calibrate subagent prompts

            - task
            - skills
            - acceptance criteria
            - `SUBAGENT-STOP`
            - model recommendation

        - define a reconciliation plan
        - execute
        - reconcile and verify

    - **Why**.

        - it is the owner's second priority.
        - it unlocks parallel execution with structural safeguards.

    - **Companion files**.

        - `independence-checklist.md`
        - `model-dispatch-guide.md`
        - `reconciliation-patterns.md`

- **6. Distill**

    - **Trigger**: the session ends after solving a non-trivial problem with a repeatable approach.
    - **Workflow**.

        - identify the candidate pattern
        - triage against the skill index

            - `USE_EXISTING`
            - `IMPROVE_EXISTING`
            - `CREATE_NEW`

        - draft `SKILL.md` from the template
        - pressure-test the draft
        - store it as a candidate for human review

    - **Why**: it is the meta-skill for Bureau self-improvement.
    - **Dependency**: it depends on pressure test and governance.
    - **Companion files**.

        - `skill-template.md`
        - `triage-decision-tree.md`

- **7. Schema evolution**

    - **Trigger**: the agent is about to modify a schema or contract.
    - **Typical surfaces**.

        - database schema
        - API contract
        - config format
        - data model

    - **Workflow**.

        - map the blast radius across all consumers
        - classify the change

            - `ADDITIVE`
            - `TRANSFORM`
            - `DESTRUCTIVE`

        - design a multi-phase migration path
        - generate safety artifacts

            - migration
            - rollback
            - integrity check

        - execute with verification gates between phases

    - **Why**: it cleared the self-invocation bar in role evaluation.
    - **Failure mode addressed**: unsafe single-phase migrations.
    - **Guardrail**: force `expand` / `migrate` / `contract`.
    - **Companion files**.

        - `migration-patterns.md`
        - `rollback-checklist.md`

- **8. Incident response**

    - **Trigger**: a production incident or cascading failure occurs.
    - **Workflow**.

        - stabilize first
        - confirm the system is stable before investigation
        - reconstruct the timeline

            - `FACT`
            - `INFERENCE`

        - isolate the root cause with `5 Whys`
        - check rationalizations during root-cause analysis
        - propose remediation

            - immediate
            - systemic

        - draft a blameless postmortem

    - **Why**: it cleared the role evaluation bar.
    - **Critical differentiator**: the stabilize-first gate.
    - **Failure mode addressed**: investigating while the system is still burning.
    - **Companion files**.

        - `stabilization-playbook.md`
        - `postmortem-template.md`

## Skill lifecycle meta-system

### Creation pipeline

- **1. Triage**

    - Run `triage_skill_request.py`.
    - Do keyword-based duplicate detection against `skill-index.json`.
    - Route to 1 of 5 outcomes.

        - `USE_EXISTING`
        - `IMPROVE_EXISTING`
        - `CREATE_NEW`
        - `COMPOSE`
        - `CLARIFY`

- **2. Scaffold**

    - Run `scaffold_skill.py`.
    - Generate the skill directory.

        - `SKILL.md` from the template
        - `skill.meta.json`
        - `TRAINING.json`
        - `CHANGELOG.md`

- **3. RED-GREEN-REFACTOR**

    - Use TDD for skills.
    - **`RED`**: observe agent failure without the skill.
    - **`GREEN`**: add the minimal skill that addresses the failure.
    - **`REFACTOR`**: pressure-test with multi-pressure scenarios.
    - Continue until no new rationalizations emerge.
    - **Evidence point**: Superpowers needed 6 iterations for TDD.

### Quality measurement

- **`TRAINING.json` per skill**.

    - categorized test cases

        - `basic-compliance`
        - `adversarial-pressure`
        - `rationalization-resistance`
        - `edge-case`
        - `regression`

- **Three grader types**.

    - code-based structural checks
    - LLM-as-judge behavioral assessment
    - human review for promotion gates

- **`promptfoo` integration**.

    - `generate_promptfoo_config.py`
    - `run_skill_evals.sh`
    - `check_regression.py`

- **Tracking rules**.

    - use category-level tracking only
    - never use overall averages

- **CI gate**: skill-modifying PRs must pass the eval suite.

### Self-improvement loop

- **Observe**

    - Run `extract_improvement_candidates.py`.
    - Mine Qdrant, dossiers, and claude-mem for skill-relevant patterns.
    - Look for:

        - failures despite following the skill
        - uncovered rationalizations
        - skipped phases

- **Propose**

    - Review candidates.
    - Add failing test cases for `RED`.
    - Draft the skill modification for `GREEN`.
    - Pressure-test the change for `REFACTOR`.
    - Use Reflexion mode for drafting.
    - Cap Reflexion at 3 iterations.

- **Eval**

    - Run skill evals.
    - Verify no category-level regression.

- **Approve**

    - Review the Git diff.
    - Require explicit human sign-off.

- **Deploy**

    - commit
    - PR
    - merge
    - propagate through `set-up-skills.sh`

- **Cadence**

    - monthly
    - earlier if 5 or more candidates accumulate for one skill

### Versioning and safety

- **Semver in `skill.meta.json`**.

    - `PATCH`: no behavior change
    - `MINOR`: new rationalizations or red flags and requires eval
    - `MAJOR`: workflow restructure and requires full eval plus human review

- **Rollback model**.

    - use Git-based rollback
    - use `git revert` for recovery

- **Safety controls**.

    - `IMMUTABLE` section markers for safety-critical content
    - CI lint enforcement

- **Rollback triggers**.

    - post-deploy regression
    - operator report
    - zero invocations for 30 days after a major bump

### Skill discovery

- **Current mode**: progressive disclosure.

    - load metadata at startup
    - load full content on activation

- **Starting point**: keyword indexing.

    - `skill-index.json`
    - keyword matching
    - domain matching

- **Activation modes per skill**.

    - `auto`: exact trigger match
    - `suggest`: above keyword threshold
    - `manual`: below threshold

- **Future step**: add embedding-based retrieval via Qdrant when skill count exceeds 20.

### Skill retirement

- **Retirement triggers**.

    - declining quality scores
    - zero invocations for 60 days
    - model capability surpassing the skill

- **Quarterly review input**: run `TRAINING.json` without the skill.
- **Retirement process**.

    - deprecate for 1 month and move to `disabled`
    - archive by moving to `_archived/`
    - delete after 3 more months
    - rely on Git for long-term history

### Implementation roadmap

- **Phase 1: Foundation**

    - **Weeks**: `1-2`
    - **Work**.

        - `skill.meta.json` sidecars
        - `generate-skill-index.py`
        - `scaffold_skill.py` with the template

- **Phase 2: Quality measurement**

    - **Weeks**: `3-4`
    - **Work**.

        - `TRAINING.json` format
        - golden test cases for the pilot skill
        - `promptfoo` integration
        - regression gates

- **Phase 3: Triage and governance**

    - **Weeks**: `5-6`
    - **Work**.

        - `triage_skill_request.py`
        - `lint_immutable.py`
        - convert the first 2-3 role prompts with `RED-GREEN-REFACTOR`

- **Phase 4: Improvement loop**

    - **Weeks**: `7-8`
    - **Work**.

        - `extract_improvement_candidates.py`
        - `CANDIDATES.md` sidecar
        - first refinement cycle

- **Phase 5: Scale**

    - **Weeks**: ongoing
    - **Work**.

        - convert the remaining roles
        - run the first quarterly review
        - evaluate embedding retrieval

### Deferred capabilities

- **Embedding-based retrieval**

    - revisit when skill count exceeds 20
    - revisit when keyword recall drops below 70 percent

- **DSPy prompt compilation**

    - revisit when 50 or more golden test cases accumulate

- **Autonomous session extraction**

    - revisit when curation infrastructure is mature and battle-tested

- **A/B testing skill variants**

    - revisit when any skill exceeds 100 invocations per month

- **MCP Skills primitive**

    - revisit when MCP publishes a specification
