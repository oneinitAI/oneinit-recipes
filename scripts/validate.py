#!/usr/bin/env python3
"""Validate the OneInit recipe registry.

Checks:
  1. Every YAML recipe in recipes/<name>/<version>.yaml is well-formed
     and matches the expected schema (name, version, platforms, sha256,
     install_type, path layout).
  2. INDEX.json is consistent with the recipes/ directory:
       - every package/version in INDEX.json has a recipe file
       - every recipe file has an entry in INDEX.json
       - INDEX.json `latest` matches an existing version
  3. sha256 fields are 64-char lowercase hex.
  4. install_type is one of the supported values.

Exit code 0 = valid, 1 = invalid (blocks the PR).
"""

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent

VALID_INSTALL_TYPES = {
    "zip_extract",
    "tar_extract",
    "exe_silent",
    "binary_copy",
    "msi_install",
    "pkg_install",
}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA512_RE = re.compile(r"^[0-9a-f]{128}$")

errors: list[str] = []


def error(msg: str) -> None:
    errors.append(msg)
    print(f"  [FAIL] {msg}")


def validate_recipe(path: Path) -> None:
    """Validate a single recipe YAML file."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        error(f"{path}: invalid YAML: {e}")
        return

    if not isinstance(data, dict):
        error(f"{path}: recipe must be a YAML mapping")
        return

    name = data.get("name")
    version = data.get("version")
    if not name or not isinstance(name, str):
        error(f"{path}: missing or invalid `name` (string required)")
        return
    if not version or not isinstance(version, str):
        error(f"{path}: missing or invalid `version` (string required)")
        return

    # Path layout must match: recipes/<name>/<version>.yaml
    parts = path.relative_to(ROOT / "recipes").parts
    if len(parts) != 2:
        error(f"{path}: expected layout recipes/<name>/<version>.yaml")
        return
    dir_name, file_name = parts[0], parts[1]
    if dir_name != name:
        error(f"{path}: directory name '{dir_name}' != recipe name '{name}'")
    if file_name != f"{version}.yaml":
        error(f"{path}: file name '{file_name}' != version '{version}.yaml'")

    platforms = data.get("platforms")
    if not isinstance(platforms, dict) or not platforms:
        error(f"{path}: `platforms` must be a non-empty mapping")
        return

    for plat, cfg in platforms.items():
        if not isinstance(cfg, dict):
            error(f"{path}: platform '{plat}' must be a mapping")
            continue
        url = cfg.get("url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            error(f"{path}: platform '{plat}' has invalid `url`")
        sha = cfg.get("sha256")
        sha_valid = (
            isinstance(sha, str)
            and (SHA256_RE.match(sha) or SHA512_RE.match(sha))
        )
        if not sha_valid:
            error(f"{path}: platform '{plat}' has invalid `sha256` "
                  f"(expect 64-char hex SHA256 or 128-char hex SHA512, got {sha!r})")
        itype = cfg.get("install_type")
        if itype not in VALID_INSTALL_TYPES:
            error(f"{path}: platform '{plat}' has unsupported `install_type` "
                  f"{itype!r} (allowed: {', '.join(sorted(VALID_INSTALL_TYPES))})")
        ipath = cfg.get("install_path")
        if not isinstance(ipath, str) or not ipath:
            error(f"{path}: platform '{plat}' requires a non-empty `install_path`")

    maintainer = data.get("maintainer")
    if not isinstance(maintainer, dict) or not maintainer.get("github"):
        error(f"{path}: `maintainer.github` is required")

    # license 字段（可选，但若提供需合法）
    license_name = data.get("license")
    license_url = data.get("license_url")
    if license_name is not None and not isinstance(license_name, str):
        error(f"{path}: `license` must be a string")
    if license_url is not None:
        if not isinstance(license_url, str) or not license_url.startswith(
            ("https://", "http://")
        ):
            error(f"{path}: `license_url` must be an http(s) URL")
    if license_url and not license_name:
        # 只有 URL 也可以（提示查看）
        pass

    # verified 字段（可选，bool；作者自标 + CI 复核）
    verified = data.get("verified")
    if verified is not None and not isinstance(verified, bool):
        error(f"{path}: `verified` must be a boolean (true/false)")


def validate_index() -> None:
    """Validate INDEX.json against the recipes/ directory."""
    index_path = ROOT / "INDEX.json"
    if not index_path.exists():
        error("INDEX.json missing")
        return

    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        error(f"INDEX.json is invalid JSON: {e}")
        return

    packages = index.get("packages")
    if not isinstance(packages, dict):
        error("INDEX.json: `packages` must be an object")
        return

    # Collect all recipe files on disk
    on_disk: dict[str, set[str]] = {}
    recipes_dir = ROOT / "recipes"
    for p in sorted(recipes_dir.glob("*/*.yaml")):
        pkg = p.parent.name
        ver = p.stem
        on_disk.setdefault(pkg, set()).add(ver)

    # Check each INDEX entry has matching files
    for pkg, entry in packages.items():
        if not isinstance(entry, dict):
            error(f"INDEX.json: entry for '{pkg}' must be an object")
            continue
        versions = entry.get("versions")
        if not isinstance(versions, list) or not versions:
            error(f"INDEX.json: '{pkg}' requires a non-empty `versions` array")
            continue
        latest = entry.get("latest")
        if latest not in versions:
            error(f"INDEX.json: '{pkg}' `latest` ({latest!r}) must be in `versions`")
        for ver in versions:
            if pkg not in on_disk or ver not in on_disk[pkg]:
                error(f"INDEX.json: '{pkg}@{ver}' has no recipes/{pkg}/{ver}.yaml")

    # Check every file on disk is listed in INDEX
    for pkg, vers in on_disk.items():
        if pkg not in packages:
            error(f"recipes/{pkg}/ exists but is missing from INDEX.json `packages`")
            continue
        listed = set(packages[pkg].get("versions", []))
        for ver in vers:
            if ver not in listed:
                error(f"recipes/{pkg}/{ver}.yaml exists but is not in "
                      f"INDEX.json `{pkg}.versions`")


def main() -> int:
    print("Validating OneInit recipe registry...")

    recipes_dir = ROOT / "recipes"
    recipe_files = sorted(recipes_dir.glob("*/*.yaml"))
    if not recipe_files:
        error("no recipes found under recipes/")

    for p in recipe_files:
        print(f"  Recipe: {p.relative_to(ROOT)}")
        validate_recipe(p)

    print("  INDEX.json consistency:")
    validate_index()

    if errors:
        print(f"\n{len(errors)} validation error(s) found:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"\nOK: {len(recipe_files)} recipe(s) validated. Registry is consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
