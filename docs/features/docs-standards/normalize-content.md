# `docs-standards.md` Content Normalization Plan

**Date**: 2026-03-31  
**Status**: Draft  
**Scope**: Normalize the *content* of `protocols/context/static/docs-standards.md` so it is fit to ship as a Bureau-owned default standards file. This plan is intentionally limited to the file's substance, framing, and structure. Deployment, config, hub routing, and review-workflow plumbing are tracked separately in `docs/plans/make-docs-standards.md`.

## Goal

Turn `protocols/context/static/docs-standards.md` from a strong but still somewhat personal and essay-like standards document into a durable Bureau default:

- authoritative without sounding personal
- normative without becoming brittle
- useful for both authoring and review
- compact enough to load as context without losing important guidance
- explicit about precedence when a repository already has its own documentation system

## Fixed design decisions

These decisions are already settled and should not be reopened during normalization:

- Keep `docs-standards.md` as a single static standards file.
- Do not split the primary content into multiple files for v1.
- Do not replace the standards file with a Bureau skill.
- Keep the file as the documentation-side peer to `code-standards.md`, not as a workflow protocol.

## Major normalization goals

### 1. Reframe the document as a Bureau default standard

The current file is substantively strong, but parts of it still read like a thoughtful personal doctrine document. The normalized version should read like `code-standards.md`: stable, repo-portable, and written as a default operating standard rather than a personal manifesto.

### 2. Make precedence and applicability explicit

The current disclaimer is necessary but not sufficient. The file should clearly state when Bureau guidance applies, when repo-specific conventions win, and how to behave when a repository already has an established docs system, template suite, or docsite architecture.

### 3. Preserve all substance while removing fluff and redundancy

Most sections are worth keeping. The normalization goal is to preserve all substantive guidance and distinct insights while eliminating fluff, rhetorical drag, and redundant or repeated information. The file should minimize token usage for context loading without becoming generic, weaker, or less opinionated.

### 4. Make the file clearly usable for review as well as writing

`code-standards.md` is useful both while authoring code and while reviewing it. `docs-standards.md` should do the same for documentation. The normalized version should make review priorities explicit enough that a reviewer or `assess-mode` can use the file as an audit lens.

### 5. Tighten normative language

Reserve hard requirements for genuine cross-repo defaults. Convert guidance that is really heuristic, calibration, or context-dependent advice into clearly marked heuristics.

### 6. Eliminate temporary implementation chatter

The standards file should not refer to outstanding plumbing work, incubation status, or internal rollout notes. It should stand on its own as a canonical content artifact.

## Target end state

After normalization, `docs-standards.md` should have this character:

- A short Bureau-owned preamble.
- An explicit precedence rule for repo-specific docs systems and OSS conventions.
- A compact but strong taxonomy and selection guide, including tutorials, how-to guides, troubleshooting guides, and conceptual/explanation docs.
- Durable guidance on audience, structure, operational content, security, observability, maintenance, and doc/code boundaries.
- An explicit documentation review lens.
- Fewer rhetorical flourishes, fewer named-company examples, and fewer page-count rules presented as if they were laws.
- Lower token cost through removal of repeated or non-load-bearing text without loss of substance.

## Section-by-section rewrite plan

### 1. Title, preamble, disclaimer, and contents

**Current issues**

- The top comment still mentions unfinished plumbing work.
- The disclaimer is good but too general to carry all precedence semantics by itself.
- The file does not yet say, in content terms, how to behave when a repo already has frontmatter rules, docsite conventions, or contributor docs standards.

**Rewrite actions**

- Remove the temporary comment about pending plumbing work.
- Keep the disclaimer, but add a short applicability/preference note directly beneath it.
- Add an explicit principle along the lines of:
  - repository-specific documentation systems take precedence over Bureau defaults
  - this includes contribution guides, maintainer instructions, frontmatter requirements, navigation schemas, docsite generators, MDX/Sphinx/MkDocs/Docusaurus conventions, snippet systems, admonition styles, and established public OSS documentation norms
