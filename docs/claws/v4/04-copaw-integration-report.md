# Copaw × Bureau integration report

## Platform profile
**Research confidence:** Low.

A clearly authoritative and widely adopted technical reference for an AI platform named exactly “Copaw” was not confidently identifiable in this research pass. Treating Copaw as a candidate/emergent platform is safest.

## Functional/feature hypothesis for integration planning
Assume Copaw targets one or more of:
- assistant orchestration,
- memory-enabled personal workflow support,
- potentially developer-assistant automation.

## Memory architecture and autonomous loop assessment
Given uncertainty, use capability-based fit tests:
1. Does Copaw expose explicit memory APIs?
2. Does it separate short-term vs long-term memory?
3. Can memory writes be governed by policy hooks?
4. Does it support retrospective learning loops?

If yes to >=3/4, fit with Bureau is likely strong.

## Operational memory stack mapping template
- Copaw runtime memory -> Bureau session layer.
- Copaw long-term notes -> Bureau Qdrant embeddings.
- Copaw structured entities -> Bureau graph memory.
- Copaw execution history -> Bureau dossier attachments.

## Daily assistant and SWE assistant fit

### Daily assistant
Potentially high if Copaw supports recurring routines, reminders, preference persistence, and adaptive planning.

### SWE assistant
Fit depends on tool invocation richness and code-aware operations. Bureau can compensate via role prompts and delegation to coding-specialized CLIs.

## Workflow/UX design considerations
- Keep Copaw UX as user interaction shell.
- Shift critical execution control to Bureau for auditable, deterministic workflows.
- Add transparent “why this action” traces for autonomous decisions.

## Recommendation
Do not commit to deep integration before a discovery sprint establishes Copaw’s concrete API/runtime profile.

## High-impact merge concepts (subagent brainstorm section)

### 1) Capability negotiation protocol
At runtime, Bureau queries Copaw capabilities and dynamically composes the integration path (memory-only, tool+memory, or full autonomy).

### 2) Policy-locked autonomy capsules
Encapsulate Copaw autonomous behaviors into Bureau-approved policy capsules with measurable risk classes.

### 3) Personal+project dual brain
Copaw handles personal preference memory while Bureau maintains project engineering memory; a broker resolves boundary crossings.

### 4) Failure-aware adaptation
When Copaw actions fail repeatedly, Bureau automatically shifts execution to specialized role agents and feeds lessons back.

### 5) Explainability substrate
Every Copaw decision includes a generated causal chain and counterfactual alternatives, stored in Bureau memory for future audits.
