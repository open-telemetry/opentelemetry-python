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

import time

try:
    time_ns = time.time_ns
# Python versions < 3.7
except AttributeError:

    def time_ns():
        return int(time.time() * 1e9)


# A default event name to be used for logging events when a better event name
# can't be derived from the event's key-value pairs.
DEFAULT_EVENT_NAME = "log"


def event_name_from_kv(key_values: dict) -> str:
    """A helper function which returns an event name from the given dict, or a
    default event name.
    """

    if key_values is None or "event" not in key_values:
        return DEFAULT_EVENT_NAME

    return key_values["event"]
