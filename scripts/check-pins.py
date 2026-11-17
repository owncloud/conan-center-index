#!/usr/bin/env python3
"""Checks that every version pinned by ownCloud's conanfiles still exists in recipes/.

Usage: scripts/check-pins.py [REPO_ROOT]

Scans the root conanfile.py, if there is one, and the conanfile.py of each recipe listed in
.sync/owncloud-recipes for requires/tool_requires/build_requires/test_requires,
as method calls or class attributes, and looks each literal reference up in
recipes/<name>/config.yml. A reference built at runtime is listed as not
checked. Pins inside upstream recipes are not scanned here; the sync
workflow's conan graph info covers those.
Upstream keeps only the newest patch release per minor, so a resync routinely
removes a version that is pinned here; for those, the newest surviving version
of the same major.minor is suggested. Plain version ranges (">=a <b") are
checked for at least one matching version other than a pre-release, as Conan 2
does by default; core.version_ranges:resolve_prereleases is not read. Anything
fancier is listed as not checked.

Prints a markdown table. Exit codes: 0 all pins resolve, 1 at least one does
not, 2 on bad arguments, 3 if a file could not be read or parsed. Standard
library only, so it runs without Conan.
"""

import ast
import functools
import re
import sys
import traceback
from pathlib import Path

REQUIRE_METHODS = {"requires", "tool_requires", "build_requires", "test_requires"}
RANGE_OPS = ("<=", ">=", "<", ">", "=")


@functools.total_ordering
class _Item:
    """One dot-separated part of a version, compared the way Conan's Version does."""

    def __init__(self, text):
        self.value = int(text) if text.isdigit() else text

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        try:
            return self.value < other.value
        except TypeError:
            return str(self.value) < str(other.value)


def _items(text):
    items = [_Item(p) for p in text.split(".")] if text else []
    while items and items[-1].value == 0:
        items.pop()
    return tuple(items)


def is_prerelease(version):
    return "-" in version.rsplit("+", 1)[0]


def version_key(version):
    """Sorts like Conan 2's Version: trailing zeros do not count (1.4 == 1.4.0), and a
    pre-release comes before its release (2.0.0-beta < 2.0.0)."""
    main, plus, build = version.rpartition("+")
    if not plus:
        main, build = version, ""
    main, pre_sep, pre = main.partition("-")
    return (_items(main), 0 if pre_sep else 1, _items(pre), _items(build))


def config_versions(recipes, name):
    config = recipes / name / "config.yml"
    if not config.is_file():
        return None
    versions = []
    in_versions = False
    indent = None
    for line in config.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"""^(versions|"versions"|'versions'):\s*$""", line):
            in_versions = True
            continue
        if in_versions:
            if not line[0].isspace():
                break
            depth = len(line) - len(line.lstrip())
            indent = depth if indent is None else indent
            m = re.match(r"^\s+['\"]?([^'\":\s]+)['\"]?:\s*$", line)
            if depth == indent and m:
                versions.append(m.group(1))
    return versions


def literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def pinned_refs(conanfile):
    """Yields (reference or None, line) for each requirement; None if it is not a literal."""
    tree = ast.parse(conanfile.read_text(), filename=str(conanfile))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in REQUIRE_METHODS
            and node.args
        ):
            yield literal(node.args[0]), node.lineno
        elif isinstance(node, ast.ClassDef):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    targets = stmt.targets
                elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                    targets = [stmt.target]
                else:
                    continue
                if any(isinstance(t, ast.Name) and t.id in REQUIRE_METHODS for t in targets):
                    values = stmt.value.elts if isinstance(stmt.value, (ast.Tuple, ast.List)) else [stmt.value]
                    for value in values:
                        yield literal(value), value.lineno


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
        # Conan 2 resolves a range to a pre-release only when asked to.
        matching = [v for v in versions if not is_prerelease(v) and satisfies(v, expr)]
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
    lines = (root / ".sync" / "owncloud-recipes").read_text().splitlines()
    owncloud = [name for line in lines for name in line.split("#", 1)[0].split()]

    conanfiles = [root / "conanfile.py"] if (root / "conanfile.py").is_file() else []
    for name in owncloud:
        conanfiles += sorted(p for p in (recipes / name).glob("*/conanfile.py"))

    rows = []
    failed = 0
    for conanfile in conanfiles:
        where = conanfile.relative_to(root).as_posix()
        for ref, line in sorted(pinned_refs(conanfile), key=lambda r: r[1]):
            if ref is None or "/" not in ref:
                rows.append(f"| {f'`{ref}`' if ref else 'computed'} | `{where}:{line}` | not a literal reference, not checked |")
                continue
            ok, status = check(ref, recipes)
            failed += not ok
            rows.append(f"| `{ref}` | `{where}:{line}` | {status} |")

    print("| Requirement | Declared in | Status |")
    print("| --- | --- | --- |")
    print("\n".join(rows))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:  # noqa: BLE001 - a crash must not read as "pins pruned" (exit 1)
        traceback.print_exc()
        sys.exit(3)
