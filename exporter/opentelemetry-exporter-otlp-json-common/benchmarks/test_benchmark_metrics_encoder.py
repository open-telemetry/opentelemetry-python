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

from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.sdk.metrics import Exemplar
from tests import (
    SPAN_ID,
    TIME,
    TRACE_ID,
    make_exponential_histogram,
    make_gauge,
    make_histogram,
    make_metrics_data,
    make_sum,
)


def test_benchmark_encode_sum(benchmark):
    data = make_metrics_data([make_sum()])
    benchmark(encode_metrics, data)


def test_benchmark_encode_gauge(benchmark):
    data = make_metrics_data([make_gauge()])
    benchmark(encode_metrics, data)


def test_benchmark_encode_histogram(benchmark):
    data = make_metrics_data([
        make_histogram(
            exemplars=[
                Exemplar({"sampled": "true"}, 298.0, TIME, SPAN_ID, TRACE_ID),
            ],
        )
    ])
    benchmark(encode_metrics, data)


def test_benchmark_encode_exponential_histogram(benchmark):
    data = make_metrics_data([make_exponential_histogram()])
    benchmark(encode_metrics, data)


def test_benchmark_encode_mixed_metrics(benchmark):
    data = make_metrics_data([
        make_sum(name="counter"),
        make_gauge(name="gauge"),
        make_histogram(
            name="histogram",
            exemplars=[
                Exemplar({"sampled": "true"}, 298.0, TIME, SPAN_ID, TRACE_ID),
            ],
        ),
        make_exponential_histogram(name="exp_histogram"),
    ])
    benchmark(encode_metrics, data)
