#!/bin/sh
# Render the working spec from Markdown to standalone HTML and EPUB.
#
#   tools/spec-render/render.sh            # writes dist/
#   SPEC_TAG=v0.5 tools/spec-render/render.sh
#
# SPEC_TAG, when set, must match the version written in the spec.
# SPEC_COMMIT defaults to the current git commit when git is available.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
cd "$root"

src="working-group/exchange-and-runtime/working-spec.md"
out="${SPEC_OUT:-dist}"
repo="${SPEC_REPO_URL:-https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol}"
tag="${SPEC_TAG:-}"
commit="${SPEC_COMMIT:-}"
if [ -z "$commit" ] && command -v git >/dev/null 2>&1; then
  commit=$(git rev-parse HEAD 2>/dev/null || true)
fi
short=$(printf '%s' "$commit" | cut -c1-7)
ref="${tag:-${commit:-main}}"

mkdir -p "$out"

set -- \
  "$src" --from=gfm \
  --lua-filter="$here/spec.lua" \
  --metadata=source_path:"$src" \
  --metadata=repo_url:"$repo" \
  --metadata=build_commit:"$commit" \
  --metadata=build_commit_short:"$short" \
  --metadata=source_url:"$repo/blob/$ref/$src" \
  --metadata=expected_version:"$tag"

pandoc "$@" \
  --to=html5 --standalone \
  --template="$here/template.html" \
  --toc --toc-depth=3 \
  --syntax-highlighting=none \
  --output="$out/working-spec.html"

pandoc "$@" \
  --to=epub3 \
  --toc --toc-depth=2 \
  --css="$here/epub.css" \
  --output="$out/working-spec.epub"

echo "Wrote $out/working-spec.html and $out/working-spec.epub"
