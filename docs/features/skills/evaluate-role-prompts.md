# Role prompt evaluation: are 66 roles still justified?

- **Date**: 2026-03-30
- **Evaluators**: 3 parallel Opus agents, each reading every file in their batch
- **Methodology**: For each of 66 role prompts, assess whether (1) frontier models have subsumed its functionality, (2) it encodes a genuinely different workflow vs. just domain knowledge, and (3) "role prompt" is the right abstraction

## Executive summary

Of 66 role prompts, **3 survive as roles**. 16 have valuable workflows but belong as **skills** (on-demand, not personas). 10 should **merge** into those skills. **37 should be deleted** -- frontier models do this natively.

| Verdict | Count | What it means |
|---------|-------|---------------|
| **KEEP as role** | 3 | Fundamentally changes how the model operates |
| **CONVERT to skill** | 16 | Valuable workflow, wrong abstraction (should be on-demand) |
| **MERGE** | 10 | Absorbed into a surviving skill |
| **DROP** | 37 | Frontier models do this without prompting |

---

## The 3 roles worth keeping

These share a trait: they force the model into a mode of operation it would not enter by default.

### `migration-refactoring`

Forces phased, observable, reversible migration discipline. Without this, models start making changes directly. With it: inventory call sites, choose patterns (strangler/branch-by-abstraction/parallel-run), define revertible batches, script codemods, wire CI gates, plan expand-migrate-contract. The model reliably produces a different (better) approach to large changes.

### `interviewer`

Fundamentally different mode: the model *asks questions* instead of answering them. Socratic method with probing follow-ups, edge-case presentation, difficulty adjustment, and structured assessment. A user asking "help me understand X" gets an explanation; invoking the interviewer gets a structured assessment. This behavioral inversion doesn't happen without the prompt.

### `incident-commander`

Coordination workflow that overrides the model's default "fix it" instinct. Without this, the model debugs. With it: declare severity, assign roles, execute runbooks, maintain a live timeline, communicate status, facilitate blameless postmortem, track action items. The model coordinates instead of coding.

---

## The 16 skill conversions (with 10 merges)

These encode genuine multi-step workflows, but "persona you wear for an entire session" is the wrong abstraction. They should be on-demand skills activated when needed.

| Skill | Merges in | Core workflow value |
|-------|-----------|-------------------|
| **architect** | `task-decomposer` | ADR + options matrix + rollout plan with abort criteria; forced multi-option analysis |
| **code-reviewer** | -- | Structured review output (findings by category, severity, required vs optional); merge into existing `requesting-code-review` superpowers skill |
| **testing** | -- | Audit checklist: map tests to critical paths, detect anti-patterns (sleeps, .only, missing asserts), enforce determinism, define quality gates |
| **historian** | -- | Git archaeology: blame + bisect + PR correlation + churn hotspots + ownership analysis |
| **security-compliance** | `auth-specialist` | Threat-model-first, controls-as-code, Semgrep baseline, approval gates. Auth is a deep-dive section, not a separate role |
| **accessibility-auditor** | -- | Automated scan (axe-core/Lighthouse) then manual keyboard/screen-reader test then WCAG-criterion report |
| **observability** | `scalability-reliability` | SLO-first methodology, OTel propagation, burn-rate alerts with runbooks. Scalability/reliability is the same SLI/SLO workflow with resilience patterns folded in |
| **cost-optimization-finops** | -- | Phased: baseline spend from CUR, rank drivers, tag attribution, quick wins (idle/unused/over-provisioned), rightsize, then commitments |
| **tech-debt** | `architecture-audit` | Code archaeology: TODO/FIXME scan + churn hotspots + coverage gaps = prioritized impact/effort/risk matrix. Architecture audit is the same inventory-prioritize-roadmap methodology |
| **devops-infra-as-code** | `kubernetes-operator`, `terraform-specialist` | "Everything through code, reviews, and automated pipelines" constraint. K8s and Terraform are checklists within this, not separate workflows |
| **networking-edge-infra** | -- | Staged CDN/GSLB rollouts by path/region, canary traffic shifts, baseline-measure-change-remeasure for latency/hit-ratio |
| **api-integration** | `api-client-designer` | Versioning/deprecation/compatibility matrix + contract tests in CI. SDK design is a subtopic |
| **db-internals** | `orm-optimization-specialist` | Start from slow logs + EXPLAIN, propose minimal index/config changes with quantified impact, stage reversible migrations. ORM optimization (N+1 detection, query counting) is a section within this |
| **schema-evolution** | -- | Expand/migrate/contract multi-phase methodology; Protobuf/Avro field-number safety rules |
| **event-driven** | `background-job-architect`, `message-queue-architect` | Saga orchestration vs choreography, transactional outbox, schema registry. Job queues and broker patterns are subtopics |
| **realtime** | -- | Per-hop latency budgets, no dynamic allocation in ISRs, bounded-everything philosophy, safety/certification traceability |

