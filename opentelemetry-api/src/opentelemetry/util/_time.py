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
from sys import version_info

if version_info.minor < 7:
    getLogger(__name__).warning(  # pylint: disable=logging-not-lazy
        "You are using Python 3.%s. This version does not support timestamps "  # pylint: disable=C0209
        "with nanosecond precision and the OpenTelemetry SDK will use "
        "millisecond precision instead. Please refer to PEP 564 for more "
        "information. Please upgrade to Python 3.7 or newer to use nanosecond "
        "precision." % version_info.minor
    )
    from time import time

    def _time_ns() -> int:
        return int(time() * 1e9)

else:
    from time import time_ns

    _time_ns = time_ns
