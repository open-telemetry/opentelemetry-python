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

from __future__ import annotations

import unittest
from dataclasses import replace
from logging import WARNING

from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    split_metrics_data,
)
from opentelemetry.proto_json.collector.metrics.v1.metrics_service import (
    ExportMetricsServiceRequest as JSONExportMetricsServiceRequest,
)
from opentelemetry.proto_json.common.v1.common import (
    InstrumentationScope as JSONInstrumentationScope,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ExponentialHistogram as JSONExponentialHistogram,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ExponentialHistogramDataPoint as JSONExponentialHistogramDataPoint,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    Gauge as JSONGauge,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    Histogram as JSONHistogram,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    HistogramDataPoint as JSONHistogramDataPoint,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    Metric as JSONMetric,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    NumberDataPoint as JSONNumberDataPoint,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ResourceMetrics as JSONResourceMetrics,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    ScopeMetrics as JSONScopeMetrics,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    Sum as JSONSum,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    Summary as JSONSummary,
)
from opentelemetry.proto_json.metrics.v1.metrics import (
    SummaryDataPoint as JSONSummaryDataPoint,
)
from opentelemetry.proto_json.resource.v1.resource import (
    Resource as JSONResource,
)

_METRIC_FIELDS = (
    "gauge",
    "sum",
    "histogram",
    "exponential_histogram",
    "summary",
)


def _sum_metric(name: str, *values: int) -> JSONMetric:
    return JSONMetric(
        name=name,
        sum=JSONSum(
            data_points=[JSONNumberDataPoint(as_int=v) for v in values]
        ),
    )


def _gauge_metric(name: str, *values: int) -> JSONMetric:
    return JSONMetric(
        name=name,
        gauge=JSONGauge(
            data_points=[JSONNumberDataPoint(as_int=v) for v in values]
        ),
    )


def _histogram_metric(name: str, count: int) -> JSONMetric:
    return JSONMetric(
        name=name,
        histogram=JSONHistogram(
            data_points=[JSONHistogramDataPoint(count=i) for i in range(count)]
        ),
    )


def _exp_histogram_metric(name: str, count: int) -> JSONMetric:
    return JSONMetric(
        name=name,
        exponential_histogram=JSONExponentialHistogram(
            data_points=[
                JSONExponentialHistogramDataPoint() for _ in range(count)
            ]
        ),
    )


def _summary_metric(name: str, count: int) -> JSONMetric:
    return JSONMetric(
        name=name,
        summary=JSONSummary(
            data_points=[JSONSummaryDataPoint() for _ in range(count)]
        ),
    )


def _sm(
    scope: JSONInstrumentationScope, *metrics: JSONMetric
) -> JSONScopeMetrics:
    return JSONScopeMetrics(scope=scope, metrics=list(metrics))


def _rm(
    resource: JSONResource, *scope_metrics: JSONScopeMetrics
) -> JSONResourceMetrics:
    return JSONResourceMetrics(
        resource=resource, scope_metrics=list(scope_metrics)
    )


def _req(
    *resource_metrics: JSONResourceMetrics,
) -> JSONExportMetricsServiceRequest:
    return JSONExportMetricsServiceRequest(
        resource_metrics=list(resource_metrics)
    )


def _pts(
    batch: JSONExportMetricsServiceRequest,
    rm: int = 0,
    sm: int = 0,
    m: int = 0,
) -> list:
    """Shorthand to extract data_points from a batch via rm/sm/metric indices."""
    metric = batch.resource_metrics[rm].scope_metrics[sm].metrics[m]
    for field in _METRIC_FIELDS:
        data = getattr(metric, field, None)
        if data is not None:
            return data.data_points
    return []


def _count_data_points(batch: JSONExportMetricsServiceRequest) -> int:
    """Count total data points across all metrics in a batch."""
    total = 0
    for rm in batch.resource_metrics:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                for field in _METRIC_FIELDS:
                    data = getattr(metric, field, None)
                    if data is not None:
                        total += len(data.data_points)
    return total


def _merge_metrics(metrics: list[JSONMetric]) -> list[JSONMetric]:
    """For each unique metric name (in order), merge all data points into one metric."""
    seen: dict[str | None, tuple[JSONMetric, str, list]] = {}
    for metric in metrics:
        field = next(
            f for f in _METRIC_FIELDS if getattr(metric, f) is not None
        )
        seen.setdefault(metric.name, (metric, field, []))
        seen[metric.name][2].extend(getattr(metric, field).data_points)
    return [
        replace(
            template,
            **{field: replace(getattr(template, field), data_points=pts)},
        )
        for template, field, pts in seen.values()
    ]


