# AI Agent Guidelines for conan-center-index (ownCloud fork)

This file provides context for AI coding agents (Claude Code, GitHub Copilot, Cursor, etc.) working in this repository.

## Repository Overview

`conan-center-index` is ownCloud's copy of [conan-io/conan-center-index](https://github.com/conan-io/conan-center-index),
carrying the Conan recipes that the ownCloud Desktop and Kiteworks Desktop clients build their
C++ dependencies from. The built packages were published to an ownCloud Artifactory Conan
remote for the desktop builds to consume.

**That remote is gone.** `artifactory.owncloud-demo.com` does not resolve (NXDOMAIN, checked
2026-09-10) and no replacement has been chosen, so the `oc` remote cannot be added, logged
into, pulled from or uploaded to. Everything can still be built from source via the `local`
remote, but there is no shared binary cache and no way to publish. Do not assume a package is
obtainable prebuilt.

- **Product family:** Desktop (ownCloud Desktop, Kiteworks Desktop)
- **Relationship to upstream:** a *detached copy*, not a GitHub fork. There is no upstream
  parent, so GitHub's cross-repository compare and "sync fork" features do not work here.
  Upstream is tracked by adding it as a plain git remote.
- **Primary language(s):** Python (Conan recipes)
- **Build system:** Conan 2
- **Test framework:** per-recipe `test_package/` consumed by `conan create` / `conan test`
- **CI system:** none in this repository. Packages are built and published by hand; see
  "Build & Test Commands" below.
- **License:** MIT, inherited from upstream (`LICENSE`, Copyright (c) 2019 Conan.io)

## Architecture & Key Paths

- `recipes/` - one directory per package, the full upstream set plus ownCloud's own. Each
  recipe is `recipes/<name>/config.yml` mapping each version to a folder, then
  `recipes/<name>/<folder>/` (usually `all/`, or a version family such as `6.x.x`) containing
  `conanfile.py`, `conandata.yml` (source URLs, checksums, patch list), an optional `patches/`
  directory and a `test_package/`
- `conanfile.py` - the root aggregator, class `GlobalDependencyMirror`. This is not a package
  recipe: it is the list of what gets built and uploaded, and the single place where the
  desktop clients' dependency versions and Qt options are pinned
- `.config/global.conf` - Conan client configuration installed with `conan config install`
  (HTTP timeout, system package manager mode)
- `.github/profiles/` - Conan profiles, one per target platform:
  `macos-latest-armv8`, `macos-latest-x86_64`, `ubuntu-latest-x86_64`, `windows-latest-x86_64`
- `docs/` - upstream's recipe authoring documentation, including `docs/adding_packages/` and
  `docs/code_of_conduct.md`
- `assets/` - upstream's images

### ownCloud-only recipes

These four have no upstream counterpart and are the entire intended local delta:

- `recipes/kdsingleapplication/` - 1.2.0, 1.1.0
- `recipes/libregraphapi/` - 1.0.4
- `recipes/qtkeychain/` - 0.15.0
- `recipes/sparkle/` - 2.7.0 (macOS only)

Everything else under `recipes/` is upstream content and should be byte-identical to upstream.

## Development Conventions

