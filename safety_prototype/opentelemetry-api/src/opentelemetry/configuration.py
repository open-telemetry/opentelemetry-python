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

from pkg_resources import iter_entry_points
from importlib import import_module

_sdk = None


def set_sdk(sdk_name: str) -> None:
    """
    This is the SDK setting function mentioned in the README file.

    It is intentionally not protected to make it possible for the application
    to fail fast if it was not possible to set the SDK. In an actual
    implementation of this prototype, the SDK setting mechanism may take
    different forms to take into consideration that this SDK setting process
    may happen also in auto instrumentation. This means that SDK setting may
    also happen by using environment variables or other form of configuration.
    """
    global _sdk

    if _sdk is None:
        _sdk = next(
            iter_entry_points("opentelemetry_sdk", name=sdk_name)
        ).load().__package__


def _get_sdk_module(path: str) -> object:
    return import_module(".".join([_sdk, path]))
