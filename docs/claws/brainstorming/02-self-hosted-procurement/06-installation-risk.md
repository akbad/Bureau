# Section 6: Installation Risk and Unknowns

## Hermes Agent — unknowns requiring hands-on validation

### 1. Claude Code credential reuse — actual mechanics

The docs state "Hermes prefers Claude Code's own credential store" for Anthropic auth. What needs validation:
- **Does this work with the current Claude Code version on macOS?** Credential store format may change between Claude Code releases.
- **Is it the OAuth token or the session cookie?** The mechanism matters for token refresh behavior.
- **What happens when the Claude Code session expires?** Does Hermes gracefully re-auth, or does it fail silently?
- **Does this count against Claude Code subscription rate limits?** If Hermes uses the credential store for its own reasoning AND delegates coding to Claude Code CLI, that is two concurrent consumers of the same subscription.
- **Verification step:** Install Hermes, configure Claude Code auth, run `hermes model` to confirm provider works, then test with a multi-hour session to verify token refresh.

### 2. Claude Code / Codex CLI delegation — actual behavior

Issue #477 confirms these delegation targets exist, but:
- **Is delegation a subprocess call or an API call?** The docs suggest subprocess, but the exact invocation pattern matters for error handling and output capture.
- **Does delegation preserve Bureau's protocolized context injection?** If Hermes calls `claude -p "do X"`, Bureau's CLAUDE.md context injection still occurs because it is file-based. This should work but needs verification.
- **Can Hermes pass structured task context to the CLI worker?** Or is it a raw prompt string?
- **Verification step:** Configure Hermes with Claude Code delegation, send a coding task via Telegram, verify that the response shows Claude Code was used and that Bureau's context was injected.

### 3. Messaging channel stability on macOS

- **Telegram:** Long-polling mode (not webhooks) — should work behind NAT without port forwarding. Needs verification of reconnection behavior after Mac sleep/wake.
- **WhatsApp via Baileys:** QR code pairing needed. Known to disconnect periodically. Need to test reconnection reliability on a Mac that sleeps/wakes.
- **Signal via signal-cli:** Requires Java. Setup is non-trivial. Need to verify macOS compatibility and daemon behavior.
- **Verification step:** Set up each desired channel, test after Mac sleep/wake cycles, test after network changes, run for 48+ hours to evaluate stability.

### 4. FTS5 session search summarization — LLM dependency

The FTS5 session search feature uses an LLM to summarize retrieved past-session results before injecting them into context. By default this targets "Gemini Flash" (a cloud provider).

- **Question:** Can this summarization step be redirected to Ollama or the Claude Code credential store provider?
- **Question:** If redirected to a weaker local model, does the summarization quality degrade enough to make session search useless?
- **Mitigation:** If the feature cannot be redirected, it can be disabled — the core MEMORY.md/USER.md/skill system works without it.
- **Verification step:** Configure Hermes with Ollama as the sole provider, trigger a session search, verify it works or fails gracefully.

### 5. Memory growth and performance

- **FTS5 index growth:** After months of use, the SQLite session archive will grow. What is the query performance at 10K, 50K, 100K sessions?
- **Skill accumulation:** If Hermes creates hundreds of skill files, does system prompt bloat degrade performance?
- **Verification step:** Simulate heavy usage for a week, then benchmark memory retrieval and session startup times.

### 6. Honcho self-hosting (if desired later)

- Honcho can self-host locally via Docker (PostgreSQL backend).
- For basic operation, no external API key needed (`AUTH_USE_AUTH=false` for local development).
- **But:** Honcho's "dialectic" user-modeling features likely require an LLM API call to generate user insights. If using Ollama for this, quality may be poor.
- **Verification step:** Deploy Honcho locally, test with Ollama as the LLM backend, evaluate whether the user-modeling quality justifies the complexity.

---

## OpenClaw — unknowns requiring hands-on validation

### 1. Ollama as primary LLM — quality ceiling

