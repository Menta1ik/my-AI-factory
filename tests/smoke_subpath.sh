#!/usr/bin/env bash
# Smoke test for subpath: + Cursor .mdc generation.
#
# Steps:
#   1. Stage factory.py + catalog.yaml in a temp working dir.
#   2. Run `factory.py install --package software` (clones repos, copies skills).
#   3. Assert:
#      a. Only the frontend-design subfolder was extracted from anthropics/claude-code,
#         not the whole monorepo (no top-level README.md from anthropics/claude-code
#         in .agent/skills/frontend-design/).
#      b. .agent/skills/frontend-design/SKILL.md exists and is non-empty.
#      c. .cursor/rules/frontend-design.mdc exists and has valid frontmatter
#         (description + alwaysApply).
#
# Exit non-zero on any failed assertion. Cleans up temp dir on exit.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK_DIR="$(mktemp -d -t ai-factory-smoke.XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT

echo ">> Smoke test workdir: $WORK_DIR"

cp "$REPO_ROOT/factory.py" "$WORK_DIR/"
cp "$REPO_ROOT/catalog.yaml" "$WORK_DIR/"

cd "$WORK_DIR"
python3 factory.py install --package software >install.log 2>&1 || {
    echo "!! factory.py install failed — log:" >&2
    tail -40 install.log >&2
    exit 1
}

fail=0
check() {
    local label="$1"; shift
    if "$@"; then
        echo "   ok  - $label"
    else
        echo "   FAIL - $label" >&2
        fail=1
    fi
}

skill_dir="$WORK_DIR/.agent/skills/frontend-design"
mdc_file="$WORK_DIR/.cursor/rules/frontend-design.mdc"

check "skill dir exists"          test -d "$skill_dir"
check "SKILL.md is present"       test -s "$skill_dir/SKILL.md"
check "no monorepo README leak"   bash -c '! test -f "'"$skill_dir"'/README.md" || ! grep -q "Claude Code" "'"$skill_dir"'/README.md"'
check ".mdc file generated"       test -s "$mdc_file"
check ".mdc has frontmatter"      bash -c 'head -1 "'"$mdc_file"'" | grep -q "^---$"'
check ".mdc has description"      grep -q "^description:" "$mdc_file"
check ".mdc has alwaysApply"      grep -q "^alwaysApply:" "$mdc_file"

if [ "$fail" -ne 0 ]; then
    echo
    echo "Smoke test FAILED. install.log tail:" >&2
    tail -20 install.log >&2
    exit 1
fi

echo
echo "Smoke test PASSED."
