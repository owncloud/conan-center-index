#!/usr/bin/env bash
# Resyncs the upstream-owned part of the tree with conan-io/conan-center-index.
#
# Usage: scripts/sync-upstream.sh [--report FILE] [REF]
#
#   REF            upstream branch or full commit to sync to, default master
#   --report FILE  write a markdown summary, the sync PR's body, to FILE
#
# Run from the repository root on a clean tree. It replaces recipes/ docs/
# assets/ .editorconfig .gitattributes LICENSE with upstream's, puts back the
# recipes listed in .sync/owncloud-recipes, re-applies .sync/patches/*.patch,
# records the upstream commit in .sync/upstream-commit and stages the result.
# It never commits.
#
# A patch that upstream has absorbed (it reverse-applies cleanly) is deleted.
# A patch that applies neither way is left in place and reported. Afterwards
# the difference to upstream must be exactly the ownCloud recipes plus the
# files the applied patches touch.
#
# Needs git and python3. UPSTREAM_URL overrides the upstream repository.
#
# Exit codes: 0 synced, 10 already up to date (nothing touched), 11 synced but
# a patch conflicted, the delta check failed or a pinned version is gone,
# 2 on bad arguments, a dirty tree, an ownCloud recipe name that upstream now
# has too, or a shared path upstream no longer has; git's code otherwise.

set -euo pipefail

die() { echo "sync-upstream: error: $*" >&2; exit 2; }

UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/conan-io/conan-center-index.git}"
UPSTREAM_WEB=https://github.com/conan-io/conan-center-index
SHARED=(recipes docs assets .editorconfig .gitattributes LICENSE)

report=/dev/null
ref=master
while [ $# -gt 0 ]; do
    case "$1" in
        --report) [ $# -ge 2 ] || die "--report needs a file"; report="$2"; shift 2 ;;
        -*) die "unknown option $1" ;;
        *) ref="$1"; shift ;;
    esac
done

[ -f .sync/upstream-commit ] && [ -f .sync/owncloud-recipes ] \
    || die "run from the repository root (no .sync/ here)"
[ -z "$(git status --porcelain)" ] || die "the working tree is not clean"

old="$(tr -d '[:space:]' < .sync/upstream-commit)"
read -r -a owncloud <<< "$(tr '\n' ' ' < .sync/owncloud-recipes)"

# Shallow: only upstream's tree is needed, not its history.
git fetch -q --depth=1 --no-tags "$UPSTREAM_URL" "$ref"
new="$(git rev-parse 'FETCH_HEAD^{commit}')"

if [ "$new" = "$old" ]; then
    echo "sync-upstream: already at $UPSTREAM_WEB/commit/$new"
    exit 10
fi

for name in "${owncloud[@]}"; do
    [ -d "recipes/$name" ] || die "recipes/$name is listed in .sync/owncloud-recipes but missing"
    if git cat-file -e "$new:recipes/$name" 2>/dev/null; then
        die "upstream now has a recipe named $name too; rename ours or drop it from .sync/owncloud-recipes"
    fi
done

# Checked before anything is deleted, so a failure cannot leave a gutted tree.
for path in "${SHARED[@]}"; do
    git cat-file -e "$new:$path" 2>/dev/null \
        || die "upstream no longer has $path; update SHARED in this script"
done

aside="$(mktemp -d)"
trap 'rm -rf "$aside"' EXIT
for name in "${owncloud[@]}"; do
    cp -R "recipes/$name" "$aside/"
done

rm -rf recipes docs assets
git checkout -q "$new" -- "${SHARED[@]}"
cp -R "$aside/." recipes/

