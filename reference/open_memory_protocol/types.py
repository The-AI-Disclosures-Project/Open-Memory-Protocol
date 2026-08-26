"""Data types for the Open Memory Protocol.

Mirrors the memory-directory model in spec/draft-v0.1.md:
- An OMP memory root is a directory containing markdown files and optional subdirectories.
- Every directory (including the root) must contain a MEMORY.md.
- Top-level markdown files are "core memory" (always in context).
- Markdown in subdirectories is "external memory" (progressively disclosed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


ROOT_INDEX_FILENAME = "MEMORY.md"


@dataclass
class MemoryFile:
    """A single markdown file within an OMP memory root."""

    path: Path
    """Absolute path to the file on disk."""

    relative_path: Path
    """Path relative to the memory root."""

    is_core: bool
    """True if this file sits at the memory root (always in context)."""

    depth: int
    """Directory depth below the memory root. 0 for root-level files."""

    def read(self) -> str:
        """Read the file's contents."""
        return self.path.read_text(encoding="utf-8")


@dataclass
class MemoryDirectory:
    """A validated OMP memory root."""

    root: Path
    """Absolute path to the memory root directory."""

    core_files: list[MemoryFile] = field(default_factory=list)
    """Markdown files at the root (loaded on every request per rule 1)."""

    external_files: list[MemoryFile] = field(default_factory=list)
    """Markdown files below the root (deferred per rule 2)."""

    @property
    def root_index(self) -> MemoryFile:
        """The required root MEMORY.md file."""
        for f in self.core_files:
            if f.relative_path == Path(ROOT_INDEX_FILENAME):
                return f
        raise RuntimeError("MemoryDirectory constructed without root MEMORY.md")

    def all_files(self) -> list[MemoryFile]:
        """Every markdown file in the memory root, core + external."""
        return [*self.core_files, *self.external_files]


@dataclass
class HarnessContext:
    """What a conforming harness gives an agent for one request.

    Rule 1: core_context contains every root .md file, concatenated.
    Rule 2: external_context is empty by default.
    Rule 3: deferred_index lists the paths of external files so the agent knows they exist.
    Rule 4: the agent can call read_deferred(path) to selectively pull an external file.
    """

    core_context: str
    """All root markdown files, concatenated with a filename header per file."""

    deferred_index: list[Path]
    """Relative paths of external (nested) markdown files the agent may read on demand."""

    memory: MemoryDirectory
    """The underlying memory directory, for selective reads."""

    def read_deferred(self, relative_path: str | Path) -> str:
        """Rule 4: selectively load an external file by relative path."""
        target = Path(relative_path)
        for f in self.memory.external_files:
            if f.relative_path == target:
                return f.read()
        raise FileNotFoundError(f"No external memory file at {relative_path}")
