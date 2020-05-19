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

"""
The **OpenTelemetry Datadog Exporter** provides a span exporter from
`OpenTelemetry`_ traces to `Datadog`_ by using the Datadog Agent.

Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.ext.datadog import DatadogExportSpanProcessor, DatadogSpanExporter
    from opentelemetry.sdk.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    exporter = DatadogSpanExporter(
        agent_url="http://agent:8126", service="my-helloworld-service"
    )

    span_processor = DatadogExportSpanProcessor(exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

API
---
.. _Datadog: https://www.datadoghq.com/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
"""
# pylint: disable=import-error

from .exporter import DatadogSpanExporter
from .spanprocessor import DatadogExportSpanProcessor

__all__ = ["DatadogExportSpanProcessor", "DatadogSpanExporter"]
