#!/usr/bin/env python3

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

from argparse import REMAINDER, ArgumentParser
from logging import getLogger
from os import environ, execl, getcwd
from os.path import abspath, dirname, pathsep
from shutil import which

from pkg_resources import iter_entry_points

_logger = getLogger(__file__)


def run() -> None:

    parser = ArgumentParser(
        description="""
        opentelemetry-instrument automatically instruments a Python
        program and its dependencies and then runs the program.
        """
    )

    otel_environment_variables = []

    for entry_point in iter_entry_points(
        "opentelemetry_environment_variables"
    ):
        environment_variable_module = entry_point.load()

        for attribute in dir(environment_variable_module):

            if attribute.startswith("OTEL_"):

                parser.add_argument(
                    f"--{attribute}",
                    required=False,
                )
                otel_environment_variables.append(attribute)

    parser.add_argument("command", help="Your Python application.")
    parser.add_argument(
        "command_args",
        help="Arguments for your application.",
        nargs=REMAINDER,
    )

    args = parser.parse_args()

    for otel_environment_variable in otel_environment_variables:
        value = getattr(args, otel_environment_variable)
        if value is not None:

            environ[otel_environment_variable] = value

    python_path = environ.get("PYTHONPATH")

    if not python_path:
        python_path = []

    else:
        python_path = python_path.split(pathsep)

    cwd_path = getcwd()

    # This is being added to support applications that are being run from their
    # own executable, like Django.
    # FIXME investigate if there is another way to achieve this
    if cwd_path not in python_path:
        python_path.insert(0, cwd_path)

    filedir_path = dirname(abspath(__file__))

    python_path = [path for path in python_path if path != filedir_path]

    python_path.insert(0, filedir_path)

    environ["PYTHONPATH"] = pathsep.join(python_path)

    executable = which(args.command)
    execl(executable, executable, *args.command_args)
