#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Shared helpers for locating this repo's root and its individual
package directories (each one a directory containing setup.py or
pyproject.toml), ordered per repo.toml's [DEFAULT].sortfirst list.

Used by the release scripts in scripts/release/ and by
scripts/griffe_check.py's public-API breaking-change check."""

from collections.abc import Iterator
from itertools import chain
from pathlib import Path

from tomlkit import load


def find_projectroot(search_start: Path = Path(".")) -> Path:
    """Walks upward from search_start to the nearest directory containing
    .git or tox.ini."""
    root = search_start.resolve()
    for root in chain((root,), root.parents):
        if any((root / marker).exists() for marker in (".git", "tox.ini")):
            return root
    raise FileNotFoundError(
        "could not find project root (no .git or tox.ini) above "
        f"{search_start.resolve()}"
    )


def find_package_dirs_unordered(root_path: Path) -> Iterator[Path]:
    """Recursively yields every package directory (one containing setup.py
    or pyproject.toml) under root_path, in arbitrary order."""
    for subdir in root_path.iterdir():
        if not subdir.is_dir():
            continue
        if subdir.name.startswith(".") or subdir.name.startswith("venv"):
            continue
        if any(
            (subdir / marker).exists()
            for marker in ("setup.py", "pyproject.toml")
        ):
            yield subdir
        else:
            yield from find_package_dirs_unordered(subdir)


def find_package_dirs_ordered(root_path: Path) -> list[Path]:
    """Returns every package directory under root_path, ordered per
    repo.toml's [DEFAULT].sortfirst list."""
    with open(root_path / "repo.toml", encoding="utf-8") as file:
        sortfirst = load(file)["DEFAULT"].get("sortfirst", [])

    package_directory_paths = list(find_package_dirs_unordered(root_path))

    def keyfunc(path: Path) -> float:
        """A package directory's index in sortfirst, or infinity if it
        isn't listed."""
        path = path.relative_to(root_path)
        for idx, pattern in enumerate(sortfirst):
            if path.match(pattern):
                return idx
        return float("inf")

    package_directory_paths.sort(key=keyfunc)

    return list(dict.fromkeys(package_directory_paths))
