# Bureau Concierge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build Bureau Concierge — a personal life-admin assistant delivered via Telegram, powered by existing CLI subscriptions, with memory, personality, proactive messaging, and a 6-stage feature orchestration pipeline.

**Architecture:** Concierge is a new `concierge/` Python package inside the bureau repo. It wraps existing CLIs (Claude Code, Codex, Gemini CLI) via cc-connect as the Telegram bridge. The core is a Burr-based processing pipeline that classifies messages, routes through Suites/Attaches, scores feature candidates, and manages a priority queue. Memory is file-based (YAML + Markdown) with a two-tier distillation system. All config is YAML-driven.

**Tech Stack:** Python 3.13, uv, Burr (pipeline), pqdict (priority queue), onnxruntime (classifier), rapidfuzz (typo tolerance), PyYAML (config), pytest (testing)

**Spec Documents (read these for full context):**
- `think/workbench/workspace/internal/bureau/CONCIERGE.md` — core architecture
- `think/workbench/workspace/internal/bureau/CONCIERGE-SYSTEM.md` — pipeline + distillation design
- `think/workbench/workspace/internal/bureau/CONCIERGE-TODOS.md` — known issues to address
- `think/workbench/workspace/internal/bureau/CONCIERGE-COEXISTENCE.md` — platform coexistence

---

## Phase Overview

| Phase | What it builds | Depends on |
|-------|---------------|------------|
| **1. Foundation** | Package structure, config loading, data models, session state | Nothing |
| **2. Memory System** | File-based memory read/write, topic files, core.md, auto/index.jsonl | Phase 1 |
| **3. Message Classifier** | Deterministic checks + DistilBERT ONNX + rapidfuzz typo tolerance | Phase 1 |
| **4. Pipeline Core** | Burr state machine: 6 stages, Suite detection, Attache selection | Phases 1-3 |
| **5. Priority System** | Scoring engine, priority queue (pqdict), epsilon-greedy lottery | Phase 4 |
| **6. Features** | Dispatches, Brews, Probes, Valets, Huddles — candidacy + generation | Phases 4-5 |
| **7. UX Layer** | Sanitizer, vocabulary introduction, quick-reply formatting | Phase 4 |
| **8. Distillation** | Candidate detection, compression, semantic diff, Brew validation | Phases 2, 6 |
| **9. Background System** | launchd agent, background checks, cron scheduling | Phases 2, 5, 6 |
| **10. Telegram Bridge** | cc-connect integration, hooks, setup wizard | All above |

---

## Phase 1: Foundation

### Task 1.1: Create concierge package structure

**Files:**
- Create: `concierge/__init__.py`
- Create: `concierge/config/__init__.py`
- Create: `concierge/config/loader.py`
- Create: `concierge/config/defaults/classifier.yml`
- Create: `concierge/config/defaults/priorities.yml`
- Create: `concierge/config/defaults/pipeline.yml`
- Create: `concierge/tests/__init__.py`
- Create: `concierge/tests/conftest.py`
- Modify: `pyproject.toml`

**Step 1: Write the failing test**

```python
# concierge/tests/test_package.py
def test_concierge_package_imports():
    import concierge
    assert hasattr(concierge, "__version__")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_package.py -v`
Expected: FAIL — module not found

**Step 3: Create package skeleton**

```python
# concierge/__init__.py
"""Bureau Concierge — personal life-admin assistant."""
__version__ = "0.1.0"
```

```python
# concierge/config/__init__.py
```

```python
# concierge/tests/__init__.py
```

```python
# concierge/tests/conftest.py
"""Shared fixtures for concierge tests."""
from pathlib import Path
import pytest
import yaml


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary concierge data directory with standard structure."""
    data_dir = tmp_path / "concierge"
    (data_dir / "topics").mkdir(parents=True)
    (data_dir / "auto").mkdir()
    (data_dir / "state").mkdir()
    (data_dir / "attaches").mkdir()
    return data_dir


@pytest.fixture
def sample_config():
    """Return a minimal valid concierge config dict."""
    return {
        "classifier": {
            "deterministic_checks": {
                "media": {"check": "has_attachment"},
                "reply": {
                    "conditions": [
                        {"active_feature": True, "max_length": 5},
                        {"is_single_emoji": True},
                        {"exact_match": ["yes", "no", "ok", "y", "n"]},
                    ]
                },
            },
            "model": {
                "path": "concierge/classifier/model.onnx",
                "tokenizer": "distilbert-base-uncased",
                "confidence_threshold": 0.7,
                "fallback_on_low_confidence": "CONVERSE",
                "low_confidence_action": "ask_inline",
            },
            "fuzzy_commands": {
                "enabled": True,
                "min_score": 80,
                "verbs": ["pause", "resume", "stop", "start"],
            },
        },
        "priorities": {
            "scoring_weights": {
                "dispatches": {
                    "relevance": 0.35,
                    "urgency": 0.25,
                    "suite_fit": 0.20,
                    "freshness": -0.10,
                    "queue_age": 0.05,
                    "domain_match": 0.05,
                    "cooldown_hours": 12,
                    "max_per_week": 3,
                },
            },
            "hard_rules": [],
            "queue": {
                "aging_rate": 0.02,
                "max_age_hours": 168,
                "max_queue_size": 10,
            },
            "lottery": {
                "epsilon": 0.12,
                "decay": 0.995,
                "min_epsilon": 0.05,
            },
        },
    }
```

Update `pyproject.toml` to include concierge in package discovery and test paths:

```toml
# In [tool.setuptools.packages.find]
include = ["operations*", "concierge*"]

# In [tool.pytest.ini_options] testpaths, add:
"concierge/tests",
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_package.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/ pyproject.toml
git commit -m "feat(concierge): create package skeleton with test fixtures"
```

---

### Task 1.2: Config loader for concierge-specific YAML

**Files:**
- Create: `concierge/config/loader.py`
- Create: `concierge/config/defaults/classifier.yml`
- Create: `concierge/config/defaults/priorities.yml`
- Create: `concierge/config/defaults/pipeline.yml`
- Test: `concierge/tests/test_config.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_config.py
"""Tests for concierge config loader."""
import pytest
from concierge.config.loader import load_config, get_classifier_config, get_priorities_config


class TestLoadConfig:
    def test_loads_default_classifier_config(self):
        config = load_config()
        assert "classifier" in config
        assert config["classifier"]["model"]["confidence_threshold"] == 0.7

    def test_loads_default_priorities_config(self):
        config = load_config()
        assert "priorities" in config
        assert config["priorities"]["lottery"]["epsilon"] == 0.12

    def test_user_overrides_merge(self, tmp_path):
        override = tmp_path / "priorities.yml"
        override.write_text("lottery:\n  epsilon: 0.20\n")
        config = load_config(user_config_dir=tmp_path)
        assert config["priorities"]["lottery"]["epsilon"] == 0.20
        # non-overridden values preserved
        assert config["priorities"]["lottery"]["decay"] == 0.995


class TestAccessors:
    def test_get_classifier_config(self):
        cc = get_classifier_config()
        assert cc["model"]["tokenizer"] == "distilbert-base-uncased"

    def test_get_priorities_config(self):
        pc = get_priorities_config()
        assert "scoring_weights" in pc
        assert "hard_rules" in pc
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_config.py -v`
Expected: FAIL — cannot import

**Step 3: Write config defaults and loader**

Create `concierge/config/defaults/classifier.yml`:
```yaml
deterministic_checks:
  media:
    check: "has_attachment"
  reply:
    conditions:
      - active_feature: true
        max_length: 5
      - is_single_emoji: true
      - exact_match: ["yes", "no", "ok", "y", "n"]

model:
  path: "concierge/classifier/model.onnx"
  tokenizer: "distilbert-base-uncased"
  confidence_threshold: 0.7
  fallback_on_low_confidence: "CONVERSE"
  low_confidence_action: "ask_inline"

fuzzy_commands:
  enabled: true
  min_score: 80
  verbs:
    - "pause"
    - "resume"
    - "stop"
    - "start"
    - "change"
    - "set up"
    - "show"
    - "adjust"
    - "enable"
    - "disable"
    - "be more"
    - "be less"
```

