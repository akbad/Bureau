# Skill Installation Naming Unification Design

**Date:** 2026-03-30

## Goal

Remove install-time skill name prefixing from Bureau so that the canonical skill name is always the source directory basename, while preserving the already-planned Codex/Gemini shared install at `~/.agents/skills/`.

## Current flow

Today the skill install pipeline looks like this:

1. `defaults.yml` defines `skills.enabled`, `skills.disabled`, and `skills.sources[].prefix`
2. `operations/skills_catalog.py` prepends the configured prefix to each enabled skill name
3. `protocols/scripts/generate-skills-config.py` emits generated entries with `{name, prefix, source_path}`
4. `protocols/scripts/set-up-skills.sh` installs each skill under `<prefix><name>` in every CLI skills directory

That yields public skill names such as `bureau-assess-mode` and symlink paths such as `~/.agents/skills/bureau-assess-mode`.

## Design decisions

### 1. Canonical skill names become unprefixed everywhere

The canonical name for a Bureau skill is the source directory basename:

- `protocols/context/static/skills/assess-mode` -> `assess-mode`
- `protocols/context/static/skills/micro-mode` -> `micro-mode`
- `protocols/context/static/skills/fold-dossier` -> `fold-dossier`
- `protocols/context/static/skills/unfold-dossier` -> `unfold-dossier`

`skills.sources.prefix` is removed from configuration and from the generated skills config shape.

### 2. Codex and Gemini share `~/.agents/skills/`

Gemini CLI no longer receives a separate install into `~/.gemini/skills/`, and Bureau no longer cleans or manages that legacy directory.

Managed installs become:

- Claude Code: `~/.claude/skills/<skill-name>`
- OpenCode: `~/.config/opencode/skill/<skill-name>`
- Codex + Gemini CLI: `~/.agents/skills/<skill-name>`

### 3. Cleanup becomes ownership-based, not wildcard prefix-based

Removing the prefix removes the namespace marker, so cleanup must stop deleting arbitrary entries by unprefixed name alone.

The installer should:

- remove Bureau-owned symlinks that point to Bureau skill source directories
- remove legacy `bureau-*` skill entries from previous installs
- warn and skip when an unprefixed target path exists as foreign content

This keeps the migration safe even if a user already has a non-Bureau `assess-mode` directory in a CLI skills folder.

### 4. Frontmatter and docs align to canonical names

Static Bureau skills should either omit `name` or use the canonical unprefixed name. Existing inconsistent frontmatter such as `name: bureau-micro-mode` is corrected.

Docs and examples that currently present `bureau-assess-mode`-style names are updated to the canonical unprefixed names.

## Non-goals

This migration does **not** rename unrelated Bureau component namespaces such as:

- `bureau-dossiers`
- `bureau-ops-hub`

The user-facing fold/unfold slash commands are tracked separately as `/fold-dossier` and `/unfold-dossier`.

## Files affected

### Runtime/config path

- `defaults.yml`
- `operations/skills_catalog.py`
- `protocols/scripts/generate-skills-config.py`
- `protocols/scripts/set-up-skills.sh`

### Tests

- `operations/tests/test_skills_catalog.py`
- `protocols/scripts/tests/test_generate_skills_config.py` (new)
- `protocols/scripts/tests/test_set_up_skills.py` or equivalent script smoke coverage (new if practical)

### Skill content/docs

- `protocols/context/static/skills/README.md`
- `protocols/context/static/skills/micro-mode/SKILL.md`
- `README.md`
- `docs/CONFIGURATION.md`
- `docs/DATA-FLOWS.md`
- `docs/plans/2026-03-29-gemini-skills-shared-install.md`

Additional doc/string references to `bureau-<skill-name>` should be updated where they refer to skill names rather than unrelated Bureau commands.

## Verification

Minimum acceptance checks:

1. Generated skills config contains only canonical names and source paths
2. Fresh installs create unprefixed skill symlinks
3. Legacy `bureau-*` entries are removed during setup/uninstall
4. Gemini uses `~/.agents/skills/` only, and `~/.gemini/skills/` is untouched
5. User-facing skill docs/examples show unprefixed names
