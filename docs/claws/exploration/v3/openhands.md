# OpenHands × Bureau integration assessment

## Platform profile

OpenHands is a mature open-source coding-agent platform focused on software engineering workflows, runtime isolation, and reproducible task execution.

### Functional surface (researched)

- Dedicated docs for runtime architecture and security configuration.
- Emphasis on coding-task execution environments and tool/runtime provisioning.
- Strong open-source ecosystem signal around SWE automation.

### Memory architecture + autonomous loop

- OpenHands appears stronger in execution/runtime than in deeply differentiated long-memory architecture compared with Letta.
- It can support iterative autonomy through task loops, but Bureau would provide stronger cross-session memory semantics (dossiers + structured memory backends) and cross-CLI orchestration.

### Workflow & UX

- Excellent SWE-agent UX potential for coding tasks, issue work, and iterative patches.
- Less naturally oriented to day-to-day personal assistant channels than Hermes/OpenClaw/Memoh.
- Best used as a high-throughput engineering execution engine in a broader assistant stack.

### Fit with Bureau

**Fit score: 8.7/10.**

Why it fits:
- Very complementary: OpenHands for deep SWE execution, Bureau for orchestration protocols, role routing, memory continuity, and cross-platform cohesion.

Risks:
- Integration could feel “toolchain-heavy” without clear UX abstraction.
- Need explicit contract between Bureau delegation layer and OpenHands runtime/job lifecycle.

## High-impact Bureau × OpenHands merge concepts

1. **Spec-to-Execution Conveyor**  
   Bureau `spec-kit` + skills pipeline emits OpenHands execution batches with tracked evidence artifacts.

2. **Autonomous PR Factory (Guardrailed)**  
   OpenHands handles implementation loops; Bureau runs scrimmage/safeguard/clearance gates before PR publication.

3. **Failure Replay Lab**  
   OpenHands run traces are folded into Bureau dossiers and replayed by specialist roles for root-cause extraction.

4. **Hybrid Human Control Plane**  
   Non-technical users interact via Bureau concierge while OpenHands executes technical work behind a policy gate.

## Sources

- https://docs.openhands.dev/overview/introduction
- https://docs.openhands.dev/openhands/usage/faqs (runtime/security references)
- https://github.com/All-Hands-AI/OpenHands
