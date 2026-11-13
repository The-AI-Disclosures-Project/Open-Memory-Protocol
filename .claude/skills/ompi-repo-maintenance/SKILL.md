---
name: ompi-repo-maintenance
description: Maintain the Open Memory Protocol repository. Use when adding or revising a proposal, landing a new editors' draft, recording a meeting or event, updating the README or docs, or reviewing a PR against this repo for clutter, stale claims and broken links.
---

# Maintaining the Open Memory Protocol repository

The repository is a document set, not a codebase. Its job is to let a reader find, in one screen, what OMP is, which document is current, and how to contribute. Everything below protects that.

## Layout and what goes where

```
working-group/exchange-and-runtime/   editors' drafts and working-group notes (current spec lives here)
working-group/past-proposals/         contributed proposals, latest revision of each; archive/ holds superseded ones;
                                      README.md there is the index with one-paragraph summaries
prototypes/                           experimental code, one folder per prototype, README.md lists them all
docs/                                 contributing.md, history.md, prior-art/, the-memory-walled-garden/
media/                                logos only
GOVERNANCE.md · SECURITY.md · LICENSE · README.md
```

Do not add a top-level folder. New material goes into one of these. `working-group/exchange-and-runtime/` is the path open spec PRs target; never rename it without checking `gh pr list` for PRs that add files there.

## Rules the README follows

1. **Index, not essay.** One line per artifact, in a table: name, who it is from, link. Summaries live in the folder index (`working-group/past-proposals/README.md`, `prototypes/README.md`), not in the README.
2. **Latest only.** The README and the folder index list the latest revision of each proposal. A superseded revision is `git mv`'d to `archive/` and gets a row in the index's "Superseded revisions" table. Nothing is deleted.
3. **Past goes to history.** Dated events, convenings and milestones live in `docs/history.md`. The README's "Current work" holds only what is current: status line, current editors' draft, open PRs under review, the next event. A time-bound notice carries an HTML comment saying when to remove it, and is removed after the event.
4. **Every claim has a file behind it.** Before writing that a draft "covers X", that an organization is a partner or implementer, or that governance works a certain way, find the sentence in the repo that says so. The governance paragraph is a summary of `GOVERNANCE.md` and nothing more. No headcounts, no "we hope to grow" lists, no "reference implementer" while the status line says none exists.
5. **One call to action each.** Discord appears twice at most (nav row and contribute section). No badges: nothing in this repo is released, and the license has its own section.
6. **Plain names.** Say "specification" or "draft", not "technology"; say "OMPI" or "the working group", not "the ecosystem". OMP is the protocol, OMPI the initiative.
7. **No twins.** No HTML render next to a Markdown file (GitHub does not render HTML and the two drift). No PDF render of a Markdown file. A PDF is kept only when it is the author's source.
8. **Other authors' drafts are read-only** except for link fixes forced by a move. Prose that names a path as it was on `main` at a commit is historical and stays.

## Playbooks

**New revision of a proposal.** `git mv` the old file to `working-group/past-proposals/archive/`; add the new `draft-vX.Y-<org>.md`; update the index (summary, superseded table) and the README table row; fix the self-reference in the new file if it points at the old revision. Run the link check.

**New editors' draft.** Add it under `working-group/exchange-and-runtime/` with the date in the name; update the README nav link, the "Current work" bullet, `docs/contributing.md`'s "read the editors' draft" link, and the status line if the focus changed; add a line to `docs/history.md`. The previous draft's change log lives at the top of the new one, so the old file is not kept.

**Meeting or event.** Decisions go into the editors' draft change log; call notes (if any) go next to the spec with the date in the name. The event itself is one line in `docs/history.md`. Remove any README notice for it.

**New prototype.** Folder under `prototypes/` with its own README that states which draft it targets; one row in the README "Code" table and one bullet in `prototypes/README.md`. Links inside the prototype README to root files are `../../`.

**Reviewing a README or docs PR.** Ask of every changed sentence: is it backed by a file, is it duplicated one hop away, is it a date now in the past, does it name a path that exists. Then run the link check.

## Checks before pushing

```bash
python3 -I .claude/skills/ompi-repo-maintenance/check_links.py   # every relative link in every .md resolves
gh pr list -R The-AI-Disclosures-Project/Open-Memory-Protocol --json number,title,files \
  --jq '.[] | "#\(.number) \(.title): \([.files[].path] | join(", "))"'   # who else touches these paths
```

The `contextnest://` scheme in the Context Nest draft is a URI, not a file link; the checker skips it.

## Committing and PRs

- Subject in the repo's style: `README: …`, `docs: …`, imperative, no period. Sign off with `git commit -s` (GOVERNANCE.md asks for a DCO sign-off).
- Work on a branch from upstream `main` (`origin`), push to the fork, open the PR against `The-AI-Disclosures-Project:main`. Draft first when the change touches another author's file.
- In the PR body, name every open PR whose files overlap and say which side needs the rebase.

## Tooling notes

- `pypdf` and PyMuPDF (`fitz`) are available; `pdftoppm`, `qpdf`, `mutool` and `gs` are not. Render a page for a visual check with `page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=...)`.
- Do not use PyMuPDF redaction on Google-Docs-exported PDFs: `apply_redactions` rewrites the whole page and shifts glyphs. To change a word, edit the content stream: each glyph is its own `Td <cid> Tj`, so swap the CIDs; if the font subset lacks a glyph, switch to another subset of the same face with `/Fn size Tf` around the swapped glyphs (that is how the AIDP cover was renumbered from v1.1 to v0.2).
- Prefer asking the author for a fresh export over editing their PDF; edit only for a label the repo itself contradicts.
