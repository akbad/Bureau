# Memoh × Bureau integration assessment

## Platform profile

Memoh presents as a self-hosted, always-on agent platform with multi-bot operation and long-memory emphasis, plus channel integrations (Telegram/Discord/Feishu/Matrix/etc.). Positioning appears adjacent to OpenClaw but with explicit “multiple bots + long memory” framing.

### Functional surface (researched)

- Containerized self-hosted deployment posture.
- Multi-bot support.
- Long-memory positioning in primary project description.
- Multi-channel integration focus similar to practical personal assistant surfaces.

### Memory architecture + autonomous loop

- Memoh’s branding strongly emphasizes persistent memory, but public canonical detail sampled did not fully specify the exact internal memory stratification.
- Likely sweet spot is operational continuity + user-level recall over long windows.
- Bureau can layer deterministic memory governance (what to store, when to retrieve, provenance tags, replay safety).

### Workflow & UX

- Attractive for daily assistant workflows where always-on chat endpoints matter.
- SWE usage likely requires additional policy templates and repository-aware safety patterns.

### Fit with Bureau

**Fit score: 8.1/10.**

Why it fits:
- Strong complement to Bureau’s protocol/role-centric system with user-facing long-lived assistant endpoints.
- Multi-bot framing maps naturally to Bureau specialist-role orchestration.

Risks:
- Memory quality controls and explainability may need augmentation for enterprise-grade usage.
- Could overlap heavily with Hermes/OpenClaw depending on roadmap depth.

## High-impact Bureau × Memoh merge concepts

1. **Bot Fleet Role Binding**  
   Each Memoh bot is anchored to a Bureau role cluster and protocol profile (e.g., incident bot, PM bot, code-review bot).

2. **Memory Integrity Firewall**  
   Bureau adds ingestion validators, contradiction detection, and confidence decay policies to Memoh long-memory writes.

3. **Routine-to-Repo Bridge**  
   Daily assistant outputs (plans, reminders, meeting outcomes) can auto-open/update Bureau dossiers and task graphs.

4. **Assistant Twin Stack**  
   Personal assistant twin + engineering assistant twin share a governed core memory substrate with clear tenancy boundaries.

## Sources

- https://github.com/memohai/Memoh
- https://docs.memoh.ai/
