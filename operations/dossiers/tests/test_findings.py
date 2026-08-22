"""Tests for the frozen finding-identity contract.

`findings.canonicalize` is not an ordinary helper: its output *is* the
identity of every row in `pinned_findings`, so a change to it forks the table
(content pinned under the old function, re-sent byte-identically under the
new one, hashing differently). That hazard is invisible to behavioural tests,
which is why the vectors below are literal input -> expected-hash pairs rather
than round-trips through the implementation.

The expected hashes were computed **from the spec, not from the code**:

    printf '%s' '{"finding":"qdrant must be up before searxng"}' | shasum -a 256

so a reader can re-derive any of them at a shell prompt, and a "cleanup" that
quietly changes key order, separators, or whitespace handling fails loudly here
instead of silently minting new identities in live dossiers.
"""
import hashlib
import unicodedata

import pytest

from operations.dossiers.findings import (
    HASH_PREFIX_LENGTH,
    SEMANTIC_FIELDS,
    canonical_element,
    canonical_json,
    finding_hash,
)

# ── Fixed vectors (input -> canonical JSON -> hash) ─────────────────────
# The canonical JSON is asserted alongside the digest so a failure says which
# step drifted rather than only that the number changed.

_VECTORS = [
    pytest.param(
        # the design document's worked element: `retry: null` is dropped, the
        # whitespace run and the newline collapse, the ends strip
        {"finding": "  qdrant   must be up\nbefore searxng ", "retry": None},
        '{"finding":"qdrant must be up before searxng"}',
        "def1254b44af6a2aaad9de8c4f27955b4acd0585aabf8f56cf46ddcccd33154d",
        id="worked-example",
    ),
    pytest.param(
        {
            "finding": "port 8780 is permanently owned by another app",
            "dead_end": True,
            "why_abandoned": "the owning app cannot be uninstalled",
            "retry": "DO NOT RETRY",
        },
        '{"dead_end":true,"finding":"port 8780 is permanently owned by another '
        'app","retry":"DO NOT RETRY","why_abandoned":"the owning app cannot be '
        'uninstalled"}',
        "855c6bd14bb812107ecf0517d79c41cc43abdce1f97bf7f0f5d81beca72eab97",
        id="full-dead-end",
    ),
    pytest.param(
        # decomposed on the way in (`e` + combining acute), composed on the
        # way out: identical glyphs, different bytes, one identity. Spelled
        # with escapes because the two forms are indistinguishable on screen.
        {"finding": "cafe\u0301 must survive NFC"},
        '{"finding":"caf\u00e9 must survive NFC"}',
        "2753931c56a635711fb1b4e936d03658f6d84a4c49737c1d321fcd0589684846",
        id="decomposed-unicode",
    ),
]


@pytest.mark.parametrize(("element", "expected_json", "expected_hash"), _VECTORS)
def test_canonical_json_matches_the_frozen_vector(
    element: dict, expected_json: str, expected_hash: str
):
    assert canonical_json(element) == expected_json


@pytest.mark.parametrize(("element", "expected_json", "expected_hash"), _VECTORS)
def test_hash_matches_the_frozen_vector(
    element: dict, expected_json: str, expected_hash: str
):
    assert finding_hash(element) == expected_hash


@pytest.mark.parametrize(("element", "expected_json", "expected_hash"), _VECTORS)
def test_hash_is_sha256_of_the_canonical_utf8_bytes(
    element: dict, expected_json: str, expected_hash: str
):
    """Step 6 pinned independently: no salt, no re-encoding, no truncation."""
    assert finding_hash(element) == hashlib.sha256(
        expected_json.encode("utf-8")
    ).hexdigest()


# ── Each normalization step kills exactly one variation class ───────────


def test_absent_and_null_hash_identically():
    """Serializers disagree constantly on omit-vs-null; identity must not."""
    assert finding_hash({"finding": "x", "retry": None}) == finding_hash({"finding": "x"})


def test_composed_and_decomposed_unicode_hash_identically():
    composed = "café is up"
    decomposed = unicodedata.normalize("NFD", composed)

    assert decomposed != composed  # the vectors would be vacuous otherwise
    assert finding_hash({"finding": decomposed}) == finding_hash({"finding": composed})


