# Documentation style & standards

<!--
  Bureau's default documentation standards file.
  Default documentation-side peer to code-standards.md.
-->

> [!IMPORTANT]
>
> These are Bureau defaults. They do **not** override repository-specific contribution guides, maintainer instructions, or clear established conventions in public/open-source repos. When those conflict with this document, follow the repo.

#### Contents:

- [Applicability and precedence](#applicability-and-precedence)
- [Directives: choosing document types](#directives-choosing-document-types)
  - [Type catalog](#type-catalog)
  - [Choosing the right document type](#choosing-the-right-document-type)
- [Directives: writing, structuring and formatting](#directives-writing-structuring-and-formatting)
  - [Voice, tone and clarity](#voice-tone-and-clarity)
  - [Structure and information architecture](#structure-and-information-architecture)
  - [Length and scope heuristics](#length-and-scope-heuristics)
  - [Presenting specific information](#presenting-specific-information)
  - [Quality and rigor](#quality-and-rigor)
- [Boundary between documents and code](#boundary-between-documents-and-code)
- [Documentation review priorities](#documentation-review-priorities)

## Applicability and precedence

- Treat this file as the default standard for READMEs, design docs / RFCs, ADRs, runbooks, postmortems, migration guides, benchmark reports, tutorials, how-to guides, troubleshooting guides, conceptual / explanation docs, and API-adjacent prose docs.
- Repository-specific documentation systems take precedence over Bureau defaults.
- This includes contribution guides, maintainer instructions, frontmatter rules, navigation or sidebar structure, docsite generator conventions, template suites, admonition or callout syntax, snippet or include mechanisms, versioning metadata, slugs or URL rules, asset-path conventions, and established public OSS documentation norms.
- When editing a repository docs set, preserve those mechanics or deliberately update every affected surface together.

## Directives: choosing document types

### Type catalog

- **Design doc / RFC** proposes a system, feature, or architectural change.

    - Audience: reviewers deciding whether the approach should exist
    - Must cover the problem, the proposal, alternatives considered, trade-offs, and rollout / reversal

- **Architecture Decision Record (ADR)** records one significant decision and its context.

    - Audience: future maintainers asking why this decision was made
    - Records what was decided, why, alternatives rejected, and what would cause reconsideration
    - If the decision changes, write a new ADR that supersedes the old one

- **API reference** documents an interface contract.

    - Audience: callers integrating with the interface
    - Covers inputs, outputs, error responses, constraints, and examples

- **Runbook** gives an executable procedure for a specific operational scenario.

    - Audience: operators responding under time pressure
    - Contains steps, commands, checkpoints, and escalation paths
    - Explanatory background belongs elsewhere unless it is required to execute safely

- **Incident postmortem** documents what happened, why, and how recurrence will be prevented.

    - Audience: operators, maintainers, and decision-makers closing the loop after an incident
    - Includes timeline, root cause, impact, and owned follow-up actions

- **Benchmark / performance report** documents measured system behavior under defined conditions.

    - Audience: readers evaluating performance claims or regressions
    - Includes methodology, environment, workload, results, and interpretation

- **Strategy / vision document** states direction and decision criteria.

    - Audience: leaders and teams aligning on where to go and why
    - Stays distinct from tactical execution details

- **Changelog** records notable changes per version in reverse chronological order.

    - Audience: humans tracking technical change over time
    - Use [Keep a Changelog](https://keepachangelog.com) categories when the repo adopts that convention
    - Distinguish changelogs from release notes: changelogs are comprehensive; release notes are curated for a specific audience

- **Migration / upgrade guide** explains how to move from one version, API, or system to another.

    - Audience: operators or users upgrading from a known starting point
    - Includes prerequisites, breaking changes, ordered steps, rollback guidance, and common failure cases

- **Tutorial** teaches by guiding the reader through a coherent learning path.

    - Audience: readers learning a workflow or system for the first time
    - Optimized for confidence, sequencing, and explanation

- **How-to guide** helps the reader complete one concrete task.

    - Audience: readers who know what they want to achieve
    - Optimized for fast task completion, not broad explanation

- **Troubleshooting guide** helps the reader diagnose and remediate a problem.

    - Audience: readers starting from a symptom, alert, or failure mode
    - Organize by symptom, diagnosis, likely causes, and remediation

- **Concept / explanation document** builds the reader's mental model.

    - Audience: readers who need to understand how something works or why it exists
    - Optimized for understanding, not execution

- **PR description** explains what a changeset does and why.

    - Audience: reviewers
    - Should be self-contained enough that review does not depend on chat threads or private context

- **Service / project README** orients a newcomer to one repository or service.

    - Audience: a competent engineer getting productive with limited context
    - Covers what it does, how to run it, how to test it, and where to go next

### Choosing the right document type

- Match the document type to the reader's job.

    - Decide between approaches: design doc or ADR
    - Execute a procedure: runbook or migration guide
    - Look up a contract: API reference
    - Learn a workflow: tutorial
    - Complete a task: how-to guide
    - Diagnose a failure: troubleshooting guide
    - Build a mental model: concept / explanation doc
    - Understand what changed: changelog or release notes
    - Get oriented: README

- Use a design doc when trade-offs need alignment before implementation.

    - The trigger is ambiguity or meaningful blast radius, not code size alone
    - If the document contains no alternatives or trade-offs, it is probably the wrong document type

- Use an ADR when the decision is significant, bounded, and worth preserving.

    - A design doc explores
    - An ADR records

- Calibrate documentation depth to reversibility and blast radius.

    - One-way doors such as public APIs, schema changes, or trust-boundary changes usually need fuller design documentation
    - Easily reversible local changes may need only an ADR, README update, or clear PR description

- Do not mix tutorial, how-to, troubleshooting, and conceptual content unless the repository explicitly does so.

    - A tutorial teaches
    - A how-to solves one task
    - A troubleshooting guide diagnoses a failure
    - A conceptual document explains the model

## Directives: writing, structuring and formatting

### Voice, tone and clarity

- Be prescriptive when the document defines a recommendation, requirement, or procedure.

    - Prefer "use X when Y" over vague option lists
    - State uncertainty explicitly when it exists

- Use concrete quantities where the reader needs measurable truth.

    - Prefer thresholds, latency numbers, retry counts, and version ranges over adjectives

- Use present tense and active voice unless the repository style says otherwise.

- One concept, one name.

    - Use the same term across prose, code, APIs, dashboards, and runbooks
    - Follow repository terminology and heading patterns unless there is a strong reason to introduce a new convention

- Define domain terms and acronyms on first use.

    - Add a glossary when the document introduces specialized vocabulary or crosses team boundaries

- Keep sentences and paragraphs scoped to one idea each.

    - Short declarative prose is easier to review and less likely to hide ambiguity


### Structure and information architecture

#### Purpose, scope and audience

- Every document starts with a scope declaration.

    - State what the document covers, what it does not cover, and who it is for

- Write for the least-context reader the document explicitly targets.

    - Match terminology, examples, and background depth to that reader
    - If the intended reader needs a glossary, provide one

- One document, one purpose.

    - A design doc is not a runbook
    - A README is not an API reference
    - A troubleshooting guide is not a tutorial

#### Body content

- Lead with the decision, recommendation, or task outcome.

    - Put the conclusion first
    - Supporting rationale comes immediately after it

- Put failure modes where the reader needs them.

    - Design docs should address meaningful failure modes, constraints, and non-goals
    - Runbooks and troubleshooting guides should surface unsafe actions, abort criteria, and escalation points early

- Every design doc needs an explicit **Alternatives considered** section.

    - Name rejected options
    - State why they were rejected
    - State what would change the decision

- Use the format that matches the reader's task.

    - Tables for comparisons
    - Ordered lists for sequences
    - Unordered lists for inventories or non-goals
    - Prose for reasoning and causal explanation

- Concrete examples are proof, not decoration.

    - API references need examples that match the contract
    - Design docs should walk a concrete scenario through the proposed system when it materially clarifies the design
    - A stale example is worse than no example

- Keep information dense and scope tight.

    - Remove filler, throat-clearing, and repeated explanations
    - When a document becomes hard to review, the problem is usually scope rather than sentence count

### Length and scope heuristics

- Treat length guidance as heuristic, not law.

    - Design docs, READMEs, migration guides, and runbooks should usually fit into one careful review session
    - If a document cannot be reviewed coherently in one sitting, consider splitting by concern, scenario, or decision
    - Large cumulative artifacts such as changelogs and benchmark appendices are expected to grow; keep each entry or interpretation section scoped and readable

### Presenting specific information

#### Decision documentation

- Decisions must be falsifiable.

    - State the conditions under which the decision would be revisited

- Separate strategy from tactics in long-lived documents.

    - Strategy says where we are going and why
    - Tactics say how we execute within a bounded period

- Keep decision statements close to the evidence that supports them.

    - Do not force the reader to infer the basis for a trade-off by reading the whole document

#### Operational documentation

- Runbooks are executable procedures.

    - They must be followable under pressure by a competent operator with limited context
    - Put commands, checks, rollback steps, and escalation paths in the runbook itself

- Postmortems require timeline, root cause, impact, and owned follow-up actions.

    - Action items need owners, due dates or review points, and a way to verify completion

- API documentation must include failure modes, not just success paths.

    - Document status codes, error shapes, retry guidance, rate limits, and incompatibilities when relevant

- Design docs that change behavior in production should include rollout strategy and reversal path.

    - Separate rollout strategy in the design doc from rollout procedure in the runbook
    - If rollback is impossible or expensive, say so explicitly

- Operational commands, configuration examples, and migration steps must be copy-paste-safe or clearly marked as illustrative.

    - If an example omits required values, destructive flags, or environment-specific placeholders, label it so the reader cannot mistake it for a ready command

#### Security, privacy, and compliance

- Any design doc that crosses a trust boundary, handles sensitive data, changes authentication or authorization, or opens new access paths must address security explicitly.

    - A brief "no security impact" statement is sufficient only when that is actually true

- Classify the data the system handles when security or privacy matters.

    - Name the sensitive data classes and the relevant trust boundaries
    - State the compliance or retention implications when they apply

- Separate security design from security operations.

    - Design docs and ADRs capture architectural security decisions
    - Runbooks capture operational security procedures such as key rotation or compromise response

- Prefer concrete security reasoning over checklist theater.

    - State what is being protected, from whom, and by which controls
    - If the repository or organization already has a security review template or threat-model process, use that process instead of duplicating it in parallel prose

#### Observability documentation

- Design docs for services or production-facing features should specify what the system emits and what healthy looks like.

    - Name the relevant metrics, log keys, trace spans, and candidate SLIs when they materially affect operations

- Split observability content by document purpose.

    - Design docs specify what to measure
    - Runbooks specify how to respond
    - SLO documents define targets and review cadence
    - READMEs link to those artifacts rather than duplicating them

- Metric names, log keys, and span names are discoverability contracts.

    - Use the repository or organization telemetry vocabulary when it exists
    - If the system follows a naming convention such as Prometheus- or OpenTelemetry-style schemas, document and follow it consistently

#### Maintenance and docs-system mechanics

- Link to the source of truth instead of duplicating load-bearing values in prose.

    - If a threshold, schema, config default, or flag definition lives in code or generated docs, link to it
    - A short human-readable summary is fine when it clearly points back to the canonical source

- Version docs with the code they describe when the documents are code-adjacent.

    - Keep design docs, ADRs, READMEs, migration guides, and benchmark reports close to the implementation they explain when the repository supports that model

- Documents form a graph. Link them deliberately.

    - Design docs should link to spawned ADRs, migration guides, or follow-up runbooks
    - ADRs should link back to the design context and forward to implementation where useful
    - READMEs should link to deeper docs rather than absorb them
    - Superseded documents should say what replaced them

- Broken links are documentation bugs.

    - Update moved or renamed targets, inbound references, redirects, and cross-links together

- When editing a repository docs set, preserve or deliberately update the docs-system mechanics together.

    - Frontmatter
    - Navigation or sidebar entries
    - Slugs, URLs, and anchor stability
    - Include or snippet wiring
    - Assets and image paths
    - Versioned docs metadata

### Quality and rigor

- Use RFC 2119 keywords only where requirement language needs precision.

    - [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) is useful for contracts, requirements, and protocol-style documents
    - It is usually unnecessary for READMEs, tutorials, and most runbooks

- State invariants explicitly.

    - Separate always-true requirements from current observations or preferences

- Benchmark and metric documentation must include methodology.

    - State environment, versions, workload, what was measured, how it was measured, and what the result means

- Every factual claim should point to evidence when the claim is material.

    - Link to the benchmark, test, dashboard, incident, schema, or source document that substantiates it
    - If evidence does not exist yet, label the statement as an assumption or open question

- Distinguish facts, assumptions, and opinions.

    - A skeptical reader should be able to tell what is measured, what is inferred, and what is judgment

- Keep external references only when they define or materially clarify the standard.

    - Keep defining references such as RFC 2119, [Keep a Changelog](https://keepachangelog.com), and directly useful doctest-style examples when they sharpen the rule
    - Rewrite or drop authority-only name-dropping, borrowed prestige, and cultural commentary

## Boundary between documents and code

- Put information near the thing that changes it.

    - Information that changes with a function, type, or code path belongs in code comments or docstrings
    - Information that outlives a single code change belongs in design docs, ADRs, READMEs, or runbooks

- Cross-reference by stable identifier instead of duplicating rationale across the boundary.

    - Code should point to ADRs, design docs, or stable doc paths when the why lives there
    - Documents should point to file paths, modules, symbols, tests, or dashboards when the evidence lives there

- Review comments that explain durable rationale should become durable documentation.

    - Do not leave important why-information trapped in PR discussion

- Prefer testable documentation where the repository tooling supports it.

    - Keep directly useful executable examples such as doctests or verified snippets when they materially clarify the standard
    - If the docs system can verify snippets, examples, includes, or link targets automatically, use that path

- Self-documenting code is not enough.

    - Naming and structure help
    - They do not replace contracts, rationale, invariants, or operational guidance

## Documentation review priorities

- Check factual correctness first.

    - Key claims, requirements, thresholds, and architecture statements should match current evidence and current code

- Check commands, examples, config snippets, and migration steps for staleness.

    - They should execute as written or be clearly marked as illustrative

- Check links, references, and navigation integrity.

    - Broken links, missing cross-references, stale slugs, and orphaned docs are documentation bugs

- Check terminology drift.

    - Terms should align with code, APIs, dashboards, and existing docs unless the document explicitly defines an intentional rename

- Check coverage for rollout, rollback, security, privacy, and observability where relevant.

    - Missing operational or risk coverage in the wrong document type is a real gap, not polish

- Check document-type fit.

    - Tutorials should teach
    - How-to guides should solve one task
    - Troubleshooting guides should diagnose failures
    - Concept docs should explain
    - Design docs should justify decisions

- Check repository-specific docs conventions.

    - Frontmatter, templates, sidebars, snippets, admonitions, versioning rules, and docsite generator constraints should be preserved unless the change intentionally updates them

- Check for duplicated values that should instead link to a source of truth.

    - Load-bearing constants, flags, schemas, and compatibility statements should not drift across multiple prose copies
