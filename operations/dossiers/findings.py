"""Pinned-finding identity: the frozen canonicalization and hash contract.

# Design rationale

A pinned finding's primary key, dedupe key, and agent-facing handle are all
one value: the SHA-256 of its canonicalized semantic content, stored as the
full hex digest and rendered as an 8-hex prefix (the git object model, applied
to one-line facts). This module owns that computation and nothing else — it
imports no database and knows no SQL, so the identity rule can never quietly
acquire a dependency on storage state.

## This function is a frozen contract, not a helper

**Changing `canonical_element` is a re-hash migration, never an edit.** The
serialization *is* the identity: if two versions of it ever coexist across a
dossier's history, the table silently forks — content pinned under v1, re-sent
byte-identically under v2, hashes differently, and dedupe, revival detection,
and consolidation-by-id all stop working for cross-era pairs. Every one of
those failures is invisible at the call site.

That hazard is exactly why this looks like ordinary refactorable code and is
not: a well-meaning cleanup that sorts keys differently or tidies the
whitespace handling passes every behavioural test except identity stability,
and identity stability is the whole point. `tests/test_findings.py` therefore
pins literal input -> expected-hash vectors, computed from the spec rather
than from this implementation.

## The spec, one step per variation class

  1. Keep the semantic fields only. Provenance (which session learned the
     fact) is not part of what the fact *is*, so two sessions discovering one
     fact mint one identity. Lifecycle keys (`kind`, `supersedes`) are
     excluded for the same reason: they describe the row's relationships, not
     its content.
  2. Drop absent, null, a `false` flag, and post-normalization-empty strings
     alike. All four are the same statement — "this field says nothing" — and
     serializers pick between them arbitrarily, so an agent that spells out
     `"dead_end": false` or `"retry": ""` must not mint an identity different
     from one that omits the key. Emptiness is judged *after* step 4, so a
     whitespace-only value collapses to empty and drops too — a kept empty
     field would be invisible in the render (continuation lines are emitted
     only for non-empty values) and fork identity on copy-back.
  3. NFC-normalize strings. `café` composed (one codepoint) versus decomposed
     (`e` + combining accent): identical glyphs, different bytes.
  4. Collapse whitespace runs, strip the ends. Padding and line-wrap
     artifacts — and this is the step that makes the render copy-safe, since
     a quoted-back line that got re-wrapped still hashes the same.
  5. Serialize as canonical JSON with sorted keys and no separator padding.
  6. UTF-8 encode, SHA-256, hex.

## What is deliberately NOT normalized

No case folding, no punctuation or markdown stripping. Those characters can be
content (`*.pyc`, `--full`, `SIGKILL` != `sigkill`). The governing asymmetry:
a benign duplicate is *visible* and one consolidating fold retires it, while a
wrong merge of two distinct findings is *invisible* and unrecoverable. When in
doubt, under-normalize. Step 2's drops are the only sanctioned merges, and
each merges two spellings of "this field says nothing" — never two contents.
"""
import hashlib
import json
import re
import unicodedata
from collections.abc import Sequence
from typing import Any

# Step 1's field list. Sorted here only for reading; step 5 sorts the keys
# that actually reach the digest.
SEMANTIC_FIELDS = ("dead_end", "finding", "retry", "why_abandoned")

# How much of the digest is rendered and accepted as a handle. At dossier
# scale (tens of findings) an 8-hex collision runs about 1e-6; storage keeps
# the full hash, and an ambiguous prefix is resolved by asking the agent for a
# longer one rather than by guessing.
HASH_PREFIX_LENGTH = 8

# The three lifecycle roles a row can play. `retraction` is the only one the
# liveness filter special-cases: a tombstone's text is the *reason* a finding
# stopped being true, so it must not render as a live constraint itself.
FINDING_KINDS = ("finding", "dead_end", "retraction")

_WHITESPACE_RUN = re.compile(r"\s+")


def _normalize_value(value: Any) -> Any:
    """Apply steps 3-4 to a string; pass any other scalar through untouched."""
    if not isinstance(value, str):
        return value
    return _WHITESPACE_RUN.sub(" ", unicodedata.normalize("NFC", value)).strip()


