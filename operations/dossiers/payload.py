"""The fold payload contract: one declaration of what a fold accepts.

# Design rationale

The payload schema is documented as prose in `fold-dossier/SKILL.md` and
consumed as `input_data.get(...)` calls in `cli.cmd_fold`. With no mechanism
relating the two, they drift in **both** directions — documented fields the CLI
never reads, and accepted fields the skill never mentions — and the drift is
invisible, because the consumer is an agent that improvises around gaps rather
than reporting them. This module makes the contract a single importable
declaration, so `cmd_fold` and the contract test read the same source.

The pattern is borrowed from `db.py`'s shared DDL constants: fresh-create and
migration build byte-identical schema from one definition *specifically* so a
test can diff them, because "divergence is the classic silent-migration bug."
Documentation drifting from implementation is that same bug in a different
medium.

## Contract drift has four surfaces, and a top-level key diff catches one

  1. **Key sets** — documented vs accepted at the top level.
     → `FOLD_PERSISTED_KEYS`, `FOLD_PENDING_KEYS`.
  2. **Prose behaviour claims** — the skill restating what the CLI *does*
     (retention windows, output formats, atomicity). Not mechanically
     detectable, because no key is involved. Governed instead by a rule:
     *the skill states the CLI's contract with the agent — inputs,
     prohibitions, what to relay — and never the CLI's internal mechanism.*
     A mechanism claim has an expiry date; a contract statement does not.
  3. **Mode-conditional handling** — a key read in one mode and inert in the
     other. A set difference can never surface these, because the key is in
     both sets. → `INERT_ON_REFOLD`.
  4. **Nested element schemas** — keys inside `tasks[]`, `decisions[]`,
     `files[]`. A top-level diff cannot see into an array, which is why
     `context_notes` went undocumented for months. → `ELEMENT_KEYS`.

## Warn, never reject

Every finding here is a warning and the fold always proceeds. The instinct is
strict validation with a non-zero exit, and it is wrong for this specific
tool: Bureau ships, agents run cached skill copies at differing versions, and
a rejected fold destroys the entire session's context — the one thing the
command exists to preserve. An incomplete write is recoverable on the next
fold; a refused write is not.

The exception, when one is added, is a payload that would produce a *wrong*
write rather than an incomplete one (a `--slug` flag contradicting a payload
`slug`). Nothing here is in that class.

## Silence on the happy path is load-bearing

A payload matching the documented shape must produce **zero** warnings. A
warning that fires on the everyday path trains readers to ignore the channel,
and the real warnings share it. This is why `INERT_ON_REFOLD` holds only keys
the skill's re-fold guidance already tells agents to omit.
"""
from typing import Any

# Top-level keys `cli.cmd_fold` reads and `fold.fold_dossier` stores.
# `digest_file` is the escape hatch for digests near MAX_DIGEST_LENGTH; it is
# mutually exclusive with `digest`, which is why it appears in the skill's
# field-reference table but not in its JSON example.
FOLD_PERSISTED_KEYS = frozenset({
    "agent",
    "branch",
    "commit",
    "decisions",
    "digest",
    "digest_file",
    "files",
    "last_exchange",
    "memory_queries",
    "mood",
    "name",
    "next_words",
    "pinned_findings",
    "project",
    "slug",
    "tasks",
})

# Documented and sent by agents, but with nowhere to land: no column or table
# exists for them, so `fold_dossier` would drop them. Keeping them *distinct*
# from unrecognized keys is what lets the warning tell an agent the difference
# between "you sent something meaningless" and "you sent something this
# version cannot store yet".
#
# **Empty since the v5 migration**, which was scoped by exactly this set: the
# five fields it used to hold (`last_exchange`, `memory_queries`, `mood`,
# `next_words`, `pinned_findings`) now have storage. It stays declared, and
# tested, because the next field documented ahead of its schema belongs here
# rather than in a silence.
FOLD_PENDING_KEYS: frozenset[str] = frozenset()

# The full documented contract: everything an agent may legitimately send.
FOLD_DOCUMENTED_KEYS = FOLD_PERSISTED_KEYS | FOLD_PENDING_KEYS

