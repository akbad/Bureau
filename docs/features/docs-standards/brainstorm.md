# Adding `docs-standards.md`: a *first-class peer* to `code-standards.md`

**Date**: 2026-03-30
**Status**: Draft plan
**Scope**: Add Bureau-owned documentation standards content and wire it into the same context, deployment, configuration, and review surfaces that currently exist for `code-standards.md`

## Goal

Make `docs-standards.md` a true first-class standards artifact in Bureau, not just a markdown file living in the repo.

That means:

- Bureau ships a default docs standards file in `protocols/context/static/`
- Bureau deploys it into the user-scoped protocols directory alongside the other managed protocol files
- the ops hub routes documentation-writing tasks to it on demand
- users can override it via config just like `code_standards`
- review workflows can consume it when the target is documentation
- setup/reset/tests/docs all recognize it as Bureau-managed

## Current gap

Today, Bureau has explicit first-class support only for coding standards:

- `ops-hub.md` routes code-writing/editing tasks to `ops/code-standards.md`
- `set-up-protocols.sh` deploys and injects custom `code_standards` paths
- `bin/reset-protocols` restores `ops/code-standards.md`
- `docs/CONFIGURATION.md` documents the `code_standards` config key
- `assess-mode` resolves `code_standards` as its standards source
- tests assert that `code-standards.md` is part of the managed protocols set

Adding `protocols/context/static/docs-standards.md` without matching plumbing would create a reference file, not a peer.

## Definition of "peer"

`docs-standards.md` is only a real peer to `code-standards.md` once all of the following are true:

1. A Bureau-owned default content file exists at `protocols/context/static/docs-standards.md`
2. A deployed copy exists at `~/.config/bureau/protocols/ops/docs-standards.md`
3. `ops-hub.md` routes documentation tasks to it
4. A top-level `docs_standards` config key exists with semantics parallel to `code_standards`
5. Setup injects additional configured `docs_standards` files into the hub the same way it does for `code_standards`
6. Reset/deployment tests treat it as part of the Bureau-managed manifest
7. Review workflows can use it when auditing documentation changes
8. User-facing docs describe the new behavior and override path

## Design

### 1. Add the standards content file

**Create:**

- `protocols/context/static/docs-standards.md`

**Content rules:**

- Start from `think/masterkey/my/standards/docs.md`
- Depersonalize the title and preamble so it reads as a Bureau default, not a personal note
- Keep the existing section structure because it is already well-shaped for a standards document:
  - document taxonomy
  - choosing document types
  - purpose/audience
  - voice/clarity
  - structure/information architecture
  - operational/security/observability rules
  - maintenance
  - document/code boundary
  - evidence/rigor
- Replace references to `code.md` with `code-standards.md`
- Add the same public/open-source contribution-guidelines disclaimer that appears in `code-standards.md`

**Important constraint:**

- Do not claim config/runtime behavior inside this file until the plumbing below exists

### 2. Route documentation tasks through the hub

**Modify:**

- `protocols/context/static/ops-hub.md`

**Add:**

- A new `<read-file-when>` entry for documentation work, parallel to the existing code one

**Recommended routing text:**

```xml
<read-file-when task="writing or editing documentation" path="{{PROTOCOLS_DIR}}/ops/docs-standards.md" />
```

**Why keep the trigger broad:**

- It covers READMEs, design docs, ADRs, runbooks, postmortems, changelogs, migration guides, benchmark reports, and similar markdown/prose artifacts
- It keeps the hub compact and leaves interpretation to the agent, consistent with the current spoke-routing style

### 3. Make protocol deployment treat docs standards as Bureau-managed

**Modify:**

- `protocols/scripts/set-up-protocols.sh`
- `bin/reset-protocols`

**`set-up-protocols.sh` changes:**

- Add a `BUREAU_DOCS_STANDARDS="docs-standards.md"` manifest constant
- Deploy `protocols/context/static/docs-standards.md` into `~/.config/bureau/protocols/ops/docs-standards.md`
- Mirror the `code-standards.md` convention behavior:
  - if `~/.config/bureau/protocols/docs-standards.md` already exists, symlink it into `ops/`
  - otherwise copy the repo default into `ops/`
- Add a second injection pass for configured `docs_standards` files so external override paths are added to the hub
- Skip duplicate injection when the resolved path is already the default static file, the deployed ops file, or the convention root file

