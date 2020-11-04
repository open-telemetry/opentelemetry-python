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

import unittest
from unittest import mock

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from opencensus.proto.metrics.v1 import metrics_pb2

from opentelemetry import metrics
from opentelemetry.exporter.opencensus import metrics_exporter
from opentelemetry.sdk.metrics import (
    Counter,
    MeterProvider,
    ValueRecorder,
    get_dict_as_key,
)
from opentelemetry.sdk.metrics.export import (
    MetricRecord,
    MetricsExportResult,
    aggregate,
)
from opentelemetry.sdk.resources import Resource


# pylint: disable=no-member
class TestCollectorMetricsExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # pylint: disable=protected-access
        cls._resource_labels = {
            "key_with_str_value": "some string",
            "key_with_int_val": 321,
            "key_with_true": True,
        }
        metrics.set_meter_provider(
            MeterProvider(resource=Resource(cls._resource_labels))
        )
        cls._meter = metrics.get_meter(__name__)
        cls._labels = {"environment": "staging", "number": 321}
        cls._key_labels = get_dict_as_key(cls._labels)

    def test_constructor(self):
        mock_get_node = mock.Mock()
        patch = mock.patch(
            "opentelemetry.exporter.opencensus.util.get_node",
            side_effect=mock_get_node,
        )
        service_name = "testServiceName"
        host_name = "testHostName"
        client = grpc.insecure_channel("")
        endpoint = "testEndpoint"
        with patch:
            exporter = metrics_exporter.OpenCensusMetricsExporter(
                service_name=service_name,
                host_name=host_name,
                endpoint=endpoint,
                client=client,
            )

        self.assertIs(exporter.client, client)
        self.assertEqual(exporter.endpoint, endpoint)
        mock_get_node.assert_called_with(service_name, host_name)

    def test_get_collector_metric_type(self):
        result = metrics_exporter.get_collector_metric_type(
            Counter("testName", "testDescription", "unit", int, None)
        )
        self.assertIs(result, metrics_pb2.MetricDescriptor.CUMULATIVE_INT64)
        result = metrics_exporter.get_collector_metric_type(
            Counter("testName", "testDescription", "unit", float, None)
        )
        self.assertIs(result, metrics_pb2.MetricDescriptor.CUMULATIVE_DOUBLE)
        result = metrics_exporter.get_collector_metric_type(
            ValueRecorder("testName", "testDescription", "unit", None, None)
        )
        self.assertIs(result, metrics_pb2.MetricDescriptor.UNSPECIFIED)

    def test_get_collector_point(self):
        aggregator = aggregate.SumAggregator()
        int_counter = self._meter.create_counter(
            "testName", "testDescription", "unit", int,
        )
        float_counter = self._meter.create_counter(
            "testName", "testDescription", "unit", float,
        )
        valuerecorder = self._meter.create_valuerecorder(
            "testName", "testDescription", "unit", float,
        )
        result = metrics_exporter.get_collector_point(
            MetricRecord(
                int_counter,
                self._key_labels,
                aggregator,
                metrics.get_meter_provider().resource,
            )
        )
        self.assertIsInstance(result, metrics_pb2.Point)
        self.assertIsInstance(result.timestamp, Timestamp)
        self.assertEqual(result.int64_value, 0)
        aggregator.update(123.5)
        aggregator.take_checkpoint()
        result = metrics_exporter.get_collector_point(
            MetricRecord(
                float_counter,
                self._key_labels,
                aggregator,
                metrics.get_meter_provider().resource,
            )
        )
        self.assertEqual(result.double_value, 123.5)
        self.assertRaises(
            TypeError,
            metrics_exporter.get_collector_point(
                MetricRecord(
                    valuerecorder,
                    self._key_labels,
                    aggregator,
                    metrics.get_meter_provider().resource,
                )
            ),
        )

    def test_export(self):
        mock_client = mock.MagicMock()
        mock_export = mock.MagicMock()
        mock_client.Export = mock_export
        host_name = "testHostName"
        collector_exporter = metrics_exporter.OpenCensusMetricsExporter(
            client=mock_client, host_name=host_name
        )
        test_metric = self._meter.create_counter(
            "testname", "testdesc", "unit", int, self._labels.keys(),
        )
        record = MetricRecord(
            test_metric,
            self._key_labels,
            aggregate.SumAggregator(),
            metrics.get_meter_provider().resource,
        )

        result = collector_exporter.export([record])
        self.assertIs(result, MetricsExportResult.SUCCESS)
        # pylint: disable=unsubscriptable-object
        export_arg = mock_export.call_args[0]
        service_request = next(export_arg[0])
        output_metrics = getattr(service_request, "metrics")
        output_node = getattr(service_request, "node")
        self.assertEqual(len(output_metrics), 1)
        self.assertIsNotNone(getattr(output_node, "library_info"))
        self.assertIsNotNone(getattr(output_node, "service_info"))
        output_identifier = getattr(output_node, "identifier")
        self.assertEqual(
            getattr(output_identifier, "host_name"), "testHostName"
        )

    def test_translate_to_collector(self):
        test_metric = self._meter.create_counter(
            "testname", "testdesc", "unit", int, self._labels.keys()
        )
        aggregator = aggregate.SumAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(
            test_metric,
            self._key_labels,
            aggregator,
            metrics.get_meter_provider().resource,
        )
        start_timestamp = Timestamp()
        output_metrics = metrics_exporter.translate_to_collector(
            [record], start_timestamp,
        )
        self.assertEqual(len(output_metrics), 1)
        self.assertIsInstance(output_metrics[0], metrics_pb2.Metric)
        self.assertEqual(output_metrics[0].metric_descriptor.name, "testname")
        self.assertEqual(
            output_metrics[0].metric_descriptor.description, "testdesc"
        )
        self.assertEqual(output_metrics[0].metric_descriptor.unit, "unit")
        self.assertEqual(
            output_metrics[0].metric_descriptor.type,
            metrics_pb2.MetricDescriptor.CUMULATIVE_INT64,
        )
        self.assertEqual(
            len(output_metrics[0].metric_descriptor.label_keys), 2
        )
        self.assertEqual(
            output_metrics[0].metric_descriptor.label_keys[0].key,
            "environment",
        )
        self.assertEqual(
            output_metrics[0].metric_descriptor.label_keys[1].key, "number",
        )

        self.assertIsNotNone(output_metrics[0].resource)
        self.assertEqual(
            output_metrics[0].resource.type, "",
        )
        self.assertEqual(
            output_metrics[0].resource.labels["key_with_str_value"],
            self._resource_labels["key_with_str_value"],
        )
        self.assertIsInstance(
            output_metrics[0].resource.labels["key_with_int_val"], str,
        )
        self.assertEqual(
            output_metrics[0].resource.labels["key_with_int_val"],
            str(self._resource_labels["key_with_int_val"]),
        )
        self.assertIsInstance(
            output_metrics[0].resource.labels["key_with_true"], str,
        )
        self.assertEqual(
            output_metrics[0].resource.labels["key_with_true"],
            str(self._resource_labels["key_with_true"]),
        )

        self.assertEqual(len(output_metrics[0].timeseries), 1)
        self.assertEqual(len(output_metrics[0].timeseries[0].label_values), 2)
        self.assertEqual(
            output_metrics[0].timeseries[0].start_timestamp, start_timestamp
        )
        self.assertEqual(
            output_metrics[0].timeseries[0].label_values[0].has_value, True
        )
        self.assertEqual(
            output_metrics[0].timeseries[0].label_values[0].value, "staging"
        )
        self.assertEqual(len(output_metrics[0].timeseries[0].points), 1)
        self.assertEqual(
            output_metrics[0].timeseries[0].points[0].timestamp.seconds,
            record.aggregator.last_update_timestamp // 1000000000,
        )
        self.assertEqual(
            output_metrics[0].timeseries[0].points[0].timestamp.nanos,
            record.aggregator.last_update_timestamp % 1000000000,
        )
        self.assertEqual(
            output_metrics[0].timeseries[0].points[0].int64_value, 123
        )

    def test_infer_ot_resource_type(self):
        # empty resource
        self.assertEqual(metrics_exporter.infer_oc_resource_type({}), "")

        # container
        self.assertEqual(
            metrics_exporter.infer_oc_resource_type(
                {
                    "k8s.cluster.name": "cluster1",
                    "k8s.pod.name": "pod1",
                    "k8s.namespace.name": "namespace1",
                    "container.name": "container-name1",
                    "cloud.account.id": "proj1",
                    "cloud.zone": "zone1",
                }
            ),
            "container",
        )

        # k8s pod
        self.assertEqual(
            metrics_exporter.infer_oc_resource_type(
                {
                    "k8s.cluster.name": "cluster1",
                    "k8s.pod.name": "pod1",
                    "k8s.namespace.name": "namespace1",
                    "cloud.zone": "zone1",
                }
            ),
            "k8s",
        )

        # host
        self.assertEqual(
            metrics_exporter.infer_oc_resource_type(
                {
                    "k8s.cluster.name": "cluster1",
                    "cloud.zone": "zone1",
                    "host.name": "node1",
                }
            ),
            "host",
        )

        # cloud
        self.assertEqual(
            metrics_exporter.infer_oc_resource_type(
                {
                    "cloud.provider": "gcp",
                    "host.id": "inst1",
                    "cloud.zone": "zone1",
                }
            ),
            "cloud",
        )
