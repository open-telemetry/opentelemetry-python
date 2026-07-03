#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from os import walk
from os.path import join
from pathlib import Path
from re import escape, sub

from tomlkit import dump, load

# PEP 508 allowed specifier operators
OPERATORS = ["==", "!=", "<=", ">=", "<", ">", "===", "~=", "="]
OPERATORS_PATTERN = "|".join(escape(op) for op in OPERATORS)


def update_version_files(
    targets: list[Path], version: str, packages: list[str]
) -> None:
    print("updating version/__init__.py files")

    replace = f'__version__ = "{version}"'

    for target in targets:
        if not any(pkg in str(target) for pkg in packages):
            continue

        with open(target.joinpath("pyproject.toml"), encoding="utf-8") as file:
            version_file_path = target.joinpath(
                load(file)["tool"]["hatch"]["version"]["path"]
            )

        with open(version_file_path) as file:
            text = file.read()

        if replace in text:
            print(f"{version_file_path} already contains {replace}")
            continue

        with open(version_file_path, "w", encoding="utf-8") as file:
            file.write(sub("__version__ .*", replace, text))


def update_files(
    targets: list[Path], filename: str, search: str, replace: str
) -> None:
    for target in targets:
        curr_file = None
        for root, _, files in walk(target):
            if filename in files:
                curr_file = join(root, filename)
                break

        if curr_file is None:
            print(f"file missing: {target}/{filename}")
            continue

        with open(curr_file, encoding="utf-8") as _file:
            text = _file.read()

        if replace in text:
            print(f"{curr_file} already contains {replace}")
            continue

        with open(curr_file, "w", encoding="utf-8") as _file:
            _file.write(sub(search, replace, text))


def update_repo_toml_version(
    rootpath: Path, section: str, version: str
) -> None:
    repo_toml_path = rootpath / "repo.toml"
    with open(repo_toml_path, encoding="utf-8") as file:
        data = load(file)
    data[section]["version"] = version
    with open(repo_toml_path, "w", encoding="utf-8") as file:
        dump(data, file)
