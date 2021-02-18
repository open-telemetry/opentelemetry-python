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

import setuptools
from os.path import join, dirname
from sys import version_info
from distutils.sysconfig import get_python_lib

BASE_DIR = dirname(__file__)
VERSION_FILENAME = join(BASE_DIR, "src", "opentelemetry", "version.py")
PACKAGE_INFO = {}
with open(VERSION_FILENAME) as f:
    exec(f.read(), PACKAGE_INFO)

setuptools.setup(version=PACKAGE_INFO["__version__"],)

sitecustomize_content = """import time
from logging import getLogger

def time_ns():
    return int(time.time() * 1e9)

time.time_ns = time_ns

getLogger(__name__).warning(
    "You are using a Python version previous than 3.7. Your Python version "
    "does not include a function to get timestamps in nanoseconds. A time_ns "
    "function has been added to the time module, for the purpose of you being "
    "able to have a consistent import path with a more recent Python version. "
    "This time_ns function has not the same resolution as the time_ns "
    "function introduced in 3.7. Refer to PEP 564 for more information. "
    "Please upgrade your Python version to 3.7 or newer."
)
"""


if version_info.minor < 7:
    try:
        with open(
            join(get_python_lib(), "sitecustomize.py"),
            "w"
        ) as sitecustomize_file:

            sitecustomize_file.write(sitecustomize_content)
    except:
        pass
