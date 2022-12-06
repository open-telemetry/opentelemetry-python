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

from sys import version_info

# FIXME remove this file when support for 3.7 is dropped.
if version_info.minor == 7:
    # pylint: disable=import-error
    from importlib_metadata import entry_points, version  # type: ignore
else:
    from importlib.metadata import entry_points, version

__all__ = ["entry_points", "version"]