def _merge_scope_metrics(
    scope_metrics: list[JSONScopeMetrics],
) -> list[JSONScopeMetrics]:
    """For each unique scope (by identity, in order), merge all metrics."""
    seen: dict[
        int, tuple[JSONInstrumentationScope | None, list[JSONMetric]]
    ] = {}
    for sm in scope_metrics:
        sid = id(sm.scope)
        seen.setdefault(sid, (sm.scope, []))
        seen[sid][1].extend(sm.metrics)
    return [
        JSONScopeMetrics(scope=scope, metrics=_merge_metrics(metrics))
        for scope, metrics in seen.values()
    ]


def _merge_resource_metrics(
    resource_metrics: list[JSONResourceMetrics],
) -> list[JSONResourceMetrics]:
    """For each unique resource (by identity, in order), merge all scope metrics."""
    seen: dict[int, tuple[JSONResource, list[JSONScopeMetrics]]] = {}
    for rm in resource_metrics:
        rid = id(rm.resource)
        seen.setdefault(rid, (rm.resource, []))
        seen[rid][1].extend(rm.scope_metrics)
    return [
        JSONResourceMetrics(
            resource=resource, scope_metrics=_merge_scope_metrics(sms)
        )
        for resource, sms in seen.values()
    ]


def _merge_requests(
    batches: list[JSONExportMetricsServiceRequest],
) -> JSONExportMetricsServiceRequest:
    """Reconstruct a single request from split batches."""
    all_rms = [rm for batch in batches for rm in batch.resource_metrics]
    return JSONExportMetricsServiceRequest(
        resource_metrics=_merge_resource_metrics(all_rms)
    )


class TestSplitMetricsDataEdgeCases(unittest.TestCase):
    def setUp(self):
        self.resource = JSONResource()
        self.scope = JSONInstrumentationScope()

    def test_none_max_size_returns_original(self):
        req = _req(
            _rm(self.resource, _sm(self.scope, _sum_metric("m", 1, 2, 3)))
        )
        batches = list(split_metrics_data(req, None))
        self.assertEqual(len(batches), 1)
        self.assertIs(batches[0], req)

    def test_empty_inputs_yield_nothing(self):
        cases = [
            ("no_resource_metrics", _req()),
            ("no_scope_metrics", _req(_rm(self.resource))),
            (
                "empty_metrics_list",
                _req(
                    _rm(
                        self.resource,
                        JSONScopeMetrics(scope=self.scope, metrics=[]),
                    )
                ),
            ),
            (
                "no_data_points",
                _req(
                    _rm(
                        self.resource,
                        _sm(
                            self.scope,
                            JSONMetric(
                                name="empty", sum=JSONSum(data_points=[])
                            ),
                        ),
                    )
                ),
            ),
        ]
        for label, req in cases:
            with self.subTest(case=label):
                self.assertEqual(list(split_metrics_data(req, 10)), [])

    def test_unsupported_metric_type_warns(self):
        req = _req(
            _rm(self.resource, _sm(self.scope, JSONMetric(name="no_field")))
        )
        with self.assertLogs(level=WARNING):
            batches = list(split_metrics_data(req, 10))
        self.assertEqual(batches, [])

    def test_single_batch_when_under_limit(self):
        req = _req(
            _rm(self.resource, _sm(self.scope, _sum_metric("m", 0, 1, 2)))
        )
        self.assertEqual(len(list(split_metrics_data(req, 100))), 1)


