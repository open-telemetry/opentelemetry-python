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

from opentelemetry.metrics import Histogram, Meter

MCP_CLIENT_OPERATION_DURATION: Final = "mcp.client.operation.duration"
"""
The duration of the MCP request or notification as observed on the sender from the time it was sent until the response or ack is received
Instrument: histogram
Unit: s
"""


def create_mcp_client_operation_duration(meter: Meter) -> Histogram:
    """The duration of the MCP request or notification as observed on the sender from the time it was sent until the response or ack is received"""
    return meter.create_histogram(
        name=MCP_CLIENT_OPERATION_DURATION,
        description="The duration of the MCP request or notification as observed on the sender from the time it was sent until the response or ack is received.",
        unit="s",
    )


MCP_CLIENT_SESSION_DURATION: Final = "mcp.client.session.duration"
"""
The duration of the MCP session as observed on the MCP client
Instrument: histogram
Unit: s
"""


def create_mcp_client_session_duration(meter: Meter) -> Histogram:
    """The duration of the MCP session as observed on the MCP client"""
    return meter.create_histogram(
        name=MCP_CLIENT_SESSION_DURATION,
        description="The duration of the MCP session as observed on the MCP client.",
        unit="s",
    )


MCP_SERVER_OPERATION_DURATION: Final = "mcp.server.operation.duration"
"""
MCP request or notification duration as observed on the receiver from the time it was received until the result or ack is sent
Instrument: histogram
Unit: s
"""


def create_mcp_server_operation_duration(meter: Meter) -> Histogram:
    """MCP request or notification duration as observed on the receiver from the time it was received until the result or ack is sent"""
    return meter.create_histogram(
        name=MCP_SERVER_OPERATION_DURATION,
        description="MCP request or notification duration as observed on the receiver from the time it was received until the result or ack is sent.",
        unit="s",
    )


MCP_SERVER_SESSION_DURATION: Final = "mcp.server.session.duration"
"""
The duration of the MCP session as observed on the MCP server
Instrument: histogram
Unit: s
"""


def create_mcp_server_session_duration(meter: Meter) -> Histogram:
    """The duration of the MCP session as observed on the MCP server"""
    return meter.create_histogram(
        name=MCP_SERVER_SESSION_DURATION,
        description="The duration of the MCP session as observed on the MCP server.",
        unit="s",
    )