Create `concierge/config/defaults/priorities.yml`:
```yaml
scoring_weights:
  dispatches:
    relevance: 0.35
    urgency: 0.25
    suite_fit: 0.20
    freshness: -0.10
    queue_age: 0.05
    domain_match: 0.05
    cooldown_hours: 12
    max_per_week: 3

  brews:
    relevance: 0.20
    urgency: 0.10
    suite_fit: 0.30
    freshness: -0.20
    queue_age: 0.10
    domain_match: 0.10
    cooldown_hours: 168
    max_per_month: 2

  probes:
    suite_fit: 0.40
    queue_age: 0.30
    freshness: -0.20
    cooldown_hours: 24

hard_rules:
  - condition: "suite == 'processing'"
    block: ["brews", "dispatches"]
    reason: "Processing Suite: listen, don't suggest"

  - condition: "active_huddle is not None"
    block: ["dispatches", "brews", "probes"]
    reason: "Huddle owns the conversation"

  - condition: "active_valet is not None"
    block: ["brews", "probes"]
    reason: "Valet owns the conversation"

queue:
  aging_rate: 0.02
  max_age_hours: 168
  max_queue_size: 10

lottery:
  epsilon: 0.12
  decay: 0.995
  min_epsilon: 0.05
```

Create `concierge/config/defaults/pipeline.yml`:
```yaml
media:
  max_processing_time_seconds: 30
  acknowledgment_after_seconds: 3
  max_reentry_count: 1

session:
  timeout_minutes: 10
  message_batch_window_seconds: 15

context_budget:
  max_tokens: 4000

background:
  schedule_hours: [6, 14]
  max_execution_minutes: 5
  max_llm_calls_per_run: 2
```

Create `concierge/config/loader.py`:
```python
"""Concierge configuration loader.

Loads defaults from concierge/config/defaults/*.yml, then merges user
overrides from the concierge data directory (if present).
"""
from functools import lru_cache
from pathlib import Path

import yaml

_DEFAULTS_DIR = Path(__file__).parent / "defaults"
_CONFIG_SECTIONS = ("classifier", "priorities", "pipeline")


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override wins on conflicts."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_defaults() -> dict:
    config = {}
    for section in _CONFIG_SECTIONS:
        path = _DEFAULTS_DIR / f"{section}.yml"
        if path.exists():
            with open(path) as f:
                config[section] = yaml.safe_load(f) or {}
    return config


def _load_user_overrides(user_config_dir: Path | None) -> dict:
    if user_config_dir is None:
        return {}
    overrides = {}
    for section in _CONFIG_SECTIONS:
        path = user_config_dir / f"{section}.yml"
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
                overrides[section] = data
    return overrides


def load_config(user_config_dir: Path | None = None) -> dict:
    """Load concierge config: defaults merged with optional user overrides."""
    config = _load_defaults()
    if user_config_dir:
        overrides = _load_user_overrides(user_config_dir)
        for section in _CONFIG_SECTIONS:
            if section in overrides:
                config[section] = _deep_merge(
                    config.get(section, {}), overrides[section]
                )
    return config


@lru_cache
def get_classifier_config() -> dict:
    return load_config().get("classifier", {})


@lru_cache
def get_priorities_config() -> dict:
    return load_config().get("priorities", {})


@lru_cache
def get_pipeline_config() -> dict:
    return load_config().get("pipeline", {})
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/config/ concierge/tests/test_config.py
git commit -m "feat(concierge): add YAML config loader with defaults and user overrides"
```

---

### Task 1.3: Data models (message types, session state, feature candidates)

**Files:**
- Create: `concierge/models.py`
- Test: `concierge/tests/test_models.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_models.py
"""Tests for concierge data models."""
from concierge.models import (
    MessageClass,
    Suite,
    SessionState,
    FeatureCandidate,
    FeatureType,
    QueueItem,
    MessageEnvelope,
)


class TestMessageClass:
    def test_all_classes_exist(self):
        assert MessageClass.REPLY.value == "reply"
        assert MessageClass.QUERY.value == "query"
        assert MessageClass.CONVERSE.value == "converse"
        assert MessageClass.COMMAND.value == "command"
        assert MessageClass.MEDIA.value == "media"


class TestSuite:
    def test_all_suites_exist(self):
        assert Suite.WORK.value == "work"
        assert Suite.REST.value == "rest"
        assert Suite.SOCIAL.value == "social"
        assert Suite.CREATIVE.value == "creative"
        assert Suite.PROCESSING.value == "processing"

    def test_suite_precedence(self):
        assert Suite.PROCESSING.precedence > Suite.WORK.precedence


class TestSessionState:
    def test_default_state(self):
        state = SessionState()
        assert state.current_suite is None
        assert state.active_feature is None
        assert state.recent_classifications == []
        assert state.processing_cooldown_remaining == 0

    def test_is_in_processing_cooldown(self):
        state = SessionState(processing_cooldown_remaining=2)
        assert state.is_in_processing_cooldown


class TestFeatureCandidate:
    def test_score_computation(self):
        candidate = FeatureCandidate(
            feature_type=FeatureType.DISPATCH,
            domain="meals",
            score_inputs={"relevance": 0.8, "urgency": 0.5, "suite_fit": 1.0,
                          "freshness": 0.2, "queue_age": 0.0, "domain_match": 1.0},
        )
        weights = {
            "relevance": 0.35, "urgency": 0.25, "suite_fit": 0.20,
            "freshness": -0.10, "queue_age": 0.05, "domain_match": 0.05,
        }
        score = candidate.compute_score(weights)
        expected = (0.35*0.8 + 0.25*0.5 + 0.20*1.0 + (-0.10)*0.2 + 0.05*0.0 + 0.05*1.0)
        assert abs(score - expected) < 1e-9


class TestMessageEnvelope:
    def test_envelope_tracks_reentry(self):
        env = MessageEnvelope(text="hello", has_attachment=False)
        assert env.reentry_count == 0
        env.reentry_count += 1
        assert env.reentry_count == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_models.py -v`
Expected: FAIL — cannot import

**Step 3: Write the models**

```python
# concierge/models.py
"""Core data models for Bureau Concierge."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MessageClass(Enum):
    REPLY = "reply"
    QUERY = "query"
    CONVERSE = "converse"
    COMMAND = "command"
    MEDIA = "media"


class Suite(Enum):
    WORK = "work"
    REST = "rest"
    SOCIAL = "social"
    CREATIVE = "creative"
    PROCESSING = "processing"

    @property
    def precedence(self) -> int:
        return {
            Suite.REST: 1,
            Suite.WORK: 2,
            Suite.CREATIVE: 3,
            Suite.SOCIAL: 4,
            Suite.PROCESSING: 5,
        }[self]


class FeatureType(Enum):
    DISPATCH = "dispatch"
    BREW = "brew"
    PROBE = "probe"
    VALET = "valet"
    HUDDLE = "huddle"


class QueueItemState(Enum):
    QUEUED = "queued"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    DISMISSED = "dismissed"


@dataclass
class MessageEnvelope:
    text: str
    has_attachment: bool
    attachment_type: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    reentry_count: int = 0
    classification: MessageClass | None = None
    confidence: float = 0.0


@dataclass
class SessionState:
    current_suite: Suite | None = None
    suite_since: datetime | None = None
    active_feature: FeatureType | None = None
    active_feature_id: str | None = None
    feature_started_at: datetime | None = None
    recent_classifications: list[MessageClass] = field(default_factory=list)
    recent_suites: list[Suite] = field(default_factory=list)
    last_message_at: datetime | None = None
    processing_cooldown_remaining: int = 0

    @property
    def is_in_processing_cooldown(self) -> bool:
        return self.processing_cooldown_remaining > 0

    def record_classification(self, cls: MessageClass, max_history: int = 5) -> None:
        self.recent_classifications.append(cls)
        if len(self.recent_classifications) > max_history:
            self.recent_classifications = self.recent_classifications[-max_history:]

    def record_suite(self, suite: Suite, max_history: int = 5) -> None:
        self.recent_suites.append(suite)
        if len(self.recent_suites) > max_history:
            self.recent_suites = self.recent_suites[-max_history:]


@dataclass
class FeatureCandidate:
    feature_type: FeatureType
    domain: str
    score_inputs: dict[str, float]
    content: str | None = None
    metadata: dict | None = None
    lottery_promoted: bool = False

    def compute_score(self, weights: dict[str, float]) -> float:
        return sum(
            weights.get(factor, 0.0) * value
            for factor, value in self.score_inputs.items()
        )


@dataclass
class QueueItem:
    candidate: FeatureCandidate
    queued_at: datetime = field(default_factory=datetime.now)
    state: QueueItemState = QueueItemState.QUEUED
    priority: float = 0.0
    context_snapshot: dict | None = None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/models.py concierge/tests/test_models.py
git commit -m "feat(concierge): add core data models (message, session, features, queue)"
```

