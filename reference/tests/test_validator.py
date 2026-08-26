"""Tests for the OMP validator.

Covers each valid and invalid configuration from spec/draft-v0.1.md.
"""

from pathlib import Path

import pytest

from open_memory_protocol import ValidationError, load_memory, validate_memory
from open_memory_protocol.loader import build_harness_context


def _write(root: Path, relative: str, content: str = "test") -> None:
    p = root / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_minimal_valid(tmp_path: Path) -> None:
    _write(tmp_path, "MEMORY.md")
    validate_memory(tmp_path)


def test_core_only_valid(tmp_path: Path) -> None:
    _write(tmp_path, "MEMORY.md")
    _write(tmp_path, "SOUL.md")
    _write(tmp_path, "USER.md")
    validate_memory(tmp_path)


def test_nested_with_index_valid(tmp_path: Path) -> None:
    _write(tmp_path, "MEMORY.md")
    _write(tmp_path, "projects/MEMORY.md")
    _write(tmp_path, "projects/project_1/MEMORY.md")
    validate_memory(tmp_path)


def test_missing_root_index_invalid(tmp_path: Path) -> None:
    _write(tmp_path, "project-1/MEMORY.md")
    _write(tmp_path, "project-1/user_preferences.md")
    with pytest.raises(ValidationError, match="Missing required root MEMORY.md"):
        validate_memory(tmp_path)


def test_subdir_without_index_invalid(tmp_path: Path) -> None:
    _write(tmp_path, "MEMORY.md")
    _write(tmp_path, "notes/2026-08-12.md")  # no notes/MEMORY.md
    with pytest.raises(ValidationError, match="no MEMORY.md"):
        validate_memory(tmp_path)


def test_load_separates_core_and_external(tmp_path: Path) -> None:
    _write(tmp_path, "MEMORY.md", "root index")
    _write(tmp_path, "persona.md", "persona")
    _write(tmp_path, "notes/MEMORY.md", "notes index")
    _write(tmp_path, "notes/2026-08-12.md", "log entry")

    mem = load_memory(tmp_path)
    core_names = {str(f.relative_path) for f in mem.core_files}
    external_names = {str(f.relative_path) for f in mem.external_files}

    assert core_names == {"MEMORY.md", "persona.md"}
    assert external_names == {"notes/MEMORY.md", "notes/2026-08-12.md"}


def test_harness_context_includes_only_root(tmp_path: Path) -> None:
    _write(tmp_path, "MEMORY.md", "root")
    _write(tmp_path, "persona.md", "persona")
    _write(tmp_path, "notes/MEMORY.md", "notes index")
    _write(tmp_path, "notes/2026-08-12.md", "log")

    ctx = build_harness_context(load_memory(tmp_path))
    assert "root" in ctx.core_context
    assert "persona" in ctx.core_context
    assert "log" not in ctx.core_context  # rule 2: nested not auto-loaded
    assert Path("notes/2026-08-12.md") in ctx.deferred_index


def test_selective_read(tmp_path: Path) -> None:
    _write(tmp_path, "MEMORY.md")
    _write(tmp_path, "notes/MEMORY.md")
    _write(tmp_path, "notes/2026-08-12.md", "hello")
    ctx = build_harness_context(load_memory(tmp_path))
    assert ctx.read_deferred("notes/2026-08-12.md") == "hello"
