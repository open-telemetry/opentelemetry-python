# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import defaultdict
from difflib import unified_diff
from pathlib import Path
from re import match
from sys import exit

from git import Repo
from git.db import GitDB

repo = Repo(__file__, odbt=GitDB, search_parent_directories=True)


added_symbols = defaultdict(list)
removed_symbols = defaultdict(list)


def get_symbols(change_type, diff_lines_getter, prefix):

    if change_type == "D" or prefix == r"\-":
        file_path_symbols = removed_symbols
    else:
        file_path_symbols = added_symbols

    for diff_lines in (
        repo.commit("main")
        .diff(repo.head.commit)
        .iter_change_type(change_type)
    ):

        b_file_path = diff_lines.b_blob.path
        b_file_path_obj = Path(b_file_path)

        if (
            b_file_path_obj.suffix != ".py"
            or "opentelemetry" not in b_file_path
            or any(
                # single leading underscore
                part[0] == "_" and part[1] != "_"
                # tests directories
                or part == "tests"
                for part in b_file_path_obj.parts
            )
        ):
            continue

        for diff_line in diff_lines_getter(diff_lines):
            matching_line = match(
                r"{prefix}({symbol_re})\s=\s.+|"
                r"{prefix}def\s({symbol_re})|"
                r"{prefix}class\s({symbol_re})".format(
                    symbol_re=r"[a-zA-Z][_\w]+", prefix=prefix
                ),
                diff_line,
            )

            if matching_line is not None:
                file_path_symbols[b_file_path].append(
                    next(filter(bool, matching_line.groups()))
                )


def a_diff_lines_getter(diff_lines):
    return diff_lines.b_blob.data_stream.read().decode("utf-8").split("\n")


def d_diff_lines_getter(diff_lines):
    return diff_lines.a_blob.data_stream.read().decode("utf-8").split("\n")


def m_diff_lines_getter(diff_lines):
    return unified_diff(
        diff_lines.a_blob.data_stream.read().decode("utf-8").split("\n"),
        diff_lines.b_blob.data_stream.read().decode("utf-8").split("\n"),
    )


get_symbols("A", a_diff_lines_getter, r"")
get_symbols("D", d_diff_lines_getter, r"")
get_symbols("M", m_diff_lines_getter, r"\+")
get_symbols("M", m_diff_lines_getter, r"\-")


def remove_common_symbols():
    # For each file, we remove the symbols that are added and removed in the
    # same commit.
    common_symbols = defaultdict(list)
    for file_path, symbols in added_symbols.items():
        for symbol in symbols:
            if symbol in removed_symbols[file_path]:
                common_symbols[file_path].append(symbol)

    for file_path, symbols in common_symbols.items():
        for symbol in symbols:
            added_symbols[file_path].remove(symbol)
            removed_symbols[file_path].remove(symbol)

    # If a file has no added or removed symbols, we remove it from the
    # dictionaries.
    for file_path in list(added_symbols.keys()):
        if not added_symbols[file_path]:
            del added_symbols[file_path]

    for file_path in list(removed_symbols.keys()):
        if not removed_symbols[file_path]:
            del removed_symbols[file_path]


if added_symbols or removed_symbols:

    # If a symbol is added and removed in the same commit, we consider it
    # as not added or removed.
    remove_common_symbols()
    print("The code in this branch adds the following public symbols:")
    print()
    for file_path_, symbols_ in added_symbols.items():
        print(f"- {file_path_}")
        for symbol_ in symbols_:
            print(f"\t{symbol_}")
        print()

    print(
        "Please make sure that all of them are strictly necessary, if not, "
        "please consider prefixing them with an underscore to make them "
        'private. After that, please label this PR with "Skip Public API '
        'check".'
    )
    print()
    print("The code in this branch removes the following public symbols:")
    print()
    for file_path_, symbols_ in removed_symbols.items():
        print(f"- {file_path_}")
        for symbol_ in symbols_:
            print(f"\t{symbol_}")
        print()

    print(
        "Please make sure no public symbols are removed, if so, please "
        "consider deprecating them instead. After that, please label this "
        'PR with "Skip Public API check".'
    )
    exit(1)
else:
    print("The code in this branch will not add any public symbols")
