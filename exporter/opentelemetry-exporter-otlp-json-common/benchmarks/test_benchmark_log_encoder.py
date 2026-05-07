# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