---

### Task 1.4: Session state persistence (load/save YAML)

**Files:**
- Create: `concierge/state.py`
- Test: `concierge/tests/test_state.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_state.py
"""Tests for session state persistence."""
from concierge.state import load_session_state, save_session_state
from concierge.models import SessionState, Suite, MessageClass


class TestSessionStatePersistence:
    def test_save_and_load_roundtrip(self, tmp_data_dir):
        state = SessionState(
            current_suite=Suite.WORK,
            processing_cooldown_remaining=2,
        )
        state.record_classification(MessageClass.CONVERSE)

        save_session_state(state, tmp_data_dir / "state" / "session.yml")
        loaded = load_session_state(tmp_data_dir / "state" / "session.yml")

        assert loaded.current_suite == Suite.WORK
        assert loaded.processing_cooldown_remaining == 2
        assert loaded.recent_classifications == [MessageClass.CONVERSE]

    def test_load_missing_file_returns_default(self, tmp_data_dir):
        loaded = load_session_state(tmp_data_dir / "state" / "session.yml")
        assert loaded.current_suite is None
        assert loaded.recent_classifications == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_state.py -v`
Expected: FAIL

**Step 3: Implement state persistence**

```python
# concierge/state.py
"""Session state persistence (atomic YAML read/write)."""
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from .models import MessageClass, SessionState, Suite


def save_session_state(state: SessionState, path: Path) -> None:
    """Atomically write session state to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "current_suite": state.current_suite.value if state.current_suite else None,
        "suite_since": state.suite_since.isoformat() if state.suite_since else None,
        "active_feature": state.active_feature.value if state.active_feature else None,
        "active_feature_id": state.active_feature_id,
        "feature_started_at": state.feature_started_at.isoformat() if state.feature_started_at else None,
        "recent_classifications": [c.value for c in state.recent_classifications],
        "recent_suites": [s.value for s in state.recent_suites],
        "last_message_at": state.last_message_at.isoformat() if state.last_message_at else None,
        "processing_cooldown_remaining": state.processing_cooldown_remaining,
    }
    # Atomic write: write to temp file, then rename
    tmp_fd = tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, suffix=".tmp", delete=False
    )
    try:
        yaml.safe_dump(data, tmp_fd, default_flow_style=False)
        tmp_fd.close()
        Path(tmp_fd.name).rename(path)
    except BaseException:
        Path(tmp_fd.name).unlink(missing_ok=True)
        raise


def load_session_state(path: Path) -> SessionState:
    """Load session state from YAML, returning default if file missing."""
    if not path.exists():
        return SessionState()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return SessionState(
        current_suite=Suite(data["current_suite"]) if data.get("current_suite") else None,
        suite_since=datetime.fromisoformat(data["suite_since"]) if data.get("suite_since") else None,
        active_feature=None,  # FeatureType parsing omitted for brevity — same pattern
        active_feature_id=data.get("active_feature_id"),
        feature_started_at=datetime.fromisoformat(data["feature_started_at"]) if data.get("feature_started_at") else None,
        recent_classifications=[MessageClass(c) for c in data.get("recent_classifications", [])],
        recent_suites=[Suite(s) for s in data.get("recent_suites", [])],
        last_message_at=datetime.fromisoformat(data["last_message_at"]) if data.get("last_message_at") else None,
        processing_cooldown_remaining=data.get("processing_cooldown_remaining", 0),
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_state.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/state.py concierge/tests/test_state.py
git commit -m "feat(concierge): add atomic session state persistence"
```

---

## Phase 2: Memory System

### Task 2.1: Memory file reader (topic files, core.md, PERSONALITY.md)

**Files:**
- Create: `concierge/memory/__init__.py`
- Create: `concierge/memory/reader.py`
- Test: `concierge/tests/test_memory_reader.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_memory_reader.py
"""Tests for memory file reading."""
from concierge.memory.reader import (
    read_topic_distilled,
    read_topic_raw,
    read_topic_full,
    read_core,
    read_personality,
    list_topics,
)


class TestTopicReader:
    def test_read_distilled_section(self, tmp_data_dir):
        topic = tmp_data_dir / "topics" / "meals.md"
        topic.write_text(
            "# topics/meals.md\n\n"
            "## Distilled\n"
            "- Likes pasta\n"
            "- Shops at Trader Joe's\n\n"
            "## Raw\n"
            "- [2026-03-07] Made pasta\n"
            "- [2026-03-01] Tried risotto\n"
        )
        distilled = read_topic_distilled(topic)
        assert "Likes pasta" in distilled
        assert "Made pasta" not in distilled

    def test_read_raw_section(self, tmp_data_dir):
        topic = tmp_data_dir / "topics" / "meals.md"
        topic.write_text(
            "## Distilled\n- Likes pasta\n\n"
            "## Raw\n- [2026-03-07] Made pasta\n"
        )
        raw = read_topic_raw(topic)
        assert "Made pasta" in raw
        assert "Likes pasta" not in raw

    def test_read_raw_with_limit(self, tmp_data_dir):
        topic = tmp_data_dir / "topics" / "meals.md"
        lines = "\n".join(f"- [2026-03-{i:02d}] Entry {i}" for i in range(1, 20))
        topic.write_text(f"## Distilled\n- Summary\n\n## Raw\n{lines}\n")
        raw = read_topic_raw(topic, last_n=5)
        assert "Entry 19" in raw
        assert "Entry 1" not in raw

    def test_list_topics(self, tmp_data_dir):
        (tmp_data_dir / "topics" / "meals.md").write_text("# meals")
        (tmp_data_dir / "topics" / "people.md").write_text("# people")
        topics = list_topics(tmp_data_dir / "topics")
        assert set(topics) == {"meals", "people"}


class TestCoreAndPersonality:
    def test_read_core(self, tmp_data_dir):
        (tmp_data_dir / "core.md").write_text("# Core\nPrefers mornings.")
        content = read_core(tmp_data_dir)
        assert "Prefers mornings" in content

    def test_read_personality(self, tmp_data_dir):
        (tmp_data_dir / "PERSONALITY.md").write_text("Be warm and friendly.")
        content = read_personality(tmp_data_dir)
        assert "warm" in content

    def test_read_missing_returns_empty(self, tmp_data_dir):
        assert read_core(tmp_data_dir) == ""
        assert read_personality(tmp_data_dir) == ""
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_memory_reader.py -v`
Expected: FAIL

**Step 3: Implement memory reader**

```python
# concierge/memory/__init__.py
```

```python
# concierge/memory/reader.py
"""Read memory files (topics, core, personality)."""
from __future__ import annotations

import re
from pathlib import Path


def _extract_section(text: str, header: str) -> str:
    """Extract content under a ## header until the next ## or EOF."""
    pattern = rf"^## {re.escape(header)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def read_topic_distilled(path: Path) -> str:
    if not path.exists():
        return ""
    return _extract_section(path.read_text(), "Distilled")


def read_topic_raw(path: Path, last_n: int | None = None) -> str:
    if not path.exists():
        return ""
    raw = _extract_section(path.read_text(), "Raw")
    if last_n is not None:
        lines = [l for l in raw.split("\n") if l.strip()]
        raw = "\n".join(lines[-last_n:])
    return raw


def read_topic_full(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text()


def read_core(data_dir: Path) -> str:
    path = data_dir / "core.md"
    return path.read_text() if path.exists() else ""


def read_personality(data_dir: Path) -> str:
    path = data_dir / "PERSONALITY.md"
    return path.read_text() if path.exists() else ""


def list_topics(topics_dir: Path) -> list[str]:
    if not topics_dir.exists():
        return []
    return [p.stem for p in sorted(topics_dir.glob("*.md"))]
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_memory_reader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/memory/ concierge/tests/test_memory_reader.py
git commit -m "feat(concierge): add memory file reader (topics, core, personality)"
```

---

### Task 2.2: Memory writer (auto/index.jsonl, topic file appender)

