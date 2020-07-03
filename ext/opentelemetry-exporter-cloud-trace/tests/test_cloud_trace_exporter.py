# Copyright OpenTelemetry Authors
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

import unittest
from unittest import mock

import pkg_resources
from google.cloud.trace_v2.proto.trace_pb2 import AttributeValue
from google.cloud.trace_v2.proto.trace_pb2 import Span as ProtoSpan
from google.cloud.trace_v2.proto.trace_pb2 import TruncatableString
from google.rpc.status_pb2 import Status

from opentelemetry.exporter.cloud_trace import (
    MAX_EVENT_ATTRS,
    MAX_LINK_ATTRS,
    MAX_NUM_EVENTS,
    MAX_NUM_LINKS,
    CloudTraceSpanExporter,
    _extract_attributes,
    _extract_events,
    _extract_links,
    _extract_status,
    _format_attribute_value,
    _strip_characters,
    _truncate_str,
)
from opentelemetry.exporter.cloud_trace.version import (
    __version__ as cloud_trace_version,
)
from opentelemetry.sdk.trace import Event
from opentelemetry.sdk.trace.export import Span
from opentelemetry.trace import Link, SpanContext, SpanKind
from opentelemetry.trace.status import Status as SpanStatus
from opentelemetry.trace.status import StatusCanonicalCode


