#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
from os.path import basename
from pathlib import Path
from sys import path

path.insert(0, str(Path(__file__).resolve().parent.parent))

from repo_targets import find_projectroot, find_targets_unordered
from tomlkit import load
from version_files import (
    OPERATORS_PATTERN,
    update_files,
    update_repo_toml_version,
    update_version_files,
)


def update_patch_dependencies(
    targets: list[Path],
    version: str,
    prev_version: str,
    packages: list[str],
) -> None:
    print("updating patch dependencies")
    for pkg in packages:
        search = rf"({basename(pkg)}[^,]*?)(\s?({OPERATORS_PATTERN})\s?)(.*{prev_version})"
        replace = r"\g<1>\g<2>" + version
        print(f"{search=}\t{replace=}\t{pkg=}")
        update_files(targets, "pyproject.toml", search, replace)


parser = ArgumentParser(
    description="Updates version numbers during patch release, used by maintainers and CI"
)
parser.add_argument("--stable_version", required=True)
parser.add_argument("--unstable_version", required=True)
parser.add_argument("--stable_version_prev", required=True)
parser.add_argument("--unstable_version_prev", required=True)
args = parser.parse_args()

print("preparing patch release")

rootpath = find_projectroot()
targets = list(find_targets_unordered(rootpath))

update_repo_toml_version(rootpath, "stable", args.stable_version)
update_repo_toml_version(rootpath, "prerelease", args.unstable_version)

with open(rootpath / "repo.toml", encoding="utf-8") as file:
    cfg = load(file)

packages = cfg["stable"]["packages"]
print(f"update stable packages to {args.stable_version}")
update_patch_dependencies(
    targets, args.stable_version, args.stable_version_prev, packages
)
update_version_files(targets, args.stable_version, packages)

packages = cfg["prerelease"]["packages"]
print(f"update prerelease packages to {args.unstable_version}")
update_patch_dependencies(
    targets, args.unstable_version, args.unstable_version_prev, packages
)
update_version_files(targets, args.unstable_version, packages)