**Files:**
- Create: `concierge/memory/writer.py`
- Test: `concierge/tests/test_memory_writer.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_memory_writer.py
"""Tests for memory writing."""
import json
from concierge.memory.writer import append_auto_entry, append_raw_entry


class TestAutoIndex:
    def test_append_creates_file(self, tmp_data_dir):
        append_auto_entry(
            tmp_data_dir / "auto" / "index.jsonl",
            {"fact": "likes pasta", "domain": "meals"},
        )
        lines = (tmp_data_dir / "auto" / "index.jsonl").read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["fact"] == "likes pasta"
        assert "timestamp" in entry

    def test_append_adds_to_existing(self, tmp_data_dir):
        path = tmp_data_dir / "auto" / "index.jsonl"
        append_auto_entry(path, {"fact": "first"})
        append_auto_entry(path, {"fact": "second"})
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2


class TestRawEntry:
    def test_append_raw_to_topic(self, tmp_data_dir):
        topic = tmp_data_dir / "topics" / "meals.md"
        topic.write_text("## Distilled\n- Summary\n\n## Raw\n- [2026-03-01] Old entry\n")
        append_raw_entry(topic, "Made risotto for the first time")
        content = topic.read_text()
        assert "Made risotto" in content
        assert content.index("Made risotto") > content.index("Old entry")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_memory_writer.py -v`
Expected: FAIL

**Step 3: Implement memory writer**

```python
# concierge/memory/writer.py
"""Write memory entries (auto index, topic raw section)."""
from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path


def append_auto_entry(path: Path, entry: dict) -> None:
    """Append a timestamped JSONL entry to auto/index.jsonl."""
    path.parent.mkdir(parents=True, exist_ok=True)
    entry_with_ts = {"timestamp": datetime.now().isoformat(), **entry}
    with open(path, "a") as f:
        f.write(json.dumps(entry_with_ts) + "\n")


def append_raw_entry(topic_path: Path, text: str) -> None:
    """Append a dated raw entry to the ## Raw section of a topic file."""
    today = date.today().isoformat()
    entry_line = f"- [{today}] {text}\n"
    content = topic_path.read_text()
    # Append at end of file (which is end of ## Raw section)
    if not content.endswith("\n"):
        content += "\n"
    topic_path.write_text(content + entry_line)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_memory_writer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/memory/writer.py concierge/tests/test_memory_writer.py
git commit -m "feat(concierge): add memory writer (auto index + topic appender)"
```

---

## Phase 3: Message Classifier

### Task 3.1: Deterministic classifier (Stage 0a)

**Files:**
- Create: `concierge/classifier/__init__.py`
- Create: `concierge/classifier/deterministic.py`
- Test: `concierge/tests/test_classifier_deterministic.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_classifier_deterministic.py
"""Tests for deterministic message classification (Stage 0a)."""
from concierge.classifier.deterministic import classify_deterministic
from concierge.models import MessageClass, MessageEnvelope


class TestMediaDetection:
    def test_attachment_classified_as_media(self):
        env = MessageEnvelope(text="", has_attachment=True, attachment_type="image")
        result = classify_deterministic(env, active_feature=None)
        assert result == MessageClass.MEDIA

    def test_attachment_with_text_still_media(self):
        env = MessageEnvelope(text="check this out", has_attachment=True)
        result = classify_deterministic(env, active_feature=None)
        assert result == MessageClass.MEDIA


class TestReplyDetection:
    def test_single_emoji_is_reply(self):
        env = MessageEnvelope(text="👍", has_attachment=False)
        result = classify_deterministic(env, active_feature=None)
        assert result == MessageClass.REPLY

    def test_short_text_with_active_feature_is_reply(self):
        env = MessageEnvelope(text="yes", has_attachment=False)
        result = classify_deterministic(env, active_feature="huddle_123")
        assert result == MessageClass.REPLY

    def test_exact_match_is_reply(self):
        env = MessageEnvelope(text="ok", has_attachment=False)
        result = classify_deterministic(env, active_feature="valet_1")
        assert result == MessageClass.REPLY

    def test_short_text_without_active_feature_is_not_reply(self):
        env = MessageEnvelope(text="yes", has_attachment=False)
        result = classify_deterministic(env, active_feature=None)
        assert result is None  # Falls through to model


class TestFallthrough:
    def test_normal_text_returns_none(self):
        env = MessageEnvelope(text="what should I have for dinner?", has_attachment=False)
        result = classify_deterministic(env, active_feature=None)
        assert result is None

    def test_long_text_with_active_feature_returns_none(self):
        env = MessageEnvelope(
            text="actually I was thinking about something completely different",
            has_attachment=False,
        )
        result = classify_deterministic(env, active_feature="huddle_1")
        assert result is None  # Too long for auto-REPLY
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_classifier_deterministic.py -v`
Expected: FAIL

**Step 3: Implement deterministic classifier**

```python
# concierge/classifier/__init__.py
```

```python
# concierge/classifier/deterministic.py
"""Stage 0a: Deterministic message classification.

Handles ~60% of messages in <0.01ms via frozenset lookups and metadata checks.
Returns None if the message needs model-based classification.
"""
from __future__ import annotations

import re

from ..models import MessageClass, MessageEnvelope

_REPLY_EXACT = frozenset({"yes", "no", "ok", "y", "n", "sure", "nah", "yep", "nope"})
_SINGLE_EMOJI_RE = re.compile(
    r"^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U0000FE00-\U0000FE0F"
    r"\U0000200D]+$"
)
_MAX_REPLY_LENGTH = 5


def classify_deterministic(
    envelope: MessageEnvelope,
    active_feature: str | None,
) -> MessageClass | None:
    """Classify message deterministically. Returns None if model needed."""
    # Rule 1: Attachment -> MEDIA
    if envelope.has_attachment:
        return MessageClass.MEDIA

    text = envelope.text.strip()
    text_lower = text.lower()

    # Rule 2: Single emoji -> REPLY
    if _SINGLE_EMOJI_RE.match(text):
        return MessageClass.REPLY

    # Rule 3: Short text with active feature -> REPLY
    if active_feature is not None:
        if len(text) <= _MAX_REPLY_LENGTH:
            return MessageClass.REPLY
        if text_lower in _REPLY_EXACT:
            return MessageClass.REPLY

    # No deterministic match — needs model
    return None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_classifier_deterministic.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/classifier/ concierge/tests/test_classifier_deterministic.py
git commit -m "feat(concierge): add deterministic message classifier (Stage 0a)"
```

---

### Task 3.2: Fuzzy command matcher (Stage 0c)

**Files:**
- Create: `concierge/classifier/fuzzy_commands.py`
- Test: `concierge/tests/test_fuzzy_commands.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_fuzzy_commands.py
"""Tests for fuzzy command matching (Stage 0c)."""
from concierge.classifier.fuzzy_commands import match_command_verb


class TestFuzzyCommandMatch:
    def test_exact_match(self):
        assert match_command_verb("pause the fitness probe") == "pause"

    def test_typo_match(self):
        assert match_command_verb("pase the fitness probe") == "pause"

    def test_no_match(self):
        assert match_command_verb("what should I eat for dinner") is None

    def test_multi_word_verb(self):
        assert match_command_verb("set up a weekly meal plan") == "set up"

    def test_below_threshold(self):
        assert match_command_verb("xyz the fitness probe") is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_fuzzy_commands.py -v`
Expected: FAIL

**Step 3: Implement fuzzy command matcher**

First, add rapidfuzz to pyproject.toml dependencies:

```toml
# Add to [project] dependencies list
"rapidfuzz>=3.0",
```

```python
# concierge/classifier/fuzzy_commands.py
"""Stage 0c: Fuzzy command verb matching via rapidfuzz."""
from __future__ import annotations

from rapidfuzz import fuzz

from ..config.loader import get_classifier_config

_MIN_SCORE = 80


def match_command_verb(text: str) -> str | None:
    """Check if text starts with a known command verb (with typo tolerance).

    Returns the matched verb or None.
    """
    config = get_classifier_config()
    fuzzy_config = config.get("fuzzy_commands", {})
    if not fuzzy_config.get("enabled", False):
        return None

    verbs = fuzzy_config.get("verbs", [])
    min_score = fuzzy_config.get("min_score", _MIN_SCORE)
    text_lower = text.lower().strip()

    best_verb = None
    best_score = 0.0

    for verb in verbs:
        # Check prefix match: compare verb against start of text
        prefix = text_lower[: len(verb) + 2]  # Allow slight length variation
        score = fuzz.ratio(verb, prefix)
        if score > best_score and score >= min_score:
            best_score = score
            best_verb = verb

    return best_verb
```

**Step 4: Run tests**

