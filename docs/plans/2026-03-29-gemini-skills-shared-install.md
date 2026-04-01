# Skill Installation Naming Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove install-time Bureau skill prefixing, make Codex and Gemini share `~/.agents/skills/`, migrate public skill names from `bureau-*` to canonical unprefixed names, and update tests/docs to match.

**Architecture:** Treat the skill source directory basename as the single source of truth for skill naming. The config/catalog/generator pipeline resolves unprefixed names, the installer creates unprefixed symlinks and cleans only Bureau-owned or legacy-prefixed installs in managed skill directories, and docs/examples are updated to describe the canonical names alongside the renamed dossier slash commands `/fold-dossier` and `/unfold-dossier`.

**Tech Stack:** Bash, Python, JSON, Markdown, `pytest`, `jq`, `uv`

---

### Task 1: Remove prefix-aware resolution from the config/catalog pipeline

**Files:**
- Modify: `defaults.yml`
- Modify: `operations/skills_catalog.py`
- Modify: `protocols/scripts/generate-skills-config.py`
- Modify: `operations/tests/test_skills_catalog.py`
- Create: `protocols/scripts/tests/test_generate_skills_config.py`

- [ ] **Step 1: Write failing unit tests for unprefixed catalog and generated config output**

```python
from operations.skills_catalog import resolve_skills_catalog


def test_filters_by_enabled_disabled_and_sources_without_prefix(tmp_path):
    skills_dir = tmp_path / "skills"
    (skills_dir / "alpha").mkdir(parents=True)
    (skills_dir / "beta").mkdir(parents=True)

    config = {
        "skills": {
            "enabled": ["alpha"],
            "disabled": ["beta"],
            "sources": [{"path": str(skills_dir)}],
        }
    }

    resolved = resolve_skills_catalog(config)
    assert resolved["skills"] == ["alpha"]
```

```python
from pathlib import Path
from runpy import run_path


def test_build_skills_entries_emits_name_and_source_path_only(tmp_path):
    skills_dir = tmp_path / "skills"
    alpha = skills_dir / "alpha"
    alpha.mkdir(parents=True)
    repo_root = Path(__file__).resolve().parents[3]
    module = run_path(str(repo_root / "protocols/scripts/generate-skills-config.py"))
    build_skills_entries = module["_build_skills_entries"]

    payload = build_skills_entries(
        {
            "skills": {
                "enabled": ["alpha"],
                "disabled": [],
                "sources": [{"path": str(skills_dir)}],
            }
        },
        repo_root=Path("/repo"),
    )

    assert payload == {
        "skills": [{"name": "alpha", "source_path": str(alpha)}]
    }
```

- [ ] **Step 2: Run the focused tests to confirm current behavior fails**

Run:

```bash
pytest operations/tests/test_skills_catalog.py protocols/scripts/tests/test_generate_skills_config.py -q
```

Expected:

```text
FAIL operations/tests/test_skills_catalog.py::test_filters_by_enabled_disabled_and_sources_without_prefix
ERROR or FAIL protocols/scripts/tests/test_generate_skills_config.py::test_build_skills_entries_emits_name_and_source_path_only
```

- [ ] **Step 3: Remove `skills.sources.prefix` from config defaults and simplify the resolver/generator**

```yaml
skills:
  enabled: [micro-mode, assess-mode, fold, unfold]
  disabled: []
  sources:
    - path: protocols/context/static/skills
```

```python
def resolve_skills_catalog(config: Mapping[str, Any]) -> dict[str, Any]:
    skills_cfg = config.get("skills", {})
    enabled = (
        None
        if skills_cfg.get("enabled") in (None, "all")
        else set(skills_cfg.get("enabled", []))
    )
    disabled = set(skills_cfg.get("disabled", []))
    sources = skills_cfg.get("sources", [])
    try:
        repo_root = find_repo_root()
    except FileNotFoundError:
        repo_root = Path.cwd()

    resolved: list[str] = []
    for source in sources:
        root = Path(source["path"]).expanduser()
        if not root.is_absolute():
            root = repo_root / root
        if not root.exists():
            continue
        for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            name = skill_dir.name
            if enabled is not None and name not in enabled:
                continue
            if name in disabled:
                continue
            resolved.append(name)

    return {"skills": resolved}
```

