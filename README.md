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
maintained here. The intended local delta is four recipes with no upstream counterpart:

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

`master` requires linear history and the repository squash-merges, so **do not** resync with
`git merge` - a merge commit cannot be pushed. Replace the shared tree instead:

```bash
git remote add upstream https://github.com/conan-io/conan-center-index.git
git fetch upstream master
git switch -c chore/sync-upstream-recipes master

# set the ownCloud-only recipes aside
mkdir -p "$TMPDIR/oc-recipes"
cp -R recipes/kdsingleapplication recipes/libregraphapi \
      recipes/qtkeychain recipes/sparkle "$TMPDIR/oc-recipes/"

# take upstream verbatim for everything shared
rm -rf recipes docs assets
git checkout upstream/master -- recipes docs assets .editorconfig .gitattributes LICENSE

# restore the ownCloud-only recipes
cp -R "$TMPDIR/oc-recipes/." recipes/
git add -A
```

Do **not** take `README.md`, `.gitignore`, `.config/`, `conanfile.py`, `.github/profiles/` or the
community health files from upstream, and leave `CONTRIBUTING.md`, `.github/ISSUE_TEMPLATE/`,
`.github/PULL_REQUEST_TEMPLATE.md` and `.github/workflows/stale.yml` deleted.

Then check the delta is exactly what it should be:

```bash
git diff --stat upstream/master -- recipes docs assets
```

This must show **only** the four ownCloud recipe trees as additions. Anything else means an
upstream recipe is still being patched locally, which should be sent upstream instead.

Upstream keeps only the newest patch release per minor, so a resync routinely deletes the
exact versions `conanfile.py` pins. Re-check every `requires` and `tool_requires` against the
relevant `recipes/<name>/config.yml` afterwards and bump as needed. Note that `cmake` must
stay below 4 while `extra-cmake-modules` pins `cmake/[>=3.16 <4]`.

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
