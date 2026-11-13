# conan-center-index (ownCloud)

ownCloud's copy of [Conan Center Index](https://github.com/conan-io/conan-center-index),
carrying the Conan recipes that the ownCloud Desktop and Kiteworks Desktop clients build
their C++ dependencies from. The packages built here were published to an ownCloud
Artifactory Conan remote for the desktop builds to consume - **that remote no longer
resolves and its replacement has not been decided**, so today this repository is the
recipe source and nothing more. See "Building locally" below.

This is a **detached copy, not a GitHub fork.** It has no upstream parent, so GitHub's
"Sync fork" button and cross-repository compare do not work on it. Upstream is tracked by
adding it as an ordinary git remote.

Almost everything under `recipes/` is upstream content that is carried rather than
maintained here. The intended local delta is four recipes with no upstream counterpart,
plus the patches in `.sync/patches/` that are carried until upstream takes them:

| Recipe | Versions |
| --- | --- |
| `kdsingleapplication` | 1.2.0, 1.1.0 |
| `libregraphapi` | 1.0.4 |
| `qtkeychain` | 0.15.0 |
| `sparkle` | 2.7.0 (macOS only) |

Plus the ownCloud-specific plumbing: `conanfile.py`, `.config/global.conf` and `.github/profiles/`.

## Layout

- `conanfile.py` - the root aggregator (`GlobalDependencyMirror`). Not a package recipe: it
  is the list of what gets built and uploaded, and the single place where the desktop
  clients' dependency versions and Qt options are pinned.
- `recipes/<name>/config.yml` - maps each version of a package to a recipe folder, then
  `recipes/<name>/<folder>/` holds `conanfile.py`, `conandata.yml`, optional `patches/` and a
  `test_package/`.
- `.config/global.conf` - Conan client configuration.
- `.github/profiles/` - one Conan profile per target platform.
- `docs/` - upstream's recipe authoring documentation.

## Building locally

This repository has no CI. Packages are built and published by hand with the commands
below, which were previously carried by `.github/workflows/conan.yml`.

> **The Artifactory remote below does not currently exist.**
> `artifactory.owncloud-demo.com` does not resolve (NXDOMAIN, checked 2026-09-10), so the
> `oc` remote cannot be added, logged into, pulled from or uploaded to. The URL is recorded
> here because it is the one the build used; the replacement has not been decided. Until it
> is, only the `local` remote works, which is enough to build everything from source but
> means no shared binary cache and no publishing.

### One-time setup

```bash
conan config install ./.config/global.conf

# `local` must be added before `oc` so that recipes from this checkout take
# precedence over the ones already published to Artifactory.
conan remote add local .
conan remote remove conancenter
conan remote add oc https://artifactory.owncloud-demo.com/artifactory/api/conan/conan-local
conan remote login oc "$CONAN_USER" -p "$CONAN_PASSWORD"

conan remote list
conan profile show
```

See the [Conan documentation on building binaries from a private conan-center-index
fork](https://docs.conan.io/2/devops/devops_local_recipes_index.html#building-binaries-from-a-private-conan-center-index-fork)
for the background on this layout.

On Windows, set `CONAN_HOME` to a short path first to stay clear of the path length
limit:

```powershell
$Env:CONAN_HOME = "D:\a\b\"
```

### Build

Pick a profile from `.github/profiles/` and a build type (`Release`, `RelWithDebInfo`, `Debug`):

```bash
conan install . --profile=.github/profiles/macos-latest-armv8.conanprofile \
  -s build_type=Release --build=missing
```

To cross-compile, pass the host and build profiles separately:

```bash
conan install . --profile:host=.github/profiles/macos-latest-x86_64.conanprofile \
  --profile:build=.github/profiles/macos-latest-armv8.conanprofile \
  -s build_type=Release --build=missing
```

Use `conan graph info . --profile=<profile> -s build_type=<type>` to check that the
dependencies in `conanfile.py` resolve before starting an expensive build.

### Publish

Blocked until the Artifactory remote exists again (see the note above).

```bash
conan upload -r oc "*" -c
```

## Resyncing with upstream

The [Sync upstream](.github/workflows/sync-upstream.yml) workflow does this every Monday,
and on demand from the Actions tab. It opens, or updates, a single pull request from
`chore/sync-upstream` titled `chore: sync recipes with upstream conan-center-index`. A human
reviews and squash-merges it. If anyone else pushes a commit to that branch, the workflow
stops updating the PR until it is merged or closed.

The workflow authenticates as a GitHub App, because a pull request opened with the default
`GITHUB_TOKEN` would not trigger the required checks. The app needs read and write access to
contents and pull requests on this repository. Its client ID and private key go in the
repository secrets `SYNC_APP_CLIENT_ID` and `SYNC_APP_PRIVATE_KEY`.

The workflow runs [`scripts/sync-upstream.sh`](scripts/sync-upstream.sh), which also works
locally from a clean checkout:

```bash
git switch -c chore/sync-upstream-recipes master
scripts/sync-upstream.sh --report "$TMPDIR/sync.md"   # stages the result, never commits
```

`master` requires linear history and the repository squash-merges, so the sync **replaces
the shared tree** rather than merging: it checks `recipes/` `docs/` `assets/`
`.editorconfig` `.gitattributes` `LICENSE` out from upstream verbatim, then restores the
ownCloud-only recipes and re-applies the local patches. `README.md`, `.gitignore`,
`.config/`, `conanfile.py`, `.github/` and the community health files are never taken
from upstream.

Its state lives in `.sync/`:

- `.sync/upstream-commit` - the upstream commit of the last sync.
- `.sync/owncloud-recipes` - the recipes that exist only here. The sync fails if upstream
  gains a recipe with one of these names.
- `.sync/patches/*.patch` - changes to upstream recipes that are carried until upstream
  takes them. A patch that upstream has absorbed is deleted automatically. A patch that no
  longer applies is reported, and the PR is opened as a draft.

The sync then checks that the difference to upstream is exactly the ownCloud recipes plus
the patched files.

Upstream keeps only the newest patch release per minor, so a resync routinely deletes the
exact versions `conanfile.py` pins. [`scripts/check-pins.py`](scripts/check-pins.py)
lists every pin that no longer resolves, with the version to bump to, in the PR body. The
workflow also adds `conan graph info` results for every profile, and opens the PR as a draft
while any pin is broken. Push the bumps to the sync branch itself, because the new versions
often arrive only with the sync; that also stops the workflow from replacing the branch.
Then mark the PR ready. Note that `cmake` must stay below 4 while `extra-cmake-modules` pins
`cmake/[>=3.16 <4]`.

## Contributing

Changes to an upstream recipe belong
[upstream](https://github.com/conan-io/conan-center-index); see upstream's
[CONTRIBUTING.md](https://github.com/conan-io/conan-center-index/blob/master/CONTRIBUTING.md)
and the `docs/` directory here for how recipes are written and reviewed. Fixes merged
upstream arrive here on the next resync.

Changes to the four ownCloud-only recipes, to `conanfile.py`, or to the plumbing are made
here by pull request against `master`. Commits must be signed and DCO signed-off
(`git commit -S -s`), and commit subjects and PR titles follow
[Conventional Commits](https://www.conventionalcommits.org/).

- [AGENTS.md](AGENTS.md) - guidance for AI coding agents working in this repository
- [SUPPORT.md](SUPPORT.md) - where to ask questions and which tracker to use
- [SECURITY.md](SECURITY.md) - how to report a vulnerability

## License

MIT, inherited from upstream - see [LICENSE](LICENSE). The recipes describe third-party
software; each declares that software's own license in its `conanfile.py`.
