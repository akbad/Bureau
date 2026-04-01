# Independence checklist

Use this checklist for every pair of candidate work units during Phase 2.
A pair is **independent** only if ALL checks pass. A single failure means the
pair has shared mutable state and must be restructured or sequenced.

## File-level checks

- [ ] **No shared write targets.** List every file each unit will create or
  modify. If any file appears in both lists, the pair is NOT independent.
  - Common trap: shared `__init__.py` files when both units add exports
  - Common trap: shared config files (e.g., `pyproject.toml`, `package.json`)
    when both units add dependencies
  - Common trap: shared index or registry files (e.g., `index.ts`,
    `__all__` lists, route registries)

- [ ] **No append-to-same-file patterns.** Even if units write to "different
  parts" of a file, appending to the same file (e.g., both adding entries to a
  log, both adding routes to a router) creates ordering conflicts.

- [ ] **No shared generated files.** Check whether the build or test process
  for either unit generates files that the other unit also generates (lock
  files, compiled assets, coverage reports).

## Data-level checks

- [ ] **No shared database tables (write-write).** If both units INSERT,
  UPDATE, or DELETE in the same table, they are NOT independent. Both reading
  the same table is fine.

- [ ] **No shared cache keys.** If both units invalidate or write to the same
  cache namespace, they are NOT independent.

- [ ] **No shared environment variables (write-write).** If both units set or
  modify the same env var, they are NOT independent. Both reading the same env
  var is fine.

## Dependency-level checks

- [ ] **No producer-consumer relationship.** If unit A's output is unit B's
  input, they are sequentially dependent, not independent. This includes
  transitive dependencies (A produces for C, C produces for B).

- [ ] **No shared singleton or global state.** If both units modify a
  singleton, global variable, module-level mutable state, or lock file, they
  are NOT independent.

- [ ] **No shared external resource mutations.** If both units call an
  external API that performs a mutation (POST, PUT, DELETE) on the same
  resource, they are NOT independent. Both reading the same API is fine.

## Restructuring strategies when a pair fails

When a check fails, try these strategies before falling back to sequential
execution:

1. **Extract the shared resource.** Move the shared file, table, or state
   into its own work unit that runs first. Downstream units then only read it.

2. **Narrow the blast radius.** Split one of the units so the part that
   touches the shared resource becomes a separate (sequential) mini-unit.

3. **Use a staging pattern.** Have both units write to separate staging
   locations (temp files, staging tables). Add a reconciliation step that
   merges the staged outputs into the shared target.

4. **Defer the shared write.** If both units need to add entries to a shared
   registry, have each unit produce its entries as output, and let the
   reconciliation phase add all entries at once.

If none of these strategies work, the pair must execute sequentially.
Document the dependency in the independence matrix.
