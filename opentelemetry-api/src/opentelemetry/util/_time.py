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
        "You are using Python version 3.%s. This version does not include a "
        "function to get timestamps in nanoseconds. The _time_ns function in "
        "opentelemetry.util._time does not have the same resolution as the "
        "time_ns function included in the time package in Python 3.7 onwards. "
        "This _time_ns function must not be used by any application code and "
        "it will be removed once opentelemetry-api no longer supports any "
        "Python version older than 3.7. Refer to PEP 546 for more "
        "information. Please upgrade your Python version to 3.7 or "
        "newer." % version_info.minor
    )
    from time import time

    def _time_ns():
        return int(time() * 1e9)


else:
    from time import time_ns

    _time_ns = time_ns
