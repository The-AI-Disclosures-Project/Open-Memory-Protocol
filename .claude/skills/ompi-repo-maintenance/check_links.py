"""Check that every relative link in every Markdown file of the repo resolves.

Run from the repository root:  python3 -I .claude/skills/ompi-repo-maintenance/check_links.py
Exit code 1 when a link is broken. Skips http(s), mailto, in-page anchors and the
contextnest:// URI scheme used as an example in the Context Nest draft.
"""

import pathlib
import re
import sys

LINK = re.compile(r'\]\(([^)\s]+)\)|href="([^"]+)"|src="([^"]+)"')
SKIP = re.compile(r"^(https?:|mailto:|#|contextnest:)")


def main() -> int:
    root = pathlib.Path(".")
    checked = 0
    broken: list[str] = []
    for md in root.rglob("*.md"):
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        for match in LINK.finditer(text):
            link = next(group for group in match.groups() if group)
            if SKIP.match(link):
                continue
            target = link.split("#")[0]
            if not target:
                continue
            checked += 1
            if not (md.parent / target).resolve().exists():
                broken.append(f"{md}: {link}")
    print(f"checked {checked} relative links; broken: {len(broken)}")
    for line in broken:
        print(line)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
