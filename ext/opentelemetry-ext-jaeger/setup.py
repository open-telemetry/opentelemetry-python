# Copyright 2019, OpenTelemetry Authors
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
import os

import setuptools
from setuptools.command.install import install

BASE_DIR = os.path.dirname(__file__)
VERSION_FILENAME = os.path.join(
    BASE_DIR, "src", "opentelemetry", "ext", "jaeger", "version.py"
)
PACKAGE_INFO = {}
with open(VERSION_FILENAME) as f:
    exec(f.read(), PACKAGE_INFO)

BASE_CMD = """docker run --user `id -u` -v "$PWD:/data" \
    thrift:0.10.0 thrift \
    -out /data/build/lib/opentelemetry/ext/jaeger/gen/ \
    --gen py /data/thrift/{}
"""

init_py_str = """
import sys
from os.path import dirname
sys.path.append(dirname(__file__))
"""


def gen_thrift(path):
    os.system(BASE_CMD.format(path))


class JaegerInstallCommand(install):
    """Generates Jaeger thrift files before installing"""

    def run(self):
        path = "build/lib/opentelemetry/ext/jaeger/gen"
        os.makedirs(path, exist_ok=True)

        with open(path + "/__init__.py", "w") as init_py_f:
            init_py_f.write(init_py_str)

        gen_thrift("agent.thrift")
        gen_thrift("zipkincore.thrift")
        gen_thrift("jaeger.thrift")

        install.run(self)


setuptools.setup(
    version=PACKAGE_INFO["__version__"],
    cmdclass={"install": JaegerInstallCommand},
)
