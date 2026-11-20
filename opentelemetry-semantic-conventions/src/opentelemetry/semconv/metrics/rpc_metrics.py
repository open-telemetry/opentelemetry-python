# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


from typing import Final

RPC_CLIENT_CALL_DURATION: Final = "rpc.client.call.duration"
"""
Measures the duration of an outgoing Remote Procedure Call (RPC)
Instrument: histogram
Unit: s
Note: When this metric is reported alongside an RPC client span, the metric value
SHOULD be the same as the RPC client span duration.
"""


RPC_SERVER_CALL_DURATION: Final = "rpc.server.call.duration"
"""
Measures the duration of an incoming Remote Procedure Call (RPC)
Instrument: histogram
Unit: s
Note: When this metric is reported alongside an RPC server span, the metric value
SHOULD be the same as the RPC server span duration.
"""
