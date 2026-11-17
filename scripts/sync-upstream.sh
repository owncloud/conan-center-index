#!/usr/bin/env bash
# Resyncs the upstream-owned part of the tree with conan-io/conan-center-index.
#
# Usage: scripts/sync-upstream.sh [--report FILE] [REF]
#        scripts/sync-upstream.sh --verify
#
#   REF            upstream branch or full commit to sync to, default master
#   --report FILE  write a markdown summary, the sync PR's body, to FILE
#   --verify       check that HEAD's shared tree is exactly what a sync to
#                  .sync/upstream-commit produces, and touch nothing
#
# Run from the repository root on a clean tree, without ignored files in the
# shared paths outside the ownCloud recipes. It replaces recipes/ docs/
# assets/ .editorconfig .gitattributes LICENSE with upstream's, puts back the
# recipes listed in .sync/owncloud-recipes, re-applies .sync/patches/*.patch,
# records the upstream commit in .sync/upstream-commit and stages the result.
# It never commits.
#
# A patch that upstream has absorbed (it reverse-applies cleanly) is deleted.
# A patch that applies neither way is left in place and reported, as obsolete
# if upstream removed the files it modifies.
#
# --verify rebuilds the shared tree from upstream, HEAD's ownCloud recipes and
# HEAD's patches in a scratch index and compares it with HEAD, so an in-place
# edit of an upstream file, or a patch committed without its result, fails.
# The "Upstream tree" check runs it on every pull request.
#
# Needs git and python3. UPSTREAM_URL overrides the upstream repository.
#
# Exit codes: 0 synced or verified, 1 --verify found a difference, 10 already
# up to date (nothing touched), 11 synced but a patch did not apply or a
# pinned version is gone,
# 2 on bad arguments, a dirty tree or ignored files in the way, an ownCloud
# recipe name that upstream now has too, or a shared path upstream no longer
# has; git's code otherwise.

set -euo pipefail

die() { echo "sync-upstream: error: $*" >&2; exit 2; }

UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/conan-io/conan-center-index.git}"
UPSTREAM_WEB=https://github.com/conan-io/conan-center-index
SHARED=(recipes docs assets .editorconfig .gitattributes LICENSE)

report=/dev/null
ref=master
verify=0
while [ $# -gt 0 ]; do
    case "$1" in
        --report) [ $# -ge 2 ] || die "--report needs a file"; report="$2"; shift 2 ;;
        --verify) verify=1; shift ;;
        -*) die "unknown option $1" ;;
        *) ref="$1"; shift ;;
    esac
done

# Reads .sync/owncloud-recipes from stdin into owncloud: one name per line or
# space-separated, "#" starts a comment.
read_owncloud() {
    owncloud=()
    while IFS= read -r name; do
        owncloud+=("$name")
    done < <(sed 's/#.*//' | tr -s '[:blank:]' '\n' | grep -v '^$' || true)
}

verify() {
    local up path mode obj name patch differ
    up="$(git show HEAD:.sync/upstream-commit | tr -d '[:space:]')"
    read_owncloud < <(git show HEAD:.sync/owncloud-recipes)
    git fetch -q --depth=1 --no-tags "$UPSTREAM_URL" "$up"

    # A scratch index, so neither the real index nor the working tree changes.
    scratch="$(mktemp -d)"
    trap 'rm -rf "$scratch"' EXIT
    export GIT_INDEX_FILE="$scratch/index"
    for path in "${SHARED[@]}"; do
        case "$(git cat-file -t "$up:$path" 2>/dev/null || true)" in
            tree) git read-tree --prefix="$path/" "$up:$path" ;;
            blob)
                read -r mode _ obj _ < <(git ls-tree "$up" -- "$path")
                git update-index --add --cacheinfo "$mode,$obj,$path" ;;
            *) die "upstream $up has no $path" ;;
        esac
    done
    for name in ${owncloud[@]+"${owncloud[@]}"}; do
        git cat-file -e "HEAD:recipes/$name" 2>/dev/null \
            || die "recipes/$name is listed in .sync/owncloud-recipes but missing"
        if git cat-file -e "$up:recipes/$name" 2>/dev/null; then
            die "upstream has a recipe named $name too; rename ours or drop it from .sync/owncloud-recipes"
        fi
        git read-tree --prefix="recipes/$name/" "HEAD:recipes/$name"
    done
    while IFS= read -r patch; do
        case "$patch" in *.patch) ;; *) continue ;; esac
        git show "HEAD:$patch" | git apply --cached - \
            || die "$patch does not apply to upstream $up; fix it, or resync"
    done < <(git ls-tree --name-only HEAD -- .sync/patches/)

    differ="$(git diff --name-status "$(git write-tree)" HEAD -- "${SHARED[@]}")"
    if [ -n "$differ" ]; then
        echo "sync-upstream: these upstream files differ from conan-io/conan-center-index@${up:0:9}" >&2
        echo "with the ownCloud recipes and .sync/patches/ applied. Fix them upstream, or carry" >&2
        echo "the change as a patch in .sync/patches/ (see AGENTS.md):" >&2
        printf '%s\n' "$differ" >&2
        exit 1
    fi
    echo "sync-upstream: the shared tree matches conan-io/conan-center-index@${up:0:9}"
}