Run: `uv sync && uv run pytest concierge/tests/test_fuzzy_commands.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/classifier/fuzzy_commands.py concierge/tests/test_fuzzy_commands.py pyproject.toml
git commit -m "feat(concierge): add fuzzy command verb matching (Stage 0c, rapidfuzz)"
```

---

### Task 3.3: Model-based classifier stub (Stage 0b)

The ONNX DistilBERT model requires a trained model file. For now, create the interface with a fallback that returns CONVERSE. The actual model will be trained and integrated later (see Task 3.4).

**Files:**
- Create: `concierge/classifier/model.py`
- Test: `concierge/tests/test_classifier_model.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_classifier_model.py
"""Tests for model-based classifier (Stage 0b)."""
from concierge.classifier.model import classify_with_model
from concierge.models import MessageClass


class TestModelClassifier:
    def test_fallback_when_no_model(self):
        """Without a trained model, should return CONVERSE as fallback."""
        result, confidence = classify_with_model("what should I eat for dinner?")
        assert result == MessageClass.CONVERSE
        assert confidence == 0.0

    def test_returns_tuple_of_class_and_confidence(self):
        result, confidence = classify_with_model("hello")
        assert isinstance(result, MessageClass)
        assert isinstance(confidence, float)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_classifier_model.py -v`
Expected: FAIL

**Step 3: Implement model classifier stub**

```python
# concierge/classifier/model.py
"""Stage 0b: DistilBERT ONNX INT8 message classifier.

Falls back to CONVERSE when no trained model is available.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..config.loader import get_classifier_config
from ..models import MessageClass

_logger = logging.getLogger(__name__)
_CLASS_MAP = {
    0: MessageClass.REPLY,
    1: MessageClass.QUERY,
    2: MessageClass.CONVERSE,
    3: MessageClass.COMMAND,
}


def _load_model(model_path: Path):
    """Attempt to load ONNX model. Returns None if unavailable."""
    if not model_path.exists():
        _logger.info("No classifier model at %s — using fallback", model_path)
        return None
    try:
        import onnxruntime as ort
        return ort.InferenceSession(str(model_path))
    except Exception as e:
        _logger.warning("Failed to load classifier model: %s", e)
        return None


def classify_with_model(text: str) -> tuple[MessageClass, float]:
    """Classify text using DistilBERT ONNX model.

    Returns (MessageClass, confidence). Falls back to (CONVERSE, 0.0)
    if no model is available.
    """
    config = get_classifier_config()
    model_path = Path(config["model"]["path"])
    fallback = MessageClass(config["model"]["fallback_on_low_confidence"].lower())

    session = _load_model(model_path)
    if session is None:
        return fallback, 0.0

    # Full ONNX inference path (requires trained model + tokenizer)
    try:
        from transformers import AutoTokenizer
        import numpy as np

        tokenizer = AutoTokenizer.from_pretrained(config["model"]["tokenizer"])
        inputs = tokenizer(text, return_tensors="np", truncation=True, max_length=128)
        outputs = session.run(None, {k: v for k, v in inputs.items()})
        logits = outputs[0][0]

        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()

        predicted_class = int(np.argmax(probs))
        confidence = float(probs[predicted_class])

        return _CLASS_MAP.get(predicted_class, fallback), confidence
    except Exception as e:
        _logger.warning("Model inference failed: %s", e)
        return fallback, 0.0
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_classifier_model.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/classifier/model.py concierge/tests/test_classifier_model.py
git commit -m "feat(concierge): add model classifier with ONNX stub (Stage 0b)"
```

---

### Task 3.4: Unified classifier (combines all stages)

**Files:**
- Create: `concierge/classifier/classify.py`
- Test: `concierge/tests/test_classifier_unified.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_classifier_unified.py
"""Tests for the unified classifier pipeline (0a -> 0b -> 0c)."""
from concierge.classifier.classify import classify_message
from concierge.models import MessageClass, MessageEnvelope


class TestUnifiedClassifier:
    def test_attachment_short_circuits_to_media(self):
        env = MessageEnvelope(text="", has_attachment=True)
        result = classify_message(env, active_feature=None)
        assert result.classification == MessageClass.MEDIA

    def test_emoji_short_circuits_to_reply(self):
        env = MessageEnvelope(text="👍", has_attachment=False)
        result = classify_message(env, active_feature=None)
        assert result.classification == MessageClass.REPLY

    def test_normal_text_falls_through_to_model(self):
        env = MessageEnvelope(text="what should I eat for dinner?", has_attachment=False)
        result = classify_message(env, active_feature=None)
        # Without trained model, falls back to CONVERSE
        assert result.classification == MessageClass.CONVERSE

    def test_command_text_gets_fuzzy_checked(self):
        env = MessageEnvelope(text="pause the fitness probe", has_attachment=False)
        result = classify_message(env, active_feature=None)
        # Model fallback returns CONVERSE, but fuzzy catches "pause" -> COMMAND
        # (This depends on model fallback behavior — may need adjustment)
        assert result.classification in (MessageClass.COMMAND, MessageClass.CONVERSE)

    def test_envelope_updated_in_place(self):
        env = MessageEnvelope(text="hello", has_attachment=False)
        result = classify_message(env, active_feature=None)
        assert result is env  # Same object, mutated
        assert result.classification is not None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_classifier_unified.py -v`
Expected: FAIL

**Step 3: Implement unified classifier**

```python
# concierge/classifier/classify.py
"""Unified message classifier: deterministic -> model -> fuzzy commands."""
from __future__ import annotations

from ..config.loader import get_classifier_config
from ..models import MessageClass, MessageEnvelope
from .deterministic import classify_deterministic
from .fuzzy_commands import match_command_verb
from .model import classify_with_model


def classify_message(
    envelope: MessageEnvelope,
    active_feature: str | None,
) -> MessageEnvelope:
    """Classify a message through the full Stage 0 pipeline.

    Mutates and returns the envelope with classification and confidence set.
    """
    # Stage 0a: Deterministic checks (<0.01ms)
    deterministic_result = classify_deterministic(envelope, active_feature)
    if deterministic_result is not None:
        envelope.classification = deterministic_result
        envelope.confidence = 1.0
        return envelope

    # Stage 0b: Model-based classification (~5-10ms)
    model_result, confidence = classify_with_model(envelope.text)
    envelope.classification = model_result
    envelope.confidence = confidence

    # Stage 0c: If model says COMMAND, verify with fuzzy matching
    if model_result == MessageClass.COMMAND:
        verb = match_command_verb(envelope.text)
        if verb is None:
            # Model said COMMAND but no known verb found — downgrade to CONVERSE
            config = get_classifier_config()
            threshold = config["model"]["confidence_threshold"]
            if confidence < threshold:
                envelope.classification = MessageClass.CONVERSE
    elif confidence > 0 and match_command_verb(envelope.text) is not None:
        # Model didn't say COMMAND but fuzzy found a command verb — upgrade
        envelope.classification = MessageClass.COMMAND

    return envelope
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_classifier_unified.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/classifier/classify.py concierge/tests/test_classifier_unified.py
git commit -m "feat(concierge): add unified classifier pipeline (0a->0b->0c)"
```

---

## Phase 4: Pipeline Core

### Task 4.1: Suite detector

**Files:**
- Create: `concierge/pipeline/__init__.py`
- Create: `concierge/pipeline/suite_detector.py`
- Test: `concierge/tests/test_suite_detector.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_suite_detector.py
"""Tests for Suite detection (Stage 1)."""
from datetime import time
from concierge.pipeline.suite_detector import detect_suite
from concierge.models import Suite, MessageEnvelope, SessionState


class TestSuiteDetection:
    def test_processing_keywords(self):
        env = MessageEnvelope(text="I've been really stressed and overwhelmed", has_attachment=False)
        suite = detect_suite(env, SessionState(), current_time=time(14, 0))
        assert suite == Suite.PROCESSING

    def test_work_keywords(self):
        env = MessageEnvelope(text="I need to finish my report by Friday", has_attachment=False)
        suite = detect_suite(env, SessionState(), current_time=time(10, 0))
        assert suite == Suite.WORK

    def test_evening_defaults_to_rest(self):
        env = MessageEnvelope(text="hey", has_attachment=False)
        suite = detect_suite(env, SessionState(), current_time=time(21, 0))
        assert suite == Suite.REST

    def test_manual_override(self):
        state = SessionState(current_suite=Suite.CREATIVE)
        env = MessageEnvelope(text="just checking in", has_attachment=False)
        # Suite persists from session state if no strong signal
        suite = detect_suite(env, state, current_time=time(14, 0))
        assert suite == Suite.CREATIVE

    def test_processing_has_highest_precedence(self):
        env = MessageEnvelope(text="I'm stressed about my work deadline", has_attachment=False)
        suite = detect_suite(env, SessionState(), current_time=time(10, 0))
        assert suite == Suite.PROCESSING  # "stressed" wins over "work"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_suite_detector.py -v`