- Keep a table of contents, but make it stylistically match `code-standards.md` more closely.

**Desired effect**

The file should establish itself immediately as a default baseline that defers cleanly to stronger local authority when present.

### 2. `Technical document types`

**Current issues**

- The taxonomy is valuable and should mostly remain.
- Some entries are more expansive than they need to be for a default standards file.
- Several bullets include rhetorical emphasis that can be tightened.

**Rewrite actions**

- Keep the section and keep the taxonomy broad.
- Tighten each document type entry to:
  - primary purpose
  - intended reader/job-to-be-done
  - one or two defining constraints
- Preserve the distinction between design docs, ADRs, API references, runbooks, postmortems, changelogs, migration guides, strategy docs, PR descriptions, READMEs, tutorials, how-to guides, troubleshooting guides, and conceptual/explanation docs.
- Add explicit treatment of:
  - **Tutorials** as guided learning paths optimized for confidence and sequential understanding
  - **How-to guides** as task-completion documents optimized for one concrete outcome
  - **Troubleshooting guides** as symptom/diagnosis/remediation docs optimized for diagnosis under pressure
  - **Concept/explanation docs** as mental-model docs optimized for understanding rather than execution
- Trim the more speech-like lines so the section reads like classification guidance, not an essay.

**Specific content to preserve**

- The difference between design docs and ADRs.
- The difference between changelogs and release notes.
- The distinction between migration guides and feature/how-to docs.
- The distinction between tutorials, how-to guides, troubleshooting guides, and conceptual/explanation docs.
- The executable nature of runbooks.

### 3. `Choosing the right document type`

**Current issues**

- This section is strong and practical.
- Some rules read more absolute than they should.
- Some material overlaps with the taxonomy above.

**Rewrite actions**

- Keep the section, but rewrite it as a decision rubric rather than a series of strongly voiced judgments.
- Preserve the reversibility/blast-radius framing.
- Preserve the "match doc type to reader job" mapping.
- Soften statements that imply a single correct threshold in all teams.
- Remove any phrasing that sounds like scolding the author for choosing the wrong document before the rubric has even been applied.

**Desired effect**

A reader should be able to decide, quickly and calmly, whether they need a design doc, ADR, runbook, README, migration guide, or just a good PR description.

### 4. `Document purpose and audience`

**Current issues**

- This section is already close to the right shape.
- It could do a better job connecting audience to structure and expected depth.

**Rewrite actions**

- Keep the section short and crisp.
- Preserve:
  - scope declaration
  - default audience model
  - one document, one purpose
- Add a line that the depth of context, examples, and terminology should match the least-context reader the document explicitly targets.

### 5. `Writing voice and clarity`

**Current issues**

- The section is good, but some rules are stated in a way that feels like a personal style manifesto rather than a Bureau default.
- The glossary/acronym guidance is useful and should remain.

**Rewrite actions**

- Keep most of the guidance.
- Tighten the tone to short prescriptive rules and short rationale, similar to `code-standards.md`.
- Preserve:
  - be prescriptive, not vague
  - use concrete quantities
  - one concept, one name
  - define domain terms and acronyms
- Add one docs-system-aware rule:
  - follow the repository's established terminology, headings, and callout patterns unless there is a strong reason to introduce a new convention

### 6. `Structure and information architecture`

**Current issues**

- This is one of the strongest sections in the file.
- It is also one of the densest and most rhetorical.
- The length guidance is useful but currently over-specified and risks being misread as policy.

**Rewrite actions**

- Keep the section, but split its content mentally into:
  - durable rules
  - useful heuristics
- Preserve as durable rules:
  - lead with the decision
  - include alternatives considered in design docs
  - use the right format for the reader's task
  - include concrete examples where they prove understanding
  - include non-goals in design docs
- Reframe as heuristics rather than near-laws:
  - information density over length
  - "fits in one review session"
  - document length by type
  - "scope, not verbosity" as the usual cause of overlong docs
- Replace the current page-count-heavy subsection with a compact "length and scope heuristics" subsection.
- Trim examples down to the minimum needed to preserve the rule.

