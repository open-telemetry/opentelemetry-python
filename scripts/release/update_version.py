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

parser = ArgumentParser(
    description="Updates version numbers, used by maintainers and CI"
)
parser.add_argument("--stable_version", required=True)
parser.add_argument("--unstable_version", required=True)
args = parser.parse_args()

print("preparing release")

rootpath = find_projectroot()
targets = list(find_targets_unordered(rootpath))

update_repo_toml_version(rootpath, "stable", args.stable_version)
update_repo_toml_version(rootpath, "prerelease", args.unstable_version)

with open(rootpath / "repo.toml", encoding="utf-8") as file:
    cfg = load(file)

for group, version in (
    ("stable", args.stable_version),
    ("prerelease", args.unstable_version),
):
    packages = cfg[group]["packages"]
    print(f"update {group} packages to {version}")

    print("updating dependencies")
    for pkg in packages:
        update_files(
            targets,
            "pyproject.toml",
            rf"({basename(pkg)}[^,]*)({OPERATORS_PATTERN})(.*\.dev)",
            r"\1\2 " + version,
        )

    update_version_files(targets, version, packages)
