#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Bumps repo.toml's stable/prerelease versions, along with every
dependency pin and __version__ file currently pinned to a ".dev"
version, to the given new version. Used both to finalize a release
branch's version and, separately, to advance main to the next dev
version right after a release branch is cut.

Example, given --stable_version=1.45.0:

repo.toml, before:
    [stable]
    version = "1.44.0.dev"
after:
    [stable]
    version = "1.45.0"

opentelemetry-sdk/pyproject.toml, before:
    dependencies = [
      "opentelemetry-api == 1.44.0.dev",
    ]
after:
    dependencies = [
      "opentelemetry-api == 1.45.0",
    ]

opentelemetry-sdk/src/opentelemetry/sdk/version/__init__.py, before:
    __version__ = "1.44.0.dev"
after:
    __version__ = "1.45.0"
"""

from argparse import ArgumentParser
from logging import INFO, basicConfig, getLogger
from os.path import basename
from pathlib import Path
from sys import path

path.insert(0, str(Path(__file__).resolve().parent.parent))

from edit import (
    OPERATORS_PATTERN,
    edit_files,
    edit_repo_toml_version,
    edit_version_files,
)
from find import find_package_dirs_unordered, find_projectroot
from tomlkit import load

basicConfig(level=INFO, format="%(message)s")
logger = getLogger(__name__)

parser = ArgumentParser(
    description="Updates version numbers, used by maintainers and CI"
)
parser.add_argument("--stable_version", required=True)
parser.add_argument("--unstable_version", required=True)
args = parser.parse_args()

logger.info("preparing release")

root_path = find_projectroot()
package_directory_paths = list(find_package_dirs_unordered(root_path))

edit_repo_toml_version(root_path, "stable", args.stable_version)
edit_repo_toml_version(root_path, "prerelease", args.unstable_version)

with open(root_path / "repo.toml", encoding="utf-8") as file:
    cfg = load(file)

for group, version in (
    ("stable", args.stable_version),
    ("prerelease", args.unstable_version),
):
    packages = cfg[group]["packages"]
    logger.info("update %s packages to %s", group, version)

    logger.info("updating dependencies")
    for pkg in packages:
        edit_files(
            package_directory_paths,
            "pyproject.toml",
            rf"({basename(pkg)}[^,]*)({OPERATORS_PATTERN})(.*\.dev)",
            r"\1\2 " + version,
        )

    edit_version_files(package_directory_paths, version, packages)
