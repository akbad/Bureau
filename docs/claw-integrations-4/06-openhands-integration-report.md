# OpenHands × Bureau integration report

## Platform profile
**Research confidence:** High.

OpenHands is an open-source software engineering agent platform focused on autonomous code task execution (issue solving, code edits, tool use, environment interaction). It is strongly SWE-oriented rather than general personal-assistant-first.

## Full functionality/feature set and workflow UX

### Core SWE capabilities
- autonomous issue/task handling,
- repository interaction and code modification workflows,
- execution loops with tool usage in sandboxed/controlled environments,
- collaboration surfaces for human oversight.

### Workflow shape
1. user defines coding objective,
2. OpenHands plans and executes edits/tool calls,
3. agent iterates on feedback/errors,
4. human validates/merges.

This is highly compatible with Bureau’s protocolized development style.

## Memory architecture and operational memory stack fit
OpenHands is execution-strong; Bureau can augment long-horizon memory continuity:
- OpenHands run traces -> Bureau dossier and memory stores,
- reusable fix patterns -> Qdrant semantic memory,
- architecture facts discovered during runs -> graph memory.

If OpenHands memory is mostly run-local, Bureau closes the gap for cross-session/cross-CLI learning persistence.

## Autonomous learning loop fit
OpenHands naturally supports execution feedback loops (test fail -> patch -> retest). Bureau can add:
- multi-role reflective critique,
- cross-task lesson extraction,
- deployment gating via skills.

Combined loop quality can outperform either alone:
- OpenHands provides fast embodied trial-and-error.
- Bureau provides structured reflection and policy consistency.

## Daily assistant vs SWE assistant applicability

### Daily assistant
OpenHands is not primarily optimized for consumer daily-assistant routines.

### SWE assistant
Excellent fit. This is where OpenHands+Bureau can be maximally differentiated.

## Workflow/UX integration design
- OpenHands as execution engine for coding tasks.
- Bureau as orchestration layer selecting roles/skills/models and memory policies.
- Unified dashboard/log stream for traceability and rollback.

## Recommendation
Top-tier candidate for Bureau integration when the objective is engineering throughput + reliability.

## High-impact merge concepts (subagent brainstorm section)

### 1) Bureau-governed OpenHands task router
Bureau classifies incoming engineering work and dispatches to OpenHands execution profiles (bugfix, refactor, migration, test hardening).

### 2) Multi-agent critique swarm
After OpenHands completes a patch, Bureau spawns role-specialist reviewers (security, performance, architecture, test) before approval.

### 3) Patch memory distillation
Every merged OpenHands patch is distilled into reusable strategy memories with retrieval hooks for similar future issues.

### 4) Autonomous sprint engine
Weekly backlog items are decomposed and executed semi-autonomously with explicit human checkpoints and risk-tier escalation.

### 5) Regression immunization loop
Post-incident, Bureau auto-generates OpenHands tasks to add tests, assertions, and safeguards that encode lessons permanently.
