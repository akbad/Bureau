# Protocol deployment modes

**Date**: 2026-03-29
**Status**: Design approved, pending implementation
**Depends on**: 2026-03-29-context-hub-spoke-design.md (hub + spoke files must exist)

## Problem

The hub-and-spoke setup script currently copies protocol files to `~/.config/bureau/protocols/` on every run, which clobbers user customizations. Users need control over when and how protocol files are deployed.

## Design

### Four mutually exclusive deployment modes

| Mode | CLI flag | Config key | Behavior |
|------|----------|------------|----------|
| **Default** | *(none)* | *(all false)* | First-run-only: deploy if directory is empty, skip if files exist |
| **Update** | `-u` / `--update-protocols` | `protocols.update: true` | Re-copy from repo; back up modified files to `.bak` before overwriting |
| **Force** | `-f` (implies `-u`) | `protocols.force: true` | Re-copy from repo; overwrite without backup |
| **Bare** | `-b` / `--bare` | `protocols.bare: true` | Remove all protocol files and hooks; user manages their own context |

### Precedence

CLI flags > config (defaults.yml → .bureau.yml → local.yml → env vars).

If any CLI flag is set, config values are ignored entirely.

### Conflict rules

- `-u` + `-b` → error (contradictory: update vs remove)
- `-f` alone → implicitly enables `-u`
- `protocols.bare: true` in config + `-u` on CLI → update wins (CLI overrides config)

### Config keys

```yaml
protocols:
  update: false   # -u: re-copy protocol files on every run
  force: false    # -f: overwrite without backup (implies update)
  bare: false     # -b: remove all protocol files and hooks
```

## Mode behaviors

### Default mode (no flags)

```
if ~/.config/bureau/protocols/ is empty or missing:
    copy hub + spokes + code-standards from repo
    resolve {{PROTOCOLS_DIR}} in hub
    configure hooks
else:
    skip copying (use existing files)
    still run old-file migration if needed
    still configure hooks
```

### Update mode (-u)

```
for each Bureau-managed file (hub + 4 spokes + code-standards):
    if file exists at destination:
        diff source vs destination (hub: resolve placeholder in-memory first)
        if different AND not --force:
            cp destination → destination.bak
            log "Backed up modified file: X → X.bak"
        if different AND --force:
            log "Overwriting (force): X"
        # if identical: overwrite silently
    cp source → destination
resolve {{PROTOCOLS_DIR}} in hub
configure hooks
```

**Only Bureau-managed files are touched.** Custom user files (e.g., `my-notes.md`) are left alone.

### Force mode (-f)

Same as update but `.bak` backups are skipped. Existing files with differing content are overwritten directly.

### Bare mode (-b)

```
rm -rf ~/.config/bureau/protocols/    # everything, including custom files
configure-hooks.py --remove           # remove Bureau hooks from all CLI configs
skip: template generation, hook configuration, code_standards injection
```

Templates (CLAUDE.md, AGENTS.md) and PAL configs still generate — spoke file references will simply be no-ops since the files won't exist.

## Bureau-managed file manifest

Single source of truth for what Bureau "owns" in the protocols directory:

```bash
BUREAU_HUB_FILE="ops-hub.md"
BUREAU_SPOKE_FILES=("session-start.md" "task-assessment.md" "task-execution.md" "task-completion.md")
BUREAU_CODE_STANDARDS="code-standards.md"
```

Update mode uses this manifest. Files not in this list are never touched.

## Hub file diff handling

The source hub has `{{PROTOCOLS_DIR}}` placeholders; the deployed hub has resolved absolute paths. Comparing them directly always shows a diff. Solution: resolve the placeholder in-memory before comparing:

```bash
resolved_src=$(sed "s|{{PROTOCOLS_DIR}}|$BUREAU_PROTOCOLS_DIR|g" "$src")
echo "$resolved_src" | diff -q - "$dest"
```

## Hook removal (bare mode)

`configure-hooks.py` gets a `--remove` flag that:

| CLI | Identification | Removal |
|-----|---------------|---------|
| Claude Code | Inner command contains `ops-hub.md` | Filter out the hook group from `UserPromptSubmit` array |
| Codex | TOML block containing `ops-hub.md` | Remove `[[hooks.userpromptsubmit]]` block (line-based) |
| Gemini | Entry with `name: "bureau-ops-hub"` | Filter out the entry from `BeforeAgent` array |

All removals preserve other hooks. Idempotent — running twice produces same result.

## File changes

| File | Change |
|------|--------|
| `defaults.yml` | Add `protocols:` section with `update`, `force`, `bare` keys |
| `bin/open-bureau` | Parse `-u`, `-f`, `-b` flags; config fallback; conflict validation; passthrough to set-up-protocols.sh |
| `protocols/scripts/set-up-protocols.sh` | Parse `--update`, `--force`, `--bare`; mode dispatch; `_copy_with_backup` helper; conditional hook/template sections |
| `protocols/scripts/configure-hooks.py` | Add `--remove` flag + 3 removal functions |
| `bin/reset-protocols` | No functional change; add note about `protocols.*` config keys |

## Edge cases

| Scenario | Resolution |
|----------|-----------|
| Custom files in protocols dir during update | Untouched — manifest-based targeting |
| Custom files during bare | Removed — bare means clean slate |
| code-standards.md at old location during update | Symlink from ops/ preserved |
| `.deprecated/` dir from migration | Cleaned up by bare; left alone by update |
| Multiple `.bak` from repeated updates | One `.bak` per file, overwritten each update (use git for history) |
| `set-up-protocols.sh` run directly (no open-bureau) | Default mode; flags work if passed manually |
| `--remove` without `--protocols-dir` | `--protocols-dir` made optional when `--remove` is set |

## Implementation order

1. `defaults.yml` + `config_loader.py` — add config keys (foundation, no behavioral change)
2. `configure-hooks.py` — add `--remove` flag + removal functions + tests
3. `set-up-protocols.sh` — mode dispatch rewrite (highest risk)
4. `bin/open-bureau` — flag parsing, validation, config fallback, passthrough
5. Tests for all of the above