**Important normalization note**

Do not lose the insight behind the current length guidance. The issue is tone and rigidity, not substance. Preserve the underlying rule that documents should be scoped so a reviewer can reason about them properly.

### 7. `Decision documentation`

**Current issues**

- The section is short and solid.
- It can be integrated more cleanly with the rest of the file.

**Rewrite actions**

- Keep both current ideas:
  - decisions must be falsifiable
  - separate strategy from tactics
- Tighten wording and make this section feel like a concise appendix to the design-doc guidance rather than a partially independent essay.

### 8. `Operational documentation`

**Current issues**

- Strong content, especially around runbooks, postmortems, rollout strategy, and rollback.
- Some content repeats ideas from the taxonomy.

**Rewrite actions**

- Preserve:
  - runbooks are executable procedures
  - postmortems require timeline, root cause, and owned action items
  - API docs must include failure modes
  - design docs need rollout strategy and reversal path
  - rollout strategy vs rollout procedure split
- Remove duplicated explanations that are already adequately covered in earlier sections.
- Add one practical criterion:
  - operational commands and procedures in docs should be copy-paste-safe or clearly marked as illustrative pseudocommands

### 9. `Security, privacy, and compliance`

**Current issues**

- The content is strong but currently carries more rhetoric and external-company framing than a default standards file needs.
- The section should make the difference between "required explicit consideration" and "required large security writeup" clearer.

**Rewrite actions**

- Preserve the core trigger rule:
  - when a change crosses trust boundaries, handles sensitive data, changes auth, or opens new access, security must be addressed explicitly
- Preserve data classification and the split between design-time security decisions and operational security procedures.
- Rewrite the section to emphasize explicit consideration rather than mandatory template bloat.
- Remove or reduce named-company references unless a reference is directly clarifying a standard rather than lending authority by association.
- Add a repo-docs-system-aware sentence:
  - if the repository or organization already has a security-review template or threat-model process, use that process and satisfy this section through it rather than duplicating it in parallel prose

### 10. `Observability documentation`

**Current issues**

- The content is solid and differentiated.
- It can be slightly tightened.

**Rewrite actions**

- Preserve:
  - document what the system emits
  - define what healthy looks like
  - split observability information across design docs, runbooks, SLO docs, and READMEs by purpose
  - metric/log/span naming as discoverability contracts
- Reduce rhetorical lines and long examples.
- Add one clarity improvement:
  - where a repo already has standardized observability vocabulary or telemetry schemas, documentation should use those names rather than inventing synonyms

### 11. `Maintenance and evolution`

**Current issues**

- The guidance is valuable and should largely remain intact.
- It can be made a little more concrete about docsite mechanics and link maintenance.

**Rewrite actions**

- Preserve:
  - link to the source of truth rather than duplicating values
  - version docs with code when they describe code-adjacent behavior
  - documents form a graph and should link explicitly
  - broken links are docs bugs
- Expand slightly to cover docs-system mechanics:
  - preserve existing navigation, frontmatter, slug, and versioning conventions when editing a repository's documentation set
  - when moving docs, update inbound links, navigation references, and docsite metadata together

### 12. `Boundary between documents and code`

**Current issues**

- This section is conceptually excellent and should be preserved.
- It is already the clearest bridge to `code-standards.md`.

**Rewrite actions**

- Keep the section largely intact.
- Tighten wording for symmetry with `code-standards.md`.
- Preserve:
  - proximity to change determines placement
  - cross-reference by stable identifier
  - review comments that explain rationale should become durable comments or docs
  - testable documentation where possible
  - self-documenting code is insufficient
- Add one subtle refinement:
  - if repo-specific docs tooling can verify snippets, examples, or link targets automatically, prefer that path over static prose examples

### 13. `Quality and rigor`

**Current issues**

- The section is strong but currently mixes universal rigor principles with some optional precision tools.
- The RFC 2119 point is good, but it needs clearer scoping so it is not over-applied.

**Rewrite actions**

