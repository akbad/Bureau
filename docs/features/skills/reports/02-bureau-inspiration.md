# Bureau Inspiration: Collation Report

<!-- Synthesized from two parallel document-research agents examining
     old-brainstorm.md and skillforge-inspo.md. This report captures the
     owner's skill vision, SkillForge-Lite governance design, and how both
     inform Bureau's skill development strategy. -->

## 1. The owner's skill vision (old-brainstorm.md)

The brainstorm document reveals a clear hierarchy of priorities and a distinctive philosophy for how skills should be sourced, composed, and evolved.

### Priority stack

| Priority | Domain | Signal strength |
|----------|--------|-----------------|
| 1 | Research | 5 separate inspirations + homemade fallback |
| 2 | Swarm/parallel orchestration | Labeled "genius sources of inspiration" |
| 3 | Architecture analysis & patterns | Dedicated category |
| 4 | Prompt engineering | Dedicated category |
| 5 | Security & auth | Dedicated category |

Research dominance is notable: the owner allocated more inspiration slots to research than to any other domain, and hedged against external dependencies by planning a homemade fallback. This indicates research capabilities are considered foundational -- not optional add-ons.

### Three-tier sourcing model

The brainstorm establishes a deliberate acquisition funnel:

1. **Adopt external** -- use proven third-party tools directly.
2. **Use as inspiration** -- study external approaches, then build Bureau-native equivalents.
3. **Build homemade** -- create from scratch when no adequate external source exists.

This is pragmatic: it avoids NIH syndrome while ensuring Bureau retains control over its core capabilities. The explicit merging/consolidation strategy for overlapping skills shows awareness that unchecked adoption leads to redundancy.

### Self-improvement and meta-skill concepts

Three ideas stand out as architecturally significant:

- **Developer growth analysis**: A skill that tracks how a developer's patterns evolve over time. This frames Bureau as a long-term learning system, not a stateless tool dispatcher.
- **ReasoningBank Intelligence**: Storing and retrieving structured reasoning artifacts. This is a precursor to the kind of persistent reasoning memory that Bureau's Qdrant-backed memory already partially implements.
- **Swarm orchestration as meta-skill**: The brainstorm treats parallel coordination not as infrastructure but as a first-class skill -- one that composes other skills. The "full-stack optimizer" (spawning parallel subagents per stack layer) and "containerized YOLO subagent" (autonomous agents in isolated containers) are both expressions of this idea.

The self-improvement model is implicit rather than autonomous: the system improves by accumulating better skills, richer reasoning banks, and more sophisticated orchestration -- not by rewriting itself.

### Unfinished threads

Several items remained unchecked: beehive-research, containerized YOLO orchestration, and integrations with PyMoo/PennyLane. These represent aspirational scope that was never implemented but may still hold value as future directions.

---

## 2. SkillForge-Lite design (skillforge-inspo.md)

SkillForge-Lite is a lightweight quality and governance layer for Bureau-native skills. Its core problem statement: skill proliferation and skill-versus-role ambiguity.

### Architecture

The system consists of four scripts and two index files:

```
discover-skills.py  -->  skill-index.json
discover-roles.py   -->  role-index.json
triage-skill-request.py  (reads both indices)
```

### Triage routing

The triage script is the decision engine. It uses keyword and domain matching to produce a confidence score (0--100) and routes accordingly:

| Confidence | Action |
|------------|--------|
| >= 80% | `USE_EXISTING` -- redirect to the matching skill |
| 50--79% | `IMPROVE_EXISTING` -- enhance the closest match |
| < 50% | `CREATE_NEW` -- build a new skill |
| Multi-domain | `COMPOSE` -- combine existing skills |
| Ambiguous | `CLARIFY` -- ask for more information |

This is deliberately simple: keyword-based matching, no ML, no embeddings, no external services. The trade-off is lower recall on novel requests, but the system is deterministic, auditable, and trivially debuggable.

### Quality gates