class TestCloudTraceSpanExporter(unittest.TestCase):
    def setUp(self):
        self.client_patcher = mock.patch(
            "opentelemetry.exporter.cloud_trace.TraceServiceClient"
        )
        self.client_patcher.start()
        self.project_id = "PROJECT"
        self.attributes_variety_pack = {
            "str_key": "str_value",
            "bool_key": False,
            "double_key": 1.421,
            "int_key": 123,
        }
        self.extracted_attributes_variety_pack = ProtoSpan.Attributes(
            attribute_map={
                "str_key": AttributeValue(
                    string_value=TruncatableString(
                        value="str_value", truncated_byte_count=0
                    )
                ),
                "bool_key": AttributeValue(bool_value=False),
                "double_key": AttributeValue(
                    string_value=TruncatableString(
                        value="1.4210", truncated_byte_count=0
                    )
                ),
                "int_key": AttributeValue(int_value=123),
            }
        )

    def tearDown(self):
        self.client_patcher.stop()

    def test_constructor_default(self):
        exporter = CloudTraceSpanExporter(self.project_id)
        self.assertEqual(exporter.project_id, self.project_id)

    def test_constructor_explicit(self):
        client = mock.Mock()
        exporter = CloudTraceSpanExporter(self.project_id, client=client)

        self.assertIs(exporter.client, client)
        self.assertEqual(exporter.project_id, self.project_id)

    def test_export(self):
        trace_id = "6e0c63257de34c92bf9efcd03927272e"
        span_id = "95bb5edabd45950f"
        span_datas = [
            Span(
                name="span_name",
                context=SpanContext(
                    trace_id=int(trace_id, 16),
                    span_id=int(span_id, 16),
                    is_remote=False,
                ),
                parent=None,
                kind=SpanKind.INTERNAL,
            )
        ]

        cloud_trace_spans = {
            "name": "projects/{}/traces/{}/spans/{}".format(
                self.project_id, trace_id, span_id
            ),
            "span_id": span_id,
            "parent_span_id": None,
            "display_name": TruncatableString(
                value="span_name", truncated_byte_count=0
            ),
            "attributes": ProtoSpan.Attributes(
                attribute_map={
                    "g.co/agent": _format_attribute_value(
                        "opentelemetry-python {}; google-cloud-trace-exporter {}".format(
                            _strip_characters(
                                pkg_resources.get_distribution(
                                    "opentelemetry-sdk"
                                ).version
                            ),
                            _strip_characters(cloud_trace_version),
                        )
                    )
                }
            ),
            "links": None,
            "status": None,
            "time_events": None,
            "start_time": None,
            "end_time": None,
        }

        client = mock.Mock()

        exporter = CloudTraceSpanExporter(self.project_id, client=client)

        exporter.export(span_datas)

        client.create_span.assert_called_with(**cloud_trace_spans)
        self.assertTrue(client.create_span.called)

    def test_extract_status(self):
        self.assertIsNone(_extract_status(None))
        self.assertEqual(
            _extract_status(SpanStatus(canonical_code=StatusCanonicalCode.OK)),
            Status(details=None, code=0),
        )
        self.assertEqual(
            _extract_status(
                SpanStatus(
                    canonical_code=StatusCanonicalCode.UNKNOWN,
                    description="error_desc",
                )
            ),
            Status(details=None, code=2, message="error_desc"),
        )

    def test_extract_attributes(self):
        self.assertEqual(
            _extract_attributes({}, 4), ProtoSpan.Attributes(attribute_map={})
        )
        self.assertEqual(
            _extract_attributes(self.attributes_variety_pack, 4),
            self.extracted_attributes_variety_pack,
        )
        # Test ignoring attributes with illegal value type
        self.assertEqual(
            _extract_attributes({"illegal_attribute_value": dict()}, 4),
            ProtoSpan.Attributes(attribute_map={}, dropped_attributes_count=1),
        )

        too_many_attrs = {}
        for attr_key in range(5):
            too_many_attrs[str(attr_key)] = 0
        proto_attrs = _extract_attributes(too_many_attrs, 4)
        self.assertEqual(proto_attrs.dropped_attributes_count, 1)

    def test_extract_events(self):
        self.assertIsNone(_extract_events([]))
        time_in_ns1 = 1589919268850900051
        time_in_ms_and_ns1 = {"seconds": 1589919268, "nanos": 850899968}
        time_in_ns2 = 1589919438550020326
        time_in_ms_and_ns2 = {"seconds": 1589919438, "nanos": 550020352}
        event1 = Event(
            name="event1",
            attributes=self.attributes_variety_pack,
            timestamp=time_in_ns1,
        )
        event2 = Event(
            name="event2",
            attributes={"illegal_attr_value": dict()},
            timestamp=time_in_ns2,
        )
        self.assertEqual(
            _extract_events([event1, event2]),
            ProtoSpan.TimeEvents(
                time_event=[
                    {
                        "time": time_in_ms_and_ns1,
                        "annotation": {
                            "description": TruncatableString(
                                value="event1", truncated_byte_count=0
                            ),
                            "attributes": self.extracted_attributes_variety_pack,
                        },
                    },
                    {
                        "time": time_in_ms_and_ns2,
                        "annotation": {
                            "description": TruncatableString(
                                value="event2", truncated_byte_count=0
                            ),
                            "attributes": ProtoSpan.Attributes(
                                attribute_map={}, dropped_attributes_count=1
                            ),
                        },
                    },
                ]
            ),
        )

    def test_extract_links(self):
        self.assertIsNone(_extract_links([]))
        trace_id = "6e0c63257de34c92bf9efcd03927272e"
        span_id1 = "95bb5edabd45950f"
        span_id2 = "b6b86ad2915c9ddc"
        link1 = Link(
            context=SpanContext(
                trace_id=int(trace_id, 16),
                span_id=int(span_id1, 16),
                is_remote=False,
            ),
            attributes={},
        )
        link2 = Link(
            context=SpanContext(
                trace_id=int(trace_id, 16),
                span_id=int(span_id1, 16),
                is_remote=False,
            ),
            attributes=self.attributes_variety_pack,
        )
        link3 = Link(
            context=SpanContext(
                trace_id=int(trace_id, 16),
                span_id=int(span_id2, 16),
                is_remote=False,
            ),
            attributes={"illegal_attr_value": dict(), "int_attr_value": 123},
        )
        self.assertEqual(
            _extract_links([link1, link2, link3]),
            ProtoSpan.Links(
                link=[
                    {
                        "trace_id": trace_id,
                        "span_id": span_id1,
                        "type": "TYPE_UNSPECIFIED",
                        "attributes": ProtoSpan.Attributes(attribute_map={}),
                    },
                    {
                        "trace_id": trace_id,
                        "span_id": span_id1,
                        "type": "TYPE_UNSPECIFIED",
                        "attributes": self.extracted_attributes_variety_pack,
                    },
                    {
                        "trace_id": trace_id,
                        "span_id": span_id2,
                        "type": "TYPE_UNSPECIFIED",
                        "attributes": {
                            "attribute_map": {
                                "int_attr_value": AttributeValue(int_value=123)
                            },
                            "dropped_attributes_count": 1,
                        },
                    },
                ]
            ),
        )

    # pylint:disable=too-many-locals
    def test_truncate(self):
        """Cloud Trace API imposes limits on the length of many things,
        e.g. strings, number of events, number of attributes. We truncate
        these things before sending it to the API as an optimization.
        """
        str_300 = "a" * 300
        str_256 = "a" * 256
        str_128 = "a" * 128
        self.assertEqual(_truncate_str("aaaa", 1), ("a", 3))
        self.assertEqual(_truncate_str("aaaa", 5), ("aaaa", 0))
        self.assertEqual(_truncate_str("aaaa", 4), ("aaaa", 0))
        self.assertEqual(_truncate_str("中文翻译", 4), ("中", 9))

        self.assertEqual(
            _format_attribute_value(str_300),
            AttributeValue(
                string_value=TruncatableString(
                    value=str_256, truncated_byte_count=300 - 256
                )
            ),
        )

        self.assertEqual(
            _extract_attributes({str_300: str_300}, 4),
            ProtoSpan.Attributes(
                attribute_map={
                    str_128: AttributeValue(
                        string_value=TruncatableString(
                            value=str_256, truncated_byte_count=300 - 256
                        )
                    )
                }
            ),
        )

        time_in_ns1 = 1589919268850900051
        time_in_ms_and_ns1 = {"seconds": 1589919268, "nanos": 850899968}
        event1 = Event(name=str_300, attributes={}, timestamp=time_in_ns1)
        self.assertEqual(
            _extract_events([event1]),
            ProtoSpan.TimeEvents(
                time_event=[
                    {
                        "time": time_in_ms_and_ns1,
                        "annotation": {
                            "description": TruncatableString(
                                value=str_256, truncated_byte_count=300 - 256
                            ),
                            "attributes": {},
                        },
                    },
                ]
            ),
        )

        trace_id = "6e0c63257de34c92bf9efcd03927272e"
        span_id = "95bb5edabd45950f"
        link = Link(
            context=SpanContext(
                trace_id=int(trace_id, 16),
                span_id=int(span_id, 16),
                is_remote=False,
            ),
            attributes={},
        )
        too_many_links = [link] * (MAX_NUM_LINKS + 1)
        self.assertEqual(
            _extract_links(too_many_links),
            ProtoSpan.Links(
                link=[
                    {
                        "trace_id": trace_id,
                        "span_id": span_id,
                        "type": "TYPE_UNSPECIFIED",
                        "attributes": {},
                    }
                ]
                * MAX_NUM_LINKS,
                dropped_links_count=len(too_many_links) - MAX_NUM_LINKS,
            ),
        )

        link_attrs = {}
        for attr_key in range(MAX_LINK_ATTRS + 1):
            link_attrs[str(attr_key)] = 0
        attr_link = Link(
            context=SpanContext(
                trace_id=int(trace_id, 16),
                span_id=int(span_id, 16),
                is_remote=False,
            ),
            attributes=link_attrs,
        )

        proto_link = _extract_links([attr_link])
        self.assertEqual(
            len(proto_link.link[0].attributes.attribute_map), MAX_LINK_ATTRS
        )

        too_many_events = [event1] * (MAX_NUM_EVENTS + 1)
        self.assertEqual(
            _extract_events(too_many_events),
            ProtoSpan.TimeEvents(
                time_event=[
                    {
                        "time": time_in_ms_and_ns1,
                        "annotation": {
                            "description": TruncatableString(
                                value=str_256, truncated_byte_count=300 - 256
                            ),
                            "attributes": {},
                        },
                    },
                ]
                * MAX_NUM_EVENTS,
                dropped_annotations_count=len(too_many_events)
                - MAX_NUM_EVENTS,
            ),
        )

        time_in_ns1 = 1589919268850900051
        event_attrs = {}
        for attr_key in range(MAX_EVENT_ATTRS + 1):
            event_attrs[str(attr_key)] = 0
        proto_events = _extract_events(
            [Event(name="a", attributes=event_attrs, timestamp=time_in_ns1)]
        )
        self.assertEqual(
            len(
                proto_events.time_event[0].annotation.attributes.attribute_map
            ),
            MAX_EVENT_ATTRS,
        )

    def test_strip_characters(self):
        self.assertEqual("0.10.0", _strip_characters("0.10.0b"))
        self.assertEqual("1.20.5", _strip_characters("1.20.5"))
        self.assertEqual("3.1.0", _strip_characters("3.1.0beta"))
        self.assertEqual("4.2.0", _strip_characters("4b.2rc.0a"))
        self.assertEqual("6.20.15", _strip_characters("b6.20.15"))
