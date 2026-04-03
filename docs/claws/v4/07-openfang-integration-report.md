# OpenFang × Bureau integration report

## Platform profile
**Research confidence:** Low.

A clear, authoritative technical source establishing OpenFang as a specific mainstream agent platform was not confirmed in this pass. This report uses a prudent exploratory framing.

## Functional/feature assessment framework
Before integration, verify whether OpenFang provides:
- modular agent/tool runtime,
- persistent memory interfaces,
- extensible workflow engine,
- safety/approval controls,
- API and deployment ergonomics.

## Memory architecture and autonomous loop fit
Potential fit is high if OpenFang offers explicit memory APIs and policy hooks. Without those, Bureau would need a heavy adapter that may erase net benefit.

Operational stack target:
- OpenFang local memory -> Bureau L0/L1,
- curated persistent memory -> Bureau Qdrant + graph,
- execution state snapshots -> Bureau dossiers.

## Daily assistant + SWE assistant fit

### Daily assistant
Unknown; depends on OpenFang’s product orientation and integration ecosystem.

### SWE assistant
Possible if OpenFang supports terminal/tool workflows and repository-aware actions.

## Workflow/UX design implications
Treat OpenFang first as an augmentation plane:
- start with passive data/memory integration,
- then enable active task delegation,
- only then evaluate autonomous mode.

## Recommendation
Exploratory fit only until concrete platform capability confirmation.

## High-impact merge concepts (subagent brainstorm section)

### 1) Meta-orchestrator mode
OpenFang and Bureau co-run with dynamic authority transfer based on confidence/risk profile.

### 2) Universal memory contract
Define a JSON schema standard that lets OpenFang memories plug into Bureau stores without brittle per-field mapping.

### 3) Adaptive autonomy policy
Autonomy level automatically adjusts from observed reliability, with strict floor/ceiling constraints.

### 4) Strategic planning + tactical execution split
OpenFang handles strategic decomposition; Bureau handles tactical role-specialized implementation.

### 5) Continuous capability benchmarking
Run recurring benchmark tasks to compare OpenFang-only, Bureau-only, and combined performance; route workload accordingly.
