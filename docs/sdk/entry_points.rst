Entry Points
============

OpenTelemetry Python uses Python's `entry points <https://setuptools.pypa.io/en/stable/userguide/entry_point.html>`_ mechanism to provide a pluggable architecture. Entry points allow you to register custom components (exporters, samplers, etc.) that can be discovered and loaded at runtime.

Configuration
-------------

The SDK supports configuring entry points via environment variables by specifying the entry point name. For a complete list of supported environment variables, see :doc:`../api/environment_variables`.

Entry Point Configuration Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Logs Exporter**

:Environment Variable: ``OTEL_LOGS_EXPORTER``
:Entry Point Group: ``opentelemetry_logs_exporter``
:Available Names: ``console``, ``otlp_proto_grpc``, ``otlp_proto_http``
:Base Type: ``LogExporter`` *(development)*

**Metrics Exporter**

:Environment Variable: ``OTEL_METRICS_EXPORTER``
:Entry Point Group: ``opentelemetry_metrics_exporter``
:Available Names: ``console``, ``otlp``, ``otlp_proto_grpc``, ``otlp_proto_http``, ``prometheus``
:Base Type: :class:`MetricExporter <opentelemetry.sdk.metrics.export.MetricExporter>` or :class:`MetricReader <opentelemetry.sdk.metrics.export.MetricReader>`

**Propagators**

:Environment Variable: ``OTEL_PROPAGATORS``
:Entry Point Group: ``opentelemetry_propagator``
:Available Names: ``b3``, ``b3multi``, ``baggage``, ``jaeger``, ``tracecontext``
:Base Type: :class:`TextMapPropagator <opentelemetry.propagators.textmap.TextMapPropagator>`

**Traces Sampler**

:Environment Variable: ``OTEL_TRACES_SAMPLER``
:Entry Point Group: ``opentelemetry_traces_sampler``
:Available Names: ``always_off``, ``always_on``, ``parentbased_always_off``, ``parentbased_always_on``, ``parentbased_traceidratio``, ``traceidratio``
:Base Type: :class:`Sampler <opentelemetry.sdk.trace.sampling.Sampler>`

**Resource Detectors**

:Environment Variable: ``OTEL_EXPERIMENTAL_RESOURCE_DETECTORS``
:Entry Point Group: ``opentelemetry_resource_detector``
:Available Names: ``host``, ``os``, ``otel``, ``process``
:Base Type: :class:`ResourceDetector <opentelemetry.sdk.resources.ResourceDetector>`

**ID Generator**

:Environment Variable: ``OTEL_PYTHON_ID_GENERATOR``
:Entry Point Group: ``opentelemetry_id_generator``
:Available Names: ``random``
:Base Type: :class:`IdGenerator <opentelemetry.sdk.trace.id_generator.IdGenerator>`

**Traces Exporter**

:Environment Variable: ``OTEL_TRACES_EXPORTER``
:Entry Point Group: ``opentelemetry_traces_exporter``
:Available Names: ``console``, ``otlp``, ``otlp_proto_grpc``, ``otlp_proto_http``, ``zipkin``, ``zipkin_json``, ``zipkin_proto``
:Base Type: :class:`SpanExporter <opentelemetry.sdk.trace.export.SpanExporter>`

**Tracer Provider**

:Environment Variable: ``OTEL_PYTHON_TRACER_PROVIDER``
:Entry Point Group: ``opentelemetry_tracer_provider``
:Available Names: ``default_tracer_provider``, ``sdk_tracer_provider``
:Base Type: :class:`TracerProvider <opentelemetry.trace.TracerProvider>`

**Meter Provider**

:Environment Variable: ``OTEL_PYTHON_METER_PROVIDER``
:Entry Point Group: ``opentelemetry_meter_provider``
:Available Names: ``default_meter_provider``, ``sdk_meter_provider``
:Base Type: :class:`MeterProvider <opentelemetry.metrics.MeterProvider>`

**Logger Provider**

:Environment Variable: ``OTEL_PYTHON_LOGGER_PROVIDER``
:Entry Point Group: ``opentelemetry_logger_provider``
:Available Names: ``sdk_logger_provider``
:Base Type: :class:`LoggerProvider <opentelemetry._logs.LoggerProvider>`

**Event Logger Provider**

:Environment Variable: ``OTEL_PYTHON_EVENT_LOGGER_PROVIDER``
:Entry Point Group: ``opentelemetry_event_logger_provider`` *(not implemented)*
:Available Names: *None - no entry point implementations exist*
:Base Type: ``EventLoggerProvider`` *(experimental)*

.. note::
   The Events API is `experimental <https://github.com/open-telemetry/opentelemetry-python#project-status>`_ and currently has no entry point implementations. 

See Also
--------

* :doc:`trace` - Trace SDK documentation
* :doc:`metrics` - Metrics SDK documentation  
* :doc:`environment_variables` - Environment variable reference 