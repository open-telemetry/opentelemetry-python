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

from logging import getLogger
from os import environ, execl
from os.path import abspath, dirname, pathsep
from shutil import which
from sys import argv

logger = getLogger(__file__)


def run() -> None:

    python_path = environ.get("PYTHONPATH", [])

    if python_path:
        python_path = python_path.split(pathsep)

    filedir_path = dirname(abspath(__file__))

    if filedir_path in python_path:
        python_path.remove(filedir_path)

    environ["PYTHONPATH"] = pathsep.join([filedir_path, *python_path])

    executable = which(argv[1])

    execl(executable, executable, *argv[2:])
