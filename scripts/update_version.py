#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
from configparser import ConfigParser
from sys import exit

from repo_targets import find_projectroot, find_targets_unordered
from version_files import update_dependencies, update_version_files


def parse_args():
    parser = ArgumentParser(
        description="Updates version numbers, used by maintainers and CI"
    )
    parser.add_argument("--versions", required=True)
    return parser.parse_args()


def main():
    args = parse_args()

    print("preparing release")

    rootpath = find_projectroot()
    targets = list(find_targets_unordered(rootpath))
    cfg = ConfigParser()
    cfg.read(str(rootpath / "repo.ini"))

    for group in args.versions.split(","):
        mcfg = cfg[group]
        version = mcfg["version"]
        packages = mcfg["packages"].split()
        print(f"update {group} packages to {version}")
        update_dependencies(targets, version, packages)
        update_version_files(targets, version, packages)


if __name__ == "__main__":
    exit(main())
