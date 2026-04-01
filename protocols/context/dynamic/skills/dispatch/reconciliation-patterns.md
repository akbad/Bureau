# Reconciliation patterns

Reference these patterns during Phase 3 to select and define your
reconciliation strategy. Each pattern includes when to use it, what can go
wrong, and what verification to run afterward.

---

## Pattern 1: No-conflict merge (disjoint files)

### When to use

Work units touch completely disjoint sets of files. No file appears in more
than one unit's blast radius.

### Strategy

1. Collect all file changes from each subagent.
2. Apply all changes to the working tree (or branch). Since files are
   disjoint, there are no merge conflicts by construction.
3. Run the full test suite to verify the combined changes integrate correctly
   at the behavioral level (compile, lint, test).

### What can go wrong

- **Semantic conflicts.** Files are disjoint but one unit's changes break
  assumptions that another unit's code relies on (e.g., unit A renames a
  function in `utils.py`, unit B calls that function from `service.py`).
  The independence check should catch this (shared read + write = not
  independent), but verify with tests.
- **Import ordering.** Both units add new imports to different files that
  transitively create a circular dependency.

### Verification

- All tests pass after applying all changes.
- Linter passes (catches circular imports, unused imports).
- No files were modified by more than one subagent (sanity check).

---

## Pattern 2: Output assembly (compose independent artifacts)

### When to use

Work units produce independent artifacts (documents, config sections, test
files, data files) that must be composed into a larger deliverable.

### Strategy

1. Define the assembly order and format before dispatch. Each subagent must
   know exactly what format to produce and where its output fits in the
   larger structure.
2. Collect artifacts from each subagent.
3. Assemble into the final deliverable following the predefined order.
4. Add any glue logic (table of contents, imports, cross-references).
5. Verify the assembled result is internally consistent.

### What can go wrong

- **Format drift.** Subagents produce artifacts in slightly different formats
  despite instructions. Specify format precisely in subagent prompts
  (including headers, indentation, naming conventions).
- **Missing cross-references.** Assembled document has broken internal links
  or references. Run a cross-reference check after assembly.
- **Ordering ambiguity.** If assembly order matters (e.g., SQL migrations),
  define it before dispatch, not after.

### Verification

- All artifacts conform to the specified format.
- Assembled deliverable has no broken internal references.
- Assembled deliverable passes any applicable tests or linters.

---

## Pattern 3: Review-and-integrate (synthesis of analysis)

### When to use

Work units produce analysis, recommendations, or research that the
orchestrating agent must synthesize into a coherent conclusion.

### Strategy

1. Define synthesis criteria before dispatch: what dimensions to evaluate,
   what format each subagent should use for findings, how conflicts between
   analyses will be resolved.
2. Collect analyses from each subagent.
3. Normalize findings into a common structure (table, list, or document).
4. Identify agreements, contradictions, and gaps.
5. Resolve contradictions using the predefined criteria (evidence quality,
   source authority, specificity).
6. Produce a synthesized deliverable that attributes findings to their source.

### What can go wrong

- **Contradictory findings.** Two subagents reach opposite conclusions.
  Without predefined resolution criteria, the orchestrator is stuck.
- **Apples-to-oranges comparison.** Subagents frame their analysis differently,
  making synthesis difficult. Normalize the analysis framework in the prompt.
- **Confirmation bias.** Orchestrator cherry-picks findings that confirm a
  preferred conclusion. Compare all findings systematically.

### Verification

- All subagent findings are accounted for (none silently dropped).
- Contradictions are explicitly noted and resolved with stated reasoning.
- Synthesized deliverable includes source attribution.

---

## Pattern 4: Staged merge (parallel writes to shared target)

### When to use

Work units need to contribute to a shared resource (e.g., both add routes to
a router, both add entries to a config file), but the actual writes are
deferred to reconciliation.

### Strategy

1. Instruct each subagent to produce its contribution as a standalone artifact
   (e.g., a separate file with just its routes, a JSON fragment with its
   config entries).
2. Collect all contributions.
3. The orchestrating agent (not a subagent) merges all contributions into the
   shared target in a single operation.
4. Verify the merged target is valid.

### What can go wrong

- **Ordering conflicts.** Contributions must be merged in a specific order
  (e.g., database migration sequence numbers). Define the ordering scheme
  before dispatch.
- **Namespace collisions.** Two subagents define the same route path, config
  key, or function name. Check for duplicates during merge.
- **Partial application.** Merge fails halfway, leaving a corrupted shared
  target. Apply atomically (write to temp, verify, then replace).

### Verification

- No duplicate keys, routes, names, or identifiers in the merged target.
- Merged target passes validation (schema check, lint, test).
- All contributions are present in the merged result.

---

## Choosing a pattern

| Situation | Pattern |
|-----------|---------|
| Work units modify completely disjoint files | No-conflict merge |
| Work units produce artifacts for a larger document or deliverable | Output assembly |
| Work units produce analysis or recommendations | Review-and-integrate |
| Work units need to contribute to the same file or resource | Staged merge |
| Work units have mixed characteristics | Combine patterns; use the most restrictive for the shared-resource portions |

If none of these patterns fit, the work units may not be suitable for
parallel dispatch. Reconsider the decomposition in Phase 1.