- Preserve:
  - invariants must be explicit
  - benchmark and metric documentation needs methodology
  - factual claims need evidence
  - facts, assumptions, and opinions should be labeled
- Narrow the RFC 2119 guidance:
  - keep it as a tool for requirements/contract documents
  - make explicit that it is optional and often unnecessary for READMEs, tutorials, and most runbooks
- End the section with a compact synthesis rule:
  - the document should make it easy for a skeptical reader to identify what is required, what is assumed, what is measured, and what is still uncertain

### 14. New section to add: `Documentation review priorities`

**Why add it**

The current file is implicitly useful for review, but it does not yet provide an explicit review lens equivalent to how `code-standards.md` naturally supports code review.

**Add a short new section near the end covering**

- factual correctness and evidence
- stale or broken commands/examples
- broken links and missing cross-references
- terminology drift and inconsistency with code or existing docs
- missing rollout, rollback, security, privacy, or observability coverage where relevant
- mismatch between document type and content
- violation of repo-specific docs conventions
- accidental duplication of values that should instead link to a source of truth

**Desired effect**

A reviewer should be able to read one section and know what "good documentation review" means in Bureau terms.

## Cuts, moves, and consolidations

### Remove entirely

- The top comment about remaining plumbing work.
- Excessive named-company references whose main purpose is rhetorical support rather than substantive guidance.
- Any sentence whose job is mainly emphasis, posture, or voice rather than standard-setting.

### Keep but compress

- Length heuristics by document type.
- The discussion of examples and why they matter.
- The runbook/design-doc/ADR distinctions that currently appear in more than one place.
- The security section's anti-checklist point.

### Consolidate

- Merge overlapping material between the taxonomy and operational sections.
- Merge overlapping material between purpose/audience and structure.
- Merge repeated "executable docs beat descriptive docs" ideas into fewer, stronger rules.

### Consider moving later, but not in this normalization pass

- Extended examples, named external process references, or fuller rationale could eventually live in:
  - a companion authoring guide
  - a future docs-review skill
  - templates for design docs, ADRs, runbooks, or postmortems

## New content to add

### 1. Explicit repo-docs-system-wins principle

Add a top-level rule that says Bureau defaults defer to the repository's established documentation system when one exists. Make this concrete by naming the kinds of conventions that count:

- contribution guides
- maintainer instructions
- frontmatter requirements
- navigation or sidebar structure
- docsite generator conventions
- template suites
- admonition/callout syntax
- snippet/include mechanisms
- versioning and URL/slug rules

### 2. Explicit applicability rule

Add a short note clarifying that this file is primarily for:

- READMEs
- design docs / RFCs
- ADRs
- runbooks
- postmortems
- migration guides
- benchmark reports
- tutorials
- how-to guides
- troubleshooting guides
- conceptual / explanation docs
- API-adjacent prose docs

This helps prevent over-application to contexts where a repo already has more specialized requirements.

### 3. Explicit review lens

Add the `Documentation review priorities` section described above.

### 4. Copy-paste-safe command/example rule

Add a compact rule that operational commands, configuration examples, and migration steps should be executable as written or clearly marked as illustrative.

### 5. Docs-system mechanics rule

Add explicit guidance that when editing a repository's docs set, authors should preserve or deliberately update the docs system mechanics together:

- frontmatter
- sidebars/nav
- slugs/URLs
- include/snippet wiring
- assets and image paths
- versioned docs metadata

This is a material omission in the current file and matters for real-world repo compatibility.

### 6. Explicit reference-handling policy

Add a compact rule for which external references should survive normalization and which should be generalized or removed.

**Keep references that define or materially clarify the standard**

- RFC 2119, because it defines requirement-language semantics
- Keep a Changelog, because it is the actual convention being recommended
- Go `Example` tests and Rust doctests, because they are concrete and directly actionable illustrations of testable documentation
- Prometheus or OpenTelemetry naming conventions, but only when they are being used to specify a real naming rule rather than to borrow authority

**Rewrite to generic principles when the named reference is illustrative but not necessary**

