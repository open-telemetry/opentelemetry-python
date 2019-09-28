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

import locale
import os
import platform
import sys

from opentelemetry.ext.azure_monitor.protocol import BaseObject
from opentelemetry.ext.azure_monitor.version import __version__ as ext_version
from opentelemetry.sdk.version import __version__ as opentelemetry_version

azure_monitor_context = {
    "ai.cloud.role": os.path.basename(sys.argv[0]) or "Python Application",
    "ai.cloud.roleInstance": platform.node(),
    "ai.device.id": platform.node(),
    "ai.device.locale": locale.getdefaultlocale()[0],
    "ai.device.osVersion": platform.version(),
    "ai.device.type": "Other",
    "ai.internal.sdkVersion": "py{}:ot{}:ext{}".format(
        platform.python_version(), opentelemetry_version, ext_version
    ),
}


class Options(BaseObject):
    _default = BaseObject(
        endpoint="https://dc.services.visualstudio.com/v2/track",
        instrumentation_key=os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", None),
        timeout=10.0,  # networking timeout in seconds
    )


def validate_key(instrumentation_key):
    if not instrumentation_key:
        raise ValueError("The instrumentation_key is not provided.")
