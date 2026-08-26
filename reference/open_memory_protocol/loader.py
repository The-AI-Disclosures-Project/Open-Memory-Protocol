"""Loader for OMP memory directories.

Implements the four-rule harness contract from spec/draft-v0.1.md §Harness contract:
1. Load root Markdown  — every .md in the root goes into the agent's context
2. Defer nested Markdown — nested .md is not auto-loaded
3. Surface deferred memory — the agent is told the deferred paths exist
4. Support selective reads — the agent can read a deferred file on demand
"""

from __future__ import annotations

from pathlib import Path

from open_memory_protocol.types import (
    HarnessContext,
    MemoryDirectory,
    MemoryFile,
    ROOT_INDEX_FILENAME,
)
from open_memory_protocol.validator import validate_memory


def load_memory(root: Path | str) -> MemoryDirectory:
    """Load and validate an OMP memory directory.

    Returns a MemoryDirectory with core_files and external_files separated
    per the spec. Raises ValidationError if the directory does not conform.
    """
    root = Path(root)
    validate_memory(root)

    core_files: list[MemoryFile] = []
    external_files: list[MemoryFile] = []

    for md_path in sorted(root.rglob("*.md")):
        if any(part.startswith(".") for part in md_path.parts):
            continue
        rel = md_path.relative_to(root)
        depth = len(rel.parts) - 1
        mf = MemoryFile(
            path=md_path.resolve(),
            relative_path=rel,
            is_core=(depth == 0),
            depth=depth,
        )
        if mf.is_core:
            core_files.append(mf)
        else:
            external_files.append(mf)

    return MemoryDirectory(
        root=root.resolve(),
        core_files=core_files,
        external_files=external_files,
    )


def build_harness_context(memory: MemoryDirectory) -> HarnessContext:
    """Build the HarnessContext that a conforming harness passes to an agent.

    Concatenates root markdown into core_context with a filename header per file
    (rule 1). Populates deferred_index with relative paths of external files (rule 3).
    """
    core_parts: list[str] = []
    for f in memory.core_files:
        core_parts.append(f"# {f.relative_path}\n\n{f.read().rstrip()}\n")
    core_context = "\n".join(core_parts)

    deferred_index = [f.relative_path for f in memory.external_files]

    return HarnessContext(
        core_context=core_context,
        deferred_index=deferred_index,
        memory=memory,
    )
