#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import argparse
import sys
from configparser import ConfigParser

from repo_targets import find_projectroot, find_targets_unordered
from version_files import update_patch_dependencies, update_version_files


def parse_args():
    parser = argparse.ArgumentParser(
        description="Updates version numbers during patch release, used by maintainers and CI"
    )
    parser.add_argument("--stable_version", required=True)
    parser.add_argument("--unstable_version", required=True)
    parser.add_argument("--stable_version_prev", required=True)
    parser.add_argument("--unstable_version_prev", required=True)
    return parser.parse_args()


def main():
    args = parse_args()

    print("preparing patch release")

    rootpath = find_projectroot()
    targets = list(find_targets_unordered(rootpath))
    cfg = ConfigParser()
    cfg.read(str(rootpath / "repo.ini"))

    mcfg = cfg["stable"]
    packages = mcfg["packages"].split()
    print(f"update stable packages to {args.stable_version}")
    update_patch_dependencies(
        targets, args.stable_version, args.stable_version_prev, packages
    )
    update_version_files(targets, args.stable_version, packages)

    mcfg = cfg["prerelease"]
    packages = mcfg["packages"].split()
    print(f"update prerelease packages to {args.unstable_version}")
    update_patch_dependencies(
        targets, args.unstable_version, args.unstable_version_prev, packages
    )
    update_version_files(targets, args.unstable_version, packages)


if __name__ == "__main__":
    sys.exit(main())
