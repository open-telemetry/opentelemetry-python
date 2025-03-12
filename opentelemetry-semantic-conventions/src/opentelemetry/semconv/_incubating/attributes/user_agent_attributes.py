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

from enum import Enum
from typing import Final

USER_AGENT_NAME: Final = "user_agent.name"
"""
Name of the user-agent extracted from original. Usually refers to the browser's name.
Note: [Example](https://www.whatsmyua.info) of extracting browser's name from original string. In the case of using a user-agent for non-browser products, such as microservices with multiple names/versions inside the `user_agent.original`, the most significant name SHOULD be selected. In such a scenario it should align with `user_agent.version`.
"""

USER_AGENT_ORIGINAL: Final = "user_agent.original"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.user_agent_attributes.USER_AGENT_ORIGINAL`.
"""

USER_AGENT_OS_NAME: Final = "user_agent.os.name"
"""
Human readable operating system name.
Note: For mapping user agent strings to OS names, libraries such as [ua-parser](https://github.com/ua-parser) can be utilized.
"""

USER_AGENT_OS_VERSION: Final = "user_agent.os.version"
"""
The version string of the operating system as defined in [Version Attributes](/docs/resource/README.md#version-attributes).
Note: For mapping user agent strings to OS versions, libraries such as [ua-parser](https://github.com/ua-parser) can be utilized.
"""

USER_AGENT_SYNTHETIC_TYPE: Final = "user_agent.synthetic.type"
"""
Specifies the category of synthetic traffic, such as tests or bots.
Note: This attribute MAY be derived from the contents of the `user_agent.original` attribute. Components that populate the attribute are responsible for determining what they consider to be synthetic bot or test traffic. This attribute can either be set for self-identification purposes, or on telemetry detected to be generated as a result of a synthetic request. This attribute is useful for distinguishing between genuine client traffic and synthetic traffic generated by bots or tests.
"""

USER_AGENT_VERSION: Final = "user_agent.version"
"""
Version of the user-agent extracted from original. Usually refers to the browser's version.
Note: [Example](https://www.whatsmyua.info) of extracting browser's version from original string. In the case of using a user-agent for non-browser products, such as microservices with multiple names/versions inside the `user_agent.original`, the most significant version SHOULD be selected. In such a scenario it should align with `user_agent.name`.
"""


class UserAgentSyntheticTypeValues(Enum):
    BOT = "bot"
    """Bot source."""
    TEST = "test"
    """Synthetic test source."""
