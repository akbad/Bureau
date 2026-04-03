# Bureau integration strategy report: Hermes, Letta, OpenClaw, CoPaw, Memoh, OpenHands, OpenFang

## 1) Executive summary

If Bureau wants the **highest immediate impact** with defensible differentiation, the best path is:

1. **Hermes first** (primary integration bet)
2. **OpenHands second** (SWE execution depth)
3. **Letta third** (memory intelligence layer)
4. **Memoh/OpenClaw as parallel optional tracks** (channel-first assistant surfaces)
5. **CoPaw/OpenFang as watchlist incubations** (insufficient evidence or maturity)

This ordering maximizes near-term product utility while preserving upside for long-term autonomy and memory quality.

## 2) Bureau baseline: what we are integrating into

From branch reconnaissance, Bureau already provides:

- Cross-CLI role-orchestrated delegation and subagent workflows.
- Strong protocol system (skills, guardrails, step-gated modes).
- Memory backbone (semantic + structured + dossiers for resumability).
- Existing trend toward lighter context loading and cleaner skill naming/install semantics.

Strategically, Bureau already excels at **orchestration correctness** and **workflow discipline**. Missing moat is primarily in **always-on assistant presence**, **channel UX**, and **continuous autonomous follow-through at user-facing edges**.

## 3) Ranking with rationale and tradeoffs

## #1 Hermes (Recommended primary)

**Why #1:**
- Strong real-world assistant UX via multi-channel gateway and operational runtime.
- Good bridge between daily assistant workflows and engineering workflows.
- Fastest path to “Bureau everywhere the user already is” (chat, messaging, voice-ish surfaces).

**Tradeoffs:**
- Permission/sandbox harmonization is crucial.
- Some orchestration overlap must be resolved via explicit boundary contracts.

**Best role:** Bureau = brain/protocol governor; Hermes = interface/runtime fabric.

## #2 OpenHands (Recommended co-primary for SWE depth)

**Why #2:**
- Strong coding-agent focus and runtime maturity.
- Natural complement to Bureau’s protocol/role/memory governance.
- Enables high-throughput implementation while maintaining quality gates.

**Tradeoffs:**
- Not naturally a lifestyle assistant platform.
- Requires clean job lifecycle contract and observability handshake.

**Best role:** OpenHands = execution engine; Bureau = planner, reviewer, memory steward.

## #3 Letta / LettaBot (Recommended memory-intelligence layer)

**Why #3:**
- Most explicit and conceptually advanced memory model among candidates assessed.
- Sleep-time/background update concepts align with long-horizon autonomy goals.
- Excellent for raising “agent learning quality over time.”

**Tradeoffs:**
- Higher integration complexity.
- Needs user-facing shell for broad everyday assistant adoption.

**Best role:** Letta = memory compiler/reflective learner; Bureau = orchestration + policy + deployment rails.

## #4 Memoh (Promising channel + long-memory track)

**Why #4:**
- Strong positioning in multi-bot always-on long-memory assistant usage.
- Could quickly unlock practical user-facing wins.

**Tradeoffs:**
- Canonical architecture detail less explicit than top 3.
- Possible roadmap overlap with Hermes/OpenClaw.

## #5 OpenClaw (Promising, similar class to Memoh)

**Why #5:**
- Practical, self-hosted assistant stance with multi-platform surface and explicit sandbox docs.

**Tradeoffs:**
- Comparative differentiation vs Hermes/Memoh may be less pronounced depending on your priorities.

## #6 CoPaw (Exploratory)

**Why #6:**
- Potentially interesting collaboration model, but evidence confidence currently low.

**Tradeoffs:**
- Discovery/maturity uncertainty.

## #7 OpenFang (Exploratory)

**Why #7:**
- Very limited validated public evidence in this pass.

**Tradeoffs:**
- High uncertainty + opportunity cost.

## 4) Recommended phased roadmap

### Phase A (0-6 weeks): prove value fast

- Build **Bureau ↔ Hermes adapter** with:
  - session mapping,
  - role-routing,
  - dossier fold/unfold from channel commands,
  - protocol-enforced high-risk action approvals.
- Build **Bureau ↔ OpenHands pipeline** for spec-to-implementation execution.

Success metrics:
- Mean time from request to validated PR,
- user retention across assistant channels,
- reduction in context-loss incidents.

### Phase B (6-12 weeks): compound intelligence

- Integrate **Letta memory compiler** path:
  - convert Bureau artifacts into structured memory updates,
  - add background reflection loops,
  - run regression-gated memory/prompt refinement.

Success metrics:
- fewer repeated mistakes per project,
- improved first-pass task success over time,
- lower token cost per resolved issue.

### Phase C (12+ weeks): portfolio strategy

- Keep Memoh/OpenClaw adapters as configurable front-end surfaces.
- Treat CoPaw/OpenFang as incubators with strict milestone gates.

## 5) “Genius-level” differentiators Bureau can own regardless of platform

1. **Protocol-Aware Autonomy Governor**
   - Dynamic autonomy level by task risk, uncertainty, and recent reliability.

2. **Memory Trust Scoring Layer**
   - Every memory item gets provenance, confidence, age decay, and contradiction checks.

3. **Cross-Platform Agent Identity Continuity**
   - One durable task/memory identity that survives switching CLIs, channels, and execution engines.

4. **Failure-Driven Skill Evolution**
   - Mine failures and near-misses to auto-propose skill and role upgrades, gated by eval suites.

5. **Human Legibility by Default**
   - Every autonomous action has “why now / why this role / what could go wrong / rollback path.”

## 6) Final recommendation

Proceed with a **dual-track primary strategy**:

- **Track 1 (user surface): Hermes integration now**
- **Track 2 (engineering throughput): OpenHands integration now**

Then layer **Letta** as the memory-intelligence multiplier once operational telemetry is flowing.

This sequence balances short-term product impact with long-term defensibility.

## Source index

- Bureau repo docs + plans in this branch
- Hermes docs (providers + messaging gateway)
- Letta docs (memory blocks/context hierarchy/stateful agents/sleep-time)
- OpenHands docs + repo
- OpenClaw repo/site references
- Memoh repo/docs references
