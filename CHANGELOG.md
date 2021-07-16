# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/open-telemetry/opentelemetry-python/compare/v1.3.0-0.22b0...HEAD)
- `opentelemetry-semantic-conventions` Generate semconv constants update for OTel Spec 1.5.0
  ([#1946](https://github.com/open-telemetry/opentelemetry-python/pull/1946))

### Added
- Dropped attributes/events/links count available exposed on ReadableSpans.
  ([#1893](https://github.com/open-telemetry/opentelemetry-python/pull/1893))
- Added dropped count to otlp, jaeger and zipkin exporters.
  ([#1893](https://github.com/open-telemetry/opentelemetry-python/pull/1893))

### Changed
- Updated `opentelemetry-opencensus-exporter` to use `service_name` of spans instead of resource
  ([#1897](https://github.com/open-telemetry/opentelemetry-python/pull/1897))
- Added descriptions to the env variables mentioned in the opentelemetry-specification
  ([#1898](https://github.com/open-telemetry/opentelemetry-python/pull/1898))
- Ignore calls to `Span.set_status` with `StatusCode.UNSET` and also if previous status already
  had `StatusCode.OK`.
  ([#1902](https://github.com/open-telemetry/opentelemetry-python/pull/1902))
- Attributes for `Link` and `Resource` are immutable as they are for `Event`, which means
  any attempt to modify attributes directly will result in a `TypeError` exception.
  ([#1909](https://github.com/open-telemetry/opentelemetry-python/pull/1909))
- Added `BoundedAttributes` to the API to make it available for `Link` which is defined in the
  API. Marked `BoundedDict` in the SDK as deprecated as a result.
  ([#1915](https://github.com/open-telemetry/opentelemetry-python/pull/1915))
- Fix OTLP SpanExporter to distinguish spans based off Resource and InstrumentationInfo
  ([#1927](https://github.com/open-telemetry/opentelemetry-python/pull/1927))
- Updating dependency for opentelemetry api/sdk packages to support major version instead of
  pinning to specific versions.
  ([#1933](https://github.com/open-telemetry/opentelemetry-python/pull/1933))

### Fixed
- Updated `opentelementry-opentracing-shim` `ScopeShim` to report exceptions in
  opentelemetry specification format, rather than opentracing spec format.
  ([#1878](https://github.com/open-telemetry/opentelemetry-python/pull/1878))

## [1.3.0-0.22b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.3.0-0.22b0) - 2021-06-01

### Added
- Allow span limits to be set programatically via TracerProvider.
  ([#1877](https://github.com/open-telemetry/opentelemetry-python/pull/1877))
- Added support for CreateKey functionality.
  ([#1853](https://github.com/open-telemetry/opentelemetry-python/pull/1853))

### Changed
- Updated get_tracer to return an empty string when passed an invalid name
  ([#1854](https://github.com/open-telemetry/opentelemetry-python/pull/1854))
- Changed AttributeValue sequences to warn mypy users on adding None values to array
  ([#1855](https://github.com/open-telemetry/opentelemetry-python/pull/1855))
- Fixed exporter OTLP header parsing to match baggage header formatting.
  ([#1869](https://github.com/open-telemetry/opentelemetry-python/pull/1869))
- Added optional `schema_url` field to `Resource` class
  ([#1871](https://github.com/open-telemetry/opentelemetry-python/pull/1871))
- Update protos to latest version release 0.9.0
  ([#1873](https://github.com/open-telemetry/opentelemetry-python/pull/1873))

## [1.2.0, 0.21b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.2.0-0.21b0) - 2021-05-11

### Added
- Added example for running Django with auto instrumentation.
  ([#1803](https://github.com/open-telemetry/opentelemetry-python/pull/1803))
- Added `B3SingleFormat` and `B3MultiFormat` propagators to the `opentelemetry-propagator-b3` package.
  ([#1823](https://github.com/open-telemetry/opentelemetry-python/pull/1823))
- Added support for OTEL_SERVICE_NAME.
  ([#1829](https://github.com/open-telemetry/opentelemetry-python/pull/1829))
- Lazily read/configure limits and allow limits to be unset.
  ([#1839](https://github.com/open-telemetry/opentelemetry-python/pull/1839))
- Added support for OTEL_EXPORTER_JAEGER_TIMEOUT
  ([#1863](https://github.com/open-telemetry/opentelemetry-python/pull/1863))

### Changed
- Fixed OTLP gRPC exporter silently failing if scheme is not specified in endpoint.
  ([#1806](https://github.com/open-telemetry/opentelemetry-python/pull/1806))
- Rename CompositeHTTPPropagator to CompositePropagator as per specification.
  ([#1807](https://github.com/open-telemetry/opentelemetry-python/pull/1807))
- Propagators use the root context as default for `extract` and do not modify
  the context if extracting from carrier does not work.
  ([#1811](https://github.com/open-telemetry/opentelemetry-python/pull/1811))
- Fixed `b3` propagator entrypoint to point to `B3SingleFormat` propagator.
  ([#1823](https://github.com/open-telemetry/opentelemetry-python/pull/1823))
- Added `b3multi` propagator entrypoint to point to `B3MultiFormat` propagator.
  ([#1823](https://github.com/open-telemetry/opentelemetry-python/pull/1823))
- Improve warning when failing to decode byte attribute
  ([#1810](https://github.com/open-telemetry/opentelemetry-python/pull/1810))
- Fixed inconsistency in parent_id formatting from the ConsoleSpanExporter
  ([#1833](https://github.com/open-telemetry/opentelemetry-python/pull/1833))
- Include span parent in Jaeger gRPC export as `CHILD_OF` reference
  ([#1809])(https://github.com/open-telemetry/opentelemetry-python/pull/1809)
- Fixed sequence values in OTLP exporter not translating
  ([#1818](https://github.com/open-telemetry/opentelemetry-python/pull/1818))
- Update transient errors retry timeout and retryable status codes
  ([#1842](https://github.com/open-telemetry/opentelemetry-python/pull/1842))
- Apply validation of attributes to `Resource`, move attribute related logic to separate package.
  ([#1834](https://github.com/open-telemetry/opentelemetry-python/pull/1834))
- Fix start span behavior when excess links and attributes are included
  ([#1856](https://github.com/open-telemetry/opentelemetry-python/pull/1856))

### Removed
- Moved `opentelemetry-instrumentation` to contrib repository.
  ([#1797](https://github.com/open-telemetry/opentelemetry-python/pull/1797))

## [1.1.0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.1.0) - 2021-04-20

### Added
- Added `py.typed` file to every package. This should resolve a bunch of mypy
  errors for users.
  ([#1720](https://github.com/open-telemetry/opentelemetry-python/pull/1720))
- Add auto generated trace and resource attributes semantic conventions
  ([#1759](https://github.com/open-telemetry/opentelemetry-python/pull/1759))
- Added `SpanKind` to `should_sample` parameters, suggest using parent span context's tracestate
  instead of manually passed in tracestate in `should_sample`
  ([#1764](https://github.com/open-telemetry/opentelemetry-python/pull/1764))
- Added experimental HTTP back propagators.
  ([#1762](https://github.com/open-telemetry/opentelemetry-python/pull/1762))
- Zipkin exporter: Add support for timeout and implement shutdown
  ([#1799](https://github.com/open-telemetry/opentelemetry-python/pull/1799))

### Changed
- Adjust `B3Format` propagator to be spec compliant by not modifying context
  when propagation headers are not present/invalid/empty
  ([#1728](https://github.com/open-telemetry/opentelemetry-python/pull/1728))
- Silence unnecessary warning when creating a new Status object without description.
  ([#1721](https://github.com/open-telemetry/opentelemetry-python/pull/1721))
- Update bootstrap cmd to use exact version when installing instrumentation packages.
  ([#1722](https://github.com/open-telemetry/opentelemetry-python/pull/1722))
- Fix B3 propagator to never return None.
  ([#1750](https://github.com/open-telemetry/opentelemetry-python/pull/1750))
- Added ProxyTracerProvider and ProxyTracer implementations to allow fetching provider
  and tracer instances before a global provider is set up.
  ([#1726](https://github.com/open-telemetry/opentelemetry-python/pull/1726))
- Added `__contains__` to `opentelementry.trace.span.TraceState`.
  ([#1773](https://github.com/open-telemetry/opentelemetry-python/pull/1773))
- `opentelemetry-opentracing-shim` Fix an issue in the shim where a Span was being wrapped
  in a NonRecordingSpan when it wasn't necessary.
  ([#1776](https://github.com/open-telemetry/opentelemetry-python/pull/1776))
- OTLP Exporter now uses the scheme in the endpoint to determine whether to establish
  a secure connection or not.
  ([#1771](https://github.com/open-telemetry/opentelemetry-python/pull/1771))

## [1.0.0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.0.0) - 2021-03-26

### Added
- Document how to work with fork process web server models(Gunicorn, uWSGI etc...)
  ([#1609](https://github.com/open-telemetry/opentelemetry-python/pull/1609))
- Add `max_attr_value_length` support to Jaeger exporter
  ([#1633](https://github.com/open-telemetry/opentelemetry-python/pull/1633))
- Moved `use_span` from Tracer to `opentelemetry.trace.use_span`.
  ([#1668](https://github.com/open-telemetry/opentelemetry-python/pull/1668))
- `opentelemetry.trace.use_span()` will now overwrite previously set status on span in case an
  exception is raised inside the context manager and `set_status_on_exception` is set to `True`.
  ([#1668](https://github.com/open-telemetry/opentelemetry-python/pull/1668))
- Add `udp_split_oversized_batches` support to jaeger exporter
  ([#1500](https://github.com/open-telemetry/opentelemetry-python/pull/1500))

### Changed
- remove `service_name` from constructor of jaeger and opencensus exporters and
  use of env variable `OTEL_PYTHON_SERVICE_NAME`
  ([#1669])(https://github.com/open-telemetry/opentelemetry-python/pull/1669)
- Rename `IdsGenerator` to `IdGenerator`
  ([#1651](https://github.com/open-telemetry/opentelemetry-python/pull/1651))
- Make TracerProvider's resource attribute private
  ([#1652](https://github.com/open-telemetry/opentelemetry-python/pull/1652))
- Rename Resource's `create_empty` to `get_empty`
  ([#1653](https://github.com/open-telemetry/opentelemetry-python/pull/1653))
- Renamed `BatchExportSpanProcessor` to `BatchSpanProcessor` and `SimpleExportSpanProcessor` to
  `SimpleSpanProcessor`
  ([#1656](https://github.com/open-telemetry/opentelemetry-python/pull/1656))
- Rename `DefaultSpan` to `NonRecordingSpan`
  ([#1661](https://github.com/open-telemetry/opentelemetry-python/pull/1661))
- Fixed distro configuration with `OTEL_TRACES_EXPORTER` env var set to `otlp`
  ([#1657](https://github.com/open-telemetry/opentelemetry-python/pull/1657))
- Moving `Getter`, `Setter` and `TextMapPropagator` out of `opentelemetry.trace.propagation` and
  into `opentelemetry.propagators`
  ([#1662](https://github.com/open-telemetry/opentelemetry-python/pull/1662))
- Rename `BaggagePropagator` to `W3CBaggagePropagator`
  ([#1663](https://github.com/open-telemetry/opentelemetry-python/pull/1663))
- Rename `JaegerSpanExporter` to `JaegerExporter` and rename `ZipkinSpanExporter` to `ZipkinExporter`
  ([#1664](https://github.com/open-telemetry/opentelemetry-python/pull/1664))
- Expose `StatusCode` from the `opentelemetry.trace` module
  ([#1681](https://github.com/open-telemetry/opentelemetry-python/pull/1681))
- Status now only sets `description` when `status_code` is set to `StatusCode.ERROR`
  ([#1673](https://github.com/open-telemetry/opentelemetry-python/pull/1673))
- Update OTLP exporter to use OTLP proto `0.7.0`
  ([#1674](https://github.com/open-telemetry/opentelemetry-python/pull/1674))
- Remove time_ns from API and add a warning for older versions of Python
  ([#1602](https://github.com/open-telemetry/opentelemetry-python/pull/1602))
- Hide implementation classes/variables in api/sdk
  ([#1684](https://github.com/open-telemetry/opentelemetry-python/pull/1684))
- Cleanup OTLP exporter compression options, add tests
  ([#1671](https://github.com/open-telemetry/opentelemetry-python/pull/1671))
- Initial documentation for environment variables
  ([#1680](https://github.com/open-telemetry/opentelemetry-python/pull/1680))
- Change Zipkin exporter to obtain service.name from span
  ([#1696](https://github.com/open-telemetry/opentelemetry-python/pull/1696))
- Split up `opentelemetry-exporter-jaeger` package into `opentelemetry-exporter-jaeger-proto-grpc` and
  `opentelemetry-exporter-jaeger-thrift` packages to reduce dependencies for each one.
  ([#1694](https://github.com/open-telemetry/opentelemetry-python/pull/1694))
- Added `opentelemetry-exporter-otlp-proto-grpc` and changed `opentelemetry-exporter-otlp` to
  install it as a dependency. This will allow for the next package/protocol to also be in
  its own package.
  ([#1695](https://github.com/open-telemetry/opentelemetry-python/pull/1695))
- Change Jaeger exporters to obtain service.name from span
  ([#1703](https://github.com/open-telemetry/opentelemetry-python/pull/1703))
- Fixed an unset `OTEL_TRACES_EXPORTER` resulting in an error
  ([#1707](https://github.com/open-telemetry/opentelemetry-python/pull/1707))
- Split Zipkin exporter into `opentelemetry-exporter-zipkin-json` and
  `opentelemetry-exporter-zipkin-proto-http` packages to reduce dependencies. The
  `opentelemetry-exporter-zipkin` installs both.
  ([#1699](https://github.com/open-telemetry/opentelemetry-python/pull/1699))
- Make setters and getters optional
  ([#1690](https://github.com/open-telemetry/opentelemetry-python/pull/1690))

### Removed
- Removed unused `get_hexadecimal_trace_id` and `get_hexadecimal_span_id` methods.
  ([#1675](https://github.com/open-telemetry/opentelemetry-python/pull/1675))
- Remove `OTEL_EXPORTER_*_ INSECURE` env var
  ([#1682](https://github.com/open-telemetry/opentelemetry-python/pull/1682))
- Removing support for Python 3.5
  ([#1706](https://github.com/open-telemetry/opentelemetry-python/pull/1706))

## [0.19b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.19b0) - 2021-03-26

### Changed
- remove `service_name` from constructor of jaeger and opencensus exporters and
  use of env variable `OTEL_PYTHON_SERVICE_NAME`
  ([#1669])(https://github.com/open-telemetry/opentelemetry-python/pull/1669)
- Rename `IdsGenerator` to `IdGenerator`
  ([#1651](https://github.com/open-telemetry/opentelemetry-python/pull/1651))

### Removed
- Removing support for Python 3.5
  ([#1706](https://github.com/open-telemetry/opentelemetry-python/pull/1706))

## [0.18b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.18b0) - 2021-02-16

### Added
- Add urllib to opentelemetry-bootstrap target list
  ([#1584](https://github.com/open-telemetry/opentelemetry-python/pull/1584))

## [1.0.0rc1](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.0.0rc1) - 2021-02-12

### Changed
- Tracer provider environment variables are now consistent with the rest
  ([#1571](https://github.com/open-telemetry/opentelemetry-python/pull/1571))
- Rename `TRACE_` to `TRACES_` for environment variables
  ([#1595](https://github.com/open-telemetry/opentelemetry-python/pull/1595))
- Limits for Span attributes, events and links have been updated to 128
  ([1597](https://github.com/open-telemetry/opentelemetry-python/pull/1597))
- Read-only Span attributes have been moved to ReadableSpan class
  ([#1560](https://github.com/open-telemetry/opentelemetry-python/pull/1560))
- `BatchExportSpanProcessor` flushes export queue when it reaches `max_export_batch_size`
  ([#1521](https://github.com/open-telemetry/opentelemetry-python/pull/1521))

### Added
- Added `end_on_exit` argument to `start_as_current_span`
  ([#1519](https://github.com/open-telemetry/opentelemetry-python/pull/1519))
- Add `Span.set_attributes` method to set multiple values with one call
  ([#1520](https://github.com/open-telemetry/opentelemetry-python/pull/1520))
- Make sure Resources follow semantic conventions
  ([#1480](https://github.com/open-telemetry/opentelemetry-python/pull/1480))
- Allow missing carrier headers to continue without raising AttributeError
  ([#1545](https://github.com/open-telemetry/opentelemetry-python/pull/1545))

### Removed
- Remove Configuration
  ([#1523](https://github.com/open-telemetry/opentelemetry-python/pull/1523))
- Remove Metrics as part of stable, marked as experimental
  ([#1568](https://github.com/open-telemetry/opentelemetry-python/pull/1568))

## [0.17b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.17b0) - 2021-01-20

### Added
- Add support for OTLP v0.6.0
  ([#1472](https://github.com/open-telemetry/opentelemetry-python/pull/1472))
- Add protobuf via gRPC exporting support for Jaeger
  ([#1471](https://github.com/open-telemetry/opentelemetry-python/pull/1471))
- Add support for Python 3.9
  ([#1441](https://github.com/open-telemetry/opentelemetry-python/pull/1441))
- Added the ability to disable instrumenting libraries specified by OTEL_PYTHON_DISABLED_INSTRUMENTATIONS env variable, when using opentelemetry-instrument command.
  ([#1461](https://github.com/open-telemetry/opentelemetry-python/pull/1461))
- Add `fields` to propagators
  ([#1374](https://github.com/open-telemetry/opentelemetry-python/pull/1374))
- Add local/remote samplers to parent based sampler
  ([#1440](https://github.com/open-telemetry/opentelemetry-python/pull/1440))
- Add support for OTEL_SPAN_{ATTRIBUTE_COUNT_LIMIT,EVENT_COUNT_LIMIT,LINK_COUNT_LIMIT}
  ([#1377](https://github.com/open-telemetry/opentelemetry-python/pull/1377))
- Return `None` for `DictGetter` if key not found
  ([#1449](https://github.com/open-telemetry/opentelemetry-python/pull/1449))
- Added support for Jaeger propagator
  ([#1219](https://github.com/open-telemetry/opentelemetry-python/pull/1219))
- Remove dependency on SDK from `opentelemetry-instrumentation` package. The
  `opentelemetry-sdk` package now registers an entrypoint `opentelemetry_configurator`
  to allow `opentelemetry-instrument` to load the configuration for the SDK
  ([#1420](https://github.com/open-telemetry/opentelemetry-python/pull/1420))
- `opentelemetry-exporter-zipkin` Add support for array attributes in Span and Resource exports
  ([#1285](https://github.com/open-telemetry/opentelemetry-python/pull/1285))
- Added `__repr__` for `DefaultSpan`, added `trace_flags` to `__repr__` of
  `SpanContext` ([#1485](https://github.com/open-telemetry/opentelemetry-python/pull/1485))
- `opentelemetry-sdk` Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables
  ([#1496](https://github.com/open-telemetry/opentelemetry-python/pull/1496))
- Adding `opentelemetry-distro` package to add default configuration for
  span exporter to OTLP
  ([#1482](https://github.com/open-telemetry/opentelemetry-python/pull/1482))

### Changed
- `opentelemetry-exporter-zipkin` Updated zipkin exporter status code and error tag
  ([#1486](https://github.com/open-telemetry/opentelemetry-python/pull/1486))
- Recreate span on every run of a `start_as_current_span`-decorated function
  ([#1451](https://github.com/open-telemetry/opentelemetry-python/pull/1451))
- `opentelemetry-exporter-otlp` Headers are now passed in as tuple as metadata, instead of a
  string, which was incorrect.
  ([#1507](https://github.com/open-telemetry/opentelemetry-python/pull/1507))
- `opentelemetry-exporter-jaeger` Updated Jaeger exporter status code tag
  ([#1488](https://github.com/open-telemetry/opentelemetry-python/pull/1488))
- `opentelemetry-api` `opentelemety-sdk` Moved `idsgenerator` into sdk
  ([#1514](https://github.com/open-telemetry/opentelemetry-python/pull/1514))
- `opentelemetry-sdk` The B3Format propagator has been moved into its own package: `opentelemetry-propagator-b3`
  ([#1513](https://github.com/open-telemetry/opentelemetry-python/pull/1513))
- Update default port for OTLP exporter from 55680 to 4317
  ([#1516](https://github.com/open-telemetry/opentelemetry-python/pull/1516))
- `opentelemetry-exporter-zipkin` Update boolean attribute value transformation
  ([#1509](https://github.com/open-telemetry/opentelemetry-python/pull/1509))
- Move opentelemetry-opentracing-shim out of instrumentation folder
  ([#1533](https://github.com/open-telemetry/opentelemetry-python/pull/1533))
- `opentelemetry-sdk` The JaegerPropagator has been moved into its own package: `opentelemetry-propagator-jaeger`
  ([#1525](https://github.com/open-telemetry/opentelemetry-python/pull/1525))
- `opentelemetry-exporter-jaeger`, `opentelemetry-exporter-zipkin` Update InstrumentationInfo tag keys for Jaeger and Zipkin exporters
  ([#1535](https://github.com/open-telemetry/opentelemetry-python/pull/1535))
- `opentelemetry-sdk` Remove rate property setter from TraceIdRatioBasedSampler
  ([#1536](https://github.com/open-telemetry/opentelemetry-python/pull/1536))
- Fix TraceState to adhere to specs
  ([#1502](https://github.com/open-telemetry/opentelemetry-python/pull/1502))
- Update Resource `merge` key conflict precedence
  ([#1544](https://github.com/open-telemetry/opentelemetry-python/pull/1544))

### Removed
- `opentelemetry-api` Remove ThreadLocalRuntimeContext since python3.4 is not supported.

## [0.16b1](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.16b1) - 2020-11-26
### Added
- Add meter reference to observers
  ([#1425](https://github.com/open-telemetry/opentelemetry-python/pull/1425))

## [0.16b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.16b0) - 2020-11-25
### Added
- Add optional parameter to `record_exception` method
  ([#1314](https://github.com/open-telemetry/opentelemetry-python/pull/1314))
- Add pickle support to SpanContext class
  ([#1380](https://github.com/open-telemetry/opentelemetry-python/pull/1380))
- Add instrumentation library name and version to OTLP exported metrics
  ([#1418](https://github.com/open-telemetry/opentelemetry-python/pull/1418))
- Add Gzip compression for exporter
  ([#1141](https://github.com/open-telemetry/opentelemetry-python/pull/1141))
- Support for v2 api protobuf format
  ([#1318](https://github.com/open-telemetry/opentelemetry-python/pull/1318))
- Add IDs Generator as Configurable Property of Auto Instrumentation
  ([#1404](https://github.com/open-telemetry/opentelemetry-python/pull/1404))
- Added support for `OTEL_EXPORTER` to the `opentelemetry-instrument` command
  ([#1036](https://github.com/open-telemetry/opentelemetry-python/pull/1036))
### Changed
- Change temporality for Counter and UpDownCounter
  ([#1384](https://github.com/open-telemetry/opentelemetry-python/pull/1384))
- OTLP exporter: Handle error case when no credentials supplied
  ([#1366](https://github.com/open-telemetry/opentelemetry-python/pull/1366))
- Update protobuf versions
  ([#1356](https://github.com/open-telemetry/opentelemetry-python/pull/1356))
- Add missing references to instrumented packages
  ([#1416](https://github.com/open-telemetry/opentelemetry-python/pull/1416))
- Instrumentation Package depends on the OTel SDK
  ([#1405](https://github.com/open-telemetry/opentelemetry-python/pull/1405))
- Allow samplers to modify tracestate
  ([#1319](https://github.com/open-telemetry/opentelemetry-python/pull/1319))
- Update exception handling optional parameters, add escaped attribute to record_exception
  ([#1365](https://github.com/open-telemetry/opentelemetry-python/pull/1365))
- Rename `MetricRecord` to `ExportRecord`
  ([#1367](https://github.com/open-telemetry/opentelemetry-python/pull/1367))
- Rename `Record` to `Accumulation`
  ([#1373](https://github.com/open-telemetry/opentelemetry-python/pull/1373))
- Rename `Meter` to `Accumulator`
  ([#1372](https://github.com/open-telemetry/opentelemetry-python/pull/1372))
- Fix `ParentBased` sampler for implicit parent spans. Fix also `trace_state`
  erasure for dropped spans or spans sampled by the `TraceIdRatioBased` sampler.
  ([#1394](https://github.com/open-telemetry/opentelemetry-python/pull/1394))

## [0.15b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.15b0) -2020-11-02

### Added
- Add Env variables in OTLP exporter
  ([#1101](https://github.com/open-telemetry/opentelemetry-python/pull/1101))
- Add support for Jaeger Span Exporter configuration by environment variables and<br/>
  change JaegerSpanExporter constructor parameters
  ([#1114](https://github.com/open-telemetry/opentelemetry-python/pull/1114))

### Changed
- Updating status codes to adhere to specs
  ([#1282](https://github.com/open-telemetry/opentelemetry-python/pull/1282))
- Set initial checkpoint timestamp in aggregators
  ([#1237](https://github.com/open-telemetry/opentelemetry-python/pull/1237))
- Make `SpanProcessor.on_start` accept parent Context
  ([#1251](https://github.com/open-telemetry/opentelemetry-python/pull/1251))
- Fix b3 propagator entrypoint
  ([#1265](https://github.com/open-telemetry/opentelemetry-python/pull/1265))
- Allow None in sequence attributes values
  ([#998](https://github.com/open-telemetry/opentelemetry-python/pull/998))
- Samplers to accept parent Context
  ([#1267](https://github.com/open-telemetry/opentelemetry-python/pull/1267))
- Span.is_recording() returns false after span has ended
  ([#1289](https://github.com/open-telemetry/opentelemetry-python/pull/1289))
- Allow samplers to modify tracestate
  ([#1319](https://github.com/open-telemetry/opentelemetry-python/pull/1319))
- Remove TracerProvider coupling from Tracer init
  ([#1295](https://github.com/open-telemetry/opentelemetry-python/pull/1295))

## [0.14b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.14b0) - 2020-10-13

### Added
- Add optional parameter to `record_exception` method
  ([#1242](https://github.com/open-telemetry/opentelemetry-python/pull/1242))
- Add support for `OTEL_PROPAGATORS`
  ([#1123](https://github.com/open-telemetry/opentelemetry-python/pull/1123))
- Add keys method to TextMap propagator Getter
  ([#1196](https://github.com/open-telemetry/opentelemetry-python/issues/1196))
- Add timestamps to OTLP exporter
  ([#1199](https://github.com/open-telemetry/opentelemetry-python/pull/1199))
- Add Global Error Handler
  ([#1080](https://github.com/open-telemetry/opentelemetry-python/pull/1080))
- Add support for `OTEL_BSP_MAX_QUEUE_SIZE`, `OTEL_BSP_SCHEDULE_DELAY_MILLIS`, `OTEL_BSP_MAX_EXPORT_BATCH_SIZE` and `OTEL_BSP_EXPORT_TIMEOUT_MILLIS` environment variables
  ([#1105](https://github.com/open-telemetry/opentelemetry-python/pull/1120))
- Adding Resource to MeterRecord
  ([#1209](https://github.com/open-telemetry/opentelemetry-python/pull/1209))
s
### Changed
- Store `int`s as `int`s in the global Configuration object
  ([#1118](https://github.com/open-telemetry/opentelemetry-python/pull/1118))
- Allow for Custom Trace and Span IDs Generation - `IdsGenerator` for TracerProvider
  ([#1153](https://github.com/open-telemetry/opentelemetry-python/pull/1153))
- Update baggage propagation header
  ([#1194](https://github.com/open-telemetry/opentelemetry-python/pull/1194))
- Make instances of SpanContext immutable
  ([#1134](https://github.com/open-telemetry/opentelemetry-python/pull/1134))
- Parent is now always passed in via Context, intead of Span or SpanContext
  ([#1146](https://github.com/open-telemetry/opentelemetry-python/pull/1146))
- Update OpenTelemetry protos to v0.5.0
  ([#1143](https://github.com/open-telemetry/opentelemetry-python/pull/1143))
- Zipkin exporter now accepts a ``max_tag_value_length`` attribute to customize the
  maximum allowed size a tag value can have.
  ([#1151](https://github.com/open-telemetry/opentelemetry-python/pull/1151))
- Fixed OTLP events to Zipkin annotations translation.
  ([#1161](https://github.com/open-telemetry/opentelemetry-python/pull/1161))
- Fixed bootstrap command to correctly install opentelemetry-instrumentation-falcon instead of opentelemetry-instrumentation-flask.
  ([#1138](https://github.com/open-telemetry/opentelemetry-python/pull/1138))
- Update sampling result names
  ([#1128](https://github.com/open-telemetry/opentelemetry-python/pull/1128))
- Event attributes are now immutable
  ([#1195](https://github.com/open-telemetry/opentelemetry-python/pull/1195))
- Renaming metrics Batcher to Processor
  ([#1203](https://github.com/open-telemetry/opentelemetry-python/pull/1203))
- Protect access to Span implementation
  ([#1188](https://github.com/open-telemetry/opentelemetry-python/pull/1188))
- `start_as_current_span` and `use_span` can now optionally auto-record any exceptions raised inside the context manager.
  ([#1162](https://github.com/open-telemetry/opentelemetry-python/pull/1162))

## [0.13b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.13b0) - 2020-09-17

### Added
- Add instrumentation info to exported spans
  ([#1095](https://github.com/open-telemetry/opentelemetry-python/pull/1095))
- Add metric OTLP exporter
  ([#835](https://github.com/open-telemetry/opentelemetry-python/pull/835))
- Add type hints to OTLP exporter
  ([#1121](https://github.com/open-telemetry/opentelemetry-python/pull/1121))
- Add support for OTEL_EXPORTER_ZIPKIN_ENDPOINT env var. As part of this change, the
  configuration of the ZipkinSpanExporter exposes a `url` argument to replace `host_name`,
  `port`, `protocol`, `endpoint`. This brings this implementation inline with other
  implementations.
  ([#1064](https://github.com/open-telemetry/opentelemetry-python/pull/1064))
- Zipkin exporter report instrumentation info.
  ([#1097](https://github.com/open-telemetry/opentelemetry-python/pull/1097))
- Add status mapping to tags
  ([#1111](https://github.com/open-telemetry/opentelemetry-python/issues/1111))
- Report instrumentation info
  ([#1098](https://github.com/open-telemetry/opentelemetry-python/pull/1098))
- Add support for http metrics
  ([#1116](https://github.com/open-telemetry/opentelemetry-python/pull/1116))
- Populate resource attributes as per semantic conventions
  ([#1053](https://github.com/open-telemetry/opentelemetry-python/pull/1053))

### Changed
- Refactor `SpanContext.is_valid` from a method to a data attribute
  ([#1005](https://github.com/open-telemetry/opentelemetry-python/pull/1005))
- Moved samplers from API to SDK
  ([#1023](https://github.com/open-telemetry/opentelemetry-python/pull/1023))
- Change return value type of `correlationcontext.get_correlations` to immutable `MappingProxyType`
  ([#1024](https://github.com/open-telemetry/opentelemetry-python/pull/1024))
- Sampling spec changes
  ([#1034](https://github.com/open-telemetry/opentelemetry-python/pull/1034))
- Remove lazy Event and Link API from Span interface
  ([#1045](https://github.com/open-telemetry/opentelemetry-python/pull/1045))
- Rename CorrelationContext to Baggage
  ([#1060](https://github.com/open-telemetry/opentelemetry-python/pull/1060))
- Rename HTTPTextFormat to TextMapPropagator. This change also updates `get_global_httptextformat` and
  `set_global_httptextformat` to `get_global_textmap` and `set_global_textmap`
  ([#1085](https://github.com/open-telemetry/opentelemetry-python/pull/1085))
- Fix api/sdk setup.cfg to include missing python files
  ([#1091](https://github.com/open-telemetry/opentelemetry-python/pull/1091))
- Improve BatchExportSpanProcessor
  ([#1062](https://github.com/open-telemetry/opentelemetry-python/pull/1062))
- Rename Resource labels to attributes
  ([#1082](https://github.com/open-telemetry/opentelemetry-python/pull/1082))
- Rename members of `trace.sampling.Decision` enum
  ([#1115](https://github.com/open-telemetry/opentelemetry-python/pull/1115))
- Merge `OTELResourceDetector` result when creating resources
  ([#1096](https://github.com/open-telemetry/opentelemetry-python/pull/1096))

### Removed
- Drop support for Python 3.4
  ([#1099](https://github.com/open-telemetry/opentelemetry-python/pull/1099))

## [0.12b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.12.0) - 2020-08-14

### Added
- Implement Views in metrics SDK
  ([#596](https://github.com/open-telemetry/opentelemetry-python/pull/596))

### Changed
- Update environment variable names, prefix changed from `OPENTELEMETRY` to `OTEL`
  ([#904](https://github.com/open-telemetry/opentelemetry-python/pull/904))
- Stop TracerProvider and MeterProvider from being overridden
  ([#959](https://github.com/open-telemetry/opentelemetry-python/pull/959))
- Update default port to 55680
  ([#977](https://github.com/open-telemetry/opentelemetry-python/pull/977))
- Add proper length zero padding to hex strings of traceId, spanId, parentId sent on the wire, for compatibility with jaeger-collector
  ([#908](https://github.com/open-telemetry/opentelemetry-python/pull/908))
- Send start_timestamp and convert labels to strings
  ([#937](https://github.com/open-telemetry/opentelemetry-python/pull/937))
- Renamed several packages
  ([#953](https://github.com/open-telemetry/opentelemetry-python/pull/953))
- Thrift URL for Jaeger exporter doesn't allow HTTPS (hardcoded to HTTP)
  ([#978](https://github.com/open-telemetry/opentelemetry-python/pull/978))
- Change reference names to opentelemetry-instrumentation-opentracing-shim
  ([#969](https://github.com/open-telemetry/opentelemetry-python/pull/969))
- Changed default Sampler to `ParentOrElse(AlwaysOn)`
  ([#960](https://github.com/open-telemetry/opentelemetry-python/pull/960))
- Update environment variable names, prefix changed from `OPENTELEMETRY` to `OTEL`
  ([#904](https://github.com/open-telemetry/opentelemetry-python/pull/904))
- Update environment variable `OTEL_RESOURCE` to `OTEL_RESOURCE_ATTRIBUTES` as per
  the specification

## [0.11b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.11.0) - 2020-07-28

### Added
- Add support for resources and resource detector
  ([#853](https://github.com/open-telemetry/opentelemetry-python/pull/853))
### Changed
- Return INVALID_SPAN if no TracerProvider set for get_current_span
  ([#751](https://github.com/open-telemetry/opentelemetry-python/pull/751))
- Rename record_error to record_exception
  ([#927](https://github.com/open-telemetry/opentelemetry-python/pull/927))
- Update span exporter to use OpenTelemetry Proto v0.4.0
  ([#872](https://github.com/open-telemetry/opentelemetry-python/pull/889))

## [0.10b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.10.0) - 2020-06-23

### Changed
- Regenerate proto code and add pyi stubs
  ([#823](https://github.com/open-telemetry/opentelemetry-python/pull/823))
- Rename CounterAggregator -> SumAggregator
  ([#816](https://github.com/open-telemetry/opentelemetry-python/pull/816))

## [0.9b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.9.0) - 2020-06-10

### Added
- Adding trace.get_current_span, Removing Tracer.get_current_span
  ([#552](https://github.com/open-telemetry/opentelemetry-python/pull/552))
- Add SumObserver, UpDownSumObserver and LastValueAggregator in metrics
  ([#789](https://github.com/open-telemetry/opentelemetry-python/pull/789))
- Add start_pipeline to MeterProvider
  ([#791](https://github.com/open-telemetry/opentelemetry-python/pull/791))
- Initial release of opentelemetry-ext-otlp, opentelemetry-proto
### Changed
- Move stateful & resource from Meter to MeterProvider
  ([#751](https://github.com/open-telemetry/opentelemetry-python/pull/751))
- Rename Measure to ValueRecorder in metrics
  ([#761](https://github.com/open-telemetry/opentelemetry-python/pull/761))
- Rename Observer to ValueObserver
  ([#764](https://github.com/open-telemetry/opentelemetry-python/pull/764))
- Log a warning when replacing the global Tracer/Meter provider
  ([#856](https://github.com/open-telemetry/opentelemetry-python/pull/856))
- bugfix: byte type attributes are decoded before adding to attributes dict
  ([#775](https://github.com/open-telemetry/opentelemetry-python/pull/775))
- Rename opentelemetry-auto-instrumentation to opentelemetry-instrumentation,
  and console script `opentelemetry-auto-instrumentation` to `opentelemetry-instrument`

## [0.8b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.8.0) - 2020-05-27

### Added
- Add a new bootstrap command that enables automatic instrument installations.
  ([#650](https://github.com/open-telemetry/opentelemetry-python/pull/650))

### Changed
- Handle boolean, integer and float values in Configuration
  ([#662](https://github.com/open-telemetry/opentelemetry-python/pull/662))
- bugfix: ensure status is always string
  ([#640](https://github.com/open-telemetry/opentelemetry-python/pull/640))
- Transform resource to tags when exporting
  ([#707](https://github.com/open-telemetry/opentelemetry-python/pull/707))
- Rename otcollector to opencensus
  ([#695](https://github.com/open-telemetry/opentelemetry-python/pull/695))
- Transform resource to tags when exporting
  ([#645](https://github.com/open-telemetry/opentelemetry-python/pull/645))
- `ext/boto`: Could not serialize attribute aws.region to tag when exporting via jaeger
  Serialize tuple type values by coercing them into a string, since Jaeger does not
  support tuple types.
  ([#865](https://github.com/open-telemetry/opentelemetry-python/pull/865))
- Validate span attribute types in SDK
  ([#678](https://github.com/open-telemetry/opentelemetry-python/pull/678))
- Specify to_json indent from arguments
  ([#718](https://github.com/open-telemetry/opentelemetry-python/pull/718))
- Span.resource will now default to an empty resource
  ([#724](https://github.com/open-telemetry/opentelemetry-python/pull/724))
- bugfix: Fix error message
  ([#729](https://github.com/open-telemetry/opentelemetry-python/pull/729))
- deep copy empty attributes
  ([#714](https://github.com/open-telemetry/opentelemetry-python/pull/714))

## [0.7b1](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.7.1) - 2020-05-12

### Added
- Add reset for the global configuration object, for testing purposes
  ([#636](https://github.com/open-telemetry/opentelemetry-python/pull/636))
- Add support for programmatic instrumentation
  ([#579](https://github.com/open-telemetry/opentelemetry-python/pull/569))

### Changed
- tracer.get_tracer now optionally accepts a TracerProvider
  ([#602](https://github.com/open-telemetry/opentelemetry-python/pull/602))
- Configuration object can now be used by any component of opentelemetry,
  including 3rd party instrumentations
  ([#563](https://github.com/open-telemetry/opentelemetry-python/pull/563))
- bugfix: configuration object now matches fields in a case-sensitive manner
  ([#583](https://github.com/open-telemetry/opentelemetry-python/pull/583))
- bugfix: configuration object now accepts all valid python variable names
  ([#583](https://github.com/open-telemetry/opentelemetry-python/pull/583))
- bugfix: configuration undefined attributes now return None instead of raising
  an AttributeError.
  ([#583](https://github.com/open-telemetry/opentelemetry-python/pull/583))
- bugfix: 'debug' field is now correct
  ([#549](https://github.com/open-telemetry/opentelemetry-python/pull/549))
- bugfix: enable auto-instrumentation command to work for custom entry points
  (e.g. flask_run)
  ([#567](https://github.com/open-telemetry/opentelemetry-python/pull/567))
- Exporter API: span parents are now always spancontext
  ([#548](https://github.com/open-telemetry/opentelemetry-python/pull/548))
- Console span exporter now prints prettier, more legible messages
  ([#505](https://github.com/open-telemetry/opentelemetry-python/pull/505))
- bugfix: B3 propagation now retrieves parentSpanId correctly
  ([#621](https://github.com/open-telemetry/opentelemetry-python/pull/621))
- bugfix: a DefaultSpan now longer causes an exception when used with tracer
  ([#577](https://github.com/open-telemetry/opentelemetry-python/pull/577))
- move last_updated_timestamp into aggregators instead of bound metric
  instrument
  ([#522](https://github.com/open-telemetry/opentelemetry-python/pull/522))
- bugfix: suppressing instrumentation in metrics to eliminate an infinite loop
  of telemetry
  ([#529](https://github.com/open-telemetry/opentelemetry-python/pull/529))
- bugfix: freezing span attribute sequences, reducing potential user errors
  ([#529](https://github.com/open-telemetry/opentelemetry-python/pull/529))

## [0.6b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.6.0) - 2020-03-30

### Added
- Add support for lazy events and links
  ([#474](https://github.com/open-telemetry/opentelemetry-python/pull/474))
- Adding is_remote flag to SpanContext, indicating when a span is remote
  ([#516](https://github.com/open-telemetry/opentelemetry-python/pull/516))
- Adding a solution to release metric handles and observers
  ([#435](https://github.com/open-telemetry/opentelemetry-python/pull/435))
- Initial release: opentelemetry-instrumentation

### Changed
- Metrics API no longer uses LabelSet
  ([#527](https://github.com/open-telemetry/opentelemetry-python/pull/527))
- Allow digit as first char in vendor specific trace state key
  ([#511](https://github.com/open-telemetry/opentelemetry-python/pull/511))
- Exporting to collector now works
  ([#508](https://github.com/open-telemetry/opentelemetry-python/pull/508))

## [0.5b0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.5.0) - 2020-03-16

### Added
- Adding Correlation Context API/SDK and propagator
  ([#471](https://github.com/open-telemetry/opentelemetry-python/pull/471))
- Adding a global configuration module to simplify setting and getting globals
  ([#466](https://github.com/open-telemetry/opentelemetry-python/pull/466))
- Adding named meters, removing batchers
  ([#431](https://github.com/open-telemetry/opentelemetry-python/pull/431))
- Adding attach/detach methods as per spec
  ([#429](https://github.com/open-telemetry/opentelemetry-python/pull/429))
- Adding OT Collector metrics exporter
  ([#454](https://github.com/open-telemetry/opentelemetry-python/pull/454))
- Initial release opentelemetry-ext-otcollector

### Changed
- Rename metric handle to bound metric instrument
  ([#470](https://github.com/open-telemetry/opentelemetry-python/pull/470))
- Moving resources to sdk
  ([#464](https://github.com/open-telemetry/opentelemetry-python/pull/464))
- Implementing propagators to API to use context
  ([#446](https://github.com/open-telemetry/opentelemetry-python/pull/446))
- Renaming TraceOptions to TraceFlags
  ([#450](https://github.com/open-telemetry/opentelemetry-python/pull/450))
- Renaming TracerSource to TracerProvider
  ([#441](https://github.com/open-telemetry/opentelemetry-python/pull/441))
- Improve validation of attributes
  ([#460](https://github.com/open-telemetry/opentelemetry-python/pull/460))
- Re-raise errors caught in opentelemetry.sdk.trace.Tracer.use_span()
  ([#469](https://github.com/open-telemetry/opentelemetry-python/pull/469))
- Implement observer instrument
  ([#425](https://github.com/open-telemetry/opentelemetry-python/pull/425))

## [0.4a0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.4.0) - 2020-02-21

### Added
- Added named Tracers
  ([#301](https://github.com/open-telemetry/opentelemetry-python/pull/301))
- Add int and valid sequenced to AttributeValue type
  ([#368](https://github.com/open-telemetry/opentelemetry-python/pull/368))
- Add ABC for Metric
  ([#391](https://github.com/open-telemetry/opentelemetry-python/pull/391))
- Metrics export pipeline, and stdout exporter
  ([#341](https://github.com/open-telemetry/opentelemetry-python/pull/341))
- Adding Context API Implementation
  ([#395](https://github.com/open-telemetry/opentelemetry-python/pull/395))
- Adding trace.get_tracer function
  ([#430](https://github.com/open-telemetry/opentelemetry-python/pull/430))
- Add runtime validation for set_attribute
  ([#348](https://github.com/open-telemetry/opentelemetry-python/pull/348))
- Add support for B3 ParentSpanID
  ([#286](https://github.com/open-telemetry/opentelemetry-python/pull/286))
- Implement MinMaxSumCount aggregator
  ([#422](https://github.com/open-telemetry/opentelemetry-python/pull/422))
- Initial release opentelemetry-ext-zipkin, opentelemetry-ext-prometheus

### Changed
- Separate Default classes from interface descriptions
  ([#311](https://github.com/open-telemetry/opentelemetry-python/pull/311))
- Export span status
  ([#367](https://github.com/open-telemetry/opentelemetry-python/pull/367))
- Export span kind
  ([#387](https://github.com/open-telemetry/opentelemetry-python/pull/387))
- Set status for ended spans
  ([#297](https://github.com/open-telemetry/opentelemetry-python/pull/297) and
  [#358](https://github.com/open-telemetry/opentelemetry-python/pull/358))
- Use module loggers
  ([#351](https://github.com/open-telemetry/opentelemetry-python/pull/351))
- Protect start_time and end_time from being set manually by the user
  ([#363](https://github.com/open-telemetry/opentelemetry-python/pull/363))
- Set status in start_as_current_span
  ([#377](https://github.com/open-telemetry/opentelemetry-python/pull/377))
- Implement force_flush for span processors
  ([#389](https://github.com/open-telemetry/opentelemetry-python/pull/389))
- Set sampled flag on sampling trace
  ([#407](https://github.com/open-telemetry/opentelemetry-python/pull/407))
- Add io and formatter options to console exporter
  ([#412](https://github.com/open-telemetry/opentelemetry-python/pull/412))
- Clean up ProbabilitySample for 64 bit trace IDs
  ([#238](https://github.com/open-telemetry/opentelemetry-python/pull/238))

### Removed
- Remove monotonic and absolute metric instruments
  ([#410](https://github.com/open-telemetry/opentelemetry-python/pull/410))

## [0.3a0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.3.0) - 2019-12-11

### Added
- Add metrics exporters
  ([#192](https://github.com/open-telemetry/opentelemetry-python/pull/192))
- Implement extract and inject support for HTTP_HEADERS and TEXT_MAP formats
  ([#256](https://github.com/open-telemetry/opentelemetry-python/pull/256))

### Changed
- Multiple tracing API/SDK changes
- Multiple metrics API/SDK changes

### Removed
- Remove option to create unstarted spans from API
  ([#290](https://github.com/open-telemetry/opentelemetry-python/pull/290))

## [0.2a0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.2.0) - 2019-10-29

### Added
- W3C TraceContext fixes and compliance tests
  ([#228](https://github.com/open-telemetry/opentelemetry-python/pull/228))
- Sampler API/SDK
  ([#225](https://github.com/open-telemetry/opentelemetry-python/pull/225))
- Initial release: opentelemetry-ext-jaeger, opentelemetry-opentracing-shim

### Changed
- Multiple metrics API/SDK changes
- Multiple tracing API/SDK changes
- Multiple context API changes
- Multiple bugfixes and improvements

## [0.1a0](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.1.0) - 2019-09-30

### Added
- Initial release api/sdk
