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

import base64
import logging
import math
import socket

from thrift.protocol import TBinaryProtocol, TCompactProtocol
from thrift.transport import THttpClient, TTransport

from opentelemetry.exporter.jaeger.thrift.gen.agent import Agent as agent
from opentelemetry.exporter.jaeger.thrift.gen.jaeger import Collector as jaeger

UDP_PACKET_MAX_LENGTH = 65000


logger = logging.getLogger(__name__)


class AgentClientUDP:
    """Implement a UDP client to agent.

    Args:
        host_name: The host name of the Jaeger server.
        port: The port of the Jaeger server.
        max_packet_size: Maximum size of UDP packet.
        client: Class for creating new client objects for agencies.
        split_oversized_batches: Re-emit oversized batches in smaller chunks.
    """

    def __init__(
        self,
        host_name,
        port,
        max_packet_size=UDP_PACKET_MAX_LENGTH,
        client=agent.Client,
        split_oversized_batches=False,
    ):
        self.address = (host_name, port)
        self.max_packet_size = max_packet_size
        self.buffer = TTransport.TMemoryBuffer()
        self.client = client(
            iprot=TCompactProtocol.TCompactProtocol(trans=self.buffer)
        )
        self.split_oversized_batches = split_oversized_batches

    def emit(self, batch: jaeger.Batch):
        """
        Args:
            batch: Object to emit Jaeger spans.
        """

        # pylint: disable=protected-access
        self.client._seqid = 0
        #  truncate and reset the position of BytesIO object
        self.buffer._buffer.truncate(0)
        self.buffer._buffer.seek(0)
        self.client.emitBatch(batch)
        buff = self.buffer.getvalue()
        if len(buff) > self.max_packet_size:
            if self.split_oversized_batches and len(batch.spans) > 1:
                packets = math.ceil(len(buff) / self.max_packet_size)
                div = math.ceil(len(batch.spans) / packets)
                for packet in range(packets):
                    start = packet * div
                    end = (packet + 1) * div
                    if start < len(batch.spans):
                        self.emit(
                            jaeger.Batch(
                                process=batch.process,
                                spans=batch.spans[start:end],
                            )
                        )
            else:
                logger.warning(
                    "Data exceeds the max UDP packet size; size %r, max %r",
                    len(buff),
                    self.max_packet_size,
                )
            return

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.sendto(buff, self.address)


class Collector:
    """Submits collected spans to Jaeger collector in jaeger.thrift
    format over binary thrift protocol. This is recommend option in cases where
    it is not feasible to deploy Jaeger Agent next to the application,
    for example, when the application code is running as AWS Lambda function.
    In these scenarios the Jaeger Clients can be configured to submit spans directly
    to the Collectors over HTTP/HTTPS.

    Args:
        thrift_url: Endpoint used to send spans
            directly to Collector the over HTTP.
        auth: Auth tuple that contains username and password for Basic Auth.
        timeout_in_millis: timeout for THttpClient.
    """

    def __init__(self, thrift_url="", auth=None, timeout_in_millis=None):
        self.thrift_url = thrift_url
        self.auth = auth
        self.http_transport = THttpClient.THttpClient(
            uri_or_host=self.thrift_url
        )
        if timeout_in_millis is not None:
            self.http_transport.setTimeout(timeout_in_millis)

        self.protocol = TBinaryProtocol.TBinaryProtocol(self.http_transport)

        # set basic auth header
        if auth is not None:
            auth_header = f"{auth[0]}:{auth[1]}"
            decoded = base64.b64encode(auth_header.encode()).decode("ascii")
            basic_auth = dict(Authorization=f"Basic {decoded}")
            self.http_transport.setCustomHeaders(basic_auth)

    def submit(self, batch: jaeger.Batch):
        """Submits batches to Thrift HTTP Server through Binary Protocol.

        Args:
            batch: Object to emit Jaeger spans.
        """
        batch.write(self.protocol)
        self.http_transport.flush()
        code = self.http_transport.code
        msg = self.http_transport.message
        if code >= 300 or code < 200:
            logger.error(
                "Traces cannot be uploaded; HTTP status code: %s, message: %s",
                code,
                msg,
            )
