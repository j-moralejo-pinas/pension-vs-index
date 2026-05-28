#!/bin/bash
# Pin all ci-cd-python workflow references to the current HEAD commit SHA.
# Replaces @main (or any existing @<ref>) with @<sha> so the project stays
# locked to the ci-cd-python version it was initialised with.
#
# Usage: setup-cicd-version.sh [ci_cd_repo]
#   ci_cd_repo  Owner/repo of the ci-cd source (default: j-moralejo-pinas/ci-cd-python)

set -euo pipefail

CI_CD_REPO="${1:-j-moralejo-pinas/ci-cd-python}"
WORKFLOW_DIR=".github/workflows"

if [[ ! -d "$WORKFLOW_DIR" ]]; then
    echo "  ⚠ Warning: $WORKFLOW_DIR not found, skipping ci-cd version pinning"
    exit 0
fi

echo "  Fetching HEAD commit SHA for $CI_CD_REPO..."
CI_CD_SHA=$(gh api "repos/$CI_CD_REPO/commits/main" --jq '.sha')

if [[ -z "$CI_CD_SHA" ]]; then
    echo "  ⚠ Warning: Could not retrieve commit SHA for $CI_CD_REPO, skipping version pinning"
    exit 0
fi

echo "  Pinning ci-cd-python to commit $CI_CD_SHA"

find "$WORKFLOW_DIR" -name "*.yml" -type f | while IFS= read -r file; do
    if grep -q "$CI_CD_REPO" "$file"; then
        sed -i "s|${CI_CD_REPO}/\(.*\)@[a-zA-Z0-9_./\-]*|${CI_CD_REPO}/\1@${CI_CD_SHA}|g" "$file"
        echo "  ✓ Pinned $file"
    fi
done

echo "  ✓ ci-cd-python version pinned to $CI_CD_SHA"
