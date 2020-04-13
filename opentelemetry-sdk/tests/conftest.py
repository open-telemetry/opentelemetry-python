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

from os import environ
from sys import version_info


def pytest_sessionstart(session):
    # pylint: disable=unused-argument
    if version_info < (3, 5):
        # contextvars are not supported in 3.4, use thread-local storage
        environ["OPENTELEMETRY_CONTEXT"] = "threadlocal_context"
    else:
        environ["OPENTELEMETRY_CONTEXT"] = "contextvars_context"


def pytest_sessionfinish(session):
    # pylint: disable=unused-argument
    environ.pop("OPENTELEMETRY_CONTEXT")