- **Branching:** `master` only; there are no maintenance branches.
- **Commit messages:** DCO sign-off required (`git commit -s`) and commits must be signed
  (`git commit -S`). Use [Conventional Commits](https://www.conventionalcommits.org/) format.
  The repository squash-merges and takes the PR title as the commit subject, so the PR title
  must follow the same format.
- **Linear history:** the org default branch policy requires it. A merge commit cannot be
  pushed to `master` - never resync upstream with `git merge`.
- **PR process:** open a PR against `master`; one approval is required and self-approval is
  not allowed.
- **Upstream recipe changes belong upstream.** Fix recipes in
  `conan-io/conan-center-index` and pick the fix up on the next resync.

## Build & Test Commands

```bash
# One-time client setup
conan config install ./.config/global.conf

# `local` must come before `oc` so recipes from this checkout beat the published ones
conan remote add local .
conan remote remove conancenter

# The two `oc` lines below CANNOT WORK today - this host is NXDOMAIN. Kept for the record
# until a replacement Artifactory URL is decided. Skip them and build from `local` only.
conan remote add oc https://artifactory.owncloud-demo.com/artifactory/api/conan/conan-local
conan remote login oc "$CONAN_USER" -p "$CONAN_PASSWORD"

# Show the resolved configuration
conan remote list
conan profile show

# Cheap gate: resolve the dependency graph without compiling anything
conan graph info . --profile=.github/profiles/macos-latest-armv8.conanprofile -s build_type=Release

# Build everything in the root conanfile.py for one profile
conan install . --profile=.github/profiles/macos-latest-armv8.conanprofile -s build_type=Release --build=missing

# Cross-compile (host and build profiles differ)
conan install . --profile:host=.github/profiles/macos-latest-x86_64.conanprofile \
  --profile:build=.github/profiles/macos-latest-armv8.conanprofile -s build_type=Release --build=missing

# Exercise a single recipe against its test_package
conan create recipes/qtkeychain/all --version=0.15.0 --build=missing

# Publish to Artifactory (blocked - see the NXDOMAIN note above)
conan upload -r oc "*" -c
```

On Windows, set `CONAN_HOME` to a short path (e.g. `D:\a\b\`) before building to stay clear
of the path length limit.

## Important Constraints

- **Never hand-edit an upstream recipe.** The local delta is meant to be exactly the four
  ownCloud-only recipes listed above. Patching an upstream recipe in place creates a conflict
  that has to be re-resolved on every resync, and historically every such patch was later
  merged upstream anyway and became dead weight. Send the fix upstream instead.
- **Resync upstream by replacing the tree, not by merging.** `master` requires linear history,
  and the repository squash-merges, so a merge commit is neither pushable nor useful. Set the
  four ownCloud recipes aside, check `recipes/`, `docs/` and `assets/` out from
  `upstream/master`, then restore them. Verify with
  `git diff --stat upstream/master -- recipes docs assets`, which must show *only* those four
  recipe trees as additions.
- **Upstream prunes old versions.** Upstream keeps only the newest patch release per minor,
  so a resync routinely deletes the exact versions the root `conanfile.py` pins and the build
  stops resolving. After every resync, re-check each `requires`/`tool_requires` against the
  relevant `recipes/<name>/config.yml` and bump as needed.
- **`cmake` must stay below 4.** `recipes/extra-cmake-modules/all/conanfile.py` pins
  `cmake/[>=3.16 <4]`, so the root `conanfile.py` cannot `tool_requires` a 4.x cmake.
- **Do not check `.github/`, `CONTRIBUTING.md` or `README.md` out from upstream.** Upstream's
  issue templates, PR template and `stale.yml` workflow were removed deliberately, and the
  README and contribution guidance here are ownCloud's.
- **License:** MIT, inherited from upstream. Recipes describe third-party software and each
  declares its own upstream license in `conanfile.py`; do not change either.
- **No CI.** Nothing verifies a change automatically. Any recipe or version change must be
  built locally on the affected profiles before it is proposed, and the platforms that were
  not covered must be named explicitly in the PR.

## OSPO Policy Constraints

### GitHub Actions
- **Only** use actions owned by `owncloud`, created by GitHub (`actions/*`), verified on the GitHub Marketplace, or verified by the ownCloud Maintainers.
- Pin all actions to their full commit SHA (not tags): `uses: actions/checkout@<SHA> # vX.Y.Z`
- Never introduce actions from unverified third parties.

### Dependency Management
- Dependabot is configured for automated dependency updates.
- Review and merge Dependabot PRs as part of regular maintenance.
- Do not introduce new dependencies without discussion in an issue first.

### Git Workflow
- **Rebase policy**: Always rebase; never create merge commits. Use `git pull --rebase` and `git rebase` before pushing.
- **Signed commits**: All commits **must** be PGP/GPG signed (`git commit -S -s`).
- **DCO sign-off**: Every commit needs a `Signed-off-by` line (`git commit -s`).
- **Conventional Commits & Squash Merge**: Use the [Conventional Commits](https://www.conventionalcommits.org/) format where the repository enforces it. Many repos use squash merge, where the PR title becomes the commit message on the default branch — apply Conventional Commits format to PR titles as well. A reusable GitHub Actions workflow enforces this.

## Context for AI Agents

- This is a Conan recipe index, not an application. Almost every file here is upstream
  content that ownCloud carries rather than maintains, so the default answer to "should I
  change this file?" is no.
- The root `conanfile.py` is the highest-leverage file in the repository: it decides which
  dependency versions the desktop clients get. Treat a change to it as a change to the
  desktop build.
- Qt is the dominant dependency, and its recipe options (`qtdeclarative`, `qtshadertools`,
  `qtwayland`, `with_egl`, `with_libjpeg`, `with_odbc`, `with_pq`, ...) move between Qt
  minors. A Qt bump is never just a version string.
- Recipe changes are expensive to verify: a full Qt build takes a long time and disk is a
  real constraint. Use `conan graph info` to check resolution first, and `conan create` on a
  single recipe rather than `conan install .` on the whole set when only one package changed.
- The `docs/` directory is upstream's recipe authoring guide and is the right reference for
  how a recipe should be written.
- Match existing recipe style, keep PRs focused, and do not refactor unrelated recipes in the
  same PR.
