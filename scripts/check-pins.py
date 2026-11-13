#!/usr/bin/env python3
"""Checks that every version pinned by ownCloud's conanfiles still exists in recipes/.

Usage: scripts/check-pins.py [REPO_ROOT]

Scans the root conanfile.py and the conanfile.py of each recipe listed in
.sync/owncloud-recipes for requires/tool_requires/build_requires/test_requires
with a literal reference, and looks each one up in recipes/<name>/config.yml.
Upstream keeps only the newest patch release per minor, so a resync routinely
removes a version that is pinned here; for those, the newest surviving version
of the same major.minor is suggested. Plain version ranges (">=a <b") are
checked for at least one matching version; anything fancier is listed as not
checked.

Prints a markdown table. Exit codes: 0 all pins resolve, 1 at least one does
not, 2 on bad arguments. Standard library only, so it runs without Conan.
"""

import ast
import re
import sys
from pathlib import Path

REQUIRE_METHODS = {"requires", "tool_requires", "build_requires", "test_requires"}
RANGE_OPS = ("<=", ">=", "<", ">", "=")


def version_key(version):
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"[.\-+]", version))


def config_versions(recipes, name):
    config = recipes / name / "config.yml"
    if not config.is_file():
        return None
    versions = []
    in_versions = False
    for line in config.read_text().splitlines():
        if re.match(r"^versions:\s*$", line):
            in_versions = True
            continue
        if in_versions:
            if line and not line[0].isspace():
                break
            m = re.match(r"^  ['\"]?([^'\":\s]+)['\"]?:\s*$", line)
            if m:
                versions.append(m.group(1))
    return versions


def pinned_refs(conanfile):
    tree = ast.parse(conanfile.read_text(), filename=str(conanfile))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in REQUIRE_METHODS
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and "/" in node.args[0].value
        ):
            yield node.args[0].value, node.lineno


def satisfies(version, expr):
    for token in expr.split():
        op = next((o for o in RANGE_OPS if token.startswith(o)), "=")
        bound = version_key(token[len(op):] if token.startswith(op) else token)
        v = version_key(version)
        ok = {
            "<=": v <= bound,
            ">=": v >= bound,
            "<": v < bound,
            ">": v > bound,
            "=": v == bound,
        }[op]
        if not ok:
            return False
    return True


def check(ref, recipes):
    """Returns (ok, status) for one reference."""
    name, version = ref.split("@")[0].split("#")[0].split("/", 1)
    versions = config_versions(recipes, name)
    if versions is None:
        return False, f"**recipe `{name}` is gone**"
    newest = max(versions, key=version_key) if versions else None
    if version.startswith("["):
        expr = version.strip("[]")
        if any(c in expr for c in ("||", "~", "^", ",")):
            return True, "range, not checked"
        matching = [v for v in versions if satisfies(v, expr)]
        if not matching:
            return False, f"**no version matches** (newest: `{newest}`)"
        return True, f"ok, resolves to `{max(matching, key=version_key)}`"
    if version in versions:
        return True, "ok"
    minor = ".".join(version.split(".")[:2])
    same_minor = [v for v in versions if v == minor or v.startswith(minor + ".")]
    if same_minor:
        return False, f"**pruned**, bump to `{max(same_minor, key=version_key)}`"
    return False, f"**pruned, nothing left in {minor}** (newest: `{newest}`)"


def main(argv):
    if len(argv) > 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    root = Path(argv[1] if len(argv) == 2 else ".")
    recipes = root / "recipes"
    owncloud = (root / ".sync" / "owncloud-recipes").read_text().split()

    conanfiles = [root / "conanfile.py"]
    for name in owncloud:
        conanfiles += sorted(p for p in (recipes / name).glob("*/conanfile.py"))

    rows = []
    failed = 0
    for conanfile in conanfiles:
        where = conanfile.relative_to(root).as_posix()
        for ref, line in sorted(pinned_refs(conanfile), key=lambda r: r[1]):
            ok, status = check(ref, recipes)
            failed += not ok
            rows.append(f"| `{ref}` | `{where}:{line}` | {status} |")

    print("| Requirement | Declared in | Status |")
    print("| --- | --- | --- |")
    print("\n".join(rows))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
