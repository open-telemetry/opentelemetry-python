Entry Points
============

OpenTelemetry Python uses Python's `entry points <https://setuptools.pypa.io/en/stable/userguide/entry_point.html>`_ mechanism to provide a pluggable architecture. Entry points allow you to register custom components (exporters, samplers, etc.) that can be discovered and loaded at runtime.

Configuration
-------------

The SDK supports configuring entry points via environment variables by specifying the entry point name. For a complete list of supported environment variables, see :doc:`../api/environment_variables`.

Entry Point Configuration Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 
   :header-rows: 1
   :widths: 20 20 40 20

   * - Environment Variable
     - Entry Point Group
     - Available Entrypoint Names
     - Base Type
   * - OTEL_LOGS_EXPORTER
     - opentelemetry_logs_exporter  
     - ``console``, ``otlp_proto_grpc``, ``otlp_proto_http``
     - LogExporter
   * - OTEL_METRICS_EXPORTER
     - opentelemetry_metrics_exporter
     - ``console``, ``otlp``, ``otlp_proto_grpc``, 
       ``otlp_proto_http``, ``prometheus``
     - :class:`MetricExporter <opentelemetry.sdk.metrics.export.MetricExporter>` or :class:`MetricReader <opentelemetry.sdk.metrics.export.MetricReader>`
   * - OTEL_PROPAGATORS
     - opentelemetry_propagator
     - ``b3``, ``b3multi``, ``baggage``, 
       ``jaeger``, ``tracecontext``
     - :class:`TextMapPropagator <opentelemetry.propagators.textmap.TextMapPropagator>`
   * - OTEL_TRACES_SAMPLER
     - opentelemetry_traces_sampler
     - ``always_off``, ``always_on``, ``parentbased_always_off``, 
       ``parentbased_always_on``, ``parentbased_traceidratio``, ``traceidratio``
     - :class:`Sampler <opentelemetry.sdk.trace.sampling.Sampler>`
   * - OTEL_EXPERIMENTAL_RESOURCE_DETECTORS
     - opentelemetry_resource_detector
     - ``host``, ``os``, ``otel``, ``process``
     - :class:`ResourceDetector <opentelemetry.sdk.resources.ResourceDetector>`
   * - OTEL_PYTHON_ID_GENERATOR
     - opentelemetry_id_generator
     - ``random``
     - :class:`IdGenerator <opentelemetry.sdk.trace.id_generator.IdGenerator>`
   * - OTEL_TRACES_EXPORTER
     - opentelemetry_traces_exporter
     - ``console``, ``otlp``, ``otlp_proto_grpc``, ``otlp_proto_http``, 
       ``zipkin``, ``zipkin_json``, ``zipkin_proto``
     - :class:`SpanExporter <opentelemetry.sdk.trace.export.SpanExporter>`
   * - OTEL_PYTHON_TRACER_PROVIDER
     - opentelemetry_tracer_provider
     - ``default_tracer_provider``, ``sdk_tracer_provider``
     - :class:`TracerProvider <opentelemetry.trace.TracerProvider>`
   * - OTEL_PYTHON_METER_PROVIDER
     - opentelemetry_meter_provider
     - ``default_meter_provider``, ``sdk_meter_provider``
     - :class:`MeterProvider <opentelemetry.metrics.MeterProvider>`
   * - OTEL_PYTHON_LOGGER_PROVIDER
     - opentelemetry_logger_provider
     - ``default_logger_provider``, ``sdk_logger_provider``
     - :class:`LoggerProvider <opentelemetry._logs.LoggerProvider>`
   * - OTEL_PYTHON_EVENT_LOGGER_PROVIDER
     - opentelemetry_event_logger_provider
     - ``default_event_logger_provider``
     - *No implementations available*

See Also
--------

* :doc:`trace` - Trace SDK documentation
* :doc:`metrics` - Metrics SDK documentation  
* :doc:`environment_variables` - Environment variable reference 