```python
def _build_skills_entries(config: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    resolved = resolve_skills_catalog(config)
    remaining = Counter(resolved.get("skills", []))

    skills_cfg = config.get("skills", {})
    sources = skills_cfg.get("sources", [])

    entries: list[dict[str, str]] = []
    for source in sources:
        source_path = source.get("path")
        if not source_path:
            continue
        root = _resolve_source_root(source_path, repo_root)
        if not root.exists():
            continue
        for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            name = skill_dir.name
            if remaining.get(name, 0) <= 0:
                continue
            entries.append({"name": name, "source_path": str(skill_dir)})
            remaining[name] -= 1

    return {"skills": entries}
```

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
pytest operations/tests/test_skills_catalog.py protocols/scripts/tests/test_generate_skills_config.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add defaults.yml operations/skills_catalog.py protocols/scripts/generate-skills-config.py operations/tests/test_skills_catalog.py protocols/scripts/tests/test_generate_skills_config.py
git commit -m "refactor: remove skill prefix resolution"
```

### Task 2: Make the installer create canonical symlink names and perform safe migration cleanup

**Files:**
- Modify: `protocols/scripts/set-up-skills.sh`
- Create: `protocols/scripts/tests/test_set_up_skills.py`

- [ ] **Step 1: Write failing installer smoke tests for canonical names and Gemini sharing**

```python
import os
import subprocess
from pathlib import Path


