"""Shared helpers for Bureau-managed protocol runtime artifacts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Sequence

from .config_loader import Config, ProtocolDocumentSetting, find_repo_root, get_config

ProtocolArtifactKey = Literal["output_style", "code_standards"]

CODE_STANDARDS_MINDSET_RELATIVE_PATH = Path("protocols/context/static/ops/code-standards.md")
CODE_STANDARDS_SKILL_WRAPPER_RELATIVE_PATH = Path(
    "protocols/context/static/code-standards-skill-wrapper.md"
)
DEFAULT_SOURCE_RELATIVE_PATHS: dict[ProtocolArtifactKey, Path] = {
    "output_style": Path("protocols/context/static/ops/output-style.md"),
    "code_standards": Path("protocols/context/static/code-standards-reference.md"),
}

ARTIFACT_DISPLAY_NAMES: dict[ProtocolArtifactKey, str] = {
    "output_style": "output style",
    "code_standards": "code standards",
}

OFF_EXIT_CODE = 3
RUNTIME_ARTIFACT_MARKER = "<!-- Bureau protocols -->\n\n"


def resolve_protocol_source_path(raw_path: str, repo_root: Path | None = None) -> Path:
    """Resolve a config path against the repo root unless it is already absolute."""
    root = repo_root or find_repo_root()
    expanded = Path(os.path.expandvars(os.path.expanduser(raw_path)))
    if expanded.is_absolute():
        return expanded
    return (root / raw_path).resolve()


def get_default_protocol_sources(
    artifact_key: ProtocolArtifactKey, repo_root: Path | None = None
) -> list[Path]:
    """Return Bureau's shipped default source path for one artifact."""
    root = repo_root or find_repo_root()
    return [(root / DEFAULT_SOURCE_RELATIVE_PATHS[artifact_key]).resolve()]


def get_code_standards_mindset_source(repo_root: Path | None = None) -> Path:
    """Return the shipped startup mindset source for code standards."""
    root = repo_root or find_repo_root()
    return (root / CODE_STANDARDS_MINDSET_RELATIVE_PATH).resolve()


def get_code_standards_skill_wrapper_source(repo_root: Path | None = None) -> Path:
    """Return the wrapper template used for the generated code-standards skill."""
    root = repo_root or find_repo_root()
    return (root / CODE_STANDARDS_SKILL_WRAPPER_RELATIVE_PATH).resolve()


def resolve_protocol_sources(
    artifact_key: ProtocolArtifactKey,
    setting: ProtocolDocumentSetting | None,
    repo_root: Path | None = None,
) -> list[Path] | None:
    """Resolve one protocol document setting into ordered source paths."""
    if setting in (None, "default"):
        return get_default_protocol_sources(artifact_key, repo_root=repo_root)
    if setting in ("off", False):
        return None
    return [resolve_protocol_source_path(path, repo_root=repo_root) for path in setting]


def get_protocol_sources_from_config(
    artifact_key: ProtocolArtifactKey,
    *,
    config: Config | None = None,
    repo_root: Path | None = None,
) -> list[Path] | None:
    """Resolve one protocol artifact using the merged Bureau config."""
    merged_config = config or get_config()
    protocols = merged_config.get("protocols", {})
    setting = protocols.get(artifact_key, "default")
    return resolve_protocol_sources(artifact_key, setting, repo_root=repo_root)


def compile_runtime_artifact(
    artifact_name: str,
    sources: Sequence[Path],
    destination: Path,
) -> None:
    """Compile ordered source files into one runtime artifact."""
    if not sources:
        raise SystemExit(f"At least one {artifact_name} source is required")

    destination.parent.mkdir(parents=True, exist_ok=True)

    body = "".join(source.read_text(encoding="utf-8") for source in sources)
    destination.write_text(RUNTIME_ARTIFACT_MARKER + body, encoding="utf-8")


def compile_code_standards_skill(
    destination: Path,
    *,
    config: Config | None = None,
    repo_root: Path | None = None,
    source_overrides: Sequence[Path] | None = None,
    wrapper_source: Path | None = None,
) -> bool:
    """Compile the generated code-standards skill.

    Returns:
        `True` when the generated skill file was written.
        `False` when `protocols.code_standards` is explicitly disabled.
    """
    sources: list[Path] | None
    if source_overrides is not None:
        sources = [Path(path).expanduser().resolve() for path in source_overrides]
    else:
        sources = get_protocol_sources_from_config(
            "code_standards",
            config=config,
            repo_root=repo_root,
        )

    if sources is None:
        return False

    wrapper_path = (
        Path(wrapper_source).expanduser().resolve()
        if wrapper_source is not None
        else get_code_standards_skill_wrapper_source(repo_root=repo_root)
    )
    wrapper_text = wrapper_path.read_text(encoding="utf-8").rstrip("\n") + "\n\n"
    body = "".join(source.read_text(encoding="utf-8") for source in sources)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(wrapper_text + RUNTIME_ARTIFACT_MARKER + body, encoding="utf-8")
    return True


def compile_protocol_artifact(
    artifact_key: ProtocolArtifactKey,
    destination: Path,
    *,
    config: Config | None = None,
    repo_root: Path | None = None,
    source_overrides: Sequence[Path] | None = None,
) -> bool:
    """Compile one Bureau protocol artifact.

    Returns:
        `True` when an artifact was written.
        `False` when the config explicitly disables that artifact.
    """
    sources: list[Path] | None
    if source_overrides is not None:
        sources = [Path(path).expanduser().resolve() for path in source_overrides]
    else:
        sources = get_protocol_sources_from_config(
            artifact_key,
            config=config,
            repo_root=repo_root,
        )

    if sources is None:
        return False

    compile_runtime_artifact(ARTIFACT_DISPLAY_NAMES[artifact_key], sources, destination)
    return True
