Entry Points
============

OpenTelemetry Python uses Python's **entry points** mechanism to provide a pluggable architecture. Entry points allow you to register custom components (exporters, samplers, etc.) that can be discovered and loaded at runtime.

Configuration
-------------

Entry points are controlled via environment variables:

* ``OTEL_TRACES_EXPORTER`` - Trace exporters (e.g., ``console``, ``otlp_proto_grpc``)
* ``OTEL_METRICS_EXPORTER`` - Metrics exporters (e.g., ``console``, ``prometheus``)  
* ``OTEL_LOGS_EXPORTER`` - Log exporters (e.g., ``console``, ``otlp_proto_http``)
* ``OTEL_TRACES_SAMPLER`` - Trace samplers (e.g., ``always_on``, ``traceidratio``)
* ``OTEL_PROPAGATORS`` - Context propagators (e.g., ``tracecontext,baggage``)

Available Entry Point Groups
----------------------------

**Exporters** - Send telemetry data to backends:

* ``opentelemetry_traces_exporter`` - Trace exporters
* ``opentelemetry_metrics_exporter`` - Metrics exporters  
* ``opentelemetry_logs_exporter`` - Log exporters

**Configuration** - Control telemetry behavior:

* ``opentelemetry_traces_sampler`` - Decide which traces to collect
* ``opentelemetry_id_generator`` - Generate trace/span IDs
* ``opentelemetry_resource_detector`` - Detect environment info

**Context** - Manage distributed tracing context:

* ``opentelemetry_propagator`` - Cross-service context propagation
* ``opentelemetry_context`` - Context storage mechanism

**Providers** - Core telemetry factories:

* ``opentelemetry_tracer_provider`` - Create tracers
* ``opentelemetry_meter_provider`` - Create meters
* ``opentelemetry_logger_provider`` - Create loggers

Creating a Custom Exporter
---------------------------

1. **Create your exporter class**:

.. code-block:: python

   from opentelemetry.sdk.trace.export import SpanExporter
   
   class MyExporter(SpanExporter):
       def export(self, spans):
           # Your export logic here
           for span in spans:
               print(f"Exporting: {span.name}")

2. **Register in pyproject.toml**:

.. code-block:: toml

   [project.entry-points.opentelemetry_traces_exporter]
   my_exporter = "mypackage.exporters:MyExporter"

3. **Use it**:

.. code-block:: bash

   export OTEL_TRACES_EXPORTER=my_exporter
   python your_app.py

See Also
--------

* :doc:`trace` - Trace SDK documentation
* :doc:`metrics` - Metrics SDK documentation  
* :doc:`environment_variables` - Environment variable reference 