[ -f .sync/upstream-commit ] && [ -f .sync/owncloud-recipes ] \
    || die "run from the repository root (no .sync/ here)"
if [ "$verify" = 1 ]; then
    verify
    exit 0
fi
[ -z "$(git status --porcelain)" ] || die "the working tree is not clean"

old="$(tr -d '[:space:]' < .sync/upstream-commit)"
read_owncloud < .sync/owncloud-recipes

# git status --porcelain skips ignored files, but the shared tree is deleted
# wholesale below, so build output such as test_package/build/ would go too.
# The ownCloud recipes are copied aside with theirs.
ignored="$(git status --porcelain --ignored -- "${SHARED[@]}" | sed -n 's/^!! //p')"
for name in ${owncloud[@]+"${owncloud[@]}"}; do
    ignored="$(printf '%s\n' "$ignored" | grep -v "^recipes/$name/" || true)"
done
[ -z "$ignored" ] || die "ignored files would be deleted, remove them first (git clean -fdX -- ${SHARED[*]}):"$'\n'"$ignored"

# Shallow: only upstream's tree is needed, not its history.
git fetch -q --depth=1 --no-tags "$UPSTREAM_URL" "$ref"
new="$(git rev-parse 'FETCH_HEAD^{commit}')"

if [ "$new" = "$old" ]; then
    echo "sync-upstream: already at $UPSTREAM_WEB/commit/$new"
    exit 10
fi

for name in ${owncloud[@]+"${owncloud[@]}"}; do
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
for name in ${owncloud[@]+"${owncloud[@]}"}; do
    cp -R "recipes/$name" "$aside/"
done

rm -rf recipes docs assets
git checkout -q "$new" -- "${SHARED[@]}"
cp -R "$aside/." recipes/

needs_human=0
conflicted=0
patch_rows=""
for patch in .sync/patches/*.patch; do
    [ -e "$patch" ] || continue
    if git apply --check "$patch" 2>/dev/null; then
        git apply "$patch"
        patch_rows="$patch_rows| \`$patch\` | applied |"$'\n'
    elif git apply --reverse --check "$patch" 2>/dev/null; then
        git rm -q "$patch"
        patch_rows="$patch_rows| \`$patch\` | absorbed upstream, deleted |"$'\n'
    else
        needs_human=1
        conflicted=1
        # If upstream deleted or moved every file the patch modifies, it is
        # obsolete rather than in conflict; files it creates do not count.
        created="$(git apply --summary "$patch" | sed -n 's/^ create mode [0-9]* //p')"
        targets=0
        present=0
        while IFS= read -r path; do
            if printf '%s\n' "$created" | grep -qxF -- "$path"; then continue; fi
            targets=$((targets + 1))
            if [ -e "$path" ]; then present=$((present + 1)); fi
        done < <(git apply --numstat "$patch" | cut -f3)
        if [ "$targets" -gt 0 ] && [ "$present" = 0 ]; then
            patch_rows="$patch_rows| \`$patch\` | **target gone upstream, not applied:** delete or retarget it by a PR on master |"$'\n'
        else
            patch_rows="$patch_rows| \`$patch\` | **conflict, not applied** |"$'\n'
        fi
    fi
done

echo "$new" > .sync/upstream-commit
git add -A

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
        if [ "$conflicted" = 1 ]; then
            echo "- The sync is incomplete: see the local patches below. Do not merge as is."
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
    echo "## Pinned versions"
    echo
    echo "$pins"
} > "$report"

echo "sync-upstream: synced ${old:0:9} -> ${new:0:9}, $changed recipes changed"
[ "$needs_human" = 0 ] || { echo "sync-upstream: needs a human, see the report" >&2; exit 11; }
