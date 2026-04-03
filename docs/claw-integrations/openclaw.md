# OpenClaw Integration Analysis

**Date:** 2026-04-03
**Source:** [openclaw/openclaw](https://github.com/openclaw/openclaw) (346k stars, MIT, v2026.x.x)
**Language:** Node.js (Node 24 recommended)
**Maintainer:** OpenClaw community

---

## 1. Platform Overview

OpenClaw is the largest open-source personal AI assistant platform by community size (346k GitHub stars, 68.9k forks, 24,810 commits). It operates as a **gateway-centric system**: a WebSocket control plane manages sessions, channels, events, and webhooks while multiple clients (CLI, web UI, macOS app, iOS/Android nodes) connect to it.

OpenClaw's breadth is unmatched — 23+ messaging adapters, companion apps for every platform, voice wake/talk mode, live canvas, multi-agent routing, and a 13,000+ skill marketplace (ClawHub). It is the maximalist option in the field.

### Architecture

| Component | Role |
|---|---|
| **Gateway** | WebSocket control plane on localhost:18789; manages sessions, channels, events, webhooks |
| **Pi Agent Runtime** | RPC mode execution with tool/block streaming |
| **Channel Adapters** | Plugin architecture — each channel normalizes messages to common format |
| **Multi-Agent Routing** | Route channels/accounts/peers to isolated agent instances with separate workspaces |
| **Companion Apps** | macOS (menu bar + voice wake), iOS node, Android node |
| **Web UI** | Vite + Lit SPA served by Gateway |

### Key stats

| Metric | Value |
|---|---|
| GitHub stars | 346,000 |
| Forks | 68,900 |
| Commits | 24,810 |
| Channel adapters | 23+ |
| Skills (ClawHub) | 13,000+ community-contributed |
| Release cadence | Same-day stable releases (vYYYY.M.D) |
| Install | `npm install -g openclaw@latest` |

---

## 2. Memory Architecture

OpenClaw's memory is session-oriented rather than architecturally deep:

| Feature | Implementation |
|---|---|
| Session history | Transcript logging via `sessions_history` tool |
| Session compaction | `/compact` command for summarization |
| Per-agent workspace | SOUL.md and AGENTS.md per workspace directory |
| Agent-to-agent coordination | `sessions_list`, `sessions_send` tools |
| Presence tracking | Multi-agent awareness |

### What's missing (compared to Bureau and Hermes)

- **No vector memory:** No semantic search over past interactions
- **No entity/relation graphs:** No structural memory
- **No user model:** No persistent understanding of user preferences
- **No cross-session recall:** Each session starts fresh (compaction summarizes but doesn't enable retrieval)
- **No memory tools:** Agents don't actively manage their own memory

### Comparison to Bureau

| Dimension | Bureau | OpenClaw |
|---|---|---|
| Semantic vectors | Qdrant (strong) | None |
| Structural memory | Memory MCP (entity graphs) | None |
| Session persistence | claude-mem, dossiers | Session compaction only |
| User model | None | None |
| Agent workspace | Protocol context files | SOUL.md + AGENTS.md |

**Assessment:** Memory is OpenClaw's weakest dimension. Bureau already has a more sophisticated memory stack. Integrating would not improve Bureau's memory — Bureau would need to *provide* memory capabilities to OpenClaw.

---

## 3. Autonomous Learning Loop

OpenClaw has **no autonomous learning loop**. Agents do not:
- Create skills from experience
- Deepen a user model over time
- Search past conversations for recall
- Self-improve behavioral patterns

Skills are installed from ClawHub (marketplace) or the workspace, not generated from agent experience. This is a consumer install-and-use model, not a learning model.

**Comparison:** Hermes Agent's learning loop is far more advanced. Bureau would gain nothing in this dimension from OpenClaw.

---

## 4. Operational Memory Stack

| Component | Storage | Notes |
|---|---|---|
| Session transcripts | In-memory + logs | Available via `sessions_history` tool |
| Agent workspace | Filesystem (per-agent directories) | SOUL.md, AGENTS.md, local files |
| Cron jobs | Gateway config | Scheduled task execution |
| Webhooks | Gateway config | Event-triggered automation |

OpenClaw's operational state is minimal compared to Hermes's SQLite FTS5 or Bureau's multi-backend stack. The focus is on real-time session management rather than persistent knowledge.

---

## 5. Practical Assistant Features

This is where OpenClaw dominates the field.

### Voice
- **Voice Wake:** Wake-word activation on macOS/iOS with customizable triggers
- **Talk Mode:** Continuous voice conversation overlay
- **Audio pipeline:** ElevenLabs + system TTS fallback; transcription hooks; size caps for media

### Live Canvas
- Agent-driven visual workspace with A2UI (Abstract-to-UI)
- Push/reset/eval/snapshot operations
- Cross-device rendering

### Companion Apps
| Platform | Features |
|---|---|
| **macOS** | Menu bar control, voice wake + PTT overlay, WebChat, debug tools, remote gateway SSH |
| **iOS** | Device pairing, voice trigger forwarding, canvas surface |
| **Android** | Chat, voice, canvas, camera/screen recording, device commands (notifications, location, SMS, photos, contacts, calendar, motion) |

### Scheduling & Automation
- Cron jobs for recurring tasks
- Webhook triggers for event-driven automation
- Gmail Pub/Sub for email workflows

### Browser
- Dedicated Chrome/Chromium control with CDP
- Snapshots, actions, profiles
- Session persistence

### Skills Marketplace
- ClawHub: 13,000+ community skills
- Three tiers: bundled, managed, workspace-level
- Installation gating for safety

---

## 6. SWE Assistant Features

OpenClaw is a general-purpose assistant, not a specialized SWE tool. Developer capabilities include:

- **Browser-based coding** via CDP
- **Shell execution** with elevated mode toggle (`/elevated on|off`)
- **Multi-agent routing** to specialized agents per task type
- **Skills** from ClawHub for specific dev workflows
- **MCP Registry** for external tool integration

### What it lacks (compared to Bureau)
- No multi-step code review (Assess Mode)
- No step-gated editing (Micro Mode)
- No specialized agent roles (66 roles)
- No cross-CLI orchestration
- No spec-driven development
- No SWE-bench metrics

Bureau's SWE depth is significantly deeper. OpenClaw provides a platform; Bureau provides a dev workflow.

---

## 7. Channel & Platform Support

OpenClaw has the broadest channel support in the field — 23+ adapters:

| Category | Channels |
|---|---|
| **Core messaging** | WhatsApp (Baileys), Telegram (grammY), Slack (Bolt), Discord (discord.js), Signal (signal-cli) |
| **Enterprise** | Google Chat (Chat API), Microsoft Teams, Matrix |
| **Apple** | BlueBubbles (iMessage), legacy iMessage |
| **Asia** | Feishu, LINE, WeChat, Zalo |
| **Community** | IRC, Nostr, Mattermost, Nextcloud Talk, Synology Chat, Tlon, Twitch |
| **Web** | WebChat (built-in) |

Each adapter normalizes messages into a common format. Per-channel configuration includes model overrides, DM/group policies, and rate limiting.

### iMessage path
OpenClaw uses **BlueBubbles** for iMessage, which requires:
- A Mac running the BlueBubbles server
- The private API mode (recommended for send functionality) requires **disabling SIP**
- Users have reported send-path issues without the private API

**This is the messiest iMessage path in the field.** CoPaw's macOS-native approach is cleaner.

### Compared to Bureau
Bureau has Telegram only. OpenClaw adds 22+ channels. However, many of these (Tlon, Synology Chat, Nostr) are niche. The high-value additions are: Discord, Slack, WhatsApp, Signal, and iMessage.

---

## 8. Security Model

### Approval system

- **DM pairing:** Unknown senders receive pairing codes; bot ignores until approved via `openclaw pairing approve <channel> <code>`
- **Optional open mode:** Requires explicit allowlist configuration
- **Per-session elevated bash:** `/elevated on|off` toggle
- **macOS TCC integration:** Permission mapping
- **Node-based action authorization**
- **`openclaw doctor`:** Diagnostic tool for surfacing risky DM policies

### Trust model
OpenClaw explicitly states: **"The model/agent is not a trusted principal"** and **"running one gateway for multiple mutually untrusted operators is not a recommended setup."** The security model is operator-intent guardrails, not hostile multi-tenant isolation.

### CVE History (March 2026)

**Nine CVEs in four days** (March 18-21, 2026):

| CVE | CVSS | Issue |
|---|---|---|
| CVE-2026-32922 | **9.9** | `device.token.rotate` fails to constrain new token scopes — critical privilege escalation |
| CVE-2026-32978 | High | `system.run` approvals fail to bind mutable file operands — approved commands can be rewritten |
| CVE-2026-32971 | High | Approval displays extracted shell payloads instead of executed argv — misleading approval text |
| CVE-2026-33577 | High | `node.pair.approve` missing callerScopes validation — low-privilege operator can approve malicious nodes |
| CVE-2026-34503 | High | Device removal doesn't terminate active WebSocket sessions |
| + 4 more | Med-High | Various authorization and validation issues |

**Minimum safe version:** v2026.3.12 or later.

### Compared to Bureau
Bureau's single-user Telegram filter is simpler but has a much smaller attack surface. OpenClaw's breadth (23+ channels, companion apps, WebSocket gateway) creates a large attack surface, as the CVE flood demonstrates. Integrating with OpenClaw means inheriting that attack surface.

**Key concern:** The CVE-2026-32978 pattern (approval bypass via mutable operands) is a design-level issue, not a one-off bug. It suggests the approval system was not designed with adversarial robustness in mind — consistent with OpenClaw's own statement that the model is not a trusted principal.

---

## 9. Integration Architecture

### Proposed: OpenClaw as maximalist channel/UI layer, Bureau as dev backend

```
User (any of 23+ channels, companion apps, voice)
    ↓
OpenClaw Gateway (channel I/O, voice, canvas, skills)
    ↓ multi-agent routing
    ├── "bureau" agent workspace
    │   ├── Routes coding tasks to Bureau CLI agents
    │   ├── SOUL.md references Bureau's protocol context
    │   └── Returns structured results to OpenClaw for delivery
    └── "general" agent workspace
        └── OpenClaw handles directly (general assistant, ClawHub skills)
```

### How it connects

1. **OpenClaw as channel proxy:** OpenClaw receives messages from 23+ channels, normalizes them. Coding-tagged messages route to a "bureau" agent workspace.

2. **Bureau agent workspace:** An OpenClaw agent workspace configured with Bureau CLI commands as execution targets. SOUL.md loads Bureau's protocol context. The agent invokes `claude -p`, `gemini -p`, or `codex -q` based on task type.

3. **Results delivery:** Bureau agents return results via stdout. OpenClaw formats and delivers to the originating channel with appropriate truncation and formatting.

4. **Memory bridge:** Bureau's Qdrant instance shared with OpenClaw agents (if OpenClaw adds Qdrant MCP support). Otherwise, memory stays separate.

5. **Canvas for code review:** OpenClaw's A2UI canvas could render Bureau's Assess Mode review reports as interactive visual documents rather than plain text.

### Changes required

**In Bureau:**
- Expose key workflows as CLI-invocable commands
- Add OpenClaw webhook receiver to concierge for channel bridge
- Configure Qdrant for shared access

**In OpenClaw:**
- Create "bureau" agent workspace with Bureau-specific SOUL.md
- Configure multi-agent routing rules (coding → bureau, else → general)
- Add MCP memory tools pointing at Bureau's Qdrant (optional)

---

## 10. Fit Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Philosophy | **Moderate** | OpenClaw is maximalist/consumer; Bureau is focused/developer |
| Architecture | **Strong** | Both Node.js ecosystem; multi-agent routing maps cleanly to Bureau roles |
| Channel coverage | **Strong** | 23+ channels is unmatched; closes Bureau's biggest gap |
| Memory | **Weak** | OpenClaw has no meaningful memory architecture; Bureau would provide, not receive |
| Learning | **Weak** | No learning loop; no skill-from-experience; no user model deepening |
| Security | **Weak** | Largest attack surface + 9 recent CVEs; inheriting this is a significant risk |
| Dev workflows | **Moderate** | OpenClaw provides platform; Bureau provides depth. Canvas could enhance code review UX |
| Maintenance burden | **High** | OpenClaw is very large (24k commits); rapid release cycle; dependency on a massive community project |

---

## 11. Risks & Tradeoffs

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Security inheritance** | **High** | 9 CVEs in 4 days; attack surface of 23+ channels + WebSocket gateway. Every OpenClaw CVE becomes your CVE |
| **Maintenance burden** | **High** | OpenClaw moves fast — same-day releases, breaking changes. Keeping up requires constant attention |
| **Architectural overlap** | **High** | Both have agent loops, both have tool systems, both have config hierarchies. Who orchestrates whom? |
| **iMessage/SIP risk** | **Medium** | BlueBubbles private API requires disabling SIP on macOS — compromises your Mac's security posture |
| **Memory void** | **Medium** | OpenClaw adds no memory capability; you still need to solve memory unification separately |
| **Scope creep** | **Medium** | OpenClaw's 13k skills, canvas, voice, companion apps — easy to over-invest in configuring a platform that isn't your core |
| **Community dependency** | **Low-Medium** | 346k stars means strong community but also means governance, breaking changes, and priorities you don't control |

### What you gain
- 23+ channels (broadest in field)
- Voice wake/talk mode
- Live canvas for visual agent workspace
- Companion apps (macOS, iOS, Android)
- 13,000+ community skills
- Largest community and ecosystem

### What you lose
- Security simplicity (massive attack surface)
- Architectural clarity (two large systems with significant overlap)
- Memory independence (OpenClaw contributes nothing here)
- Development focus (OpenClaw is consumer-oriented, not dev-oriented)
- Maintenance bandwidth (keeping up with OpenClaw's pace)

### Verdict

**OpenClaw is the maximalist option with the highest reward and highest risk.** It provides unmatched channel breadth and the richest assistant UX (voice, canvas, companion apps) but comes with a large attack surface, recent serious CVEs, and no memory or learning capabilities. 

For Bureau's use case, OpenClaw is best treated as a **channel-only integration** — use its 23+ adapters to receive messages, route coding tasks to Bureau, and deliver results. Do not adopt its agent loop, memory model (it doesn't have one), or security model (it's been compromised).

If you want channel breadth without OpenClaw's baggage, Hermes Agent (6 channels, stronger security, learning loop) or OpenFang (40 channels, 16-layer security) are lower-risk alternatives.

---

## 12. High-Impact Feature Merges & Extensions

Brainstormed ideas for combining Bureau and OpenClaw into something neither system could deliver alone. Each targets a capability gap that no existing tool addresses.

---

### 12.1 Ambient Code Review via Talk Mode ("Voice Assess")

Pipe Bureau's Assess Mode output into OpenClaw's Talk Mode voice pipeline. A developer says "assess the last commit" into their AirPods while walking to get coffee; OpenClaw's voice wake triggers the command, routes it to Bureau's `assess-mode` skill via the `bureau` agent workspace, and reads back the structured review — file by file — as a narrated audio walkthrough. The developer can interrupt with voice to say "skip that file" or "explain that finding in more detail," and Bureau's comprehension-style selection (architectural, data-flow, etc.) is driven entirely by spoken keywords.

**Why it matters:** Code review becomes untethered from the screen entirely. No existing tool offers voice-navigable, interactive code assessment — this turns dead time (commutes, walks) into productive review cycles.

---

### 12.2 Live Canvas Diff Theater

Use OpenClaw's A2UI Live Canvas to render Bureau's Assess Mode and Blast Radius Mode outputs as interactive visual documents. File-level findings render as expandable cards; dependency graphs from Blast Radius Mode render as force-directed node diagrams where clicking a node shows affected callers, dependents, and test coverage. Canvas snapshots are versioned per commit, so reviewers can scrub through a timeline of how the blast radius evolved across a PR's commit history. The Canvas `eval` operation executes inline code samples from review findings to demonstrate issues live.

**Why it matters:** Static text diffs are the weakest representation of code change impact. This creates a navigable, visual, executable review surface that makes blast radius and assessment findings spatially intuitive rather than requiring sequential reading.

---

### 12.3 Companion App Micro Mode ("Pocket Approvals")

Bridge Bureau's Micro Mode step-gated editing to OpenClaw's iOS and Android companion apps. Each atomic edit proposed by Micro Mode's DAG-based planner is pushed as a rich notification to the user's phone showing the diff, the DAG step name, and approve/reject/defer buttons. Approvals route back through OpenClaw's Gateway WebSocket to the running Bureau agent, unblocking the next step. On iPad, the full DAG is rendered as an interactive flowchart where completed steps are green, the current step pulses, and future steps are gray — tapping any node shows its planned edit.

**Why it matters:** Step-gated editing currently requires the developer to sit at their terminal for every approval. This decouples approval authority from the development machine, enabling a developer to supervise precise, controlled edits from anywhere — a phone on the couch, a tablet in a meeting.

---

### 12.4 Role-to-Agent Routing Mesh

Map Bureau's 66 agent roles directly onto OpenClaw's multi-agent routing system, each as an isolated agent workspace with its own SOUL.md derived from the corresponding Bureau role prompt. Incoming messages are classified by OpenClaw's routing rules: a Slack message mentioning "security audit" routes to the `security-compliance` Bureau role workspace; a Discord message about "explain this function" routes to the `explainer` workspace. Each workspace invokes the appropriate Bureau CLI agent (`claude -p`, `gemini -p`, `codex -q`) with the role's system prompt, and results return through the originating channel. A meta-routing layer uses Bureau's `handoff-guide.md` logic to cascade between roles when the initial role determines the task needs escalation (e.g., `debugger` discovers a security issue and escalates to `security-compliance`).

**Why it matters:** This turns OpenClaw's 23+ channels into 66 specialized front doors. Instead of one general-purpose bot, teams get an army of domain-expert agents reachable from every messaging platform they already use, with automatic inter-role escalation preserving Bureau's orchestration intelligence.

---

### 12.5 ClawHub Skill Transpiler

Build a bridge that converts ClawHub skill packages (OpenClaw's 13,000+ community skills in their manifest format) into Bureau-compatible skill definitions under `protocols/context/static/skills/`. The transpiler parses a ClawHub skill's intent triggers, tool bindings, and prompt templates, then emits a Bureau `SKILL.md` with matching activation patterns, a tool mapping layer that redirects ClawHub tool calls to Bureau's MCP server equivalents (e.g., ClawHub's `browser.navigate` maps to Bureau's Playwright MCP, ClawHub's `search.web` maps to Bureau's Brave/Tavily MCP), and a compatibility report listing any unmappable capabilities. In the reverse direction, Bureau skills (assess-mode, micro-mode, scrimmage-mode, etc.) are packaged as ClawHub skills so the OpenClaw community can install Bureau's workflows natively.

**Why it matters:** Two skill ecosystems remain siloed today. Cross-pollination gives Bureau access to thousands of community workflows (home automation, email triage, calendar management) and gives ClawHub's community access to Bureau's rigorous dev-workflow skills — expanding both ecosystems without duplicate effort.

---

### 12.6 iMessage CI/CD War Room

Configure OpenClaw's BlueBubbles iMessage adapter as an emergency-only alert channel for Bureau agents monitoring CI/CD pipelines. Bureau's `observability` role agent watches GitHub Actions / CI webhooks (received via OpenClaw's webhook system), and when a pipeline fails, it runs Bureau's `debugger` role against the failure logs, generates a diagnosis, and pushes a structured iMessage to the on-call developer's iPhone containing: the failing job name, the diagnosed root cause, a suggested fix diff, and inline reply commands ("apply fix", "ignore", "escalate to #team-channel"). Replies in iMessage route back through OpenClaw to Bureau, which can apply the fix and re-trigger CI — all without opening a laptop.

**Why it matters:** CI/CD failures currently require context-switching to a browser, reading logs, and manually debugging. This collapses the detect-diagnose-fix loop into an iMessage conversation, using a channel developers cannot miss (unlike Slack notifications they mute).

---

### 12.7 macOS Desktop Gatekeeper for Scrimmage Mode

Integrate Bureau's Scrimmage Mode (self-attack testing) with OpenClaw's macOS companion app to create a desktop notification approval gate. When Scrimmage Mode generates attack vectors after a code change, each vector category (input validation, state corruption, concurrency, security) surfaces as a macOS notification via OpenClaw's menu bar app. The developer can expand each notification to see the attack description and the agent's findings, then approve ("mark as addressed"), dismiss ("accepted risk"), or escalate ("block merge until fixed"). The approval state syncs back to Bureau, and a merge-blocking status check is updated on the PR via GitHub API. The macOS app's debug tools panel shows a real-time dashboard of all active scrimmage sessions across the workspace.

**Why it matters:** Scrimmage Mode's attack vectors are only useful if developers actually read and act on them. Native OS-level notifications with inline actions eliminate the friction of returning to the terminal, and the merge-blocking integration ensures findings cannot be silently ignored.

---

### 12.8 Cross-Device Assess Mode Relay ("Review Handoff")

A developer starts an Assess Mode review on their desktop via Claude Code. Midway through, they need to leave. They say "hand off to iPad" (voice or text). OpenClaw's Gateway serializes the current Assess Mode state — which files have been reviewed, which comprehension style is active, outstanding findings, and position in the file queue — and pushes it to the iPad companion app's Canvas surface. On iPad, the review continues as an interactive canvas document: swipe between files, tap findings to expand, use Apple Pencil to annotate code sections with handwritten notes that are OCR'd and attached to the finding. When the developer returns to their desk, "resume on desktop" pulls the state back, including all iPad annotations, and the terminal-based review continues where the canvas left off.

**Why it matters:** No code review tool supports seamless cross-device handoff with state preservation today. This makes review a continuous activity that follows the developer across devices rather than being locked to a single terminal session.

---

### 12.9 Shadow Mode Streaming to Web UI Observers

Bureau's Shadow Mode (propose-only, no file writes) streams its proposed diffs in real-time to OpenClaw's WebChat UI, where multiple team members can observe. Each proposed change appears as a live-updating card in the web interface. Observers can vote (thumbs up/down) on individual changes, leave inline comments, or flag concerns — all rendered back to the Shadow Mode agent as structured feedback before the developer decides which diffs to apply. The Gateway's WebSocket multicasting handles fan-out to all connected observers. This turns Shadow Mode from a single-user transparency tool into a collaborative, real-time code proposal review.

**Why it matters:** Shadow Mode is currently a solo experience. Adding live multi-observer streaming with voting creates a new category: real-time collaborative AI code review, where the team watches the agent think and collectively decides what to accept — before any file is touched.

---

### 12.10 Cron-Driven Safeguard Mode Watchdog

Use OpenClaw's cron job system to schedule Bureau's Safeguard Mode as a recurring background integrity check. Every N minutes (configurable), OpenClaw triggers the `safeguard-mode` skill via the `bureau` agent workspace, which verifies all defined system invariants (value constraints, state machine rules, relationships, ordering guarantees) against the current working tree. If any invariant is violated — perhaps by a concurrent agent's edit or a manual change — an alert fires through whichever OpenClaw channels the developer has configured (Slack for team visibility, iMessage for urgency, desktop notification for immediacy). The cron job maintains a ledger of invariant check history, and Canvas renders a time-series graph of invariant health across the session.

**Why it matters:** Invariants defined by Safeguard Mode are currently only checked at the moment of invocation. Making them a continuous background watchdog catches violations the instant they occur — especially critical in multi-agent workflows where one agent's changes can silently break another agent's assumptions.

---

### 12.11 Android Sensor-Augmented Context Injection

Leverage OpenClaw's Android companion app's access to device sensors (location, motion, camera, calendar) to inject contextual signals into Bureau agent sessions. If the developer's calendar shows they are in a "Sprint Review" meeting, Bureau agents automatically switch to more conservative modes (Shadow Mode, higher Assess Mode scrutiny). If location data indicates the developer is away from their usual workspace, Micro Mode defaults to requiring explicit approval for all edits (no auto-approve). Camera/screen recording on the Android device can capture whiteboard diagrams during meetings; OpenClaw processes these via vision and injects the extracted architectural intent into Bureau's `architect` role agent as supplementary context for the next design task.

**Why it matters:** Agent behavior is currently context-blind — the same aggressiveness whether the developer is heads-down coding or in a meeting. Ambient device signals allow Bureau agents to adapt their autonomy level to real-world developer context without any manual mode-switching.

---

### 12.12 Multi-Channel Spec-Kit Collaboration

Extend Bureau's spec-driven development workflow (powered by GitHub's `spec-kit`) across OpenClaw's channel adapters so that different stakeholders contribute to specs through their preferred platform. A product manager writes requirements in a Slack thread; OpenClaw routes these to Bureau's `spec-kit` workflow, which integrates them into the spec document. A designer shares mockups in a Discord channel; these are captured and attached to the spec's UI section. An engineer asks clarifying questions via Telegram; Bureau's agent responds with spec-driven follow-ups. All contributions converge into a single `spec-kit` spec, plan, and tasklist in the repo. The Canvas renders the spec as a living document showing each contributor's input color-coded by source channel, with real-time status of which spec sections are complete, which need input, and which are being implemented.

**Why it matters:** Spec-driven development currently assumes a single developer interacting with a single CLI. Real projects involve multiple stakeholders across multiple platforms. This makes `spec-kit` a multiplayer, multi-channel specification system where the spec is a shared artifact that accumulates structured input from wherever people already communicate.
