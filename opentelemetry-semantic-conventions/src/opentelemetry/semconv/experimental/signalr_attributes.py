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


SIGNALR_CONNECTION_STATUS = "signalr.connection.status"
"""
SignalR HTTP connection closure status.
"""


SIGNALR_TRANSPORT = "signalr.transport"
"""
[SignalR transport type](https://github.com/dotnet/aspnetcore/blob/main/src/SignalR/docs/specs/TransportProtocols.md).
"""

class SignalrConnectionStatusValues(Enum):
    NORMAL_CLOSURE = "normal_closure"
    """The connection was closed normally."""

    TIMEOUT = "timeout"
    """The connection was closed due to a timeout."""

    APP_SHUTDOWN = "app_shutdown"
    """The connection was closed because the app is shutting down."""
class SignalrTransportValues(Enum):
    SERVER_SENT_EVENTS = "server_sent_events"
    """ServerSentEvents protocol."""

    LONG_POLLING = "long_polling"
    """LongPolling protocol."""

    WEB_SOCKETS = "web_sockets"
    """WebSockets protocol."""
