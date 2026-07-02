#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import re
import sys
from configparser import ConfigParser
from os.path import basename

from repo_targets import find_projectroot, find_targets_unordered
from toml import load

# PEP 508 allowed specifier operators
OPERATORS = ["==", "!=", "<=", ">=", "<", ">", "===", "~=", "="]
OPERATORS_PATTERN = "|".join(re.escape(op) for op in OPERATORS)


def find(name, path):
    for root, _, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None


def filter_packages(targets, packages):
    filtered_packages = []
    for target in targets:
        for pkg in packages:
            if pkg in str(target):
                filtered_packages.append(target)
                break
    return filtered_packages


def update_version_files(targets, version, packages):
    print("updating version/__init__.py files")

    search = "__version__ .*"
    replace = f'__version__ = "{version}"'

    for target in filter_packages(targets, packages):
        version_file_path = target.joinpath(
            load(target.joinpath("pyproject.toml"))["tool"]["hatch"][
                "version"
            ]["path"]
        )

        with open(version_file_path) as file:
            text = file.read()

        if replace in text:
            print(f"{version_file_path} already contains {replace}")
            continue

        with open(version_file_path, "w", encoding="utf-8") as file:
            file.write(re.sub(search, replace, text))


def update_files(targets, filename, search, replace):
    for target in targets:
        curr_file = find(filename, target)
        if curr_file is None:
            print(f"file missing: {target}/{filename}")
            continue

        with open(curr_file, encoding="utf-8") as _file:
            text = _file.read()

        if replace in text:
            print(f"{curr_file} already contains {replace}")
            continue

        with open(curr_file, "w", encoding="utf-8") as _file:
            _file.write(re.sub(search, replace, text))


def update_dependencies(targets, version, packages):
    print("updating dependencies")
    for pkg in packages:
        search = rf"({basename(pkg)}[^,]*)({OPERATORS_PATTERN})(.*\.dev)"
        replace = r"\1\2 " + version
        update_files(targets, "pyproject.toml", search, replace)


def update_patch_dependencies(targets, version, prev_version, packages):
    print("updating patch dependencies")
    for pkg in packages:
        search = rf"({basename(pkg)}[^,]*?)(\s?({OPERATORS_PATTERN})\s?)(.*{prev_version})"
        replace = r"\g<1>\g<2>" + version
        print(f"{search=}\t{replace=}\t{pkg=}")
        update_files(targets, "pyproject.toml", search, replace)


def version_args(args):
    cfg = ConfigParser()
    cfg.read(str(find_projectroot() / "repo.ini"))
    print(cfg[args.mode]["version"])


def update_versions_args(args):
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


def update_patch_versions_args(args):
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Release version bumping helper."
    )
    subparsers = parser.add_subparsers(metavar="COMMAND")
    subparsers.required = True

    versionparser = subparsers.add_parser(
        "version", help="Get the version for a release"
    )
    versionparser.set_defaults(func=version_args)
    versionparser.add_argument("--mode", "-m", default="DEFAULT")

    releaseparser = subparsers.add_parser(
        "update_versions",
        help="Updates version numbers, used by maintainers and CI",
    )
    releaseparser.set_defaults(func=update_versions_args)
    releaseparser.add_argument("--versions", required=True)

    patchreleaseparser = subparsers.add_parser(
        "update_patch_versions",
        help="Updates version numbers during patch release, used by maintainers and CI",
    )
    patchreleaseparser.set_defaults(func=update_patch_versions_args)
    patchreleaseparser.add_argument("--stable_version", required=True)
    patchreleaseparser.add_argument("--unstable_version", required=True)
    patchreleaseparser.add_argument("--stable_version_prev", required=True)
    patchreleaseparser.add_argument("--unstable_version_prev", required=True)

    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
