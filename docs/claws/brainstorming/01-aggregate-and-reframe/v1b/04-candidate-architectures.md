# Candidate Architectures

## Selection rules

This candidate set starts from the first-pass combinations in the decision matrix and then prunes for architectural distinctness. It keeps at most five serious end-state candidates. Bureau-synthesized superset candidates are allowed. Bureau-native candidates survive only if they remain genuinely competitive on memory-native intelligence, composability, and moat. Minor transport-only variants were folded together.

None of the candidates below is the winner. They are serious end-state hypotheses to carry into the recommendation memo, with concierge and autonomous skill evolution treated as a coupled design problem rather than separate add-ons.

## 1. Bureau-native control stack

### Stack

- Primary layer: governance / composability.
- System anchors: Bureau-native memory / governance ingredients and Bureau-native SWE orchestration ingredients.
- Ingredients: OpenHands as the executor; external memory or assistant platforms are optional adapters, not anchors.
- Concierge: transformed into a Bureau-owned front door and policy surface.
- Autonomous skill evolution: transformed into a Bureau-gated observe → propose → promote loop.

### Why it could become a world-class superset

This is the cleanest sovereignty-first architecture. Bureau keeps the composition rules, the memory promotion rules, and the review contract, while OpenHands supplies the strongest grounded execution. If Bureau can make its own memory governance stronger over time, this family keeps the control plane intact while still allowing strong external ingredients.

For it to remain serious on memory-native intelligence, Bureau has to close the gap with a Bureau-owned memory compiler or a governed external-memory attachment that can reliably promote, roll back, and rehydrate state without splitting truth.

### What it does with concierge

Concierge stops being a separate product-shaped layer and becomes Bureau's front door. The surface can change, but Bureau remains the identity and policy owner. That keeps channel routing, user state, and role selection inside one governed system.

Because Bureau owns the front door, Bureau must also own promotion and rollback: the same layer that interprets user intent must be able to decide what memories, skills, or policies graduate into the core.

### What it does with autonomous skill evolution

Dynamic skill evolution becomes a disciplined internal loop: observe outcomes, propose changes, and only then promote memory or behavior updates into the core. The architecture does not delete evolution; it subsumes it under Bureau review and promotion rights.

### Main risk

This family can become too conservative if Bureau does not add a genuinely stronger memory compiler. It may preserve coherence while underdelivering on the compounding intelligence the task is trying to maximize.

## 2. Letta-led memory spine with Bureau governance

### Stack

- Primary layer: memory / intelligence.
- System anchors: Letta as the memory hierarchy anchor; Bureau as the governance and promotion anchor.
- Ingredients: OpenHands as the executor; Bureau routing and policy as the control boundary.
- Concierge: hybridized into Bureau front door plus Letta-backed memory context.
- Autonomous skill evolution: transformed into Bureau-mediated memory promotion and rollback.

### Why it could become a world-class superset

This is the strongest memory-first architecture because it takes explicit memory structure seriously instead of trying to approximate it with a generic assistant shell. Letta gives Bureau a durable hierarchy, while Bureau keeps the truth and promotion contract. If the integration stays clean, this family can compound user understanding more reliably than a surface-first design.

Here the single source of truth lives in Letta-backed memory, but only Bureau can decide which recalled state becomes durable behavior or policy. That makes concierge ownership a memory-handoff choice: the front door is Bureau's, while the memory spine is Letta's.

### What it does with concierge

Concierge is not deleted, but it is no longer the locus of intelligence. It becomes a hybrid front door that draws on Letta-managed memory while Bureau still owns task interpretation and role routing. The result is a Bureau-led assistant surface with a much clearer memory spine.

Because Bureau owns the concierge surface in this family, Bureau also owns promotion and rollback; Letta supplies the memory depth, but Bureau decides what gets canonized.

### What it does with autonomous skill evolution

Dynamic skill evolution becomes a memory promotion pipeline rather than a free-form self-modification loop. New lessons can be written back into memory, but only through Bureau's review and rollback rules. That makes learning visible and governable instead of ambient.

### Main risk

The main risk is split truth. If Letta's memory hierarchy and Bureau's shared-state rules do not align cleanly, the system can end up with duplicate or competing memory sources.

## 3. Hermes-led gateway and evolution stack

### Stack

- Primary layer: assistant surface with autonomy / evolution coupling.
- System anchors: Hermes as the gateway and learning-loop anchor; Bureau as the policy and promotion anchor.
- Ingredients: OpenHands as the executor; Bureau memory governance as the truth boundary.
- Concierge: superseded in its current form by a Hermes-style gateway.
- Autonomous skill evolution: transformed into a Hermes learn / Bureau gate loop.

### Why it could become a world-class superset

This family is attractive if Bureau wants a daily assistant that learns from use without losing the ability to govern itself. Hermes contributes the strongest evidence for a coupled gateway-plus-improvement loop, which makes it the clearest candidate for an assistant surface that can improve with experience rather than just route messages.

### What it does with concierge

Concierge becomes an implementation detail rather than the defining surface. A Hermes-led gateway owns the day-to-day interaction pattern, while Bureau keeps the policy and identity layer underneath it. That is a more radical surface shift than the Letta-led option.

### What it does with autonomous skill evolution

Dynamic skill evolution is not bolted on later; it is part of the gateway loop. Hermes can propose or learn from outcomes, but Bureau still decides what graduates into durable behavior. The architecture therefore turns evolution into a controlled extension of the assistant surface.

### Main risk

Hermes still carries mixed-evidence maturity and canonical-identity concerns. If those do not stabilize, the architecture can gain surface energy while importing too much uncertainty into the core.

## 4. OpenClaw / Memoh breadth shell

### Stack