def test_set_up_skills_installs_unprefixed_names_into_shared_agents_dir(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    home = tmp_path / "home"
    home.mkdir()

    env = os.environ.copy()
    env["HOME"] = str(home)

    subprocess.run(
        ["bash", "protocols/scripts/set-up-skills.sh"],
        cwd=repo_root,
        env=env,
        check=True,
    )

    assert (home / ".agents/skills/assess-mode").is_symlink()
    assert not (home / ".agents/skills/bureau-assess-mode").exists()
    assert not (home / ".gemini/skills/assess-mode").exists()
```

- [ ] **Step 2: Run the installer smoke test and confirm it fails with the current prefixed install logic**

Run:

```bash
pytest protocols/scripts/tests/test_set_up_skills.py -q
```

Expected:

```text
FAIL test_set_up_skills_installs_unprefixed_names_into_shared_agents_dir
```

- [ ] **Step 3: Rewrite installer cleanup and link creation around canonical names**

```bash
LEGACY_BUREAU_SKILL_PREFIX="bureau-"

remove_legacy_prefixed_skill_dirs() {
    local skill_conf_dir=$1
    for entry in "$skill_conf_dir"/${LEGACY_BUREAU_SKILL_PREFIX}*; do
        [ -e "$entry" ] || continue
        rm -rf "$entry"
    done
}

is_bureau_skill_symlink() {
    local entry=$1
    [ -L "$entry" ] || return 1
    local target
    target="$(readlink "$entry")"
    for source_dir in "${SKILL_SOURCE_DIRS[@]}"; do
        [ "$target" = "$source_dir" ] && return 0
    done
    return 1
}

remove_owned_skill_dirs() {
    local skill_conf_dir=$1
    [ -d "$skill_conf_dir" ] || return
    for skill_name in "${ALL_SOURCE_SKILL_NAMES[@]}"; do
        local entry="$skill_conf_dir/$skill_name"
        if is_bureau_skill_symlink "$entry"; then
            rm -f "$entry"
        fi
    done
    remove_legacy_prefixed_skill_dirs "$skill_conf_dir"
}

link_skill_dir() {
    local skill_conf_dir=$1
    local skill_name=$2
    local skill_source_dir=$3
    local skill_install_dir="$skill_conf_dir/$skill_name"

    if [[ -e "$skill_install_dir" && ! -L "$skill_install_dir" ]]; then
        log_warning "Skipped conflicting non-symlink path: $skill_install_dir"
        return
    fi
    if [[ -L "$skill_install_dir" ]] && ! is_bureau_skill_symlink "$skill_install_dir"; then
        log_warning "Skipped conflicting foreign symlink: $skill_install_dir"
        return
    fi

    ln -sfn "$skill_source_dir" "$skill_install_dir"
    log_success "$skill_install_dir"
}
```

Also make these installer-level changes:

- remove `GEMINI_SKILLS_DIR` as an install target
- update the header comment so Gemini shares `~/.agents/skills/`
- parse generated JSON as `[name, source_path]`
- install Codex and Gemini together under `~/.agents/skills/`
- drop `~/.gemini/skills/` cleanup entirely

- [ ] **Step 4: Re-run the installer smoke test plus a dry-run verification**

Run:

```bash
pytest protocols/scripts/tests/test_set_up_skills.py -q
bash protocols/scripts/set-up-skills.sh --dry-run
```

Expected:

```text
1 passed
...
Codex / Gemini CLI
...
Would link from: .../.agents/skills/assess-mode
```

- [ ] **Step 5: Commit**

```bash
git add protocols/scripts/set-up-skills.sh protocols/scripts/tests/test_set_up_skills.py
git commit -m "refactor: install bureau skills under canonical names"
```

### Task 3: Normalize skill frontmatter and update user-facing docs/examples

**Files:**
- Modify: `protocols/context/static/skills/README.md`
- Modify: `protocols/context/static/skills/micro-mode/SKILL.md`
- Modify: `README.md`
- Modify: `docs/CONFIGURATION.md`
- Modify: `docs/DATA-FLOWS.md`

- [ ] **Step 1: Write failing text checks for prefixed public skill names in docs**

Run:

```bash
rg -n 'bureau-assess-mode|bureau-micro-mode|All skill names below appear in agent interfaces prefixed with `bureau-`|prefix: bureau-' README.md docs/CONFIGURATION.md docs/DATA-FLOWS.md protocols/context/static/skills/README.md protocols/context/static/skills/micro-mode/SKILL.md
```

Expected:

```text
Matches in README.md, docs/CONFIGURATION.md, docs/DATA-FLOWS.md, protocols/context/static/skills/README.md, and protocols/context/static/skills/micro-mode/SKILL.md
```

- [ ] **Step 2: Rewrite docs and frontmatter to describe canonical names**

```yaml
---
name: micro-mode
description: Step-gated editing with DAG-based planning and continuous user steering.
---
```

```md
Skills are structured multi-step protocols (e.g., `assess-mode`) that agents activate automatically when they recognise a matching task.
```

```yaml
skills:
  enabled:
    - micro-mode
    - debugging
  disabled:
    - shadow-mode
  sources:
    - path: protocols/context/static/skills
```

Also update these doc narratives:

- `README.md`: remove claims that Bureau skill names are prefixed with `bureau-`
- `protocols/context/static/skills/README.md`: replace the old "omit `name` because install dirs are prefixed" guidance with canonical-name guidance
- `docs/DATA-FLOWS.md`: change the diagram and captions from `bureau-*` nodes to canonical names/shared agents dir

- [ ] **Step 3: Re-run the text checks and ensure only intentional non-skill `bureau-*` strings remain**

Run:

```bash
rg -n "bureau-assess-mode|bureau-micro-mode|prefix: bureau-" README.md docs/CONFIGURATION.md docs/DATA-FLOWS.md protocols/context/static/skills/README.md protocols/context/static/skills/micro-mode/SKILL.md
```

Expected:

```text
No matches
```

- [ ] **Step 4: Commit**

```bash
git add protocols/context/static/skills/README.md protocols/context/static/skills/micro-mode/SKILL.md README.md docs/CONFIGURATION.md docs/DATA-FLOWS.md
git commit -m "docs: rename bureau skills to canonical names"
```

### Task 4: Update the unified plan doc and run end-to-end verification

**Files:**
- Modify: `docs/plans/2026-03-29-gemini-skills-shared-install.md`

- [ ] **Step 1: Rewrite the March 29 plan in place so it documents the unified migration**

```md
# Skill Installation Naming Unification Implementation Plan

**Goal:** Remove install-time Bureau skill prefixing, make Codex and Gemini share `~/.agents/skills/`, migrate public skill names from `bureau-*` to canonical unprefixed names, and update tests/docs to match.
```

- [ ] **Step 2: Run the full targeted verification suite**

Run:

```bash
pytest operations/tests/test_skills_catalog.py \
       protocols/scripts/tests/test_generate_skills_config.py \
       protocols/scripts/tests/test_set_up_skills.py -q
python protocols/scripts/generate-skills-config.py --stdout
bash protocols/scripts/set-up-skills.sh
ls -1 ~/.agents/skills | sort
ls -1 ~/.gemini/skills 2>/dev/null | sort
```

Expected:

```text
All targeted tests pass
Generated JSON contains {"name": "...", "source_path": "..."} entries plus source roots for ownership checks
~/.agents/skills contains assess-mode, fold, micro-mode, unfold, superpowers
~/.gemini/skills is untouched by setup
```

- [ ] **Step 3: Run targeted repo searches to confirm the public rename is complete**

Run:

```bash
rg -n "bureau-(assess-mode|micro-mode|fold|unfold)" README.md docs protocols operations defaults.yml
```

Expected:

```text
No matches for Bureau skill names, except intentional legacy/migration commentary if retained in the plan or tests
```

- [ ] **Step 4: Commit**

```bash
git add docs/plans/2026-03-29-gemini-skills-shared-install.md
git commit -m "docs: finalize skill naming migration plan"
```
