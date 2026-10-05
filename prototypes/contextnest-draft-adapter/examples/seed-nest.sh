#!/usr/bin/env sh
# Build a small example nest with the reference implementation.
# Usage: examples/seed-nest.sh /tmp/demo-nest
set -eu
NEST="${1:?usage: seed-nest.sh <dir>}"
mkdir -p "$NEST" && cd "$NEST"
export CONTEXTNEST_VAULT_PATH="$PWD"
ctx init -n "OMP demo nest" >/dev/null
ctx add nodes/people/sruly --type persona --title "Sruly" --tags "#person,#core" \
  --body "Works on the Open Memory Protocol at the AI Disclosures Project. Prefers short answers."
ctx add nodes/projects/omp --title "Open Memory Protocol" --tags "#project-omp,#core" \
  --body "Working group on portable agent memory. First drafts due Friday 2026-10-02. See [[Sruly]]."
ctx add nodes/projects/omp-areas --title "OMP areas of concern" --tags "#project-omp" \
  --body "Atomic unit; runtime access; user constraints and control; benchmarks; scope; reference implementations."
ctx add nodes/notes/old-deadline --title "Old deadline note" --tags "#project-omp,#archive" \
  --body "Deadline was September 30. Superseded."
mkdir -p packs
cat > packs/core.yml <<'YML'
id: core
label: Always-loaded core
query: "#core"
YML
ctx index >/dev/null
echo "seeded $NEST"