def _carries_meaning(value: Any) -> bool:
    """Return False for the pre-normalization spellings of "says nothing".

    `is not False` rather than a truthiness test so `dead_end: True` survives.
    Emptiness is NOT judged here: a whitespace-only string only becomes empty
    after step 4 collapses it, so `canonical_element` re-checks post-normalize.
    """
    return value is not None and value is not False


def canonical_element(element: dict[str, Any]) -> dict[str, Any]:
    """Return the semantic tuple of a payload element (spec steps 1-4).

    Callers must reject non-string values for the text fields *before* calling
    this: it hashes whatever it is given, so a numeric `finding` would hash as
    a number while storing as TEXT, giving one value two identities.
    `fold._store_pinned_findings` is that gate.

    Args:
        element: a raw `pinned_findings[]` payload object. Unknown keys are
            ignored rather than rejected — an agent running a newer skill may
            send fields this version has no opinion about, and identity must
            not depend on that.

    Returns:
        A dict holding only the semantic fields that carry meaning (step 2:
        absent, null, `false`, and post-normalization-empty values all drop),
        with every string NFC-normalized and whitespace-collapsed. This is
        also what gets *stored*, so the rendered line is single-line by
        construction and a quoted-back copy re-canonicalizes to the same
        bytes — which is why emptiness must drop: an empty field emits no
        continuation line, so a kept one could never survive the round trip.
    """
    normalized = {
        field: _normalize_value(element[field])
        for field in SEMANTIC_FIELDS
        if _carries_meaning(element.get(field))
    }
    # step 2's post-normalization half: whitespace-only became "" in step 4
    return {field: value for field, value in normalized.items() if value != ""}


