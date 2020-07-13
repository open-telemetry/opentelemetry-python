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

from google.api.label_pb2 import LabelDescriptor
from google.api.metric_pb2 import MetricDescriptor
from google.api.monitored_resource_pb2 import MonitoredResource
from google.cloud.monitoring_v3.proto.metric_pb2 import TimeSeries

from opentelemetry.exporter.cloud_monitoring import (
    MAX_BATCH_WRITE,
    UNIQUE_IDENTIFIER_KEY,
    WRITE_INTERVAL,
    CloudMonitoringMetricsExporter,
)
from opentelemetry.sdk.metrics.export import MetricRecord
from opentelemetry.sdk.metrics.export.aggregate import SumAggregator
from opentelemetry.sdk.resources import Resource


class UnsupportedAggregator:
    pass


class MockMeter:
    def __init__(self, resource=Resource.create_empty(), stateful=True):
        self.resource = resource
        self.stateful = stateful


class MockMetric:
    def __init__(
        self,
        name="name",
        description="description",
        value_type=int,
        meter=None,
        stateful=True,
    ):
        self.name = name
        self.description = description
        self.value_type = value_type
        self.meter = meter or MockMeter(stateful=stateful)


# pylint: disable=protected-access
# pylint can't deal with ProtoBuf object members
# pylint: disable=no-member


