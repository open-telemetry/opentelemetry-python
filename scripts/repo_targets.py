#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from itertools import chain
from pathlib import Path

from tomllib import load


def unique(elems):
    seen = set()
    for elem in elems:
        if elem not in seen:
            yield elem
            seen.add(elem)


def find_projectroot(search_start=Path(".")):
    root = search_start.resolve()
    for root in chain((root,), root.parents):
        if any((root / marker).exists() for marker in (".git", "tox.ini")):
            return root
    return None


def find_targets_unordered(rootpath):
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


def find_targets(rootpath):
    with open(rootpath / "repo.toml", "rb") as file:
        cfg = load(file)
    sortfirst = cfg["DEFAULT"].get("sortfirst", [])

    targets = list(find_targets_unordered(rootpath))

    def keyfunc(path):
        path = path.relative_to(rootpath)
        for idx, pattern in enumerate(sortfirst):
            if path.match(pattern):
                return idx
        return float("inf")

    targets.sort(key=keyfunc)

    return list(unique(targets))
