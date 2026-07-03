#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import sys
from argparse import ArgumentParser
from pathlib import Path
from sys import exit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from repo_targets import find_projectroot, find_targets_unordered
from tomlkit import load
from version_files import (
    update_dependencies,
    update_repo_toml_version,
    update_version_files,
)


def parse_args():
    parser = ArgumentParser(
        description="Updates version numbers, used by maintainers and CI"
    )
    parser.add_argument("--stable_version", required=True)
    parser.add_argument("--unstable_version", required=True)
    return parser.parse_args()


def main():
    args = parse_args()

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
        update_dependencies(targets, version, packages)
        update_version_files(targets, version, packages)


if __name__ == "__main__":
    exit(main())
