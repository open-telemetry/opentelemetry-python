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

from difflib import unified_diff
from os import getcwd
from pathlib import Path
from re import match
from sys import exit

from git import Repo
from git.db import GitDB

repo = Repo(getcwd(), odbt=GitDB)


file_path_symbols = {}


def get_symbols(change_type, diff_lines_getter, prefix):
    for diff_lines in (
        repo.commit("main")
        .diff(repo.head.commit)
        .iter_change_type(change_type)
    ):

        b_file_path = diff_lines.b_blob.path

        if (
            Path(b_file_path).suffix != ".py"
            or "opentelemetry" not in b_file_path
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
                if b_file_path not in file_path_symbols.keys():
                    file_path_symbols[b_file_path] = []

                file_path_symbols[b_file_path].append(
                    next(filter(bool, matching_line.groups()))
                )


def a_diff_lines_getter(diff_lines):
    return diff_lines.b_blob.data_stream.read().decode("utf-8").split("\n")


def m_diff_lines_getter(diff_lines):
    return unified_diff(
        diff_lines.a_blob.data_stream.read().decode("utf-8").split("\n"),
        diff_lines.b_blob.data_stream.read().decode("utf-8").split("\n"),
    )


get_symbols("A", a_diff_lines_getter, r"")
get_symbols("M", m_diff_lines_getter, r"\+")

if file_path_symbols:
    print("This pull request adds the following public symbols:")
    print()
    for file_path, symbols in file_path_symbols.items():
        print("- {}".format(file_path))
        for symbol in symbols:
            print("\t{}".format(symbol))
        print()

    print(
        "Please make sure that all of them are strictly necessary, if not, "
        "please consider prefixing them with an underscore to make them "
        'private. After that, please label this PR with "Skip Public API '
        'check".'
    )
    exit(1)
else:
    print("This pull request does not add any public symbols")
