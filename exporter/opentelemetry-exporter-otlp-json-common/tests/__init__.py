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

import dataclasses
import unittest

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Buckets,
    ExponentialHistogram,
    ExponentialHistogramDataPoint,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanContext, _Span
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import (
    NonRecordingSpan,
    TraceFlags,
    set_span_in_context,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

TRACE_ID = 0x3E0C63257DE34C926F9EFCD03927272E
SPAN_ID = 0x34BF92DEEFC58C92
PARENT_SPAN_ID = 0x1111111111111111
BASE_TIME = 683647322 * 10**9
START_TIME = 1641946015139533244
TIME = 1641946016139533244

_UNSET = object()


# ---------------------------------------------------------------------------
# Assertion utilities
# ---------------------------------------------------------------------------


def _is_none_equivalent(val_a, val_b):
    """Check if two values should be treated as equal because one is None
    and the other is the empty/zero default for that type.

    Only None and type-matching empty defaults are considered equivalent:
      None == []   (empty list)
      None == ""   (empty string)
      None == b""  (empty bytes)
      None == 0    (zero int)
      None == 0.0  (zero float)
    """
    if val_a is None and val_b is None:
        return True
    if val_a is None:
        return val_b == type(val_b)()
    if val_b is None:
        return val_a == type(val_a)()
    return False


def assert_proto_json_equal(
    test_case: unittest.TestCase, obj_a, obj_b, path: str = ""
):
    """Recursively compare two proto_json dataclass objects, treating
    None as equivalent to the type's empty default ([], "", b"", 0, 0.0)."""
    if dataclasses.is_dataclass(obj_a) and dataclasses.is_dataclass(obj_b):
        for field in dataclasses.fields(obj_a):
            field_path = f"{path}.{field.name}" if path else field.name
            val_a = getattr(obj_a, field.name)
            val_b = getattr(obj_b, field.name)
            assert_proto_json_equal(test_case, val_a, val_b, field_path)
    elif isinstance(obj_a, list) and isinstance(obj_b, list):
        test_case.assertEqual(
            len(obj_a),
            len(obj_b),
            f"List length mismatch at {path}: {len(obj_a)} != {len(obj_b)}",
        )
        for idx, (item_a, item_b) in enumerate(zip(obj_a, obj_b)):
            assert_proto_json_equal(
                test_case, item_a, item_b, f"{path}[{idx}]"
            )
    elif _is_none_equivalent(obj_a, obj_b):
        pass
    else:
        test_case.assertEqual(
            obj_a, obj_b, f"Mismatch at {path}: {obj_a!r} != {obj_b!r}"
        )


# ---------------------------------------------------------------------------
# Span builders
# ---------------------------------------------------------------------------


def make_span_unended(
    name="test-span",
    trace_id=TRACE_ID,
    span_id=SPAN_ID,
    parent=None,
    resource=None,
    instrumentation_scope=None,
    events=(),
    links=(),
    start_time=BASE_TIME,
):
    if resource is None:
        resource = Resource({})
    span = _Span(
        name=name,
        context=SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        ),
        parent=parent,
        resource=resource,
        instrumentation_scope=instrumentation_scope,
        events=events,
        links=links,
    )
    span.start(start_time=start_time)
    return span


def make_span(
    name="test-span",
    trace_id=TRACE_ID,
    span_id=SPAN_ID,
    parent=None,
    resource=None,
    instrumentation_scope=None,
    events=(),
    links=(),
    start_time=BASE_TIME,
    end_time=BASE_TIME + 50 * 10**6,
):
    span = make_span_unended(
        name=name,
        trace_id=trace_id,
        span_id=span_id,
        parent=parent,
        resource=resource,
        instrumentation_scope=instrumentation_scope,
        events=events,
        links=links,
        start_time=start_time,
    )
    span.end(end_time=end_time)
    return span


# ---------------------------------------------------------------------------
# Log builders
# ---------------------------------------------------------------------------


def make_log_context(trace_id=TRACE_ID, span_id=SPAN_ID):
    return set_span_in_context(
        NonRecordingSpan(
            SpanContext(trace_id, span_id, False, TraceFlags(0x01))
        )
    )


