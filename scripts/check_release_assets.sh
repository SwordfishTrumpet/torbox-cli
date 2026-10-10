#!/usr/bin/env bash
# check_release_assets.sh — assert a GitHub release carries exactly the artifacts
# this repository built (issue #53).
#
# `uv build` seeds dist/ with a .gitignore, and the release workflow uploaded the
# whole directory, so every release page offered a `default.gitignore` download
# next to the wheel, the source archive and requirements.lock.txt. The workflow
# removes the dotfile before uploading and then runs this check against the
# published release, so an unexpected asset fails the release job.
#
# Usage: scripts/check_release_assets.sh <tag>
# Requires: gh (authenticated), and a dist/ directory from `uv build`.
set -euo pipefail

tag=${1:?usage: check_release_assets.sh <tag>}

if [ ! -d dist ]; then
  echo "check_release_assets: dist/ not found; run uv build first" >&2
  exit 2
fi

expected="$(
  for f in dist/*.whl dist/*.tar.gz requirements.lock.txt; do basename "$f"; done \
    | sort | paste -sd, -
)"
actual="$(gh release view "$tag" --json assets --jq '[.assets[].name] | sort | join(",")')"

if [ "$actual" != "$expected" ]; then
  echo "check_release_assets: release $tag carries unexpected assets" >&2
  echo "  expected: $expected" >&2
  echo "  actual:   $actual" >&2
  exit 1
fi

echo "check_release_assets: release $tag carries exactly: $expected"