- Primary layer: assistant surface breadth with governed execution.
- System anchors: OpenClaw as the breadth-oriented front door; Memoh-style multi-bot compaction and containerization as the shell pattern; Bureau as the governance anchor.
- Ingredients: OpenHands as the executor; CoPaw-style transport glue as a possible secondary ingredient.
- Concierge: superseded by a broader multi-surface shell.
- Autonomous skill evolution: hybridized into curated skill discovery, compaction, and Bureau approval.

### Why it could become a world-class superset

This family exists for the case where breadth really matters. It can cover more channels and more assistant shapes than the more disciplined gateway families, while still leaving Bureau in charge of policy. If Bureau needs a wide front door and a multi-bot experience, this is the most direct architecture family for that requirement.

### What it does with concierge

Concierge is widened into a breadth shell rather than preserved as a single channel-agnostic gateway. The assistant surface becomes a portfolio of routes and containers instead of one dominant conversational path. That may be the right move if channel diversity is a first-order requirement.

### What it does with autonomous skill evolution

Dynamic skill evolution becomes more curated than self-directing. New skills are discovered, compacted, and approved through Bureau rather than learned in one closed loop. That keeps the system safer, but it also limits how self-improving the architecture can become.

### Main risk

Breadth can outrun composability. The more channels and shells this family absorbs, the easier it is for governance overhead to rise faster than actual intelligence.

## 5. Bureau-synthesized superset

### Stack

- Primary layer: composability into a coherent superset.
- System anchors: Bureau memory / governance, Letta as the memory compiler, Hermes as the gateway, and OpenHands as the executor.
- Ingredients: OpenClaw or Memoh-style breadth patterns only if they can fit behind the core contract.
- Concierge: transformed into a Bureau-mediated gateway that borrows Hermes-like surface behavior without giving up Bureau ownership.
- Autonomous skill evolution: transformed into a Bureau-gated memory / skill promotion loop.

### Why it could become a world-class superset

This is the broadest compositional hypothesis because it tries to preserve the strongest layer from each part of the corpus without collapsing into a random bundle. If Bureau can keep the contract boundaries crisp, this family tests whether the pieces can be made multiplicative rather than merely adjacent.

Its explicit identity / truth owner is Bureau: Letta and Hermes can each contribute state and interaction patterns, but Bureau must hold the canonical record and the promotion contract so the system does not split into competing truths.

### What it does with concierge

Concierge is not kept as-is. It is transformed into a Bureau-mediated gateway that can take advantage of Hermes-like interaction strength while still routing through Bureau policy and state ownership. The front door becomes a designed synthesis, not a copied product.

Because concierge ownership is Bureau-mediated here, promotion and rollback also stay Bureau-mediated; Hermes can propose and learn, but Bureau decides what enters the durable core.

### What it does with autonomous skill evolution

Dynamic skill evolution becomes a Bureau-gated synthesis loop that can pull from Letta-style memory updates and Hermes-style learning signals. The key difference from the narrower candidates is that the evolution mechanism is deliberately cross-layer, not owned by just one subsystem.

### Main risk

This family has the highest integration burden and the greatest risk of overconvergence. It can become a clever bundle instead of one coherent system if the architecture does not keep memory, gateway, execution, and promotion boundaries sharply separated.

## Comparison

| Candidate | Primary layer | Identity / truth owner | Coupling mode | Best-case upside | Coherence risk | Dependency risk | Unique Bureau moat | Concierge treatment | Evolution treatment |
|---|---|---|---|---|---|---|---|---|---|
| Bureau-native control stack | Governance / composability | Bureau | Tightly coupled inside Bureau | Cleanest sovereignty-first control plane with the least leakage | Can become too conservative if memory compounding stays weak | Depends on Bureau closing the memory gap internally or through a governed attachment | Bureau remains the policy, routing, and promotion authority | Transformed into Bureau-owned front door | Transformed into Bureau-gated propose → promote loop |
| Letta-led memory spine with Bureau governance | Memory / intelligence | Letta-backed memory with Bureau as canonical promoter | Dual-layer, Bureau-governed handoff | Strongest explicit memory spine with clearer durable state | Split truth if memory hierarchy and Bureau state diverge | Depends on Letta staying the stable memory anchor | Bureau controls what becomes durable behavior without losing memory depth | Hybridized into Bureau front door plus Letta-backed memory context | Transformed into memory promotion and rollback |
| Hermes-led gateway and evolution stack | Assistant surface + autonomy | Bureau for canon; Hermes for interaction loop | Surface-led, learning-coupled | Most direct route to a self-improving daily assistant surface | Mixed-evidence maturity and identity can leak uncertainty into core behavior | Depends on Hermes staying coherent as gateway and learning loop | Bureau keeps the promotion gate even if the surface learns quickly | Superseded by a Hermes-style gateway | Transformed into a Hermes learn / Bureau gate loop |
| OpenClaw / Memoh breadth shell | Assistant breadth + governed execution | Bureau for policy; breadth shell for interaction | Breadth-first, federated shell | Best fit for wide channel coverage and multi-surface reach | Breadth can outrun composability and make governance expensive | Depends on shell patterns staying governable across many routes | Bureau can govern a broad front door without surrendering policy | Superseded by a broader multi-surface shell | Hybridized into curated discovery and approval |
| Bureau-synthesized superset | Composability into a coherent superset | Bureau as canonical owner; Letta and Hermes as contributors | Most demanding synthesis test | Broadest compositional hypothesis with the highest multiplicative upside if it holds together | Highest integration burden and greatest risk of overconvergence | Depends on several ingredients staying aligned at once | Bureau proves it can unify memory, gateway, and execution without becoming a client | Transformed into a Bureau-mediated gateway | Transformed into a Bureau-gated memory / skill loop |
