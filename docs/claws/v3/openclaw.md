# OpenClaw × Bureau integration assessment

## Platform profile

OpenClaw positions as an always-on, self-hosted personal AI assistant spanning multiple platforms/channels, with a strong practical orientation and active ecosystem iteration.

### Functional surface (researched)

- Multi-platform assistant positioning ("Any OS. Any Platform").
- Integration-oriented product posture and docs around adapters.
- Security model documentation including sandbox guidance for non-main sessions.
- Host-vs-container execution tradeoff explicitly documented.

### Memory architecture + autonomous loop

- OpenClaw messaging and long-running assistant model imply persistent session continuity.
- Public materials sampled suggest active community experimentation with richer memory designs.
- Compared with Letta, memory formalism is less prominently specified in canonical docs; compared with Hermes, OpenClaw appears similarly practical-first.

### Workflow & UX

- Designed for day-to-day assistant continuity and channel ubiquity.
- Good human-facing ergonomics for ongoing conversations and operations.
- SWE workflows likely benefit from layering Bureau’s explicit coding protocol stack, role governance, and cross-CLI delegation patterns.

### Fit with Bureau

**Fit score: 8.5/10.**

Why it fits:
- Strong complement to Bureau’s “agent operating system for workstreams” with user-facing persistence.
- Sandbox and security docs suggest realistic operational maturity for real-world deployment.

Risks:
- Overlap with Bureau orchestration semantics must be separated cleanly.
- Need careful policy model for host-level tool execution.

## High-impact Bureau × OpenClaw merge concepts

1. **Sandbox-by-Intent Execution**  
   Bureau risk classifier sets OpenClaw session sandbox mode dynamically (main vs non-main style), balancing speed and safety.

2. **Lobster Dossiers**  
   Native OpenClaw commands to fold/unfold Bureau dossiers, enabling long project memory from chat channels.

3. **Cross-Platform Incident Room**  
   One incident thread mirrored across Discord/Telegram/Slack, with Bureau role swarm coordinated from a single command source.

4. **Memory Distillation Ladder**  
   Raw channel logs → semantic chunks → structured architecture entities → actionable playbooks.

5. **Ops Concierge Fusion**  
   Bureau concierge scheduling/scoring integrated with OpenClaw’s assistant channels for daily briefing, sprint reminders, and autonomous follow-ups.

## Sources

- https://github.com/openclaw/openclaw
- https://openclaw.ai/integrations
- https://docs.openclaw.ai (security/sandboxing references)