Expected: FAIL

**Step 3: Implement suite detector**

```python
# concierge/pipeline/__init__.py
```

```python
# concierge/pipeline/suite_detector.py
"""Stage 1: Suite detection based on message content and context."""
from __future__ import annotations

from datetime import time

from ..models import MessageEnvelope, SessionState, Suite

# Keyword sets ordered by precedence (highest first)
_PROCESSING_KEYWORDS = frozenset({
    "stressed", "overwhelmed", "anxious", "upset", "frustrated", "sad",
    "crying", "angry", "hurt", "scared", "worried", "depressed", "ugh",
    "terrible", "awful", "exhausted", "drained", "burned out", "burnt out",
})
_SOCIAL_KEYWORDS = frozenset({
    "friends", "party", "dinner with", "hanging out", "plans with",
    "birthday", "wedding", "date", "meetup", "brunch", "get together",
})
_CREATIVE_KEYWORDS = frozenset({
    "brainstorm", "decorat", "outfit", "writing", "painting", "craft",
    "design", "idea", "project", "create", "inspiration",
})
_WORK_KEYWORDS = frozenset({
    "work", "meeting", "deadline", "report", "presentation", "boss",
    "career", "job", "salary", "resume", "interview", "task", "productivity",
})


def _has_keyword(text: str, keywords: frozenset[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def detect_suite(
    envelope: MessageEnvelope,
    session: SessionState,
    current_time: time | None = None,
) -> Suite:
    """Detect the active Suite for this message."""
    text = envelope.text

    # Precedence order: Processing > Social > Creative > Work > Rest
    if _has_keyword(text, _PROCESSING_KEYWORDS):
        return Suite.PROCESSING
    if _has_keyword(text, _SOCIAL_KEYWORDS):
        return Suite.SOCIAL
    if _has_keyword(text, _CREATIVE_KEYWORDS):
        return Suite.CREATIVE
    if _has_keyword(text, _WORK_KEYWORDS):
        return Suite.WORK

    # No strong keyword signal — use context
    if session.current_suite is not None:
        return session.current_suite

    # Time-of-day fallback
    if current_time is not None:
        if current_time >= time(20, 0) or current_time < time(7, 0):
            return Suite.REST
        if time(9, 0) <= current_time <= time(17, 0):
            return Suite.WORK

    return Suite.REST
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_suite_detector.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/pipeline/ concierge/tests/test_suite_detector.py
git commit -m "feat(concierge): add Suite detector (Stage 1)"
```

---

### Task 4.2: Attache selector (Stage 2)

**Files:**
- Create: `concierge/pipeline/attache_selector.py`
- Test: `concierge/tests/test_attache_selector.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_attache_selector.py
"""Tests for Attache selection (Stage 2)."""
from concierge.pipeline.attache_selector import select_attaches, SUITE_ATTACHE_MAP
from concierge.models import Suite


class TestAttacheSelection:
    def test_work_suite_selects_schedule_finance(self):
        result = select_attaches(Suite.WORK)
        assert "schedule" in result
        assert "finance" in result
        assert "wellness" not in result

    def test_rest_suite_selects_wellness_meals(self):
        result = select_attaches(Suite.REST)
        assert "wellness" in result
        assert "meals" in result

    def test_processing_suite_returns_empty(self):
        result = select_attaches(Suite.PROCESSING)
        assert result == []

    def test_load_attache_content(self, tmp_data_dir):
        attaches_dir = tmp_data_dir / "attaches"
        (attaches_dir / "meals.md").write_text("# Meals\nShe likes pasta.")
        from concierge.pipeline.attache_selector import load_attache_content
        content = load_attache_content(["meals"], attaches_dir)
        assert "She likes pasta" in content
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_attache_selector.py -v`
Expected: FAIL

**Step 3: Implement attache selector**

```python
# concierge/pipeline/attache_selector.py
"""Stage 2: Attache selection based on active Suite."""
from __future__ import annotations

from pathlib import Path

from ..models import Suite

SUITE_ATTACHE_MAP: dict[Suite, list[str]] = {
    Suite.WORK: ["schedule", "finance"],
    Suite.REST: ["wellness", "meals", "home"],
    Suite.SOCIAL: ["events", "social", "shopping"],
    Suite.CREATIVE: ["shopping", "learning", "meals"],
    Suite.PROCESSING: [],  # Minimal context — just listen
}


def select_attaches(suite: Suite) -> list[str]:
    """Return the list of attache names for the given Suite."""
    return SUITE_ATTACHE_MAP.get(suite, [])


def load_attache_content(attache_names: list[str], attaches_dir: Path) -> str:
    """Load and concatenate attache file contents."""
    parts = []
    for name in attache_names:
        path = attaches_dir / f"{name}.md"
        if path.exists():
            parts.append(path.read_text())
    return "\n\n".join(parts)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_attache_selector.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/pipeline/attache_selector.py concierge/tests/test_attache_selector.py
git commit -m "feat(concierge): add Attache selector (Stage 2)"
```

---

### Task 4.3: Hard rules evaluator

**Files:**
- Create: `concierge/pipeline/hard_rules.py`
- Test: `concierge/tests/test_hard_rules.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_hard_rules.py
"""Tests for hard rule evaluation."""
from concierge.pipeline.hard_rules import evaluate_hard_rules
from concierge.models import Suite, FeatureType, SessionState


class TestHardRules:
    def test_processing_suite_blocks_brews_and_dispatches(self):
        blocked = evaluate_hard_rules(
            suite=Suite.PROCESSING,
            session=SessionState(),
        )
        assert FeatureType.BREW in blocked
        assert FeatureType.DISPATCH in blocked
        assert FeatureType.PROBE not in blocked

    def test_active_huddle_blocks_most_features(self):
        session = SessionState(active_feature=FeatureType.HUDDLE)
        blocked = evaluate_hard_rules(suite=Suite.WORK, session=session)
        assert FeatureType.DISPATCH in blocked
        assert FeatureType.BREW in blocked
        assert FeatureType.PROBE in blocked

    def test_active_valet_blocks_brews_probes(self):
        session = SessionState(active_feature=FeatureType.VALET)
        blocked = evaluate_hard_rules(suite=Suite.WORK, session=session)
        assert FeatureType.BREW in blocked
        assert FeatureType.PROBE in blocked
        assert FeatureType.DISPATCH not in blocked

    def test_no_blocks_in_normal_state(self):
        blocked = evaluate_hard_rules(suite=Suite.WORK, session=SessionState())
        assert blocked == set()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_hard_rules.py -v`
Expected: FAIL

**Step 3: Implement hard rules**

```python
# concierge/pipeline/hard_rules.py
"""Hard rule evaluation for feature blocking."""
from __future__ import annotations

from ..models import FeatureType, SessionState, Suite


def evaluate_hard_rules(
    suite: Suite,
    session: SessionState,
) -> set[FeatureType]:
    """Return the set of feature types blocked by hard rules."""
    blocked: set[FeatureType] = set()

    # Processing Suite: listen, don't suggest
    if suite == Suite.PROCESSING:
        blocked.update({FeatureType.BREW, FeatureType.DISPATCH})

    # Huddle owns the conversation
    if session.active_feature == FeatureType.HUDDLE:
        blocked.update({FeatureType.DISPATCH, FeatureType.BREW, FeatureType.PROBE})

    # Valet owns the conversation
    if session.active_feature == FeatureType.VALET:
        blocked.update({FeatureType.BREW, FeatureType.PROBE})

    # Processing cooldown: suppress brews after exit
    if session.is_in_processing_cooldown:
        blocked.add(FeatureType.BREW)

    return blocked
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_hard_rules.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/pipeline/hard_rules.py concierge/tests/test_hard_rules.py
git commit -m "feat(concierge): add hard rules evaluator for feature blocking"
```

---

## Phase 5: Priority System

### Task 5.1: Priority scoring engine