# Element schemas for the array-valued persisted keys (surface 4). Every
# persisted array belongs here: a key whose *elements* nobody diffs is how
# `context_notes` stayed undocumented for months.
#
# `pinned_findings` splits into two halves that are worth telling apart. The
# semantic four (`finding`, `dead_end`, `why_abandoned`, `retry`) are hashed
# into the finding's identity; `kind` and `supersedes` describe the row's
# lifecycle and are deliberately excluded from that hash. Both halves are
# accepted here, because both are things an agent legitimately sends.
ELEMENT_KEYS = {
    "tasks": frozenset({
        "blocked_by", "context_notes", "description", "owner", "status", "subject",
    }),
    "decisions": frozenset({"alternatives", "decided_by", "what", "why"}),
    "files": frozenset({"action", "annotation", "path"}),
    "pinned_findings": frozenset({
        "dead_end", "finding", "kind", "retry", "supersedes", "why_abandoned",
    }),
    "memory_queries": frozenset({"query", "result_summary", "tool", "used_for"}),
}

# Keys a re-fold reads from the payload and then ignores (surface 3).
#
#   - `tasks`: task state is managed through `tasks add`/`claim`/`complete`
#     during the session, so a re-fold's array would fight the live table.
#   - `name`: renaming is deliberately not a fold operation — the slug is
#     hashed into `registrations.agent_id`, so the name/slug pair is immutable
#     storage identity. Renaming needs a nullable alias column, not a fold.
#
# Both are already absent from the skill's re-fold guidance, which is what
# keeps this warning off the happy path.
INERT_ON_REFOLD = frozenset({"name", "tasks"})


def _fmt(keys: set[str]) -> str:
    """Render a key set as a stable, comma-separated list."""
    return ", ".join(sorted(keys))


def _check_elements(payload: dict[str, Any], skip: set[str]) -> list[str]:
    """Return warnings for unrecognized keys inside the array-valued keys.

    Args:
        payload: the parsed fold payload.
        skip: array keys to leave alone, because the fold ignores them
            wholesale in this mode. Complaining about the contents of
            something already reported as ignored is noise.

    Malformed shapes (a non-list array key, a non-object element) are passed
    over rather than reported: they are type errors, not contract questions,
    and `fold_dossier` surfaces them on its own terms.
    """
    warnings: list[str] = []
    for key, accepted in ELEMENT_KEYS.items():
        if key in skip:
            continue
        elements = payload.get(key)
        if not isinstance(elements, list):
            continue
        for index, element in enumerate(elements):
            if not isinstance(element, dict):
                continue
            unknown = set(element) - accepted
            if unknown:
                warnings.append(
                    f"ignoring unrecognized key(s) in {key}[{index}]: {_fmt(unknown)}"
                )
    return warnings


def check_fold_payload(payload: dict[str, Any], *, is_refold: bool) -> list[str]:
    """Return human-readable warnings for a fold payload. Never raises.

    Reports three distinct conditions, each phrased so an agent can tell them
    apart and act differently:

      1. **Unrecognized** — the key means nothing to any version of the CLI;
         most likely a typo or an invented field.
      2. **Not yet persisted** — documented and legitimate, but this version
         has nowhere to store it (`FOLD_PENDING_KEYS`).
      3. **Ignored in this mode** — read on a new fold, inert on a re-fold
         (`INERT_ON_REFOLD`).

    plus unrecognized keys inside `tasks[]`/`decisions[]`/`files[]`.

    Args:
        payload: the parsed JSON fold payload.
        is_refold: whether this fold appends to an existing dossier. Passed in
            rather than re-derived from ``payload["slug"]`` so the caller stays
            the single authority on mode.

    Returns:
        Warning strings without a severity prefix; the caller formats and
        routes them. Empty for a payload matching the documented shape.
    """
    keys = set(payload)
    warnings: list[str] = []

    unrecognized = keys - FOLD_DOCUMENTED_KEYS
    if unrecognized:
        warnings.append(f"ignoring unrecognized payload key(s): {_fmt(unrecognized)}")

    pending = keys & FOLD_PENDING_KEYS
    if pending:
        warnings.append(
            "payload key(s) not yet persisted by this CLI version "
            f"(the values sent will be dropped): {_fmt(pending)}"
        )

    inert = (keys & INERT_ON_REFOLD) if is_refold else set()
    if inert:
        warnings.append(f"payload key(s) ignored on re-fold: {_fmt(inert)}")

    warnings.extend(_check_elements(payload, skip=inert))
    return warnings
