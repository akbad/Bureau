# Decision Matrix

## Scoring model

This matrix uses the stable inputs from `01-capability-stack.md` as its scoring substrate. It does not treat any platform claim as a hard rule; it treats the evidence as a fit assessment for Bureau's future architecture.

The fit scale is intentionally coarse:

- `0` = absent or counterproductive
- `1` = partial or weak
- `2` = strong
- `3` = leading

Primary criteria are weighted `5x`. Secondary criteria are weighted `3x`, except elegance / maintainability, which is weighted `2x`. The weights are there to keep the matrix honest about what matters most, not to fake precision. Confidence stays separate from score so mixed-evidence platforms remain visibly mixed.

## Combination scoring rules

- Combination scores are architecture-level fit, not arithmetic sums of ingredient scores.
- A combination should not exceed its strongest ingredient on a criterion unless the justification names a clear emergent advantage.
- Unresolved integration burden caps `CO` and `EL`.
- Mixed-evidence ingredients cap the affected criteria or the overall confidence, whichever is the more disciplined reading.

## Primary weighted criteria table

| Criterion | Weight | Why it matters |
|---|---:|---|
| Memory-native, self-improving intelligence | 5 | The architecture should compound understanding and behavior over time. |
| Composability into a coherent superset | 5 | The result must behave like one system, not an awkward bundle of parts. |
| Long-term differentiation and moat | 5 | Bureau should end up genuinely distinct, not just operationally adequate. |

## Secondary criteria table

| Criterion | Weight | Why it matters |
|---|---:|---|
| Assistant-surface quality | 3 | Useful as a moat amplifier and a practical daily interface. |
| SWE execution depth | 3 | Necessary for real task completion, especially for code-heavy work. |
| Open / self-hostable posture | 3 | Closed dependencies are strategic drag unless the tradeoff is clearly worth it. |
| Elegance / maintainability | 2 | Important for longevity, but not a lead criterion on its own. |

## Ingredient matrix

Legend: `MI` = memory-native intelligence, `CO` = composability, `DI` = differentiation, `AS` = assistant-surface quality, `SWE` = SWE execution depth, `OP` = open / self-hostable posture, `EL` = elegance / maintainability.

| Ingredient | MI | CO | DI | AS | SWE | OP | EL | Confidence | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Letta | 3 | 2 | 2 | 1 | 1 | 2 | 3 | High | Best explicit memory hierarchy; weaker as a full assistant or SWE spine. |
| Hermes | 2 | 2 | 3 | 3 | 1 | 2 | 2 | Mixed | Strong procedural-learning and gateway signal; identity / maturity evidence is less stable. |
| OpenHands | 1 | 2 | 2 | 1 | 3 | 3 | 2 | High | Strongest execution substrate; not a memory-native system. |
| OpenClaw | 2 | 1 | 2 | 3 | 2 | 2 | 1 | Mixed | Broad surface and skill discovery, but breadth raises governance and maintenance pressure. |
| Memoh | 2 | 2 | 1 | 3 | 2 | 2 | 2 | High | Strong multi-bot assistant shell and memory compaction pattern; heavier operational footprint. |
| CoPaw | 1 | 2 | 1 | 2 | 1 | 3 | 2 | Mixed | Good transport glue and platform reach; weaker as a core intelligence spine. |
| OpenFang | 2 | 1 | 1 | 2 | 2 | 2 | 1 | Mixed | Ambitious breadth and security story, but maturity and trust costs remain material. |
| Bureau-native memory/governance ingredients | 2 | 3 | 3 | 1 | 1 | 3 | 3 | High | Dossiers, Memory MCP, Qdrant, role policy, provenance discipline, and promotion gates. |
| Bureau-native SWE orchestration ingredients | 1 | 3 | 3 | 1 | 3 | 3 | 2 | High | Assess Mode, Micro Mode, role catalog, MCP routing, and review policy. |

## Combination matrix

The combinations below are the ones that survive the capability-stack synthesis. They are intentionally few, because the job here is to narrow the field, not to enumerate every possible bundle.

| Combination | MI | CO | DI | AS | SWE | OP | EL | Confidence | Handoff aid | One-sentence justification | Key failure mode |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| Bureau-native control stack | 2 | 3 | 2 | 1 | 3 | 3 | 3 | High | Memory: Bureau-native; front door: Bureau gateway; execution: OpenHands; evolution: Bureau propose/promote; owner: Bureau | Bureau keeps policy, memory governance, and orchestration while OpenHands handles execution behind a clean contract. | Can stay too conservative and underdeliver on memory compounding. |
| Bureau + Letta memory spine + OpenHands executor | 3 | 2 | 3 | 1 | 3 | 2 | 2 | High | Memory: Letta + Bureau; front door: Bureau gateway; execution: OpenHands; evolution: Bureau review loop; owner: Bureau | This is the cleanest explicit memory-led stack: Letta carries memory hierarchy, Bureau owns promotion rules, and OpenHands executes. | Risk of split truth unless memory promotion and rollback are tightly defined. |
| Bureau + Hermes assistant / evolution layer + OpenHands executor | 2 | 2 | 3 | 3 | 3 | 2 | 2 | Mixed | Memory: Hermes + Bureau; front door: Hermes gateway; execution: OpenHands; evolution: Hermes learn / Bureau gate; owner: Bureau | Strong if Bureau wants a daily assistant gateway that learns from use while still keeping execution and policy separate. | Hermes's identity and maturity ambiguity can leak complexity into the core. |
| Bureau + OpenClaw breadth surface + OpenHands executor | 2 | 1 | 2 | 3 | 2 | 3 | 1 | Mixed | Memory: light Bureau adapters; front door: OpenClaw; execution: OpenHands; evolution: curated; owner: Bureau | Survives if Bureau's users need many channels and a broad front door more than a single elite assistant shell. | Breadth adds governance drag and weakens composability. |
| Bureau-synthesized superset: Bureau memory / governance + Letta memory compiler + Hermes gateway + OpenHands executor | 3 | 2 | 3 | 3 | 3 | 2 | 1 | Mixed | Memory: Bureau + Letta; front door: Hermes gateway; execution: OpenHands; evolution: Bureau-gated memory / skill loop; owner: Bureau | This is a high-potential full-stack candidate if Bureau can keep adapter boundaries crisp and own the promotion gates. | Highest integration burden and the biggest risk of becoming a clever bundle rather than one coherent system. |

## Narrowing boundary

- Pure platform end-states that displace Bureau's policy and promotion boundary were cut from candidate status.
- Breadth-first assistant surfaces were kept only when they still left Bureau with a coherent ownership model.
- Memory or learning layers that risk duplicate truth sources or unclear rollback were demoted to ingredient or adapter status.
- Mixed-evidence stacks remain hypotheses unless they can show clear architecture-level fit beyond the sum of their parts.

## Reading the matrix

- The matrix is a narrowing tool, not the final recommendation.
- Its immediate handoff is to `03-narrative-assessment.md` and then `04-candidate-architectures.md`, where the surviving combinations should be treated as hypotheses to carry forward, not conclusions.
- High primary-criterion scores matter more than secondary wins, especially for long-horizon architecture bets.
- Confidence is a first-class signal; mixed-evidence platforms can still contribute strong ingredients, but they should not be treated as settled winners.
- A higher score here means better fit for the approved architecture question, not proof that the platform should be adopted unchanged.
