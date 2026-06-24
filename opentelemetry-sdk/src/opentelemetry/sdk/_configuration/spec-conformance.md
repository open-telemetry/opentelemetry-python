# Declarative Configuration Spec Conformance

This document tracks which fields of the [OpenTelemetry declarative configuration schema](https://github.com/open-telemetry/opentelemetry-configuration) the Python SDK currently applies at runtime.

Schema version: **`1.0`** (vendored as `schema.json`; the spec is at v1.1.0 and a bump is tracked in [#5333](https://github.com/open-telemetry/opentelemetry-python/issues/5333)). The loader parses and validates the full schema; this doc only covers whether the SDK acts on each field.

| Status | Meaning |
| --- | --- |
| ✅ Supported | Parsed and applied to the SDK |
| ⚠️ Partial | Parsed and partially applied (see Notes) |
| ❌ Unsupported | Parsed and validated but ignored by the SDK |

## Top-level

| Field | Status | Notes |
| --- | --- | --- |
| `file_format` | ✅ | Required by parser; major version validated against the bundled schema. |
| `disabled` | ✅ | When `true`, `configure_sdk` returns early and no globals are touched. |
| `log_level` | ❌ | Parsed but never read by `configure_sdk`. No tracker yet. |
| `attribute_limits.attribute_count_limit` | ❌ | Parsed but not applied. The per-signal `tracer_provider.limits.*` and `logger_provider.limits.*` fields are wired separately. No tracker yet. |
| `attribute_limits.attribute_value_length_limit` | ❌ | As above. |
| `instrumentation/development` | ❌ | Parsed but not applied. Instrumentation configuration via declarative config is not yet implemented. No tracker yet. |
| `distribution` | ❌ | Vendor extension; parsed as free-form, never applied. No tracker yet. |

## `resource`

| Field | Status | Notes |
| --- | --- | --- |
| `attributes` | ✅ | Typed entries (`string`, `bool`, `int`, `double`, `*_array`). |
| `attributes_list` | ✅ | Comma-separated `key=value` form (lower priority than `attributes`). |
| `schema_url` | ✅ | Applied to the produced `Resource`. |
| `detection/development.detectors.host` | ✅ | |
| `detection/development.detectors.os` | ✅ | |
| `detection/development.detectors.process` | ✅ | |
| `detection/development.detectors.service` | ✅ | |
| `detection/development.detectors.container` | ⚠️ | Requires the `opentelemetry-resource-detector-container` contrib package; not bundled. |
| `detection/development.attributes` (include/exclude filters) | ✅ | Glob patterns supported. |
| Third-party detectors via entry point | ✅ | `opentelemetry_resource_detector` entry point group. |

## `propagator`

| Field | Status | Notes |
| --- | --- | --- |
| `composite` | ✅ | Supports built-in `tracecontext` and `baggage` directly. |
| `composite_list` | ✅ | Comma-separated form. |
| Third-party propagator names (e.g. `b3`, `b3multi`, `jaeger`) | ✅ | Loaded via the `opentelemetry_propagator` entry point group. |

## `tracer_provider`

### Span processors and exporters

| Field | Status | Notes |
| --- | --- | --- |
| `processors[].batch` | ✅ | `schedule_delay`, `export_timeout`, `max_queue_size`, `max_export_batch_size` all applied. |
| `processors[].simple` | ✅ | |
| `processors[].batch.exporter.otlp_http` | ✅ | `endpoint`, `headers`, `headers_list`, `certificate`, `client_certificate`, `client_key`, `compression`, `timeout`. |
| `processors[].batch.exporter.otlp_grpc` | ✅ | As above, plus `insecure`. |
| `processors[].batch.exporter.console` | ✅ | |
| `processors[].batch.exporter.otlp_file/development` | ❌ | Experimental exporter not wired via declarative config. No tracker yet. |
| Third-party exporters via entry point | ✅ | `opentelemetry_span_exporter` entry point group. |

### Limits

| Field | Status | Notes |
| --- | --- | --- |
| `limits.attribute_count_limit` | ✅ | |
| `limits.attribute_value_length_limit` | ✅ | |
| `limits.event_count_limit` | ✅ | |
| `limits.link_count_limit` | ✅ | |
| `limits.event_attribute_count_limit` | ✅ | |
| `limits.link_attribute_count_limit` | ✅ | |

### Sampler

| Field | Status | Notes |
| --- | --- | --- |
| `sampler.always_on` | ✅ | |
| `sampler.always_off` | ✅ | |
| `sampler.trace_id_ratio_based` | ✅ | |
| `sampler.parent_based` | ✅ | All four `*_parent_*` delegates supported. |
| `sampler.composite/development` | ✅ | Composable samplers including rule-based; merged via [#5201](https://github.com/open-telemetry/opentelemetry-python/pull/5201). |
| `sampler.jaeger_remote/development` | ❌ | Experimental; not wired. No tracker yet. |
| `sampler.probability/development` | ❌ | Experimental; not wired (use `trace_id_ratio_based` for the stable equivalent). |
| Third-party samplers via entry point | ✅ | `opentelemetry_traces_sampler` entry point group. |

### Id generator

| Field | Status | Notes |
| --- | --- | --- |
| `id_generator.*` | ❌ | Not present in schema v1.0; arrives with the v1.1.0 bump ([#5333](https://github.com/open-telemetry/opentelemetry-python/issues/5333)). Even once the model gains the field, factory wiring is tracked separately in [#5334](https://github.com/open-telemetry/opentelemetry-python/issues/5334). |

### Tracer configurator

| Field | Status | Notes |
| --- | --- | --- |
| `tracer_configurator/development` | ❌ | Parsed but never read by `configure_tracer_provider` or threaded through `configure_sdk`. Per-tracer config is not applied. No tracker yet. |

## `meter_provider`

### Readers and exporters

| Field | Status | Notes |
| --- | --- | --- |
| `readers[].periodic` | ✅ | `interval`, `timeout` applied; see `producers` below. |
| `readers[].periodic.exporter.otlp_http` | ✅ | Plus `temporality_preference` and `default_histogram_aggregation`. |
| `readers[].periodic.exporter.otlp_grpc` | ✅ | As above, with gRPC credentials. |
| `readers[].periodic.exporter.console` | ✅ | |
| `readers[].periodic.exporter.otlp_file/development` | ❌ | Experimental exporter not wired. No tracker yet. |
| `readers[].pull.exporter.prometheus/development` | ⚠️ | `host`, `port`, `without_target_info/development` (renamed `target_info_enabled/development` in spec v1.1.0) applied. `without_scope_info` and `with_resource_constant_labels` log a warning and are ignored. |
| `readers[].producers` (`MetricProducer` config) | ❌ | Tracked in [#5073](https://github.com/open-telemetry/opentelemetry-python/issues/5073). |
| `readers[].cardinality_limits` | ✅ | Per-instrument-type limits. |
| Third-party metric exporters via entry point | ✅ | `opentelemetry_metrics_exporter` entry point group. |

### Views

| Field | Status | Notes |
| --- | --- | --- |
| `views[].selector` | ✅ | `instrument_name`, `instrument_type`, `unit`, `meter_name`, `meter_version`, `meter_schema_url`. |
| `views[].stream.name` / `description` / `aggregation` | ✅ | |
| `views[].stream.attribute_keys.included` | ✅ | |
| `views[].stream.attribute_keys.excluded` | ⚠️ | Python's `View` API does not currently support exclusion lists; logs a warning and ignores the field. No tracker yet. |
| `views[].stream.aggregation_cardinality_limit` | ✅ | |

### Exemplar filter

| Field | Status | Notes |
| --- | --- | --- |
| `exemplar_filter` | ✅ | `always_on`, `always_off`, `trace_based`. |

### Meter configurator

| Field | Status | Notes |
| --- | --- | --- |
| `meter_configurator/development` | ❌ | Parsed but never read by `configure_meter_provider` or threaded through `configure_sdk`. No tracker yet. |

## `logger_provider`

| Field | Status | Notes |
| --- | --- | --- |
| `processors[].batch` | ✅ | `schedule_delay`, `export_timeout`, `max_queue_size`, `max_export_batch_size`. |
| `processors[].simple` | ✅ | |
| `processors[].batch.exporter.otlp_http` | ✅ | Full property set as for traces. |
| `processors[].batch.exporter.otlp_grpc` | ✅ | |
| `processors[].batch.exporter.console` | ✅ | |
| `processors[].batch.exporter.otlp_file/development` | ❌ | Experimental exporter not wired. No tracker yet. |
| `limits.attribute_count_limit` | ❌ | Python's `LoggerProvider` constructor does not accept log-record limits; the factory logs a warning and ignores the field. No tracker yet. |
| `limits.attribute_value_length_limit` | ❌ | As above. |
| `logger_configurator/development` | ❌ | Parsed but never read by `configure_logger_provider` or threaded through `configure_sdk`. No tracker yet. |
| Third-party log exporters via entry point | ✅ | `opentelemetry_logs_exporter` entry point group. |

## Cross-cutting

| Topic | Status | Notes |
| --- | --- | --- |
| Environment variable substitution (`${VAR}`, `${VAR:-default}`, `$$`) | ✅ | Performed before YAML/JSON parsing. |
| `OTEL_CONFIG_FILE` activation | ✅ | The standard SDK configurator entry point honors the env var ([#5271](https://github.com/open-telemetry/opentelemetry-python/pull/5271)). |
| Schema validation against bundled `schema.json` | ✅ | JSON Schema Draft 2020-12 via `jsonschema`. |
| `file_format` version validation | ✅ | Per spec versioning rules ([#5315](https://github.com/open-telemetry/opentelemetry-python/pull/5315)). |
| Honoring `OTEL_PYTHON_*` extensions when `OTEL_CONFIG_FILE` is set | ❌ | Decision tracked in [#5335](https://github.com/open-telemetry/opentelemetry-python/issues/5335). |
| Detect and log missing optional component dependencies | ⚠️ | Tracked in [#5229](https://github.com/open-telemetry/opentelemetry-python/issues/5229); PR [#5265](https://github.com/open-telemetry/opentelemetry-python/pull/5265) in flight. |
| Honoring `OTEL_*` env vars when no config file is set | ✅ | Existing env-var path via `_initialize_components`. Unifying construction with the declarative path is tracked in [#5126](https://github.com/open-telemetry/opentelemetry-python/issues/5126). |

## Keeping this doc current

When a PR adds, removes, or changes wiring for a configuration field, update the matching row here. The [declarative configuration tracking issue](https://github.com/open-telemetry/opentelemetry-python/issues/3631) lists in-flight work.