SkillForge-Lite enforces quality through four lightweight mechanisms:

1. **Triage confidence score** -- prevents unnecessary skill creation.
2. **Lens checklist** -- first-principles, inversion, and evolution lenses applied before creating any new skill.
3. **Activation-clarity checklist** -- skill descriptions must be trigger-only (not workflow summaries). This prevents skills from becoming documentation dumps.
4. **Role-overlap decision note** -- advisory, never blocking. When a proposed skill overlaps with an existing role, the overlap is surfaced but does not gate creation.

### Metadata sidecar

Each skill gets a `skill.meta.json` with keywords, domains, and triggers. This is the indexer's source of truth and the triage script's matching corpus.

### Graceful degradation

The system works partially even with missing indices -- a pragmatic concession that makes adoption easier and avoids a hard bootstrap dependency.

### Implementation feasibility

The entire system is buildable with Python stdlib, PyYAML, and pytest. No infrastructure dependencies. The 8-task implementation plan includes exact file paths and test specifications.

---

## 3. Strategic implications for Bureau

### What converges

Both documents agree on several principles that should be treated as settled design decisions:

| Principle | Brainstorm evidence | SkillForge evidence |
|-----------|-------------------|---------------------|
| Skills are composable units | Explicit in architecture | `COMPOSE` triage route |
| Governance prevents proliferation | Merging/consolidation strategy | Triage routing + quality gates |
| Pragmatism over sophistication | Three-tier sourcing (adopt before building) | Keyword matching over ML |
| Skills are domain-categorized | Categories in brainstorm | Domains in metadata sidecar |

### What diverges

The brainstorm is ambitious and exploratory; SkillForge-Lite is constrained and operational. The key tensions:

- **Autonomous vs. curator-driven improvement**: The brainstorm imagines skills that learn and evolve (developer growth tracking, ReasoningBank). SkillForge-Lite is explicitly curator-driven -- improvement happens when a human runs the triage and decides to improve or create. Bureau's current architecture (memory MCPs + manual skill authoring) sits closer to SkillForge's model, but the brainstorm's vision hints at where the system could evolve.

- **Swarm orchestration scope**: The brainstorm treats parallel orchestration as a core capability warranting deep investment (containerized YOLO, full-stack optimizer). SkillForge-Lite does not address orchestration at all -- it governs skill identity and quality, not skill execution topology. Both are needed; they operate at different layers.

- **External dependency tolerance**: The brainstorm freely references external tools (PyMoo, PennyLane, various research APIs). SkillForge-Lite is zero-dependency by design. Bureau should adopt SkillForge's constraint for its governance layer while preserving the brainstorm's openness for individual skill implementations.

### Recommended synthesis

1. **Adopt SkillForge-Lite's triage and governance model** as Bureau's skill lifecycle manager. It is simple, testable, and directly addresses the proliferation problem.

2. **Preserve the brainstorm's priority stack** for skill development roadmap ordering: research first, then orchestration, then architecture analysis, then prompt engineering, then security.

3. **Implement metadata sidecars** (`skill.meta.json`) for all Bureau skills. This unlocks triage routing and makes skills self-describing.

4. **Treat swarm orchestration as an orthogonal layer** -- not governed by SkillForge-Lite, but composed with it. SkillForge decides *which* skills to use; the orchestration layer decides *how many instances and in what topology*.

5. **Defer autonomous self-improvement** to a later phase. The curator-driven model is appropriate for Bureau's current maturity. The brainstorm's ReasoningBank and developer-growth concepts are worth revisiting once the governance layer is stable and skill count warrants it.

6. **Close the unfinished threads explicitly**: beehive-research, containerized YOLO, and PyMoo/PennyLane should be evaluated against SkillForge-Lite's triage criteria. If they score below 50% confidence against existing capabilities, they are `CREATE_NEW` candidates for the roadmap. If above, they may be `IMPROVE_EXISTING` enhancements to skills that already exist.