@pytest.mark.parametrize(
    "variant",
    [
        "qdrant   must be up",
        "qdrant\tmust be up",
        "qdrant\nmust be up",
        "  qdrant must be up  ",
        "qdrant must be up\n",
    ],
    ids=["run", "tab", "newline", "padded", "trailing-newline"],
)
def test_whitespace_variants_hash_identically(variant: str):
    """Line-wrap and padding artifacts are what make D9's render copy-safe."""
    assert finding_hash({"finding": variant}) == finding_hash({"finding": "qdrant must be up"})


def test_key_order_does_not_affect_the_hash():
    a = {"finding": "x", "retry": "DO NOT RETRY", "dead_end": True}
    b = {"dead_end": True, "retry": "DO NOT RETRY", "finding": "x"}

    assert finding_hash(a) == finding_hash(b)


def test_provenance_and_lifecycle_keys_are_excluded_from_identity():
    """Where a fact was learned is not part of what the fact is."""
    bare = {"finding": "x"}
    decorated = {
        "finding": "x",
        "source_session": "current",
        "kind": "finding",
        "supersedes": ["a3f91c2e"],
    }

    assert finding_hash(decorated) == finding_hash(bare)


# ── Deliberately NOT normalized (D5's under-normalize bias) ─────────────


def test_case_is_content():
    assert finding_hash({"finding": "SIGKILL"}) != finding_hash({"finding": "sigkill"})


def test_punctuation_is_content():
    """`*.pyc` carries an asterisk that a markdown stripper would eat."""
    assert finding_hash({"finding": "the rewriter skips *.pyc fixup"}) != finding_hash(
        {"finding": "the rewriter skips .pyc fixup"}
    )


def test_a_richer_resend_is_new_content_not_a_duplicate():
    """The r2-F7 defect class: a stronger `retry` must not hash as a duplicate."""
    weak = {"finding": "x", "dead_end": True, "retry": "CONDITIONAL: port frees up"}
    strong = {"finding": "x", "dead_end": True, "retry": "DO NOT RETRY"}

    assert finding_hash(weak) != finding_hash(strong)


def test_a_false_flag_hashes_as_absence():
    """`false`, `null` and omitted are three spellings of the same statement.

    Keeping `false` would fork identity on a serializer's habit: one agent
    spells out `"dead_end": false`, another omits the key, and the same
    finding lands twice.
    """
    assert finding_hash({"finding": "x", "dead_end": False}) == finding_hash(
        {"finding": "x"}
    )


def test_an_empty_string_hashes_as_absence():
    """A field that says nothing must not mint an identity (A2 delta 2).

    The render emits continuation lines only for non-empty values, so a kept
    `retry: ""` would render invisibly and fork on copy-back — the exact
    round-trip failure D9 exists to prevent. `{"retry": ""}` and `{}` are two
    spellings of one statement, so merging them merges nothing distinct.
    """
    assert finding_hash({"finding": "x", "retry": ""}) == finding_hash({"finding": "x"})


def test_a_whitespace_only_string_hashes_as_absence():
    """Step 4 collapses `"   "` to `""`, so the emptiness check runs after it."""
    assert finding_hash({"finding": "x", "retry": "   "}) == finding_hash(
        {"finding": "x"}
    )


def test_a_non_empty_string_still_carries_meaning():
    """The boundary: emptiness is absence, but one character is content."""
    assert finding_hash({"finding": "x", "retry": "?"}) != finding_hash({"finding": "x"})


# ── Surface shape ───────────────────────────────────────────────────────


def test_canonical_element_returns_only_normalized_semantic_fields():
    element = canonical_element(
        {"finding": "  a   b ", "kind": "retraction", "retry": None}
    )

    assert element == {"finding": "a b"}


def test_semantic_fields_are_the_four_the_spec_names():
    assert set(SEMANTIC_FIELDS) == {"finding", "dead_end", "why_abandoned", "retry"}


def test_rendered_prefix_length_is_eight_hex():
    assert HASH_PREFIX_LENGTH == 8


def test_hash_is_a_full_sha256_hex_digest():
    digest = finding_hash({"finding": "x"})

    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")