- OpenClaw's own reasoning (for non-delegated tasks like research, planning, life management) runs on Ollama or the bundled Pi binary.
- **Quality gap:** Ollama with llama 3.3 8B or similar is significantly weaker than Claude 3.5/4 for complex reasoning, research synthesis, and nuanced planning.
- **Can OpenClaw route its OWN reasoning through a Claude Code CLI backend?** The CLI backends are documented for coding delegation, but it is unclear whether OpenClaw can use a CLI backend as its general LLM provider. This is the critical question.
- **Verification step:** Deploy OpenClaw with Ollama, test non-coding tasks (research, planning, complex questions). Compare quality to the same tasks through Hermes using Claude Code auth.

### 2. iMessage via BlueBubbles — setup complexity

- BlueBubbles requires a running macOS machine (which is the user's setup — good).
- **But:** BlueBubbles needs to run as a separate service alongside OpenClaw.
- **Question:** Does the BlueBubbles setup require a paid Apple Developer account? Does it work with a free Apple ID?
- **Question:** How does BlueBubbles handle iMessage delivery receipts, typing indicators, and group chats?
- **Verification step:** Install BlueBubbles, configure OpenClaw iMessage adapter, test from iPhone. Evaluate UX (latency, media handling, group chat behavior).

### 3. Supply-chain security — ClawHub skill vetting

- After the January 2026 Atomic Stealer incident, skill vetting is non-optional.
- **Question:** Does OpenClaw have a built-in skill integrity checker? Or must every skill be manually reviewed?
- **Question:** Can you use OpenClaw with zero ClawHub skills (filesystem-only)?
- **Mitigation:** Install only bundled skills. Review any third-party skill source code manually. Never use `--dangerously-force-unsafe-install` for untrusted skills.
- **Verification step:** Fresh install, audit bundled skills, operate for a week without any ClawHub skills.

### 4. Daemon reliability on macOS

- `openclaw onboard --install-daemon` sets up auto-start.
- **Question:** What is the restart behavior after crashes? Is there a watchdog?
- **Question:** How does it handle macOS sleep/wake with active WebSocket connections to messaging platforms?
- **Question:** Memory usage over time — Node.js can leak. What is the 30-day footprint?
- **Verification step:** Deploy, run for 2+ weeks, monitor memory and reconnection behavior.

### 5. Multi-agent council — practical reliability

- Parallel Claude Code instances with git worktree isolation is architecturally elegant.
- **Question:** How does the consensus voting actually work? Is it majority-rules, or does one dissenter block?
- **Question:** What happens when one agent crashes mid-council?
- **Question:** What is the resource cost of 3+ concurrent Claude Code processes on a MacBook Pro?
- **Verification step:** Run a council task with 3 agents, monitor CPU/RAM, intentionally kill one agent, observe recovery behavior.

---

## Both platforms — shared unknowns

### 1. Bureau integration wiring

Neither Hermes nor OpenClaw has built-in Bureau integration. The wiring would be:

- **Option A:** Hermes/OpenClaw calls Bureau's MCP servers directly (Qdrant, Memory MCP, Sourcegraph, etc.) via MCP client support.
- **Option B:** Hermes/OpenClaw delegates certain tasks to Bureau's concierge, which then delegates to Claude Code/Codex.
- **Option C:** Bureau's concierge is retired; Hermes/OpenClaw replaces it entirely.

Each option has different complexity. Option A is most modular. Option C is simplest operationally. Option B creates a confusing delegation chain.

### 2. Concurrent subscription use

If both Hermes (as LLM provider) and Claude Code (as coding worker) use the same Anthropic subscription, rate limits may apply. Need to verify Anthropic's per-subscription concurrency limits for Claude Code subscription auth.

### 3. Mac sleep/wake behavior

Both platforms run as daemons. macOS sleep behavior (especially with Power Nap, clamshell mode on a plugged-in MacBook) may interrupt WebSocket connections, Telegram long-polling, or background cron tasks. Need to verify and potentially configure `caffeinate` or `pmset` to prevent sleep.

### 4. Telegram Bot API rate limits

Single-user bots have generous limits, but automated systems can hit them. Need to verify: how many messages per minute does each platform send? Do background tasks generate messages? Is there rate-limit handling?
