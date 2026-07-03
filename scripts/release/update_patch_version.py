#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
from logging import INFO, basicConfig, getLogger
from os.path import basename
from pathlib import Path
from sys import path

path.insert(0, str(Path(__file__).resolve().parent.parent))

from repo_targets import find_package_dirs_unordered, find_projectroot
from tomlkit import load
from version_files import (
    OPERATORS_PATTERN,
    update_files,
    update_repo_toml_version,
    update_version_files,
)

basicConfig(level=INFO, format="%(message)s")
logger = getLogger(__name__)


def update_patch_dependencies(
    package_dirs: list[Path],
    version: str,
    prev_version: str,
    packages: list[str],
) -> None:
    """For each of package_dirs, updates its pinned dependency on packages
    from prev_version to version."""
    logger.info("updating patch dependencies")
    for pkg in packages:
        search = rf"({basename(pkg)}[^,]*?)(\s?({OPERATORS_PATTERN})\s?)(.*{prev_version})"
        replace = r"\g<1>\g<2>" + version
        logger.debug("search=%r replace=%r pkg=%r", search, replace, pkg)
        update_files(package_dirs, "pyproject.toml", search, replace)


parser = ArgumentParser(
    description="Updates version numbers during patch release, used by maintainers and CI"
)
parser.add_argument("--stable_version", required=True)
parser.add_argument("--unstable_version", required=True)
parser.add_argument("--stable_version_prev", required=True)
parser.add_argument("--unstable_version_prev", required=True)
args = parser.parse_args()

logger.info("preparing patch release")

rootpath = find_projectroot()
package_dirs = list(find_package_dirs_unordered(rootpath))

update_repo_toml_version(rootpath, "stable", args.stable_version)
update_repo_toml_version(rootpath, "prerelease", args.unstable_version)

with open(rootpath / "repo.toml", encoding="utf-8") as file:
    cfg = load(file)

packages = cfg["stable"]["packages"]
logger.info("update stable packages to %s", args.stable_version)
update_patch_dependencies(
    package_dirs, args.stable_version, args.stable_version_prev, packages
)
update_version_files(package_dirs, args.stable_version, packages)

packages = cfg["prerelease"]["packages"]
logger.info("update prerelease packages to %s", args.unstable_version)
update_patch_dependencies(
    package_dirs,
    args.unstable_version,
    args.unstable_version_prev,
    packages,
)
update_version_files(package_dirs, args.unstable_version, packages)
