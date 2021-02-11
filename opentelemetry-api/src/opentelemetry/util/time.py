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

if version_info.minor < 7:
    from time import time

    def time_ns() -> int:
        # FIXME this approach can have precision problems as explained here:
        # https://github.com/open-telemetry/opentelemetry-python/issues/1594
        return int(time() * 1e9)


else:
    from time import time_ns  # pylint: disable=unused-import
