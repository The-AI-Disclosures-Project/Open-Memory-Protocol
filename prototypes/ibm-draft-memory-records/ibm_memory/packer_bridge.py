"""Packer-draft memory directory  <->  IBM memory records.

A cross-draft interoperability check: a Packer memory (markdown files in a folder) becomes a
set of IBM records and back again, losslessly. Mapping:

    file path                -> scope tag  "path:<relative path>"   (carries layout)
    root vs nested           -> scope tag  "tier:core" | "tier:deferred"
    frontmatter description  -> semantic tag "description:<text>"
    frontmatter tags: a, b   -> semantic tags a, b
    body (frontmatter removed) -> record body
    author                   -> "user" unless frontmatter `author:`
    provenance               -> ai_used from frontmatter `ai_generated: true`
"""

from __future__ import annotations

import re
from pathlib import Path

from ibm_memory.schema import MemoryRecord, Provenance
from ibm_memory.store import MemoryStore

_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = _FM.match(text)
    if not m:
        return {}, text
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip().strip('"').strip("'")
    return fields, text[m.end() :]


def records_from_memory_dir(
    root: str | Path,
    store: MemoryStore,
    *,
    author: str = "user",
    extra_scopes: list[str] | None = None,
) -> list[MemoryRecord]:
    root = Path(root).resolve()
    if not (root / "MEMORY.md").exists():
        raise ValueError(f"not a Packer memory root (no MEMORY.md): {root}")
    out = []
    for md in sorted(root.rglob("*.md")):
        if any(p.startswith(".") for p in md.relative_to(root).parts):
            continue
        rel = md.relative_to(root).as_posix()
        fields, body = _parse_frontmatter(md.read_text(encoding="utf-8"))
        sem = [t.strip() for t in fields.get("tags", "").split(",") if t.strip()]
        if fields.get("description"):
            sem.append(f"description:{fields['description']}")
        scopes = [
            f"path:{rel}",
            "tier:core" if "/" not in rel else "tier:deferred",
            *(extra_scopes or []),
        ]
        out.append(
            store.write(
                body.rstrip("\n") + "\n",
                author=fields.get("author", author),
                provenance=Provenance(
                    ai_used=fields.get("ai_generated", "").lower() == "true",
                    how="imported from Packer memory directory",
                ),
                semantic_tags=sem,
                scope_tags=scopes,
                source_material=[f"file:{md}"],
            )
        )
    return out


def memory_dir_from_records(records: list[MemoryRecord], root: str | Path) -> list[Path]:
    """Write valid records carrying a `path:` scope back to a Packer layout."""
    root = Path(root)
    written = []
    for r in records:
        if not r.is_valid:
            continue
        path_tag = next((s for s in r.scope_tags if s.startswith("path:")), None)
        if not path_tag:
            continue
        target = root / path_tag.removeprefix("path:")
        target.parent.mkdir(parents=True, exist_ok=True)
        fm = []
        desc = next(
            (
                t.removeprefix("description:")
                for t in r.semantic_tags
                if t.startswith("description:")
            ),
            None,
        )
        tags = [t for t in r.semantic_tags if not t.startswith("description:")]
        if desc:
            fm.append(f"description: {desc}")
        if tags:
            fm.append("tags: " + ", ".join(tags))
        if r.lifecycle.author != "user":
            fm.append(f"author: {r.lifecycle.author}")
        if r.lifecycle.provenance.ai_used:
            fm.append("ai_generated: true")
        text = (("---\n" + "\n".join(fm) + "\n---\n") if fm else "") + r.body
        target.write_text(text, encoding="utf-8")
        written.append(target)
    # keep every directory spec-valid
    for d in {p.parent for p in written}:
        cur = d
        while cur != root and cur.is_relative_to(root):
            idx = cur / "MEMORY.md"
            if not idx.exists():
                idx.write_text(f"# {cur.name}\n", encoding="utf-8")
            cur = cur.parent
    return written