needs_human=0
patch_rows=""
touched=""
for patch in .sync/patches/*.patch; do
    [ -e "$patch" ] || continue
    if git apply --check "$patch" 2>/dev/null; then
        git apply "$patch"
        touched="$touched$(git apply --numstat "$patch" | cut -f3)"$'\n'
        patch_rows="$patch_rows| \`$patch\` | applied |"$'\n'
    elif git apply --reverse --check "$patch" 2>/dev/null; then
        git rm -q "$patch"
        patch_rows="$patch_rows| \`$patch\` | absorbed upstream, deleted |"$'\n'
    else
        needs_human=1
        patch_rows="$patch_rows| \`$patch\` | **conflict, not applied** |"$'\n'
    fi
done

echo "$new" > .sync/upstream-commit
git add -A

expected="$( { for name in "${owncloud[@]}"; do git ls-files "recipes/$name"; done
              printf '%s' "$touched"; } | grep -v '^$' | sort -u)"
actual="$(git diff --cached --name-only "$new" -- "${SHARED[@]}" | sort -u)"
unexpected="$(comm -13 <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") | grep -v '^$' || true)"
[ -z "$unexpected" ] || needs_human=1

pins_rc=0
pins="$(python3 scripts/check-pins.py)" || pins_rc=$?
[ "$pins_rc" -le 1 ] || die "scripts/check-pins.py failed"
[ "$pins_rc" = 0 ] || needs_human=1

changed="$(git diff --cached --name-only HEAD -- recipes | cut -d/ -f2 | sort -u | wc -l | tr -d ' ')"
added="$(git diff --cached --name-only --diff-filter=A HEAD -- 'recipes/*/config.yml' | cut -d/ -f2)"
removed="$(git diff --cached --name-only --diff-filter=D HEAD -- 'recipes/*/config.yml' | cut -d/ -f2)"

names() {
    if [ -z "$1" ]; then echo "none"; else echo "$1" | sed 's/.*/`&`/' | paste -sd, - | sed 's/,/, /g'; fi
}
count() { if [ -z "$1" ]; then echo 0; else echo "$1" | wc -l | tr -d ' '; fi; }

{
    echo "Resyncs with [\`conan-io/conan-center-index@${new:0:9}\`]($UPSTREAM_WEB/commit/$new)."
    echo "Upstream changes since the last sync: [\`${old:0:9}...${new:0:9}\`]($UPSTREAM_WEB/compare/$old...$new)."
    echo
    if [ "$needs_human" = 1 ]; then
        echo "## Needs attention"
        echo
        if [ -n "$unexpected" ] || [[ "$patch_rows" == *conflict* ]]; then
            echo "- The sync is incomplete: see the local patches and the delta below. Do not merge as is."
        fi
        if [ "$pins_rc" = 1 ]; then
            echo "- Upstream removed versions that ownCloud pins (see the pinned versions below). Push the bumps to"
            echo "  this branch, since the new versions may only arrive with this sync, then mark the PR ready."
        fi
        echo
    fi
    echo "## Recipes"
    echo
    echo "$changed recipes changed, $(count "$added") added, $(count "$removed") removed."
    echo
    echo "- Added: $(names "$added")"
    echo "- Removed: $(names "$removed")"
    echo
    echo "## Local patches"
    echo
    if [ -z "$patch_rows" ]; then
        echo "None in \`.sync/patches/\`."
    else
        echo "| Patch | Status |"
        echo "| --- | --- |"
        printf '%s' "$patch_rows"
    fi
    echo
    echo "## Delta to upstream"
    echo
    if [ -z "$unexpected" ]; then
        echo "Exactly the ownCloud recipes ($(names "$(printf '%s\n' "${owncloud[@]}")")) and the files the applied patches touch."
    else
        echo "These files differ from upstream but are neither an ownCloud recipe nor touched by a patch:"
        echo
        echo "$unexpected" | sed 's/.*/- `&`/'
    fi
    echo
    echo "## Pinned versions"
    echo
    echo "$pins"
} > "$report"

echo "sync-upstream: synced ${old:0:9} -> ${new:0:9}, $changed recipes changed"
[ "$needs_human" = 0 ] || { echo "sync-upstream: needs a human, see the report" >&2; exit 11; }
