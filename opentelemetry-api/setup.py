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

from distutils.sysconfig import get_python_lib
from os.path import dirname, join
from sys import version_info
from logging import getLogger

import setuptools

_logger = getLogger(__name__)
BASE_DIR = dirname(__file__)
VERSION_FILENAME = join(BASE_DIR, "src", "opentelemetry", "version.py")
PACKAGE_INFO = {}
with open(VERSION_FILENAME) as f:
    exec(f.read(), PACKAGE_INFO)

setuptools.setup(version=PACKAGE_INFO["__version__"],)

# FIXME The code below has been added to make it possible for the user to
# import time_ns from time in Python < 3.7. The intention behind this is to
# allow the user to import this function while we support this old Python
# versions and to make it possible for the user to upgrade to 3.7 or newer
# without having to change any application code. Remove the code below when
# no Python versions older than 3.7 are supported.

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
            join(get_python_lib(), "sitecustomize.py"), "w"
        ) as sitecustomize_file:

            sitecustomize_file.write(sitecustomize_content)
    except:
        _logger.exception("Unable to add time_ns to time")