def make_log(
    body="test log message",
    severity_text="INFO",
    severity_number=SeverityNumber.INFO,
    attributes=None,
    timestamp=TIME,
    observed_timestamp=TIME + 1000,
    resource=None,
    instrumentation_scope=_UNSET,
    event_name=None,
    context=None,
    limits=None,
):
    kwargs = {
        "timestamp": timestamp,
        "observed_timestamp": observed_timestamp,
        "severity_text": severity_text,
        "severity_number": severity_number,
        "body": body,
        "attributes": attributes or {},
        "event_name": event_name,
    }
    if context is not None:
        kwargs["context"] = context

    rkwargs = {
        "resource": resource or Resource({}),
        "instrumentation_scope": InstrumentationScope("test_scope", "1.0")
        if instrumentation_scope is _UNSET
        else instrumentation_scope,
    }
    if limits is not None:
        rkwargs["limits"] = limits

    return ReadableLogRecord(LogRecord(**kwargs), **rkwargs)


# ---------------------------------------------------------------------------
# Metric builders
# ---------------------------------------------------------------------------


def make_metrics_data(
    metrics,
    resource_attrs=None,
    resource_schema_url=None,
    scope_name="test_scope",
    scope_version="1.0",
    scope_schema_url=None,
):
    return MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=Resource(
                    attributes=resource_attrs or {},
                    schema_url=resource_schema_url,
                ),
                scope_metrics=[
                    ScopeMetrics(
                        scope=InstrumentationScope(
                            name=scope_name,
                            version=scope_version,
                            schema_url=scope_schema_url,
                        ),
                        metrics=metrics,
                        schema_url=scope_schema_url,
                    )
                ],
                schema_url=resource_schema_url,
            )
        ]
    )


def make_sum(
    name="test_sum",
    value=33,
    attributes=None,
    temporality=AggregationTemporality.CUMULATIVE,
    is_monotonic=True,
    description="desc",
    unit="s",
):
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=Sum(
            data_points=[
                NumberDataPoint(
                    attributes=attributes or {"a": 1},
                    start_time_unix_nano=START_TIME,
                    time_unix_nano=TIME,
                    value=value,
                )
            ],
            aggregation_temporality=temporality,
            is_monotonic=is_monotonic,
        ),
    )


def make_gauge(
    name="test_gauge",
    value=9000,
    attributes=None,
    description="desc",
    unit="1",
):
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=Gauge(
            data_points=[
                NumberDataPoint(
                    attributes=attributes or {"a": 1},
                    start_time_unix_nano=None,
                    time_unix_nano=TIME,
                    value=value,
                )
            ],
        ),
    )


def make_histogram(
    name="test_histogram",
    attributes=None,
    count=5,
    sum_value=67,
    bucket_counts=None,
    explicit_bounds=None,
    min_value=8,
    max_value=18,
    exemplars=None,
    temporality=AggregationTemporality.DELTA,
    description="desc",
    unit="ms",
):
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=Histogram(
            data_points=[
                HistogramDataPoint(
                    attributes=attributes or {"a": 1},
                    start_time_unix_nano=START_TIME,
                    time_unix_nano=TIME,
                    count=count,
                    sum=sum_value,
                    bucket_counts=bucket_counts or [1, 4],
                    explicit_bounds=explicit_bounds or [10.0, 20.0],
                    min=min_value,
                    max=max_value,
                    exemplars=exemplars or [],
                )
            ],
            aggregation_temporality=temporality,
        ),
    )


def make_exponential_histogram(
    name="test_exp_hist",
    attributes=None,
    count=10,
    sum_value=100.5,
    scale=1,
    zero_count=2,
    positive=None,
    negative=None,
    flags=0,
    min_value=1.0,
    max_value=50.0,
    exemplars=None,
    temporality=AggregationTemporality.CUMULATIVE,
    description="desc",
    unit="s",
):
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=ExponentialHistogram(
            data_points=[
                ExponentialHistogramDataPoint(
                    attributes=attributes or {"a": 1},
                    start_time_unix_nano=START_TIME,
                    time_unix_nano=TIME,
                    count=count,
                    sum=sum_value,
                    scale=scale,
                    zero_count=zero_count,
                    positive=positive
                    or Buckets(offset=0, bucket_counts=[1, 2, 3]),
                    negative=negative or Buckets(offset=1, bucket_counts=[1]),
                    flags=flags,
                    min=min_value,
                    max=max_value,
                    exemplars=exemplars or [],
                )
            ],
            aggregation_temporality=temporality,
        ),
    )
