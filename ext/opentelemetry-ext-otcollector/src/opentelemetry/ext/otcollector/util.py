# Copyright 2020, OpenTelemetry Authors
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

import os
import socket
import time

from google.protobuf.timestamp_pb2 import Timestamp
from opencensus.proto.agent.common.v1 import common_pb2
from opencensus.proto.trace.v1 import trace_pb2

from opentelemetry.trace import SpanKind
from opentelemetry.util.version import __version__ as opentelemetry_version

# OT Collector exporter version
EXPORTER_VERSION = "0.0.1"


def proto_timestamp_from_time_ns(time_ns):
    """Converts datetime to protobuf timestamp.

    :type time_ns: int
    :param time_ns: Time in nanoseconds

    :rtype: :class:`~google.protobuf.timestamp_pb2.Timestamp`
    :returns: protobuf timestamp
    """
    ts = Timestamp()
    if time_ns is not None:
        ts.FromNanoseconds(time_ns)
    return ts


def get_collector_span_kind(kind: SpanKind):
    if kind is SpanKind.SERVER:
        return trace_pb2.Span.SpanKind.SERVER
    if kind is SpanKind.CLIENT:
        return trace_pb2.Span.SpanKind.CLIENT
    return trace_pb2.Span.SpanKind.SPAN_KIND_UNSPECIFIED


def add_proto_attribute_value(pb_attributes, attribute_key, attribute_value):
    """Sets string, int, boolean or float value on protobuf
        span, link or annotation attributes.

    :type pb_attributes:
        :class: `~opencensus.proto.trace.Span.Attributes`
    :param pb_attributes: protobuf Span's attributes property

    :type attribute_key: str
    :param attribute_key: attribute key to set

    :type attribute_value: str or int or bool or float
    :param attribute_value: attribute value
    """

    if isinstance(attribute_value, bool):
        pb_attributes.attribute_map[attribute_key].bool_value = attribute_value
    elif isinstance(attribute_value, int):
        pb_attributes.attribute_map[attribute_key].int_value = attribute_value
    elif isinstance(attribute_value, str):
        pb_attributes.attribute_map[
            attribute_key
        ].string_value.value = attribute_value
    elif isinstance(attribute_value, float):
        pb_attributes.attribute_map[
            attribute_key
        ].double_value = attribute_value
    else:
        pb_attributes.attribute_map[attribute_key].string_value.value = str(
            attribute_value
        )


def get_node(service_name, host_name):
    """Generates Node message from params and system information.
    """
    return common_pb2.Node(
        identifier=common_pb2.ProcessIdentifier(
            host_name=socket.gethostname() if host_name is None else host_name,
            pid=os.getpid(),
            start_timestamp=proto_timestamp_from_time_ns(
                int(time.time() * 1e9)
            ),
        ),
        library_info=common_pb2.LibraryInfo(
            language=common_pb2.LibraryInfo.Language.Value("PYTHON"),
            exporter_version=EXPORTER_VERSION,
            core_library_version=opentelemetry_version,
        ),
        service_info=common_pb2.ServiceInfo(name=service_name),
    )