def canonical_json(element: dict[str, Any]) -> str:
    """Return the canonical JSON serialization of an element (steps 1-5).

    Sorted keys and no separator whitespace, so key order and JSON-library
    formatting differences cannot reach the digest. `ensure_ascii=False`
    because step 6 hashes UTF-8 bytes: escaping non-ASCII here would hash the
    escape sequence instead of the character NFC just normalized.
    """
    return json.dumps(
        canonical_element(element),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def finding_hash(element: dict[str, Any]) -> str:
    """Return a finding's identity: SHA-256 of its canonical JSON, as hex."""
    return hashlib.sha256(canonical_json(element).encode("utf-8")).hexdigest()


def short_hash(digest: str) -> str:
    """Return the rendered handle for a full digest."""
    return digest[:HASH_PREFIX_LENGTH]


# ── Render grammar (the other half of the round trip) ───────────────────
# The renderer lives beside the hash on purpose: these lines are the one part
# of the CLI's output an agent may quote *back* into a fold payload, so the
# grammar below and `canonical_element` above are two halves of one contract.
# Both `unfold` and `context` render through this, so a worker and an
# orchestrator read findings in exactly the same shape.

FINDINGS_HEADING = "## Pinned findings"

# Continuation lines are indented by exactly this, and each is `key: value`.
CONTINUATION_INDENT = "    "
_CONTINUATION_FIELDS = (("why abandoned", "why_abandoned"), ("retry", "retry"))

# THE CLOSED VOCABULARY. Only these exact strings may appear as bracketed
# tokens on a finding's main line, which is what lets an extractor treat every
# *other* bracket as text. Adding a token is a grammar change: every reader
# that parses these lines has to learn it first.
_SUPERSEDED_TOKEN = "[superseded]"
_RETRACTION_TOKEN = "[retraction]"
_DEAD_END_TOKEN = "[dead end]"
# retry prefix -> token. The token carries the *class* of the retry rule
# because a condition is free text and free text cannot live inside a
# delimiter; the exact value follows on its own continuation line.
_DEAD_END_CLASSES = (
    ("DO NOT RETRY", "[dead end: DO NOT RETRY]"),
    ("CONDITIONAL", "[dead end: CONDITIONAL]"),
)
FINDING_LINE_TOKENS = (
    _SUPERSEDED_TOKEN,
    _RETRACTION_TOKEN,
    _DEAD_END_TOKEN,
    *(token for _, token in _DEAD_END_CLASSES),
)


def _dead_end_token(retry: str | None) -> str:
    """Return the closed-vocabulary token summarizing a dead end's retry rule."""
    for prefix, token in _DEAD_END_CLASSES:
        if retry and retry.startswith(prefix):
            return token
    return _DEAD_END_TOKEN


def _line_tokens(row: Any) -> list[str]:
    """Return a finding row's main-line tokens, in their fixed order."""
    tokens = []
    if not row["is_live"] and row["kind"] != "retraction":
        tokens.append(_SUPERSEDED_TOKEN)
    if row["kind"] == "retraction":
        tokens.append(_RETRACTION_TOKEN)
    elif row["kind"] == "dead_end":
        tokens.append(_dead_end_token(row["retry"]))
    return tokens


def render_findings(rows: Sequence[Any]) -> list[str]:
    """Render pinned findings as plain fixed-position lines.

    ## The grammar

        - <8-hex id> [<closed-vocabulary token>]... <verbatim text to EOL>
            why abandoned: <verbatim to EOL>
            retry: <verbatim to EOL>

    Extraction is positional: read the id, greedily consume *exact* tokens
    from `FINDING_LINE_TOKENS`, and everything left on the line is the text.
    Continuation lines are indented and keyed, and each value runs to
    end-of-line. **EOL is a sound terminator because step 4 of
    canonicalization collapses whitespace runs**, so no stored field can
    contain a newline — there is nothing for a value to run past.

    ## Why free text is not allowed inline

    An earlier shape put `[why abandoned: ...]` on the main line and broke on
    the first `]` inside the value — and `[inferred] concurrent writes
    corrupted data` is a value the fold skill's own example documents. A
    delimiter can only be trusted around a value drawn from a closed set;
    everything else has to be terminated by something the value cannot
    contain.

    ## Why plain, and not markdown

    Dedupe holds only if quoted-back text re-enters byte-identical after
    normalization. A prettier line — bold labels, italic text, a backticked id
    — is unfixable by construction: an agent quoting `_qdrant must be up_`
    plausibly scrapes the underscores, the hash differs, and a near-duplicate
    row is born. Normalization cannot rescue it either, because `*` and `_`
    can be *content* (`*.pyc`), and a stripper aggressive enough to remove
    decoration would merge distinct findings. So the render adds no characters
    that need removing, including markdown escapes.

    ## Known residual bound (accepted, not a bug to fix)

    Text that begins byte-for-byte with an exact vocabulary token — a finding
    whose first characters really are `[superseded] ` — is parsed as that
    token and loses the prefix. Closing it would need a delimiter that content
    can never contain, and there is no such delimiter. The failure is in the
    benign direction: the re-hash differs, so the copy-back lands as a
    *visible duplicate* row, never as a silent merge of two distinct findings.

    Args:
        rows: finding rows carrying `hash`, `kind`, `text`, `why_abandoned`,
            `retry` and an `is_live` flag. The caller decides which rows to
            pass (compact renders the live set; `--full` renders every row and
            the retired ones self-identify through their tokens).

    Returns:
        Section lines including the heading, or an empty list for no rows.
        The health warning is not part of this: it is a property of the whole
        dossier, and only the full render has the count for it.
    """
    if not rows:
        return []

    lines = [FINDINGS_HEADING, ""]
    for row in rows:
        lines.append(
            " ".join(["-", short_hash(row["hash"]), *_line_tokens(row), row["text"]])
        )
        for label, field in _CONTINUATION_FIELDS:
            if row[field]:
                lines.append(f"{CONTINUATION_INDENT}{label}: {row[field]}")
    lines.append("")
    return lines


def finding_kind(element: dict[str, Any]) -> str | None:
    """Return the lifecycle role a payload element asks for, or None if unknown.

    `kind` wins when it names a known role; otherwise the boolean `dead_end`
    flag decides, because that is the spelling the skill has always documented
    for dead ends. Returning None (rather than defaulting) keeps the choice
    between "coerce and warn" and "reject" with the caller: an unrecognized
    role is a contract question, not an identity one, and `kind` never
    participates in the hash.
    """
    kind = element.get("kind")
    if kind in FINDING_KINDS:
        return str(kind)
    if kind is not None:
        return None
    return "dead_end" if element.get("dead_end") else "finding"
