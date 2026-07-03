#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Iterable, Iterator
from itertools import chain
from pathlib import Path

from tomlkit import load


def unique(elems: Iterable[Path]) -> Iterator[Path]:
    """Yields each element once, in first-seen order."""
    seen = set()
    for elem in elems:
        if elem not in seen:
            yield elem
            seen.add(elem)


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


def find_targets_unordered(rootpath: Path) -> Iterator[Path]:
    """Recursively yields every package directory (one containing setup.py
    or pyproject.toml) under rootpath, in arbitrary order."""
    for subdir in rootpath.iterdir():
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
            yield from find_targets_unordered(subdir)


def find_targets(rootpath: Path) -> list[Path]:
    """Returns every package directory under rootpath, ordered per
    repo.toml's [DEFAULT].sortfirst list."""
    with open(rootpath / "repo.toml", encoding="utf-8") as file:
        sortfirst = load(file)["DEFAULT"].get("sortfirst", [])

    targets = list(find_targets_unordered(rootpath))

    def keyfunc(path: Path) -> float:
        """A target's index in sortfirst, or infinity if it isn't
        listed."""
        path = path.relative_to(rootpath)
        for idx, pattern in enumerate(sortfirst):
            if path.match(pattern):
                return idx
        return float("inf")

    targets.sort(key=keyfunc)

    return list(unique(targets))