---

## The 37 drops

These are domain knowledge that frontier models (Claude Opus 4.6, GPT-5.1-Codex, Gemini 2.5 Pro) already have internalized. No workflow differentiation from what the model produces when asked directly.

### Workflow roles (6)

| Role | Why drop |
|------|----------|
| `debugger` | Redundant with `systematic-debugging` superpowers skill and native model capability |
| `optimization` | "Profile first, fix top hotspots, re-measure" is what models already do |
| `implementation-helper` | Describes the default behavior of every frontier coding model |
| `explainer` | "Explain code progressively" is how models already respond |
| `searcher` | Describes basic tool usage (grep + glob); zero workflow value |
| `git-surgeon` | Safety constraints belong in global policy; models handle advanced git natively |

### Domain roles (9)

| Role | Why drop |
|------|----------|
| `frontend` | Generic frontend knowledge (CWV, SSR/CSR, bundle optimization) -- models do this natively |
| `chaos-engineer` | Textbook chaos engineering methodology; no novel workflow |
| `platform-eng` | "Build paved roads, measure DORA" -- standard platform engineering summary |
| `data-eng` | ETL/ELT, idempotency, schema evolution, partitioning -- standard knowledge |
| `ai-ml-eng` | MLOps basics; models (especially GPT-5.1-Codex) know this cold |
| `localization-engineer` | ICU format, CLDR plural rules, RTL -- standard i18n knowledge |
| `log-analyst` | Default model behavior when analyzing logs |
| `environment-debugger` | Basic troubleshooting subsumed by `debugger` |
| `dependency-auditor` | Run audit tools, triage, plan upgrades -- models do this natively |

### Language-specific roles (4)

| Role | Why drop |
|------|----------|
| `golang-pro` | Models write idiomatic Go (context propagation, `%w` errors, goroutine safety) natively |
| `rust-pro` | Models handle ownership, lifetimes, unsafe minimization natively |
| `cpp-pro` | Models modernize to C++17/20 (RAII, smart pointers, sanitizers) natively |
| `shell-scripter` | `set -euo pipefail` + quoting is baseline competence |

### Infrastructure roles (4)

| Role | Why drop |
|------|----------|
| `serverless-specialist` | Cold start, stateless design, idempotent handlers -- standard knowledge |
| `ci-pipeline-builder` | "Cache, parallelize, fail fast, pin by SHA" -- models produce this by default |
| `monorepo-architect` | Nx/Turborepo/Bazel configuration -- tool documentation summary |
| `distributed-systems` | Consensus, CAP, Paxos/Raft, partition tolerance -- deep model knowledge |

### API/integration roles (4)

| Role | Why drop |
|------|----------|
| `api-mocking-specialist` | MSW/WireMock/Pact -- standard testing knowledge |
| `graphql-specialist` | DataLoader, Relay connections, @deprecated -- standard GraphQL knowledge |
| `webhook-integration-specialist` | Four bullet points of webhook best practices |
| `http-client-specialist` | Timeout, retry, circuit breaker -- standard resilience patterns |

### Data/storage roles (1)

| Role | Why drop |
|------|----------|
| `caching-specialist` | Multi-tier caching, TTL strategy, stampede prevention -- enumeration of known patterns |

### Niche roles (9)

| Role | Why drop |
|------|----------|
| `regex-wizard` | Models are already excellent at regex including ReDoS warnings |
| `datetime-specialist` | "Store UTC, handle DST" -- well-known best practices |
| `type-system-expert` | Models excel at advanced TypeScript/Python typing natively |
| `state-machine-designer` | Models suggest state machines when they see tangled booleans |
| `concurrency-specialist` | Textbook concurrency advice the model already follows |
| `feature-flag-engineer` | Lifecycle checklist, not a workflow |
| `search-implementation-specialist` | Standard Elasticsearch/search engineering |
| `mobile-eng-architect` | Platform docs summary (SwiftUI/Compose, offline-first, Fastlane) |
| `build-optimizer` | Standard build tooling knowledge (Webpack/Vite/esbuild) |

---

## The pattern

The role-prompt system was designed when models needed more hand-holding. In March 2026, the value has shifted:

- **Then**: "Tell the model what to know" (domain knowledge dumps)
- **Now**: "Tell the model what constraints to enforce and what workflow to follow" (procedural skills)

The 3 surviving roles work because they force a **behavioral inversion** the model wouldn't adopt unprompted. The 16 skill candidates work because they impose **procedural constraints** (multi-phase migrations, measurement-before-change, per-hop latency budgets) that a user might forget to ask for. The 37 drops are domain knowledge the model already has -- prompting it with "you are a Kubernetes specialist" does not make it better at Kubernetes.