class TestCloudMonitoringMetricsExporter(unittest.TestCase):
    def setUp(self):
        self.client_patcher = mock.patch(
            "opentelemetry.exporter.cloud_monitoring.MetricServiceClient"
        )
        self.client_patcher.start()
        self.project_id = "PROJECT"
        self.project_name = "PROJECT_NAME"

    def tearDown(self):
        self.client_patcher.stop()

    def test_constructor_default(self):
        exporter = CloudMonitoringMetricsExporter(self.project_id)
        self.assertEqual(exporter.project_id, self.project_id)

    def test_constructor_explicit(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            self.project_id, client=client
        )

        self.assertIs(exporter.client, client)
        self.assertEqual(exporter.project_id, self.project_id)

    def test_batch_write(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            project_id=self.project_id, client=client
        )
        exporter.project_name = self.project_name
        exporter._batch_write(range(2 * MAX_BATCH_WRITE + 1))
        client.create_time_series.assert_has_calls(
            [
                mock.call(self.project_name, range(MAX_BATCH_WRITE)),
                mock.call(
                    self.project_name,
                    range(MAX_BATCH_WRITE, 2 * MAX_BATCH_WRITE),
                ),
                mock.call(
                    self.project_name,
                    range(2 * MAX_BATCH_WRITE, 2 * MAX_BATCH_WRITE + 1),
                ),
            ]
        )

        exporter._batch_write(range(MAX_BATCH_WRITE))
        client.create_time_series.assert_has_calls(
            [mock.call(self.project_name, range(MAX_BATCH_WRITE))]
        )

        exporter._batch_write(range(MAX_BATCH_WRITE - 1))
        client.create_time_series.assert_has_calls(
            [mock.call(self.project_name, range(MAX_BATCH_WRITE - 1))]
        )

    def test_get_metric_descriptor(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            project_id=self.project_id, client=client
        )
        exporter.project_name = self.project_name

        self.assertIsNone(
            exporter._get_metric_descriptor(
                MetricRecord(MockMetric(), (), UnsupportedAggregator())
            )
        )

        record = MetricRecord(
            MockMetric(), (("label1", "value1"),), SumAggregator(),
        )
        metric_descriptor = exporter._get_metric_descriptor(record)
        client.create_metric_descriptor.assert_called_with(
            self.project_name,
            MetricDescriptor(
                **{
                    "name": None,
                    "type": "custom.googleapis.com/OpenTelemetry/name",
                    "display_name": "name",
                    "description": "description",
                    "labels": [
                        LabelDescriptor(key="label1", value_type="STRING")
                    ],
                    "metric_kind": "CUMULATIVE",
                    "value_type": "INT64",
                }
            ),
        )

        # Getting a cached metric descriptor shouldn't use another call
        cached_metric_descriptor = exporter._get_metric_descriptor(record)
        self.assertEqual(client.create_metric_descriptor.call_count, 1)
        self.assertEqual(metric_descriptor, cached_metric_descriptor)

        # Drop labels with values that aren't string, int or bool
        exporter._get_metric_descriptor(
            MetricRecord(
                MockMetric(name="name2", value_type=float),
                (
                    ("label1", "value1"),
                    ("label2", dict()),
                    ("label3", 3),
                    ("label4", False),
                ),
                SumAggregator(),
            )
        )
        client.create_metric_descriptor.assert_called_with(
            self.project_name,
            MetricDescriptor(
                **{
                    "name": None,
                    "type": "custom.googleapis.com/OpenTelemetry/name2",
                    "display_name": "name2",
                    "description": "description",
                    "labels": [
                        LabelDescriptor(key="label1", value_type="STRING"),
                        LabelDescriptor(key="label3", value_type="INT64"),
                        LabelDescriptor(key="label4", value_type="BOOL"),
                    ],
                    "metric_kind": "CUMULATIVE",
                    "value_type": "DOUBLE",
                }
            ),
        )

    def test_export(self):
        client = mock.Mock()

        with mock.patch(
            "opentelemetry.exporter.cloud_monitoring.time_ns", lambda: 1e9
        ):
            exporter = CloudMonitoringMetricsExporter(
                project_id=self.project_id, client=client
            )

        exporter.project_name = self.project_name

        exporter.export(
            [
                MetricRecord(
                    MockMetric(),
                    (("label1", "value1"),),
                    UnsupportedAggregator(),
                )
            ]
        )
        client.create_time_series.assert_not_called()

        client.create_metric_descriptor.return_value = MetricDescriptor(
            **{
                "name": None,
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [
                    LabelDescriptor(key="label1", value_type="STRING"),
                    LabelDescriptor(key="label2", value_type="INT64"),
                ],
                "metric_kind": "CUMULATIVE",
                "value_type": "DOUBLE",
            }
        )

        resource = Resource(
            labels={
                "cloud.account.id": 123,
                "host.id": "host",
                "cloud.zone": "US",
                "cloud.provider": "gcp",
                "extra_info": "extra",
                "gcp.resource_type": "gce_instance",
                "not_gcp_resource": "value",
            }
        )

        sum_agg_one = SumAggregator()
        sum_agg_one.checkpoint = 1
        sum_agg_one.last_update_timestamp = (WRITE_INTERVAL + 1) * 1e9
        exporter.export(
            [
                MetricRecord(
                    MockMetric(meter=MockMeter(resource=resource)),
                    (("label1", "value1"), ("label2", 1),),
                    sum_agg_one,
                ),
                MetricRecord(
                    MockMetric(meter=MockMeter(resource=resource)),
                    (("label1", "value2"), ("label2", 2),),
                    sum_agg_one,
                ),
            ]
        )
        expected_resource = MonitoredResource(
            type="gce_instance",
            labels={"project_id": "123", "instance_id": "host", "zone": "US"},
        )

        series1 = TimeSeries(resource=expected_resource)
        series1.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        series1.metric.labels["label1"] = "value1"
        series1.metric.labels["label2"] = "1"
        point = series1.points.add()
        point.value.int64_value = 1
        point.interval.end_time.seconds = WRITE_INTERVAL + 1
        point.interval.end_time.nanos = 0
        point.interval.start_time.seconds = 1
        point.interval.start_time.nanos = 0

        series2 = TimeSeries(resource=expected_resource)
        series2.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        series2.metric.labels["label1"] = "value2"
        series2.metric.labels["label2"] = "2"
        point = series2.points.add()
        point.value.int64_value = 1
        point.interval.end_time.seconds = WRITE_INTERVAL + 1
        point.interval.end_time.nanos = 0
        point.interval.start_time.seconds = 1
        point.interval.start_time.nanos = 0

        client.create_time_series.assert_has_calls(
            [mock.call(self.project_name, [series1, series2])]
        )

        # Attempting to export too soon after another export with the exact
        # same labels leads to it being dropped

        sum_agg_two = SumAggregator()
        sum_agg_two.checkpoint = 1
        sum_agg_two.last_update_timestamp = (WRITE_INTERVAL + 2) * 1e9
        exporter.export(
            [
                MetricRecord(
                    MockMetric(),
                    (("label1", "value1"), ("label2", 1),),
                    sum_agg_two,
                ),
                MetricRecord(
                    MockMetric(),
                    (("label1", "value2"), ("label2", 2),),
                    sum_agg_two,
                ),
            ]
        )
        self.assertEqual(client.create_time_series.call_count, 1)

        # But exporting with different labels is fine
        sum_agg_two.checkpoint = 2
        exporter.export(
            [
                MetricRecord(
                    MockMetric(),
                    (("label1", "changed_label"), ("label2", 2),),
                    sum_agg_two,
                ),
            ]
        )
        series3 = TimeSeries()
        series3.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        series3.metric.labels["label1"] = "changed_label"
        series3.metric.labels["label2"] = "2"
        point = series3.points.add()
        point.value.int64_value = 2
        point.interval.end_time.seconds = WRITE_INTERVAL + 2
        point.interval.end_time.nanos = 0
        point.interval.start_time.seconds = 1
        point.interval.start_time.nanos = 0

        client.create_time_series.assert_has_calls(
            [
                mock.call(self.project_name, [series1, series2]),
                mock.call(self.project_name, [series3]),
            ]
        )

    def test_stateless_times(self):
        client = mock.Mock()
        with mock.patch(
            "opentelemetry.exporter.cloud_monitoring.time_ns", lambda: 1e9
        ):
            exporter = CloudMonitoringMetricsExporter(
                project_id=self.project_id, client=client,
            )

        client.create_metric_descriptor.return_value = MetricDescriptor(
            **{
                "name": None,
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [
                    LabelDescriptor(
                        key=UNIQUE_IDENTIFIER_KEY, value_type="STRING"
                    ),
                ],
                "metric_kind": "CUMULATIVE",
                "value_type": "DOUBLE",
            }
        )

        agg = SumAggregator()
        agg.checkpoint = 1
        agg.last_update_timestamp = (WRITE_INTERVAL + 1) * 1e9

        metric_record = MetricRecord(MockMetric(stateful=False), (), agg)

        exporter.export([metric_record])

        exports_1 = client.create_time_series.call_args_list[0]

        # verify the first metric started at exporter start time
        self.assertEqual(
            exports_1[0][1][0].points[0].interval.start_time.seconds, 1
        )
        self.assertEqual(
            exports_1[0][1][0].points[0].interval.start_time.nanos, 0
        )

        self.assertEqual(
            exports_1[0][1][0].points[0].interval.end_time.seconds,
            WRITE_INTERVAL + 1,
        )

        agg.last_update_timestamp = (WRITE_INTERVAL * 2 + 2) * 1e9

        metric_record = MetricRecord(MockMetric(stateful=False), (), agg)

        exporter.export([metric_record])

        exports_2 = client.create_time_series.call_args_list[1]

        # 1ms ahead of end time of last export
        self.assertEqual(
            exports_2[0][1][0].points[0].interval.start_time.seconds,
            WRITE_INTERVAL + 1,
        )
        self.assertEqual(
            exports_2[0][1][0].points[0].interval.start_time.nanos, 1e6
        )

        self.assertEqual(
            exports_2[0][1][0].points[0].interval.end_time.seconds,
            WRITE_INTERVAL * 2 + 2,
        )

    def test_unique_identifier(self):
        client = mock.Mock()
        exporter1 = CloudMonitoringMetricsExporter(
            project_id=self.project_id,
            client=client,
            add_unique_identifier=True,
        )
        exporter2 = CloudMonitoringMetricsExporter(
            project_id=self.project_id,
            client=client,
            add_unique_identifier=True,
        )
        exporter1.project_name = self.project_name
        exporter2.project_name = self.project_name

        client.create_metric_descriptor.return_value = MetricDescriptor(
            **{
                "name": None,
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [
                    LabelDescriptor(
                        key=UNIQUE_IDENTIFIER_KEY, value_type="STRING"
                    ),
                ],
                "metric_kind": "CUMULATIVE",
                "value_type": "DOUBLE",
            }
        )

        sum_agg_one = SumAggregator()
        sum_agg_one.update(1)
        metric_record = MetricRecord(MockMetric(), (), sum_agg_one,)
        exporter1.export([metric_record])
        exporter2.export([metric_record])

        (
            first_call,
            second_call,
        ) = client.create_metric_descriptor.call_args_list
        self.assertEqual(first_call[0][1].labels[0].key, UNIQUE_IDENTIFIER_KEY)
        self.assertEqual(
            second_call[0][1].labels[0].key, UNIQUE_IDENTIFIER_KEY
        )

        first_call, second_call = client.create_time_series.call_args_list
        self.assertNotEqual(
            first_call[0][1][0].metric.labels[UNIQUE_IDENTIFIER_KEY],
            second_call[0][1][0].metric.labels[UNIQUE_IDENTIFIER_KEY],
        )

    def test_extract_resources(self):
        exporter = CloudMonitoringMetricsExporter(project_id=self.project_id)

        self.assertIsNone(
            exporter._get_monitored_resource(Resource.create_empty())
        )
        resource = Resource(
            labels={
                "cloud.account.id": 123,
                "host.id": "host",
                "cloud.zone": "US",
                "cloud.provider": "gcp",
                "extra_info": "extra",
                "gcp.resource_type": "gce_instance",
                "not_gcp_resource": "value",
            }
        )
        expected_extract = MonitoredResource(
            type="gce_instance",
            labels={"project_id": "123", "instance_id": "host", "zone": "US"},
        )
        self.assertEqual(
            exporter._get_monitored_resource(resource), expected_extract
        )

        resource = Resource(
            labels={
                "cloud.account.id": "123",
                "host.id": "host",
                "extra_info": "extra",
                "not_gcp_resource": "value",
                "gcp.resource_type": "gce_instance",
                "cloud.provider": "gcp",
            }
        )
        # Should throw when passed a malformed GCP resource dict
        self.assertRaises(KeyError, exporter._get_monitored_resource, resource)

        resource = Resource(
            labels={
                "cloud.account.id": "123",
                "host.id": "host",
                "extra_info": "extra",
                "not_gcp_resource": "value",
                "gcp.resource_type": "unsupported_gcp_resource",
                "cloud.provider": "gcp",
            }
        )
        self.assertIsNone(exporter._get_monitored_resource(resource))

        resource = Resource(
            labels={
                "cloud.account.id": "123",
                "host.id": "host",
                "extra_info": "extra",
                "not_gcp_resource": "value",
                "cloud.provider": "aws",
            }
        )
        self.assertIsNone(exporter._get_monitored_resource(resource))
