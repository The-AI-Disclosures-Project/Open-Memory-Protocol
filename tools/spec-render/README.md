# Spec render

`working-group/exchange-and-runtime/working-spec.md` is the only copy of the working spec that anyone edits. This folder turns it into a styled HTML page and an EPUB with [pandoc](https://pandoc.org).

The file name carries no date or version. The version lives in the spec itself, on the bold line under the title (for example `**Editors' draft v0.5, 2026-11-06**`). The renderer reads that line and puts it in the page header.

## Build locally

You need pandoc 3.11 or later.

```sh
tools/spec-render/render.sh
```

The output lands in `dist/`, which git ignores.

## What CI does

`.github/workflows/render-spec.yml` runs the same script in the `pandoc/core` container.

- On a pull request that touches the spec, it uploads the HTML and EPUB as a build artifact you can download from the run.
- On a tag such as `v0.5`, it attaches both files to the GitHub release for that tag. The build fails if the tag doesn't match the version written in the spec.

## Files

- `spec.lua` reads the title and version, styles status markers like `[agreed]` and RFC 2119 keywords, and rewrites relative links to GitHub links.
- `template.html`, `spec.css` and `spec.js` make up the HTML page. The page is one self-contained file with no web fonts or outside requests.
- `epub.css` holds the small set of EPUB styles.
