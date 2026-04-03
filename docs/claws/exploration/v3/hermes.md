# Hermes × Bureau integration assessment

## Platform profile

Hermes Agent (Nous Research ecosystem) presents as a self-hosted/open personal-agent platform with broad provider support, rich messaging-channel adapters, and operational primitives (gateway, sessions, cron, tools). Notably, Hermes appears to prioritize “always-on assistant” ergonomics over purely code-agent workflows.

### Functional surface (researched)

- Multi-provider model routing (OpenAI-compatible endpoints, GitHub Copilot paths, Hugging Face routing, Chinese provider support, and custom endpoints).
- Messaging Gateway supporting many channels in one daemon-like service (Telegram, Discord, Slack, WhatsApp, Signal, SMS, Email, Matrix, Feishu/Lark, WeCom, etc.).
- Per-session routing architecture and periodic scheduler ticks for due jobs.
- Tooling exposure across channels, including terminal access depending on adapter mode.

### Memory + autonomous loop observations

- Hermes appears to support persistent multi-session operation through gateway/session stores and long-lived runtime components.
- Clear evidence of background scheduling exists (cron tick loop), which can host autonomous follow-up behaviors.
- Public docs sampled emphasize operational transport/integration breadth more than a deeply formalized multi-tier memory theory (compared with Letta’s explicit block hierarchy).

### Workflow & UX

- Strong for practical daily-assistant UX: message-first interactions, voice/media handling, and channel continuity.
- Setup UX includes interactive configuration commands and adapter-by-adapter onboarding docs.
- SWE-assistant UX is possible but may need stronger code-centric guardrails + repo-scoped policy overlays to match Bureau’s coding protocol rigor.

### Fit with Bureau

**Fit score: 9.2/10 (frontrunner validated).**

Why it fits:
- Bureau can contribute protocol rigor, role specialization, and cross-CLI quality controls.
- Hermes can contribute persistent multi-channel runtime presence, user-facing assistant continuity, and broad delivery surfaces.
- Combined stack can bridge “operator console” and “daily assistant” into one coherent system.

Risks:
- Tool-permission and sandbox defaults must be harmonized carefully.
- Potential overlap in orchestration semantics requires clear ownership boundaries.

## High-impact Bureau × Hermes merge concepts

1. **Bureau Mission Control over Hermes Gateway**  
   Add Bureau dossier state + task DAG visualization as a Hermes-native dashboard that can be queried/controlled from any channel.

2. **Role-Adaptive Messaging Threads**  
   Hermes channel sessions automatically select Bureau roles (architect/debugger/security/etc.) based on thread intent classification, with transparent role handoff logs.

3. **Autonomous Maintenance Loops**  
   Use Hermes scheduler to run Bureau skills in background windows (nightly safeguard/scrimmage checks, stale task resurfacing, dependency-risk scans).

4. **Cross-Channel Memory Weaving**  
   Capture channel-native context (voice notes, SMS snippets, Slack decisions) and distill into Bureau’s structured memory graph + qdrant semantic memory.

5. **Dual-Mode Assistant (Life + SWE)**  
   A single persona with policy-separated stacks: personal ops (calendar, reminders, routines) and SWE ops (repo tasks, PR quality gates), both supervised by Bureau protocols.

## Sources

- https://hermes-agent.nousresearch.com/docs/
- https://hermes-agent.nousresearch.com/docs/integrations/providers/
- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/
