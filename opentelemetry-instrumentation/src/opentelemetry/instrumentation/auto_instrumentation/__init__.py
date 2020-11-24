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

import argparse
from logging import getLogger
from os import environ, execl, getcwd
from os.path import abspath, dirname, pathsep
from shutil import which

logger = getLogger(__file__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="""
        opentelemetry-instrument automatically instruments a Python
        program and it's dependencies and then runs the program.
        """
    )

    parser.add_argument(
        "-e",
        "--exporter",
        required=False,
        help="""
        Uses the specified exporter to export spans or metrics.
        Accepts multiple exporters as comma separated values.

        Examples:

            -e=otlp
            -e=otlp_span,prometheus
            -e=jaeger,otlp_metric
        """,
    )

    parser.add_argument(
        "--ids-generator",
        required=False,
        help="""
        The IDs Generator to be used with the Tracer Provider.

        Examples:

            --ids-generator=random
        """,
    )

    parser.add_argument(
        "-s",
        "--service-name",
        required=False,
        help="""
        The service name that should be passed to a trace exporter.
        """,
    )

    parser.add_argument("command", help="Your Python application.")
    parser.add_argument(
        "command_args",
        help="Arguments for your application.",
        nargs=argparse.REMAINDER,
    )
    return parser.parse_args()


def load_config_from_cli_args(args):
    if args.exporter:
        environ["OTEL_EXPORTER"] = args.exporter
    if args.service_name:
        environ["OTEL_SERVICE_NAME"] = args.service_name
    if args.ids_generator:
        environ["OTEL_IDS_GENERATOR"] = args.ids_generator


def run() -> None:
    args = parse_args()
    load_config_from_cli_args(args)

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