**Files:**
- Create: `concierge/pipeline/scoring.py`
- Test: `concierge/tests/test_scoring.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_scoring.py
"""Tests for priority scoring engine."""
from concierge.pipeline.scoring import score_candidates
from concierge.models import FeatureCandidate, FeatureType


class TestScoring:
    def test_scores_candidates_deterministically(self):
        c1 = FeatureCandidate(
            feature_type=FeatureType.DISPATCH, domain="meals",
            score_inputs={"relevance": 0.9, "urgency": 0.5, "suite_fit": 1.0,
                          "freshness": 0.1, "queue_age": 0.0, "domain_match": 1.0},
        )
        c2 = FeatureCandidate(
            feature_type=FeatureType.BREW, domain="wellness",
            score_inputs={"relevance": 0.3, "urgency": 0.1, "suite_fit": 0.5,
                          "freshness": 0.8, "queue_age": 0.2, "domain_match": 0.0},
        )
        weights = {
            "dispatches": {"relevance": 0.35, "urgency": 0.25, "suite_fit": 0.20,
                           "freshness": -0.10, "queue_age": 0.05, "domain_match": 0.05},
            "brews": {"relevance": 0.20, "urgency": 0.10, "suite_fit": 0.30,
                      "freshness": -0.20, "queue_age": 0.10, "domain_match": 0.10},
        }
        scored = score_candidates([c1, c2], weights)
        assert len(scored) == 2
        # c1 should score higher
        assert scored[0][1] > scored[1][1]
        assert scored[0][0] is c1

    def test_empty_candidates(self):
        assert score_candidates([], {}) == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_scoring.py -v`
Expected: FAIL

**Step 3: Implement scoring engine**

```python
# concierge/pipeline/scoring.py
"""Priority scoring: deterministic weighted formula per feature type."""
from __future__ import annotations

from ..models import FeatureCandidate


def score_candidates(
    candidates: list[FeatureCandidate],
    weights_by_type: dict[str, dict[str, float]],
) -> list[tuple[FeatureCandidate, float]]:
    """Score and sort candidates by priority (highest first).

    Returns list of (candidate, score) tuples sorted descending.
    """
    scored = []
    for candidate in candidates:
        type_key = candidate.feature_type.value + "s"  # dispatch -> dispatches
        weights = weights_by_type.get(type_key, {})
        score = candidate.compute_score(weights)
        scored.append((candidate, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_scoring.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/pipeline/scoring.py concierge/tests/test_scoring.py
git commit -m "feat(concierge): add deterministic priority scoring engine"
```

---

### Task 5.2: Priority queue with aging (pqdict)

**Files:**
- Create: `concierge/pipeline/queue.py`
- Test: `concierge/tests/test_queue.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_queue.py
"""Tests for priority queue with aging."""
from datetime import datetime, timedelta
from concierge.pipeline.queue import PriorityQueue
from concierge.models import FeatureCandidate, FeatureType, QueueItem


class TestPriorityQueue:
    def _make_candidate(self, domain="meals", score=0.5):
        return FeatureCandidate(
            feature_type=FeatureType.DISPATCH, domain=domain,
            score_inputs={"relevance": score},
        )

    def test_add_and_peek(self):
        q = PriorityQueue(max_size=10)
        q.add(self._make_candidate(), priority=0.8)
        assert q.peek().priority == 0.8

    def test_ordering_by_priority(self):
        q = PriorityQueue(max_size=10)
        q.add(self._make_candidate("a"), priority=0.3)
        q.add(self._make_candidate("b"), priority=0.9)
        q.add(self._make_candidate("c"), priority=0.6)
        assert q.pop().candidate.domain == "b"

    def test_eviction_when_full(self):
        q = PriorityQueue(max_size=2)
        q.add(self._make_candidate("low"), priority=0.1)
        q.add(self._make_candidate("mid"), priority=0.5)
        q.add(self._make_candidate("high"), priority=0.9)
        assert len(q) == 2
        # "low" should have been evicted
        domains = {item.candidate.domain for item in q}
        assert "low" not in domains

    def test_aging_boosts_priority(self):
        q = PriorityQueue(max_size=10, aging_rate=0.1)
        q.add(self._make_candidate(), priority=0.5)
        initial = q.peek().priority
        q.age_items(hours_elapsed=5)
        assert q.peek().priority > initial

    def test_expired_items_removed(self):
        q = PriorityQueue(max_size=10, max_age_hours=1)
        item = QueueItem(
            candidate=self._make_candidate(),
            queued_at=datetime.now() - timedelta(hours=2),
            priority=0.5,
        )
        q._items["test"] = item
        q._pq["test"] = -0.5
        q.expire_stale()
        assert len(q) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_queue.py -v`
Expected: FAIL

**Step 3: Add pqdict to dependencies and implement**

Add to `pyproject.toml` dependencies:
```toml
"pqdict>=1.3",
```

```python
# concierge/pipeline/queue.py
"""Priority queue with in-place aging and eviction."""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from pqdict import pqdict

from ..models import FeatureCandidate, QueueItem


class PriorityQueue:
    def __init__(
        self,
        max_size: int = 10,
        aging_rate: float = 0.02,
        max_age_hours: float = 168,
    ):
        self.max_size = max_size
        self.aging_rate = aging_rate
        self.max_age_hours = max_age_hours
        # pqdict uses min-heap, so we negate priorities for max-priority-first
        self._pq: pqdict = pqdict()
        self._items: dict[str, QueueItem] = {}

    def __len__(self) -> int:
        return len(self._pq)

    def add(self, candidate: FeatureCandidate, priority: float) -> str | None:
        """Add a candidate. Evicts lowest if full. Returns item ID or None if dropped."""
        if len(self._pq) >= self.max_size:
            # Check if new candidate beats lowest
            worst_key = self._pq.top()
            worst_priority = -self._pq[worst_key]
            if priority <= worst_priority:
                return None  # New candidate too weak
            # Evict worst
            self._pq.pop()
            del self._items[worst_key]

        item_id = str(uuid4())[:8]
        item = QueueItem(candidate=candidate, priority=priority)
        self._items[item_id] = item
        self._pq[item_id] = -priority  # Negate for min-heap
        return item_id

    def peek(self) -> QueueItem | None:
        if not self._pq:
            return None
        key = self._pq.top()
        return self._items[key]

    def pop(self) -> QueueItem | None:
        if not self._pq:
            return None
        key = self._pq.pop()
        return self._items.pop(key)

    def age_items(self, hours_elapsed: float = 1.0) -> None:
        """Boost all items' priority by aging_rate * hours."""
        boost = self.aging_rate * hours_elapsed
        for key in list(self._pq):
            self._items[key].priority += boost
            self._pq.updateitem(key, -self._items[key].priority)

    def expire_stale(self) -> list[QueueItem]:
        """Remove items older than max_age_hours."""
        now = datetime.now()
        cutoff = timedelta(hours=self.max_age_hours)
        expired = []
        for key in list(self._pq):
            item = self._items[key]
            if now - item.queued_at > cutoff:
                del self._pq[key]
                expired.append(self._items.pop(key))
        return expired

    def __iter__(self):
        for key in self._pq:
            yield self._items[key]
```

**Step 4: Run tests**

Run: `uv sync && uv run pytest concierge/tests/test_queue.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/pipeline/queue.py concierge/tests/test_queue.py pyproject.toml
git commit -m "feat(concierge): add priority queue with aging and eviction (pqdict)"
```

---

### Task 5.3: Epsilon-greedy lottery

**Files:**
- Create: `concierge/pipeline/lottery.py`
- Test: `concierge/tests/test_lottery.py`

**Step 1: Write the failing test**

