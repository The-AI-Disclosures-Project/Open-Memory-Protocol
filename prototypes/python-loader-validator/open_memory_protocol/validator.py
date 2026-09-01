"""Structural validation for OMP memory directories.

Enforces the "valid memory configurations" rules from spec/draft-v0.1.md:
- Every directory that is part of the agent's memory must contain a MEMORY.md.
- The root MEMORY.md is required.
"""

from __future__ import annotations

from pathlib import Path

from open_memory_protocol.types import ROOT_INDEX_FILENAME


class ValidationError(Exception):
    """Raised when a memory directory does not conform to the OMP spec."""


def validate_memory(root: Path | str) -> None:
    """Validate an OMP memory directory. Raises ValidationError on any violation.

    Rules enforced:
    1. Root path exists and is a directory.
    2. Root directory contains MEMORY.md.
    3. Every subdirectory that contains any files also contains MEMORY.md.
    """
    root = Path(root)

    if not root.exists():
        raise ValidationError(f"Memory root does not exist: {root}")
    if not root.is_dir():
        raise ValidationError(f"Memory root is not a directory: {root}")

    root_index = root / ROOT_INDEX_FILENAME
    if not root_index.exists():
        raise ValidationError(
            f"Missing required root {ROOT_INDEX_FILENAME} at {root_index}. "
            f"See spec/draft-v0.1.md §Invalid memory configurations."
        )

    for subdir in _iter_subdirectories(root):
        if _has_files(subdir) and not (subdir / ROOT_INDEX_FILENAME).exists():
            rel = subdir.relative_to(root)
            raise ValidationError(
                f"Subdirectory {rel} contains files but no {ROOT_INDEX_FILENAME}. "
                f"Every directory in an OMP memory root must have a {ROOT_INDEX_FILENAME}."
            )


def _iter_subdirectories(root: Path):
    """Yield every subdirectory of root, recursively, skipping hidden dirs."""
    for path in root.rglob("*"):
        if path.is_dir() and not any(part.startswith(".") for part in path.parts):
            yield path


def _has_files(directory: Path) -> bool:
    """True if directory contains at least one regular file."""
    return any(child.is_file() for child in directory.iterdir())
