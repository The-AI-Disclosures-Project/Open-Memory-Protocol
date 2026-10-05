"""Deterministic rendering of an OMP memory directory for the context window.

This module is pure (no LangChain imports) so it can be tested and reused on its own.
It turns a validated MemoryDirectory into two strings:

- core context  (rule 1): every root-level .md file, optionally truncated
- deferred index (rule 3): metadata about memory exactly one level down
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from open_memory_protocol import MemoryDirectory
from open_memory_protocol.types import ROOT_INDEX_FILENAME

# Spec §Size guidance. The draft's per-file figure ("500 tokens (~20,000 characters)")
# is internally inconsistent; we expose both knobs and let the harness author choose.
DEFAULT_MAX_FILE_CHARS = 20_000
DEFAULT_MAX_TOTAL_TOKENS = 20_000
CHARS_PER_TOKEN_ESTIMATE = 4

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def estimate_tokens(text: str) -> int:
    """Cheap tokenizer-free estimate so the harness has no model-specific dependency."""
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE) if text else 0


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract simple `key: value` YAML-ish frontmatter (spec §Optional metadata).

    Only flat string fields are parsed; anything more complex is passed through verbatim
    under its key so the agent still sees it. Returns (fields, body).
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, text[m.end() :]


def description_of(path: Path) -> str | None:
    """Return the `description` frontmatter field of a markdown file, if any."""
    try:
        fields, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    return fields.get("description")


@dataclass
class DeferredEntry:
    """One item surfaced to the agent under rule 3."""

    relative_path: Path
    is_dir: bool
    description: str | None
    file_count: int = 0  # for directories: .md files anywhere beneath


def deferred_entries(memory: MemoryDirectory) -> list[DeferredEntry]:
    """Rule 3: enumerate memory exactly one level below the root.

    Immediate subdirectories are listed (with their MEMORY.md description and a count of
    markdown files beneath them). Files directly inside those subdirectories are listed too,
    since the spec says the agent must know of "context in immediate subdirectories".
    Anything deeper is left for the agent to discover by reading the subdirectory's MEMORY.md.
    """
    entries: list[DeferredEntry] = []
    for subdir in sorted(p for p in memory.root.iterdir() if p.is_dir()):
        if subdir.name.startswith("."):
            continue
        beneath = [f for f in memory.external_files if f.relative_path.parts[0] == subdir.name]
        if not beneath:
            continue
        index = subdir / ROOT_INDEX_FILENAME
        entries.append(
            DeferredEntry(
                relative_path=subdir.relative_to(memory.root),
                is_dir=True,
                description=description_of(index) if index.exists() else None,
                file_count=len(beneath),
            )
        )
        for f in sorted(beneath, key=lambda f: f.relative_path):
            if len(f.relative_path.parts) == 2:  # directly inside the subdirectory
                entries.append(
                    DeferredEntry(
                        relative_path=f.relative_path,
                        is_dir=False,
                        description=description_of(f.path),
                    )
                )
    return entries


def render_core_context(
    memory: MemoryDirectory,
    *,
    max_file_chars: int | None = DEFAULT_MAX_FILE_CHARS,
) -> tuple[str, list[str]]:
    """Rule 1: concatenate every root-level .md file.

    Returns (text, warnings). Files over `max_file_chars` are truncated with a visible marker,
    which the spec explicitly permits ("The harness may truncate the contents").
    """
    parts: list[str] = []
    warnings: list[str] = []
    for f in memory.core_files:
        raw = f.read()
        fields, body = parse_frontmatter(raw)
        body = body.rstrip()
        if max_file_chars is not None and len(body) > max_file_chars:
            body = (
                body[:max_file_chars].rstrip()
                + f"\n\n[... truncated by harness at {max_file_chars} characters; "
                f"call read_memory('{f.relative_path}') for the full file ...]"
            )
            warnings.append(f"{f.relative_path} exceeds {max_file_chars} chars; truncated")
        truncated = bool(warnings) and warnings[-1].startswith(str(f.relative_path))
        header = f"### {f.relative_path} ({'truncated' if truncated else 'loaded in full'})"
        if desc := fields.get("description"):
            header += f"\n_{desc}_"
        parts.append(f"{header}\n\n{body}\n")
    return "\n".join(parts), warnings


def render_deferred_index(memory: MemoryDirectory) -> str:
    """Rule 3: render the one-level-down index as markdown for the system prompt."""
    entries = deferred_entries(memory)
    if not entries:
        return "_No deferred memory. The root files above are the entire memory._"
    lines: list[str] = []
    for e in entries:
        if e.is_dir:
            label = (
                f"- `{e.relative_path}/` ({e.file_count} file{'s' if e.file_count != 1 else ''})"
            )
        else:
            label = f"  - `{e.relative_path}`"
        if e.description:
            label += f" — {e.description}"
        lines.append(label)
    return "\n".join(lines)


def render_directory_listing(memory: MemoryDirectory, directory: Path) -> str:
    """For rule 4 reads of a directory: its MEMORY.md plus the next level of disclosure."""
    rel_dir = directory.relative_to(memory.root)
    index = directory / ROOT_INDEX_FILENAME
    out: list[str] = []
    if index.exists():
        out.append(
            f"### {rel_dir / ROOT_INDEX_FILENAME}\n\n{index.read_text(encoding='utf-8').rstrip()}\n"
        )
    children: list[str] = []
    for child in sorted(directory.iterdir()):
        if child.name.startswith(".") or child.name == ROOT_INDEX_FILENAME:
            continue
        if child.is_dir():
            n = sum(1 for _ in child.rglob("*.md"))
            if n:
                children.append(f"- `{rel_dir / child.name}/` ({n} file{'s' if n != 1 else ''})")
        elif child.suffix == ".md":
            desc = description_of(child)
            children.append(f"- `{rel_dir / child.name}`" + (f" — {desc}" if desc else ""))
    if children:
        out.append("### Contents\n\n" + "\n".join(children))
    return "\n".join(out) if out else f"(empty directory: {rel_dir})"