- "Bezos test" -> generic reversibility / one-way-door test
- "Amazon six-pager" -> generic heuristic that a document should fit in one careful review session
- named launch-review or security-review examples -> generic point that many organizations require explicit security review before launch
- organizational cautionary tales about template bloat -> generic warning against accreted compliance-template sprawl

**Drop references whose main function is borrowed authority or cultural commentary**

- named-company lists that do not sharpen the actual rule
- references included mainly to make a point sound more legitimate
- cultural or organizational critique that does not materially improve documentation guidance

## Wording and tone changes

### Tone to adopt

- concise
- stable
- repo-portable
- prescriptive where needed
- skeptical without sounding performative

### Tone to remove

- manifesto-like phrasing
- clever or overly emphatic lines
- authority-by-name-dropping
- statements that read like cultural critique instead of documentation guidance

### Style transformations to apply throughout

- Replace long rhetorical explanations with short rule + short rationale.
- Prefer "use", "include", "document", "link", "preserve", "avoid" wording over speech-like exposition.
- Reserve `must` for true requirements that should hold across most repos.
- Use `should` or explicitly label heuristics where local context may reasonably differ.
- Keep examples short and functional rather than decorative.
- Preserve all distinct substance while collapsing repeated guidance to a single authoritative rule plus cross-reference where needed.
- Optimize for context efficiency: every paragraph should earn its token cost.

## Risks during normalization

### Risk 1: Over-trimming the file into generic advice

If the rewrite removes too much specificity, the file will become bland and non-actionable. Preserve the strongest content even while tightening it.

### Risk 2: Leaving hidden absolutes in place

If page-count or structure guidance still reads like policy when it is really heuristic, the file will create unnecessary conflict with good local practice.

### Risk 3: Adding repo-precedence language that is too vague

If the precedence rule is generic rather than concrete, agents may still miss frontmatter, nav, or docsite-generator conventions that matter operationally.

### Risk 4: Turning the file into a second implementation plan

The standards file should define how to write and review docs, not explain Bureau rollout mechanics or future plumbing tasks.

### Risk 5: Losing symmetry with `code-standards.md`

The docs file should not mimic the code file mechanically, but it should feel like it belongs next to it: same level of crispness, similar authority model, similar usefulness during review.

## Review checklist for the normalization pass

Before declaring the normalized content ready, verify all of the following:

- The top comment contains no rollout, plumbing, or temporary-status chatter.
- The file clearly says repo-specific documentation systems and contribution guidance take precedence.
- The document still covers taxonomy, doc selection, audience, structure, operations, security, observability, maintenance, doc/code boundaries, and rigor.
- Tutorials, how-to guides, troubleshooting guides, and conceptual/explanation docs are either explicitly covered or explicitly scoped.
- The strongest current insights survived the rewrite.
- Length guidance is framed as heuristic, not policy.
- Named-company references were removed or reduced to only the ones that materially clarify a standard.
- The file explicitly supports documentation review, not just authorship.
- The file contains at least one concrete rule about docs-system mechanics such as frontmatter, navigation, or versioning.
- The file no longer reads like a personal essay or manifesto.
- The file still feels stronger and more opinionated than generic style-guide filler.
- The rewrite preserves all unique substance while materially reducing repeated, fluffy, or non-load-bearing text.
- The resulting file is denser and cheaper to load as task context.

## Recommended execution order

1. Normalize the top matter and precedence framing first.
2. Tighten the taxonomy and document-selection sections without changing their conceptual model.
3. Rewrite voice/clarity and structure sections, including heuristic recalibration.
4. Tighten operational, security, observability, and maintenance sections.
5. Preserve and refine the doc/code boundary and rigor sections.
6. Add the explicit review-priorities section.
7. Do one final pass for tone, redundancy, and absolute-language cleanup.

## Done criteria

This plan is complete when the resulting `docs-standards.md`:

- reads like a Bureau default rather than a personal standards essay
- defers cleanly to repo-specific docs systems and OSS conventions
- remains materially stronger than a generic documentation style guide
- is easier to load as task context without losing its best ideas
- is directly usable as both an authoring aid and a review standard
