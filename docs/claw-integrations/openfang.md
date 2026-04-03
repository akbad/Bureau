# OpenFang -- Integration Analysis for Bureau

**Date:** 2026-04-03
**Source:** [github.com/RightNow-AI/openfang](https://github.com/RightNow-AI/openfang) (16K+ stars, MIT, v0.3.30)
**Language:** Rust (137K LOC, 14 crates, 1,767+ tests)
**Maintainer:** Jaber / RightNow AI

---

## 1. Platform Overview

OpenFang brands itself as an **Agent Operating System** rather than a framework or
chatbot wrapper.  It compiles to a single ~32 MB Rust binary with a Tauri 2.0
desktop app, a web dashboard on `:4200`, and a daemon that runs autonomous agents
around the clock.

Core concept: **Hands** -- pre-built autonomous capability packages that operate
on schedules without interactive prompting.  Seven ship bundled (Clip, Lead,
Collector, Predictor, Researcher, Twitter, Browser).  Each Hand bundles a
`HAND.toml` manifest, a multi-phase system prompt, a `SKILL.md` domain reference,
and configurable guardrails (e.g. the Browser Hand enforces purchase approval
gates).

Additional primitives:

| Primitive | Count | Notes |
|-----------|-------|-------|
| Built-in tools | 53 | Plus MCP + A2A support |
| Channel adapters | 40 | Telegram through DingTalk (see Section 7) |
| LLM providers | 27 | 123+ models via 3 native drivers (Anthropic, Gemini, OpenAI-compat) |
| Skills | 60 bundled | SKILL.md format, FangHub marketplace |
| REST/WS/SSE endpoints | 140+ | OpenAI-compatible chat completions API |

OpenFang includes a one-command migration engine for OpenClaw (`openfang migrate
--from openclaw`) and reads SKILL.md natively, making it compatible with the
broader ClawHub/AgentSkills ecosystem Bureau already tracks.

**Status:** Pre-1.0.  The project ships fast and breaks between minor versions.
Production users are advised to pin to a specific commit.

---

## 2. Memory Architecture

OpenFang uses a dual-layer memory system built on **SQLite + vector embeddings**
(crate: `openfang-memory`).

| Layer | Backend | Purpose |
|-------|---------|---------|
| Structured persistence | SQLite | Canonical sessions, agent state, audit trail |
| Semantic retrieval | Vector embeddings (SQLite-backed) | Similarity search over conversation history and knowledge |

Additional memory features documented:

- **Session compaction** -- long conversations are compressed to stay within
  context windows while preserving salient facts.
- **Canonical sessions** -- a single source-of-truth representation for each
  conversation thread, regardless of which channel originated it.
- **7-phase session repair** (security system #14) -- automatic validation and
  recovery from corrupted message histories.

**Comparison with Bureau's stack:**

| Concern | Bureau | OpenFang |
|---------|--------|----------|
| Vector store | Qdrant (dedicated server) | SQLite-embedded vectors |
| Structured memory | Memory MCP + claude-mem (fragmented) | SQLite (unified) |
| Compaction | Not yet unified | Built-in session compaction |
| Semantic search | Qdrant ANN | Embedded vector search |
| Scalability | Qdrant scales independently | SQLite single-file; may bottleneck at scale |

Bureau has more powerful vector infrastructure (Qdrant) but fragments its memory
across three backends.  OpenFang has a unified but less scalable store.  An
integration could use Qdrant as a drop-in replacement for OpenFang's vector layer
while adopting OpenFang's compaction and canonical-session logic.

---

## 3. Autonomous Learning Loop

OpenFang's Hands operate on scheduled loops without user prompting:

1. **Wake** -- the scheduler triggers a Hand at its configured interval.
2. **Collect** -- the Hand gathers signals from configured sources (web, APIs,
   prior knowledge graph).
3. **Reason** -- multi-phase system prompts guide structured analysis.  The
   Predictor Hand, for example, builds calibrated reasoning chains with
   confidence intervals and tracks accuracy via Brier scores.
4. **Act** -- outputs are generated (reports, social posts, lead lists, video
   clips) and staged for delivery.
5. **Gate** -- sensitive actions pass through approval queues (Browser purchases,
   Twitter posts).
6. **Deliver** -- results are pushed to configured channels.
7. **Learn** -- ICP profiles (Lead Hand), accuracy calibration (Predictor), and
   knowledge graphs (Collector) accumulate across runs.

Bureau currently lacks a comparable proactive loop.  The evaluation doc
(`2026-04-02-agent-framework-evaluation.md`) identifies this as a "significant"
gap (task A8: "proactive assistant loop -- heartbeat-driven dispatches").

**Integration opportunity:** Bureau could adopt the Hand abstraction to wrap its
existing agent roles in autonomous schedules.  A `HAND.toml` manifest maps
cleanly to Bureau's existing role YAML + SKILL.md structure, adding schedule,
dashboard-metric, and guardrail declarations.

---

## 4. Operational Memory Stack

OpenFang's operational memory goes beyond conversation history:

| Data type | Storage | Retention |
|-----------|---------|-----------|
| Conversation sessions | SQLite canonical sessions | Indefinite, compacted |
| Agent state (Hand progress, partial results) | SQLite | Persistent across daemon restarts |
| Knowledge graphs (Collector Hand) | SQLite + vector embeddings | Grows over time; change-detected |
| Audit trail | Merkle hash-chain in SQLite | Immutable, tamper-evident |
| Credentials | AES-256-GCM vault (`openfang-extensions`) | Encrypted at rest |
| ICP profiles (Lead Hand) | SQLite | Refined per run |
| Prediction track records (Predictor Hand) | SQLite | Brier-scored history |

The Merkle hash-chain audit trail (security system #2) is notable: every agent
action is cryptographically linked to the previous one, making post-hoc tampering
detectable.  Bureau has no equivalent -- its audit trail is plain log files.

---

## 5. Practical Assistant Features

OpenFang's 7 Hands cover a broad practical-assistant surface:

| Hand | Bureau equivalent | Gap |
|------|-------------------|-----|
| **Researcher** -- deep multi-source research with CRAAP credibility scoring, APA citations, multi-language | Partial: Bureau's research agents can invoke browsing MCPs, but lack structured credibility scoring or citation formatting | Moderate |
| **Lead** -- daily prospect discovery, enrichment, ICP scoring, deduplication | None | Full gap |
| **Collector** -- OSINT monitoring, change detection, sentiment tracking, knowledge graphs | None | Full gap |
| **Predictor** -- superforecasting with calibration tracking | None | Full gap |
| **Twitter** -- autonomous social media management with approval queue | None | Full gap |
| **Clip** -- YouTube-to-shorts pipeline (FFmpeg + yt-dlp + STT) | None | Full gap |
| **Browser** -- Playwright web automation with session persistence | Partial: Bureau can invoke browser MCPs | Low gap |

Bureau's strength is coding-CLI orchestration; OpenFang's strength is
general-purpose autonomous assistance.  These are complementary, not overlapping.

---

## 6. SWE Assistant Features

OpenFang's README does not highlight software engineering workflows.  The `coder`
agent can be spawned (`openfang agent spawn coder`), but there is no mention of:

- Multi-step code editing with diff review
- Test-driven iteration loops
- Repository-aware context management
- Cross-CLI orchestration (Claude Code, Gemini CLI, Codex)

**This is Bureau's core domain and where Bureau has no peer.**  OpenFang's 53
built-in tools likely include file I/O and shell execution, but the SWE workflow
depth (Micro Mode step-gated editing, Assess Mode multi-style review, Dossier
snapshot/resume, 66 specialized agent roles) is not replicated.

**Assessment:** OpenFang and Bureau occupy complementary niches.  OpenFang excels
at always-on general-purpose autonomous tasks; Bureau excels at developer-workflow
orchestration.  A combined system would cover both.

---

## 7. Channel & Platform Support

OpenFang ships 40 channel adapters.  Bureau currently supports Telegram only.

### Adapter categories

| Category | Channels |
|----------|----------|
| Core | Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email (IMAP/SMTP) |
| Enterprise | Teams, Mattermost, Google Chat, Webex, Feishu/Lark, Zulip |
| Social | LINE, Viber, Facebook Messenger, Mastodon, Bluesky, Reddit, LinkedIn, Twitch |
| Community | IRC, XMPP, Guilded, Revolt, Keybase, Discourse, Gitter |
| Privacy | Threema, Nostr, Mumble, Nextcloud Talk, Rocket.Chat, Ntfy, Gotify |
| Workplace | Pumble, Flock, Twist, DingTalk, Zalo, Webhooks |

Each adapter supports per-channel model overrides, DM/group policies, rate
limiting, and output formatting.

WhatsApp is notable: OpenFang includes a **WhatsApp Web Gateway** that connects
via QR code (like WhatsApp Web), requiring no Meta Business account.  This is a
Node.js sidecar (`packages/whatsapp-gateway`) that bridges to the Rust daemon via
HTTP.

**Integration path for Bureau:**

Bureau's evaluation doc (task A1) already plans to abstract a `ChannelTransport`
protocol from `telegram.py`.  Two options:

1. **Borrow adapter patterns** -- Port OpenFang's adapter architecture to Python.
   OpenFang's per-channel config (model overrides, DM/group policies, rate limits)
   is a mature design to reference.
2. **Bridge via API** -- Run OpenFang as a channel gateway and route messages to
   Bureau's pipeline via OpenFang's OpenAI-compatible API or webhooks.  This
   avoids rewriting 40 adapters in Python but introduces a Rust binary dependency.

Option 2 is faster; option 1 gives Bureau full control.

---

## 8. Security Model

OpenFang claims **16 discrete security systems**, the most comprehensive set in
the competitive landscape.

| # | System | Bureau equivalent |
|---|--------|-------------------|
| 1 | WASM dual-metered sandbox (fuel + epoch interruption) | None |
| 2 | Merkle hash-chain audit trail | Plain logs |
| 3 | Information flow taint tracking (source-to-sink) | None |
| 4 | Ed25519 signed agent manifests | None |
| 5 | SSRF protection (private IP, metadata endpoint, DNS rebinding) | None |
| 6 | Secret zeroization (`Zeroizing<String>`) | Env vars |
| 7 | OFP mutual authentication (HMAC-SHA256 nonce-based) | None (single-user) |
| 8 | Capability gates (RBAC for tools) | Admin filter (basic) |
| 9 | Security headers (CSP, HSTS, X-Frame-Options) | N/A (no web UI) |
| 10 | Health endpoint redaction | N/A |
| 11 | Subprocess sandbox (env_clear + selective passthrough) | None |
| 12 | Prompt injection scanner | None |
| 13 | Loop guard (SHA256 tool-call dedup + circuit breaker) | None |
| 14 | Session repair (7-phase validation) | None |
| 15 | Path traversal prevention (canonicalization + symlink escape) | None |
| 16 | GCRA rate limiter (cost-aware, per-IP) | None |

Bureau's security posture is minimal (single-user Telegram filter + environment
variables for secrets).  This was flagged as a "moderate" gap in the evaluation
doc.  OpenFang's model is substantially more mature.

**Priority adoptions for Bureau:**

- **Prompt injection scanning** (#12) -- directly relevant to Bureau's multi-agent
  orchestration where untrusted content flows between agents.
- **Loop guard** (#13) -- Bureau's multi-agent pipelines could loop; a
  SHA256-based circuit breaker is cheap to implement.
- **SSRF protection** (#5) -- relevant once Bureau's browsing MCPs are in
  production.
- **Capability gates** (#8) -- Bureau's 66 roles should declare required tools;
  the orchestrator should enforce it.

---

## 9. Integration Architecture

### Option A: Side-by-side with shared memory

```
                    +------------------+
                    |     Qdrant       |
                    | (shared vector)  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
     +--------+--------+          +--------+--------+
     |     Bureau       |          |    OpenFang      |
     | (coding CLI      |          | (autonomous      |
     |  orchestration)  |          |  Hands + 40 ch)  |
     +--------+---------+          +--------+---------+
              |                             |
     Telegram + future ch          40 channel adapters
```

- OpenFang replaces its SQLite vector layer with Qdrant, sharing the same
  collection namespace as Bureau.
- Agents in both systems read/write to the same user memory.
- Bureau handles all SWE tasks; OpenFang handles autonomous assistant Hands.
- Coordination via A2A agent cards or shared Qdrant metadata.

### Option B: OpenFang as channel gateway only

- Run OpenFang in front, using its 40 adapters to receive messages.
- Route all messages to Bureau's pipeline via OpenFang's OpenAI-compatible API
  endpoint, where Bureau agents are exposed as "models."
- Bureau handles all logic; OpenFang handles transport.
- Simpler but wastes OpenFang's Hand capabilities.

### Option C: Hand-as-Bureau-role mapping

- Map each OpenFang Hand to a Bureau agent role.
- Bureau's orchestrator dispatches to OpenFang Hands via its REST API when
  non-coding tasks are requested.
- Bureau retains orchestration authority; OpenFang provides execution.
- Requires Bureau to understand `HAND.toml` manifests or map them to its own
  role YAML format.

**Recommended:** Start with Option C (lowest coupling, highest leverage).
Graduate to Option A when Bureau's memory unification (task A7) is complete.

---

## 10. Fit Assessment

### Synergies

| Area | Value |
|------|-------|
| Channel breadth | OpenFang's 40 adapters close Bureau's most critical gap instantly |
| Autonomous Hands | Researcher, Collector, and Predictor complement Bureau's coding focus |
| Security patterns | 16-layer model provides a reference architecture Bureau can adopt incrementally |
| SKILL.md compatibility | Both use SKILL.md; skill sharing is frictionless |
| MCP + A2A support | OpenFang speaks both protocols; interop is straightforward |
| Migration engine | Users coming from OpenClaw can land in either system |

### Mismatches

| Area | Concern |
|------|---------|
| Language mismatch | OpenFang is Rust; Bureau is Python -- no code sharing, only API-level integration |
| Overlapping chat layer | Both have an LLM chat loop; deciding which orchestrates requires clear boundaries |
| Pre-1.0 instability | OpenFang ships breaking changes between minors; pinning adds maintenance burden |
| Binary dependency | Adding a 32 MB Rust binary to Bureau's Python stack complicates deployment |
| Single maintainer risk | Built and maintained primarily by one developer (Jaber / RightNow) |

### Overall fit: **High for channel + autonomous-assistant gaps; low for SWE core**

OpenFang does not compete with Bureau's coding-CLI orchestration.  It fills the
exact gaps identified in the 2026-04-02 evaluation: channel breadth (critical),
proactive assistant loop (significant), and security hardening (moderate).

---

## 11. Risks & Tradeoffs

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Pre-1.0 breaking changes** | High | Pin to specific commit; integration tests against pinned version |
| **Single-maintainer bus factor** | High | LibreFang (community fork, 187 stars) exists as fallback; MIT license allows Bureau to vendor critical crates |
| **Rust/Python boundary** | Medium | API-only integration (Option C) avoids FFI complexity; gRPC or HTTP |
| **Memory model divergence** | Medium | Standardize on Qdrant as shared vector store; let each system manage its own structured state |
| **Scope creep** | Medium | Define clear boundary: Bureau owns SWE orchestration; OpenFang owns autonomous Hands and channel transport |
| **Performance assumptions** | Low | OpenFang's benchmarks (180ms cold start, 40MB idle) are self-reported; validate independently |
| **WhatsApp gateway legality** | Low-Medium | WhatsApp Web gateway uses unofficial protocol (like whatsapp-web.js); Meta could block it; Cloud API is the production-safe alternative |
| **Dashboard overlap** | Low | OpenFang has a Tauri desktop app + web dashboard; Bureau has Telegram as its UI; no conflict if roles are clear |

### Recommendation

Integrate OpenFang via its REST API (Option C) to immediately access its 40
channel adapters and autonomous Hands.  Do not embed the Rust binary into
Bureau's core deployment.  Treat OpenFang as an optional sidecar that users can
opt into for expanded channel support and always-on assistant features.

Priority integration tasks:

1. **Bureau -> OpenFang channel bridge** -- Route Bureau responses through
   OpenFang's channel adapters for Discord, Slack, WhatsApp delivery.
2. **OpenFang Hand -> Bureau role mapping** -- Expose Researcher, Collector, and
   Predictor as Bureau agent roles dispatched via OpenFang's API.
3. **Shared Qdrant memory** -- Configure OpenFang to use Bureau's Qdrant instance
   for vector storage (requires OpenFang to support external vector backends,
   which may need a PR upstream).
4. **Security pattern adoption** -- Implement prompt injection scanning and loop
   guards in Bureau, inspired by OpenFang's designs.
