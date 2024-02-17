
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

# pylint: disable=too-many-lines

from enum import Enum


EVENT_DOMAIN = "event.domain"
"""
The domain identifies the business context for the events.
Note: Events across different domains may have same `event.name`, yet be unrelated events.
"""


EVENT_NAME = "event.name"
"""
The name identifies the event.
"""


class EventDomainValues(Enum):
    BROWSER = "browser"
    """Events from browser apps."""

    DEVICE = "device"
    """Events from mobile apps."""

    K8S = "k8s"
    """Events from Kubernetes."""

