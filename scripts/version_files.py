#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from os import walk
from os.path import basename, join
from re import escape, sub

from tomlkit import dump, load

# PEP 508 allowed specifier operators
OPERATORS = ["==", "!=", "<=", ">=", "<", ">", "===", "~=", "="]
OPERATORS_PATTERN = "|".join(escape(op) for op in OPERATORS)


def find(name, path):
    for root, _, files in walk(path):
        if name in files:
            return join(root, name)
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
        with open(target.joinpath("pyproject.toml"), encoding="utf-8") as file:
            pyproject = load(file)
        version_file_path = target.joinpath(
            pyproject["tool"]["hatch"]["version"]["path"]
        )

        with open(version_file_path) as file:
            text = file.read()

        if replace in text:
            print(f"{version_file_path} already contains {replace}")
            continue

        with open(version_file_path, "w", encoding="utf-8") as file:
            file.write(sub(search, replace, text))


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
            _file.write(sub(search, replace, text))


def update_repo_toml_version(rootpath, section, version):
    repo_toml_path = rootpath / "repo.toml"
    with open(repo_toml_path, encoding="utf-8") as file:
        data = load(file)
    data[section]["version"] = version
    with open(repo_toml_path, "w", encoding="utf-8") as file:
        dump(data, file)


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