class TestSplitMetricsData(unittest.TestCase):
    def setUp(self):
        self.resource = JSONResource()
        self.resource_a = JSONResource()
        self.resource_b = JSONResource()
        self.scope = JSONInstrumentationScope()
        self.scope_a = JSONInstrumentationScope(name="scope_a")
        self.scope_b = JSONInstrumentationScope(name="scope_b")

    def split(self, req, max_size):
        return list(split_metrics_data(req, max_size))

    def assert_roundtrip(self, req, batches):
        self.assertEqual(_merge_requests(batches), req)

    def test_all_metric_types(self):
        """Every metric type splits correctly and respects max batch size."""
        cases = [
            ("sum", _sum_metric("s", 0, 1, 2, 3)),
            ("gauge", _gauge_metric("g", 0, 1, 2, 3)),
            ("histogram", _histogram_metric("h", 4)),
            ("exponential_histogram", _exp_histogram_metric("eh", 4)),
            ("summary", _summary_metric("s", 4)),
        ]
        for field_name, metric in cases:
            req = _req(_rm(self.resource, _sm(self.scope, metric)))
            for max_size in [1, 2, 3, 10]:
                with self.subTest(metric_type=field_name, max_size=max_size):
                    batches = self.split(req, max_size)
                    self.assertEqual(len(batches), -(-4 // max_size))
                    for batch in batches:
                        self.assertLessEqual(
                            _count_data_points(batch), max_size
                        )
                    self.assert_roundtrip(req, batches)

    def test_no_split_preserves_structure(self):
        """When all data fits in one batch, hierarchy is preserved as-is."""
        cases = [
            (
                "two_metrics_one_scope",
                _req(
                    _rm(
                        self.resource,
                        _sm(
                            self.scope,
                            _sum_metric("sum_a", 1, 2),
                            _gauge_metric("gauge_b", 3, 4),
                        ),
                    )
                ),
            ),
            (
                "two_scopes",
                _req(
                    _rm(
                        self.resource,
                        _sm(self.scope_a, _sum_metric("m", 1)),
                        _sm(self.scope_b, _sum_metric("m", 2)),
                    )
                ),
            ),
            (
                "two_resources",
                _req(
                    _rm(self.resource_a, _sm(self.scope, _sum_metric("m", 1))),
                    _rm(self.resource_b, _sm(self.scope, _sum_metric("m", 2))),
                ),
            ),
        ]
        for label, req in cases:
            with self.subTest(case=label):
                batches = self.split(req, 10)
                self.assertEqual(len(batches), 1)
                self.assert_roundtrip(req, batches)

    def test_split_preserves_identity(self):
        """After splitting, resource and scope objects are the same instances."""
        cases = [
            (
                "scope",
                (
                    _req(
                        _rm(
                            self.resource,
                            _sm(self.scope_a, _sum_metric("m", 1, 2)),
                        )
                    ),
                    lambda b: b.resource_metrics[0].scope_metrics[0].scope,
                    self.scope_a,
                ),
            ),
            (
                "resource",
                (
                    _req(
                        _rm(
                            self.resource_a,
                            _sm(self.scope, _sum_metric("m", 1, 2)),
                        )
                    ),
                    lambda b: b.resource_metrics[0].resource,
                    self.resource_a,
                ),
            ),
        ]
        for label, (req, extract, expected) in cases:
            with self.subTest(level=label):
                batches = self.split(req, 1)
                for i, batch in enumerate(batches):
                    with self.subTest(batch=i):
                        self.assertIs(extract(batch), expected)
                self.assert_roundtrip(req, batches)

    def test_split_mid_metric(self):
        """A batch boundary mid-metric keeps earlier metrics in the first batch."""
        req = _req(
            _rm(
                self.resource,
                _sm(
                    self.scope,
                    _sum_metric("sum_a", 10),
                    _gauge_metric("gauge_b", 20, 21, 22),
                ),
            )
        )
        batches = self.split(req, 2)
        self.assertEqual(len(batches), 2)

        b0_metrics = batches[0].resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(len(b0_metrics), 2)
        self.assertEqual(
            [p.as_int for p in b0_metrics[0].sum.data_points], [10]
        )
        self.assertEqual(
            [p.as_int for p in b0_metrics[1].gauge.data_points], [20]
        )

        b1_metrics = batches[1].resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(len(b1_metrics), 1)
        self.assertEqual(
            [p.as_int for p in b1_metrics[0].gauge.data_points], [21, 22]
        )
        self.assert_roundtrip(req, batches)

    def test_split_across_hierarchy(self):
        """Data spanning two scopes or two resources splits identically"""
        cases = [
            (
                "scopes",
                _req(
                    _rm(
                        self.resource,
                        _sm(self.scope_a, _sum_metric("m", 0, 1, 2)),
                        _sm(self.scope_b, _sum_metric("m", 0, 1)),
                    )
                ),
            ),
            (
                "resources",
                _req(
                    _rm(
                        self.resource_a,
                        _sm(self.scope, _sum_metric("m", 0, 1, 2)),
                    ),
                    _rm(
                        self.resource_b,
                        _sm(self.scope, _sum_metric("m", 0, 1)),
                    ),
                ),
            ),
        ]
        for label, req in cases:
            with self.subTest(level=label):
                batches = self.split(req, 2)
                self.assertEqual(len(batches), 3)
                self.assertEqual(
                    [_count_data_points(b) for b in batches], [2, 2, 1]
                )
                self.assert_roundtrip(req, batches)