**`bin/reset-protocols` changes:**

- Copy `docs-standards.md` into `ops/` during reset
- Include it in the restored-files output

### 4. Add config parity with `code_standards`

**Modify:**

- `defaults.yml`
- `docs/CONFIGURATION.md`

**`defaults.yml`:**

- Add a commented default block for:

```yaml
# docs_standards:
#   - protocols/context/static/docs-standards.md
```

**`docs/CONFIGURATION.md`:**

- Add `docs_standards` to the table of contents
- Add a new `### docs_standards` section directly parallel to `code_standards`
- Document:
  - purpose
  - resolution order
  - default shipped file
  - override examples
  - path resolution rules
  - behavior when no docs standards are found

**Recommended resolution order:**

1. `docs_standards` config key is set
2. `~/.config/bureau/protocols/docs-standards.md` exists
3. otherwise no external docs standards are loaded

### 5. Make review workflows documentation-aware

**Modify:**

- `protocols/context/static/skills/assess-mode/SKILL.md`

**Change the standards-resolution model from code-only to file-type-aware:**

- If all review targets are documentation files, resolve `docs_standards`
- If all review targets are code files, resolve `code_standards`
- If the changeset is mixed, resolve and read both

**Documentation file classes to treat as docs for standards selection:**

- `*.md`
- repo docs directories such as `docs/`
- ADR / RFC / README / CONTRIBUTING / changelog / migration-guide style files

**Fallback behavior:**

- If doc targets exist but no docs standards are configured/found, the review should still run with internal clarity/consistency checks, analogous to the current `code_standards` fallback

### 6. Update protocol inventory and flow docs

**Modify:**

- `docs/CONFIGURATION.md`
- `docs/DATA-FLOWS.md`
- optionally `README.md` if we want the public feature description to mention docs standards explicitly

**Required doc changes:**

- Add `ops/docs-standards.md` to the "Agent context files" inventory table
- Update any data-flow diagrams or prose that currently describe `code_standards` as the only standards input

**Optional `README.md` change:**

- Extend language like "configurable quality standards" to make it clear that Bureau can carry both code and documentation standards

### 7. Extend tests so peerhood is enforced

**Modify:**

- `protocols/scripts/tests/test_protocols_dir.py`

**Add assertions for:**

- `ops/docs-standards.md` existing after reset/deploy
- deployed content matching the new static source
- the managed manifest including docs standards
- hub placeholder resolution still working with the extra spoke

**Add shell-function / deployment coverage if the setup script grows new helper logic for docs standards injection**

## Exact file set

### Create

- `protocols/context/static/docs-standards.md`
- `docs/plans/make-docs-standards.md`

### Modify

- `protocols/context/static/code-standards.md`
- `protocols/context/static/ops-hub.md`
- `protocols/context/static/skills/assess-mode/SKILL.md`
- `protocols/scripts/set-up-protocols.sh`
- `protocols/scripts/tests/test_protocols_dir.py`
- `bin/reset-protocols`
- `defaults.yml`
- `docs/CONFIGURATION.md`
- `docs/DATA-FLOWS.md`
- `README.md` (optional but recommended)

### No changes expected

- `protocols/context/templates/AGENTS.template.md`
- `protocols/context/templates/CLAUDE.template.md`

The templates already point agents at `ops-hub.md`; once the hub knows about docs standards, template behavior updates automatically.

## Disclaimer language to standardize

Apply the same warning banner to both standards files:

> These are Bureau defaults. They do **not** override repository-specific contribution guides, maintainer instructions, or clear established conventions in public/open-source repos. When those conflict with this document, follow the repo.

## Implementation order

1. Add `protocols/context/static/docs-standards.md` and standardize disclaimers in both standards files
2. Update `ops-hub.md`
3. Update `set-up-protocols.sh` and `bin/reset-protocols`
4. Update `defaults.yml` and `docs/CONFIGURATION.md`
5. Make `assess-mode` docs-aware
6. Update tests
7. Update `docs/DATA-FLOWS.md` and any optional `README.md` language

## Done criteria

- A fresh reset/deploy produces `ops/docs-standards.md`
- The hub contains a docs-standards routing entry
- Users can override docs standards via `docs_standards`
- Review guidance knows when to use docs standards vs code standards
- Docs and tests reflect the new peer relationship
