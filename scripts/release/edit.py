#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Shared file-editing helpers used by update_version.py and
update_patch_version.py: rewriting repo.toml's version fields, bumping
each package's pinned dependencies, and rewriting each package's
__version__."""

from logging import getLogger
from os import walk
from os.path import join
from pathlib import Path
from re import escape, sub

from tomlkit import dump, load

logger = getLogger(__name__)

# PEP 508 allowed specifier operators
OPERATORS_PATTERN = "|".join(
    escape(op) for op in ["==", "!=", "<=", ">=", "<", ">", "===", "~=", "="]
)


def edit_version_files(
    package_directory_paths: list[Path], version: str, packages: list[str]
) -> None:
    """Rewrites __version__ to version in each package directory's version
    file, for package directories matching one of packages."""
    logger.info("updating version/__init__.py files")

    replace = f'__version__ = "{version}"'

    for package_directory_path in package_directory_paths:
        if not any(pkg in str(package_directory_path) for pkg in packages):
            continue

        with open(
            package_directory_path.joinpath("pyproject.toml"),
            encoding="utf-8",
        ) as file:
            version_file_path = package_directory_path.joinpath(
                load(file)["tool"]["hatch"]["version"]["path"]
            )

        with open(version_file_path) as file:
            text = file.read()

        if replace in text:
            logger.info("%s already contains %s", version_file_path, replace)
            continue

        with open(version_file_path, "w", encoding="utf-8") as file:
            file.write(sub("__version__ .*", replace, text))


def edit_files(
    package_directory_paths: list[Path],
    filename: str,
    search: str,
    replace: str,
) -> None:
    """Finds filename under each package directory and replaces every
    regex match of search with replace."""
    for package_directory_path in package_directory_paths:
        curr_file = None
        for root, _, files in walk(package_directory_path):
            if filename in files:
                curr_file = join(root, filename)
                break

        if curr_file is None:
            logger.warning(
                "file missing: %s/%s", package_directory_path, filename
            )
            continue

        with open(curr_file, encoding="utf-8") as _file:
            text = _file.read()

        if replace in text:
            logger.info("%s already contains %s", curr_file, replace)
            continue

        with open(curr_file, "w", encoding="utf-8") as _file:
            _file.write(sub(search, replace, text))


def edit_repo_toml_version(
    root_path: Path, section: str, version: str
) -> None:
    """Sets repo.toml's [section].version to version."""
    repo_toml_path = root_path / "repo.toml"
    with open(repo_toml_path, encoding="utf-8") as file:
        data = load(file)
    data[section]["version"] = version
    with open(repo_toml_path, "w", encoding="utf-8") as file:
        dump(data, file)