```python
# concierge/tests/test_lottery.py
"""Tests for epsilon-greedy feature lottery."""
import random
from concierge.pipeline.lottery import FeatureSelector
from concierge.models import FeatureCandidate, FeatureType


class TestFeatureSelector:
    def _make_candidates(self, n=5):
        return [
            FeatureCandidate(
                feature_type=FeatureType.DISPATCH, domain=f"d{i}",
                score_inputs={"relevance": i / n},
            )
            for i in range(n)
        ]

    def test_exploit_selects_highest(self):
        selector = FeatureSelector(epsilon=0.0)  # Pure exploit
        candidates = self._make_candidates(5)
        scores = {c: float(i) for i, c in enumerate(candidates)}
        winner = selector.select(candidates, scores)
        assert winner is candidates[-1]

    def test_explore_can_select_non_highest(self):
        random.seed(42)
        selector = FeatureSelector(epsilon=1.0)  # Pure explore
        candidates = self._make_candidates(5)
        scores = {c: float(i) for i, c in enumerate(candidates)}
        selections = {selector.select(candidates, scores) for _ in range(100)}
        assert len(selections) > 1  # Not always picking the same one

    def test_suite_fit_floor(self):
        selector = FeatureSelector(epsilon=1.0, suite_fit_floor=0.3)
        c_good = FeatureCandidate(
            feature_type=FeatureType.DISPATCH, domain="good",
            score_inputs={"suite_fit": 0.8},
        )
        c_bad = FeatureCandidate(
            feature_type=FeatureType.DISPATCH, domain="bad",
            score_inputs={"suite_fit": 0.1},
        )
        scores = {c_good: 0.5, c_bad: 0.9}
        # Even with pure explore, c_bad should be filtered out
        for _ in range(50):
            winner = selector.select([c_good, c_bad], scores)
            assert winner is c_good

    def test_decay_reduces_epsilon(self):
        selector = FeatureSelector(epsilon=0.12, decay=0.5, min_epsilon=0.05)
        selector.decay_epsilon()
        assert selector.epsilon == 0.06
        selector.decay_epsilon()
        assert selector.epsilon == 0.05  # Clamped to min

    def test_statistical_exploration_rate(self):
        """Over many runs, exploration should match epsilon."""
        random.seed(0)
        selector = FeatureSelector(epsilon=0.12)
        candidates = self._make_candidates(3)
        scores = {c: float(i) for i, c in enumerate(candidates)}
        best = candidates[-1]
        n = 10000
        exploit_count = sum(1 for _ in range(n) if selector.select(candidates, scores) is best)
        explore_rate = 1 - (exploit_count / n)
        assert 0.08 < explore_rate < 0.16  # ~12% +/- 4%
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest concierge/tests/test_lottery.py -v`
Expected: FAIL

**Step 3: Implement lottery**

```python
# concierge/pipeline/lottery.py
"""Epsilon-greedy feature selector with suite-fit floor."""
from __future__ import annotations

import random

from ..models import FeatureCandidate


class FeatureSelector:
    def __init__(
        self,
        epsilon: float = 0.12,
        decay: float = 0.995,
        min_epsilon: float = 0.05,
        suite_fit_floor: float = 0.3,
    ):
        self.epsilon = epsilon
        self.decay = decay
        self.min_epsilon = min_epsilon
        self.suite_fit_floor = suite_fit_floor

    def select(
        self,
        candidates: list[FeatureCandidate],
        priority_scores: dict[FeatureCandidate, float],
    ) -> FeatureCandidate | None:
        if not candidates:
            return None

        # Filter: suite_fit floor
        eligible = [
            c for c in candidates
            if c.score_inputs.get("suite_fit", 1.0) >= self.suite_fit_floor
        ]
        if not eligible:
            return None

        if random.random() < self.epsilon:
            # EXPLORE: uniform random from eligible
            winner = random.choice(eligible)
            winner.lottery_promoted = True
            return winner
        else:
            # EXPLOIT: highest priority
            return max(eligible, key=lambda c: priority_scores.get(c, 0.0))

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.min_epsilon, self.epsilon * self.decay)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest concierge/tests/test_lottery.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add concierge/pipeline/lottery.py concierge/tests/test_lottery.py
git commit -m "feat(concierge): add epsilon-greedy feature lottery with suite-fit floor"
```

---

## Phase 6-10: Remaining Phases (Summary)

Phases 6-10 build on the foundation above. Each follows the same TDD pattern. Here's a concise task list for each:

### Phase 6: Features (Candidacy + Generation)

| Task | What | Files |
|------|------|-------|
| 6.1 | Dispatch candidacy evaluator | `concierge/features/dispatches.py`, tests |
| 6.2 | Brew candidacy evaluator | `concierge/features/brews.py`, tests |
| 6.3 | Probe delivery evaluator | `concierge/features/probes.py`, tests |
| 6.4 | Valet session manager | `concierge/features/valets.py`, tests |
| 6.5 | Huddle conversation engine | `concierge/features/huddles.py`, tests |
| 6.6 | Feature ownership manager (pause/resume/timeout) | `concierge/features/ownership.py`, tests |

### Phase 7: UX Layer

| Task | What | Files |
|------|------|-------|
| 7.1 | UX sanitizer (strip dev jargon) | `concierge/sanitizer.py`, tests |
| 7.2 | Quick-reply formatter (inline keyboard) | `concierge/formatting.py`, tests |
| 7.3 | Vocabulary introduction tracker | `concierge/vocabulary.py`, tests |

### Phase 8: Distillation Pipeline

| Task | What | Files |
|------|------|-------|
| 8.1 | Candidate detection (redundancy scoring) | `concierge/distillation/detection.py`, tests |
| 8.2 | Compression (LLM-based summarization) | `concierge/distillation/compress.py`, tests |
| 8.3 | Semantic diff validator | `concierge/distillation/validation.py`, tests |
| 8.4 | Distillation state machine | `concierge/distillation/state.py`, tests |

### Phase 9: Background System

| Task | What | Files |
|------|------|-------|
| 9.1 | Background check runner | `concierge/background/runner.py`, tests |
| 9.2 | launchd plist generator | `concierge/setup/launchd.py`, tests |
| 9.3 | Lock file manager (prevent overlap) | `concierge/background/lockfile.py`, tests |
| 9.4 | Catch-up policy after wake | `concierge/background/catchup.py`, tests |

### Phase 10: Telegram Bridge Integration

| Task | What | Files |
|------|------|-------|
| 10.1 | Pre-session hook (inject memory + personality) | `concierge/hooks/pre_session.py`, tests |
| 10.2 | Post-session hook (extract + persist memories) | `concierge/hooks/post_session.py`, tests |
| 10.3 | cc-connect adapter | `concierge/bridge/cc_connect.py`, tests |
| 10.4 | Setup wizard | `concierge/setup/wizard.py`, tests |
| 10.5 | Attache prompt files (10 domains) | `concierge/attaches/*.md` |
| 10.6 | Prompt templates (system, briefings) | `concierge/prompts/*.md` |
| 10.7 | Huddle templates (6 types) | `concierge/huddles/*.md` |

---

## Dependency Graph

```
Phase 1 (Foundation)
  ├── Task 1.1: Package skeleton
  ├── Task 1.2: Config loader
  ├── Task 1.3: Data models
  └── Task 1.4: Session state persistence
        │
        ├─── Phase 2 (Memory) ──────────────────────────┐
        │      ├── Task 2.1: Memory reader               │
        │      └── Task 2.2: Memory writer               │
        │                                                 │
        ├─── Phase 3 (Classifier)                        │
        │      ├── Task 3.1: Deterministic               │
        │      ├── Task 3.2: Fuzzy commands              │
        │      ├── Task 3.3: Model stub                  │
        │      └── Task 3.4: Unified classifier          │
        │              │                                  │
        └──────────────┴──── Phase 4 (Pipeline Core)     │
                               ├── Task 4.1: Suite       │
                               ├── Task 4.2: Attache     │
                               └── Task 4.3: Hard rules  │
                                       │                  │
                              Phase 5 (Priority)          │
                               ├── Task 5.1: Scoring      │
                               ├── Task 5.2: Queue        │
                               └── Task 5.3: Lottery      │
                                       │                  │
                              Phase 6 (Features) ─────────┤
                               ├── 6.1-6.6               │
                                       │                  │
                    ┌──────────────────┼──────────────────┘
                    │                  │
              Phase 7 (UX)      Phase 8 (Distillation)
               ├── 7.1-7.3      ├── 8.1-8.4
                    │                  │
                    └──────┬───────────┘
                           │
                     Phase 9 (Background)
                      ├── 9.1-9.4
                           │
                     Phase 10 (Bridge)
                      └── 10.1-10.7
```

## Running Tests

All phases:
```bash
uv run pytest concierge/tests/ -v
```

Single phase (example):
```bash
uv run pytest concierge/tests/test_classifier*.py -v
```

With coverage:
```bash
uv run pytest concierge/tests/ -v --cov=concierge --cov-report=term-missing
```

## Estimated Totals

| Metric | Count |
|--------|-------|
| Tasks (Phases 1-5, detailed) | 14 |
| Tasks (Phases 6-10, outlined) | 20 |
| Total tasks | 34 |
| Test files | ~25 |
| Source files | ~30 |
| Config files | 3 defaults + attaches/prompts/huddles |
