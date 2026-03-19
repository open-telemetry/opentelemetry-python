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

import pytest

from opentelemetry._logs import SeverityNumber
from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from tests import TIME, make_log, make_log_context


@pytest.mark.parametrize("batch_size", [1, 10, 100])
def test_benchmark_encode_logs(benchmark, batch_size):
    ctx = make_log_context()
    logs = [
        make_log(
            body=f"log message {i}",
            context=ctx,
            timestamp=TIME + i,
            observed_timestamp=TIME + i + 1000,
            severity_text="INFO",
            severity_number=SeverityNumber.INFO,
        )
        for i in range(batch_size)
    ]

    benchmark(encode_logs, logs)
