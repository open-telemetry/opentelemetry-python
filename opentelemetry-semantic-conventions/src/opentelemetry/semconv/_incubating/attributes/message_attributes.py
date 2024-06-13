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

from typing import Final





from enum import Enum

MESSAGE_COMPRESSED_SIZE: Final = "message.compressed_size"
"""
Compressed size of the message in bytes.
"""

MESSAGE_ID: Final = "message.id"
"""
MUST be calculated as two different counters starting from `1` one for sent messages and one for received message.
Note: This way we guarantee that the values will be consistent between different implementations.
"""

MESSAGE_TYPE: Final = "message.type"
"""
Whether this is a received or sent message.
"""

MESSAGE_UNCOMPRESSED_SIZE: Final = "message.uncompressed_size"
"""
Uncompressed size of the message in bytes.
"""


class MessageTypeValues(Enum):
    SENT: Final = "SENT"
    """sent."""
    RECEIVED: Final = "RECEIVED"
    """received."""