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

from os import getpid
from socket import gethostname
from time import time

# pylint: disable=wrong-import-position
from google.protobuf.timestamp_pb2 import (  # pylint: disable=no-name-in-module
    Timestamp,
)
from opencensus.proto.agent.common.v1 import common_pb2
from opencensus.proto.trace.v1 import trace_pb2

from opentelemetry.exporter.opencensus.version import (
    __version__ as opencensusexporter_exporter_version,
)
from opentelemetry.trace import SpanKind
from opentelemetry.util._importlib_metadata import version

OPENTELEMETRY_VERSION = version("opentelemetry-api")


def proto_timestamp_from_time_ns(time_ns):
    """Converts datetime to protobuf timestamp.

    Args:
        time_ns: Time in nanoseconds

    Returns:
        Returns protobuf timestamp.
    """
    ts = Timestamp()
    if time_ns is not None:
        # pylint: disable=no-member
        ts.FromNanoseconds(time_ns)
    return ts


# pylint: disable=no-member
def get_collector_span_kind(kind: SpanKind):
    if kind is SpanKind.SERVER:
        return trace_pb2.Span.SpanKind.SERVER
    if kind is SpanKind.CLIENT:
        return trace_pb2.Span.SpanKind.CLIENT
    return trace_pb2.Span.SpanKind.SPAN_KIND_UNSPECIFIED


def add_proto_attribute_value(pb_attributes, key, value):
    """Sets string, int, boolean or float value on protobuf
        span, link or annotation attributes.

    Args:
        pb_attributes: protobuf Span's attributes property.
        key: attribute key to set.
        value: attribute value
    """

    if isinstance(value, bool):
        pb_attributes.attribute_map[key].bool_value = value
    elif isinstance(value, int):
        pb_attributes.attribute_map[key].int_value = value
    elif isinstance(value, str):
        pb_attributes.attribute_map[key].string_value.value = value
    elif isinstance(value, float):
        pb_attributes.attribute_map[key].double_value = value
    else:
        pb_attributes.attribute_map[key].string_value.value = str(value)


# pylint: disable=no-member
def get_node(service_name, host_name):
    """Generates Node message from params and system information.

    Args:
       service_name: Name of Collector service.
       host_name: Host name.
    """
    return common_pb2.Node(
        identifier=common_pb2.ProcessIdentifier(
            host_name=gethostname() if host_name is None else host_name,
            pid=getpid(),
            start_timestamp=proto_timestamp_from_time_ns(int(time() * 1e9)),
        ),
        library_info=common_pb2.LibraryInfo(
            language=common_pb2.LibraryInfo.Language.Value("PYTHON"),
            exporter_version=opencensusexporter_exporter_version,
            core_library_version=OPENTELEMETRY_VERSION,
        ),
        service_info=common_pb2.ServiceInfo(name=service_name),
    )
