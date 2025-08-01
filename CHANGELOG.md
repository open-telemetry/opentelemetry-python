# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## Version 1.36.0/0.57b0 (2025-07-29)

- Add missing Prometheus exporter documentation
  ([#4485](https://github.com/open-telemetry/opentelemetry-python/pull/4485))
- Overwrite logging.config.fileConfig and logging.config.dictConfig to ensure
the OTLP `LogHandler` remains attached to the root logger. Fix a bug that
can cause a deadlock to occur over `logging._lock` in some cases ([#4636](https://github.com/open-telemetry/opentelemetry-python/pull/4636)).
- otlp-http-exporter: set default value for param `timeout_sec` in `_export` method
  ([#4691](https://github.com/open-telemetry/opentelemetry-python/pull/4691))

- Update OTLP gRPC/HTTP exporters: calling shutdown will now interrupt exporters that are sleeping
  before a retry attempt, and cause them to return failure immediately.
  Update BatchSpan/LogRecordProcessors: shutdown will now complete after 30 seconds of trying to finish
  exporting any buffered telemetry, instead of continuing to export until all telemetry was exported.
  ([#4638](https://github.com/open-telemetry/opentelemetry-python/pull/4638)).

## Version 1.35.0/0.56b0 (2025-07-11)

- Update OTLP proto to v1.7 [#4645](https://github.com/open-telemetry/opentelemetry-python/pull/4645).
- Add `event_name` as a top level field in the `LogRecord`. Events are now simply logs with the
`event_name` field set, the logs SDK should be used to emit events ([#4652](https://github.com/open-telemetry/opentelemetry-python/pull/4652)).
- Update OTLP gRPC/HTTP exporters: the export timeout is now inclusive of all retries and backoffs.
  A +/-20% jitter was added to all backoffs. A pointless 32 second sleep that occurred after all retries
  had completed/failed was removed.
  ([#4564](https://github.com/open-telemetry/opentelemetry-python/pull/4564)).
- Update ConsoleLogExporter.export to handle LogRecord's containing bytes type
  in the body ([#4614](https://github.com/open-telemetry/opentelemetry-python/pull/4614/)).
- opentelemetry-sdk: Fix invalid `type: ignore` that causes mypy to ignore the whole file
  ([#4618](https://github.com/open-telemetry/opentelemetry-python/pull/4618))
- Add `span_exporter` property back to `BatchSpanProcessor` class
  ([#4621](https://github.com/open-telemetry/opentelemetry-python/pull/4621))
- Fix license field in pyproject.toml files
  ([#4625](https://github.com/open-telemetry/opentelemetry-python/pull/4625))
- Update logger level to NOTSET in logs example
  ([#4637](https://github.com/open-telemetry/opentelemetry-python/pull/4637))
- Logging API accepts optional `context`; deprecates `trace_id`, `span_id`, `trace_flags`.
  ([#4597](https://github.com/open-telemetry/opentelemetry-python/pull/4597)) and
  ([#4668](https://github.com/open-telemetry/opentelemetry-python/pull/4668))
- sdk: use context instead of trace_id,span_id for initializing LogRecord
  ([#4653](https://github.com/open-telemetry/opentelemetry-python/pull/4653))
- Rename LogRecordProcessor.emit to on_emit
  ([#4648](https://github.com/open-telemetry/opentelemetry-python/pull/4648))
- Logging API hide std_to_otel function to convert python logging severity to otel severity
  ([#4649](https://github.com/open-telemetry/opentelemetry-python/pull/4649))
- proto: relax protobuf version requirement to support v6
  ([#4620](https://github.com/open-telemetry/opentelemetry-python/pull/4620))
- Bump semantic-conventions to 1.36.0
  ([#4669](https://github.com/open-telemetry/opentelemetry-python/pull/4669))
- Set expected User-Agent in HTTP headers for grpc OTLP exporter
  ([#4658](https://github.com/open-telemetry/opentelemetry-python/pull/4658))

## Version 1.34.0/0.55b0 (2025-06-04)

- typecheck: add sdk/resources and drop mypy
  ([#4578](https://github.com/open-telemetry/opentelemetry-python/pull/4578))
- Use PEP702 for marking deprecations
  ([#4522](https://github.com/open-telemetry/opentelemetry-python/pull/4522))
- Refactor `BatchLogRecordProcessor` and `BatchSpanProcessor` to simplify code
  and make the control flow more clear ([#4562](https://github.com/open-telemetry/opentelemetry-python/pull/4562/)
  [#4535](https://github.com/open-telemetry/opentelemetry-python/pull/4535), and
  [#4580](https://github.com/open-telemetry/opentelemetry-python/pull/4580)).
- Remove log messages from `BatchLogRecordProcessor.emit`, this caused the program
  to crash at shutdown with a max recursion error ([#4586](https://github.com/open-telemetry/opentelemetry-python/pull/4586)).
- Configurable max retry timeout for grpc exporter
  ([#4333](https://github.com/open-telemetry/opentelemetry-python/pull/4333))
- opentelemetry-api: allow importlib-metadata 8.7.0
  ([#4593](https://github.com/open-telemetry/opentelemetry-python/pull/4593))
- opentelemetry-test-utils: assert explicit bucket boundaries in histogram metrics
  ([#4595](https://github.com/open-telemetry/opentelemetry-python/pull/4595))
- Bump semantic conventions to 1.34.0
  ([#4599](https://github.com/open-telemetry/opentelemetry-python/pull/4599))
- Drop support for Python 3.8
  ([#4520](https://github.com/open-telemetry/opentelemetry-python/pull/4520))

## Version 1.33.0/0.54b0 (2025-05-09)

- Fix intermittent `Connection aborted` error when using otlp/http exporters
  ([#4477](https://github.com/open-telemetry/opentelemetry-python/pull/4477))
- opentelemetry-sdk: use stable code attributes: `code.function` -> `code.function.name`, `code.lineno` -> `code.line.number`, `code.filepath` -> `code.file.path`
  ([#4508](https://github.com/open-telemetry/opentelemetry-python/pull/4508))
- Fix serialization of extended attributes for logs signal
  ([#4342](https://github.com/open-telemetry/opentelemetry-python/pull/4342))
- Handle OTEL_PROPAGATORS contains None
  ([#4553](https://github.com/open-telemetry/opentelemetry-python/pull/4553))
- docs: updated and added to the metrics and log examples
  ([#4559](https://github.com/open-telemetry/opentelemetry-python/pull/4559))
- Bump semantic conventions to 1.33.0
  ([#4567](https://github.com/open-telemetry/opentelemetry-python/pull/4567))

## Version 1.32.0/0.53b0 (2025-04-10)

- Fix user agent in OTLP HTTP metrics exporter
  ([#4475](https://github.com/open-telemetry/opentelemetry-python/pull/4475))
- Improve performance of baggage operations
  ([#4466](https://github.com/open-telemetry/opentelemetry-python/pull/4466))
- sdk: remove duplicated constant definitions for `environment_variables`
  ([#4491](https://github.com/open-telemetry/opentelemetry-python/pull/4491))
- api: Revert record `BaseException` change in `trace_api.use_span()`
  ([#4494](https://github.com/open-telemetry/opentelemetry-python/pull/4494))
- Improve CI by cancelling stale runs and setting timeouts
  ([#4498](https://github.com/open-telemetry/opentelemetry-python/pull/4498))
- Patch logging.basicConfig so OTel logs don't cause console logs to disappear
  ([#4436](https://github.com/open-telemetry/opentelemetry-python/pull/4436))
- Bump semantic conventions to 1.32.0
  ([#4530](https://github.com/open-telemetry/opentelemetry-python/pull/4530))
- Fix ExplicitBucketHistogramAggregation to handle multiple explicit bucket boundaries advisories
  ([#4521](https://github.com/open-telemetry/opentelemetry-python/pull/4521))
- opentelemetry-sdk: Fix serialization of objects in log handler
  ([#4528](https://github.com/open-telemetry/opentelemetry-python/pull/4528))

## Version 1.31.0/0.52b0 (2025-03-12)

- semantic-conventions: Bump to 1.31.0
  ([#4471](https://github.com/open-telemetry/opentelemetry-python/pull/4471))
- Add type annotations to context's attach & detach
  ([#4346](https://github.com/open-telemetry/opentelemetry-python/pull/4346))
- Fix OTLP encoders missing instrumentation scope schema url and attributes
  ([#4359](https://github.com/open-telemetry/opentelemetry-python/pull/4359))
- prometheus-exporter: fix labels out of place for data points with different
  attribute sets
  ([#4413](https://github.com/open-telemetry/opentelemetry-python/pull/4413))
- Type indent parameter in to_json
  ([#4402](https://github.com/open-telemetry/opentelemetry-python/pull/4402))
- Tolerates exceptions when loading resource detectors via `OTEL_EXPERIMENTAL_RESOURCE_DETECTORS`
  ([#4373](https://github.com/open-telemetry/opentelemetry-python/pull/4373))
- Disconnect gRPC client stub when shutting down `OTLPSpanExporter`
  ([#4370](https://github.com/open-telemetry/opentelemetry-python/pull/4370))
- opentelemetry-sdk: fix OTLP exporting of Histograms with explicit buckets advisory
  ([#4434](https://github.com/open-telemetry/opentelemetry-python/pull/4434))
- opentelemetry-exporter-otlp-proto-grpc: better dependency version range for Python 3.13
  ([#4444](https://github.com/open-telemetry/opentelemetry-python/pull/4444))
- opentelemetry-exporter-opencensus: better dependency version range for Python 3.13
  ([#4444](https://github.com/open-telemetry/opentelemetry-python/pull/4444))
- Updated `tracecontext-integration-test` gitref to `d782773b2cf2fa4afd6a80a93b289d8a74ca894d`
  ([#4448](https://github.com/open-telemetry/opentelemetry-python/pull/4448))
- Make `trace_api.use_span()` record `BaseException` as well as `Exception`
  ([#4406](https://github.com/open-telemetry/opentelemetry-python/pull/4406))
- Fix env var error message for TraceLimits/SpanLimits
  ([#4458](https://github.com/open-telemetry/opentelemetry-python/pull/4458))
- pylint-ci updated python version to 3.13
  ([#4450](https://github.com/open-telemetry/opentelemetry-python/pull/4450))
- Fix memory leak in Log & Trace exporter
  ([#4449](https://github.com/open-telemetry/opentelemetry-python/pull/4449))

## Version 1.30.0/0.51b0 (2025-02-03)

- Always setup logs sdk, OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED only controls python `logging` module handler setup
  ([#4340](https://github.com/open-telemetry/opentelemetry-python/pull/4340))
- Add `attributes` field in `metrics.get_meter` wrapper function
  ([#4364](https://github.com/open-telemetry/opentelemetry-python/pull/4364))
- Add Python 3.13 support
  ([#4353](https://github.com/open-telemetry/opentelemetry-python/pull/4353))
- sdk: don't log or print warnings when the SDK has been disabled
  ([#4371](https://github.com/open-telemetry/opentelemetry-python/pull/4371))
- Fix span context manager typing by using ParamSpec from typing_extensions
  ([#4389](https://github.com/open-telemetry/opentelemetry-python/pull/4389))
- Fix serialization of None values in logs body to match 1.31.0+ data model
  ([#4400](https://github.com/open-telemetry/opentelemetry-python/pull/4400))
- [BREAKING] semantic-conventions: Remove `opentelemetry.semconv.attributes.network_attributes.NETWORK_INTERFACE_NAME`
  introduced by mistake in the wrong module.
  ([#4391](https://github.com/open-telemetry/opentelemetry-python/pull/4391))
- Add support for explicit bucket boundaries advisory for Histograms
  ([#4361](https://github.com/open-telemetry/opentelemetry-python/pull/4361))
- semantic-conventions: Bump to 1.30.0
  ([#4337](https://github.com/open-telemetry/opentelemetry-python/pull/4397))

## Version 1.29.0/0.50b0 (2024-12-11)

- Fix crash exporting a log record with None body
  ([#4276](https://github.com/open-telemetry/opentelemetry-python/pull/4276))
- Fix metrics export with exemplar and no context and filtering observable instruments
  ([#4251](https://github.com/open-telemetry/opentelemetry-python/pull/4251))
- Fix recursion error with sdk disabled and handler added to root logger
  ([#4259](https://github.com/open-telemetry/opentelemetry-python/pull/4259))
- sdk: setup EventLogger when OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED is set
  ([#4270](https://github.com/open-telemetry/opentelemetry-python/pull/4270))
- api: fix logging of duplicate EventLogger setup warning
  ([#4299](https://github.com/open-telemetry/opentelemetry-python/pull/4299))
- sdk: fix setting of process owner in ProcessResourceDetector
  ([#4311](https://github.com/open-telemetry/opentelemetry-python/pull/4311))
- sdk: fix serialization of logs severity_number field to int
  ([#4324](https://github.com/open-telemetry/opentelemetry-python/pull/4324))
- Remove `TestBase.assertEqualSpanInstrumentationInfo` method, use `assertEqualSpanInstrumentationScope` instead
  ([#4310](https://github.com/open-telemetry/opentelemetry-python/pull/4310))
- sdk: instantiate lazily `ExemplarBucket`s in `ExemplarReservoir`s
  ([#4260](https://github.com/open-telemetry/opentelemetry-python/pull/4260))
- semantic-conventions: Bump to 1.29.0
  ([#4337](https://github.com/open-telemetry/opentelemetry-python/pull/4337))

## Version 1.28.0/0.49b0 (2024-11-05)

- Removed superfluous py.typed markers and added them where they were missing
  ([#4172](https://github.com/open-telemetry/opentelemetry-python/pull/4172))
- Include metric info in encoding exceptions
  ([#4154](https://github.com/open-telemetry/opentelemetry-python/pull/4154))
- sdk: Add support for log formatting
  ([#4137](https://github.com/open-telemetry/opentelemetry-python/pull/4166))
- sdk: Add Host resource detector
  ([#4182](https://github.com/open-telemetry/opentelemetry-python/pull/4182))
- sdk: Implementation of exemplars
  ([#4094](https://github.com/open-telemetry/opentelemetry-python/pull/4094))
- Implement events sdk
  ([#4176](https://github.com/open-telemetry/opentelemetry-python/pull/4176))
- Update semantic conventions to version 1.28.0
  ([#4218](https://github.com/open-telemetry/opentelemetry-python/pull/4218))
- Add support to protobuf 5+ and drop support to protobuf 3 and 4
  ([#4206](https://github.com/open-telemetry/opentelemetry-python/pull/4206))
- Update environment variable descriptions to match signal
  ([#4222](https://github.com/open-telemetry/opentelemetry-python/pull/4222))
- Record logger name as the instrumentation scope name
  ([#4208](https://github.com/open-telemetry/opentelemetry-python/pull/4208))
- Fix memory leak in exporter and reader
  ([#4224](https://github.com/open-telemetry/opentelemetry-python/pull/4224))
- Drop `OTEL_PYTHON_EXPERIMENTAL_DISABLE_PROMETHEUS_UNIT_NORMALIZATION` environment variable
  ([#4217](https://github.com/open-telemetry/opentelemetry-python/pull/4217))
- Improve compatibility with other logging libraries that override
  `LogRecord.getMessage()` in order to customize message formatting
  ([#4216](https://github.com/open-telemetry/opentelemetry-python/pull/4216))

## Version 1.27.0/0.48b0 (2024-08-28)

- Implementation of Events API
  ([#4054](https://github.com/open-telemetry/opentelemetry-python/pull/4054))
- Make log sdk add `exception.message` to logRecord for exceptions whose argument
  is an exception not a string message
  ([#4122](https://github.com/open-telemetry/opentelemetry-python/pull/4122))
- Fix use of `link.attributes.dropped`, which may not exist
  ([#4119](https://github.com/open-telemetry/opentelemetry-python/pull/4119))
- Running mypy on SDK resources
  ([#4053](https://github.com/open-telemetry/opentelemetry-python/pull/4053))
- Added py.typed file to top-level module
  ([#4084](https://github.com/open-telemetry/opentelemetry-python/pull/4084))
- Drop Final annotation from Enum in semantic conventions
  ([#4085](https://github.com/open-telemetry/opentelemetry-python/pull/4085))
- Update log export example to not use root logger ([#4090](https://github.com/open-telemetry/opentelemetry-python/pull/4090))
- sdk: Add OS resource detector
  ([#3992](https://github.com/open-telemetry/opentelemetry-python/pull/3992))
- sdk: Accept non URL-encoded headers in `OTEL_EXPORTER_OTLP_*HEADERS` to match other languages SDKs
  ([#4103](https://github.com/open-telemetry/opentelemetry-python/pull/4103))
- Update semantic conventions to version 1.27.0
  ([#4104](https://github.com/open-telemetry/opentelemetry-python/pull/4104))
- Add support to type bytes for OTLP AnyValue
  ([#4128](https://github.com/open-telemetry/opentelemetry-python/pull/4128))
- Export ExponentialHistogram and ExponentialHistogramDataPoint
  ([#4134](https://github.com/open-telemetry/opentelemetry-python/pull/4134))
- Implement Client Key and Certificate File Support for All OTLP Exporters
  ([#4116](https://github.com/open-telemetry/opentelemetry-python/pull/4116))
- Remove `_start_time_unix_nano` attribute from `_ViewInstrumentMatch` in favor
  of using `time_ns()` at the moment when the aggregation object is created
  ([#4137](https://github.com/open-telemetry/opentelemetry-python/pull/4137))

## Version 1.26.0/0.47b0 (2024-07-25)

- Standardizing timeout calculation in measurement consumer collect to nanoseconds
  ([#4074](https://github.com/open-telemetry/opentelemetry-python/pull/4074))
- optional scope attributes for logger creation
  ([#4035](https://github.com/open-telemetry/opentelemetry-python/pull/4035))
- optional scope attribute for tracer creation
  ([#4028](https://github.com/open-telemetry/opentelemetry-python/pull/4028))
- OTLP exporter is encoding invalid span/trace IDs in the logs fix
  ([#4006](https://github.com/open-telemetry/opentelemetry-python/pull/4006))
- Update sdk process resource detector `process.command_args` attribute to also include the executable itself
  ([#4032](https://github.com/open-telemetry/opentelemetry-python/pull/4032))
- Fix `start_time_unix_nano` for delta collection for explicit bucket histogram aggregation
  ([#4009](https://github.com/open-telemetry/opentelemetry-python/pull/4009))
- Fix `start_time_unix_nano` for delta collection for sum aggregation
  ([#4011](https://github.com/open-telemetry/opentelemetry-python/pull/4011))
- Update opentracing and opencesus docs examples to not use JaegerExporter
  ([#4023](https://github.com/open-telemetry/opentelemetry-python/pull/4023))
- Do not execute Flask Tests in debug mode
  ([#3956](https://github.com/open-telemetry/opentelemetry-python/pull/3956))
- When encountering an error encoding metric attributes in the OTLP exporter, log the key that had an error.
  ([#3838](https://github.com/open-telemetry/opentelemetry-python/pull/3838))
- Fix `ExponentialHistogramAggregation`
  ([#3978](https://github.com/open-telemetry/opentelemetry-python/pull/3978))
- Log a warning when a `LogRecord` in `sdk/log` has dropped attributes
  due to reaching limits
  ([#3946](https://github.com/open-telemetry/opentelemetry-python/pull/3946))
- Fix RandomIdGenerator can generate invalid Span/Trace Ids
  ([#3949](https://github.com/open-telemetry/opentelemetry-python/pull/3949))
- Add Python 3.12 to tox
  ([#3616](https://github.com/open-telemetry/opentelemetry-python/pull/3616))
- Improve resource field structure for LogRecords
  ([#3972](https://github.com/open-telemetry/opentelemetry-python/pull/3972))
- Update Semantic Conventions code generation scripts:
  - fix namespace exclusion that resulted in dropping  `os` and `net` namespaces.
  - add `Final` decorator to constants to prevent collisions
  - enable mypy and fix detected issues
  - allow to drop specific attributes in preparation for Semantic Conventions v1.26.0
  ([#3973](https://github.com/open-telemetry/opentelemetry-python/pull/3966))
- Update semantic conventions to version 1.26.0.
  ([#3964](https://github.com/open-telemetry/opentelemetry-python/pull/3964))
- Use semconv exception attributes for record exceptions in spans
  ([#3979](https://github.com/open-telemetry/opentelemetry-python/pull/3979))
- Fix _encode_events assumes events.attributes.dropped exists
  ([#3965](https://github.com/open-telemetry/opentelemetry-python/pull/3965))
- Validate links at span creation
  ([#3991](https://github.com/open-telemetry/opentelemetry-python/pull/3991))
- Add attributes field in  `MeterProvider.get_meter` and `InstrumentationScope`
  ([#4015](https://github.com/open-telemetry/opentelemetry-python/pull/4015))
- Fix inaccessible `SCHEMA_URL` constants in `opentelemetry-semantic-conventions`
  ([#4069](https://github.com/open-telemetry/opentelemetry-python/pull/4069))

## Version 1.25.0/0.46b0 (2024-05-30)

- Fix class BoundedAttributes to have RLock rather than Lock
  ([#3859](https://github.com/open-telemetry/opentelemetry-python/pull/3859))
- Remove thread lock by loading RuntimeContext explicitly.
  ([#3763](https://github.com/open-telemetry/opentelemetry-python/pull/3763))
- Update proto version to v1.2.0
  ([#3844](https://github.com/open-telemetry/opentelemetry-python/pull/3844))
- Add to_json method to ExponentialHistogram
  ([#3780](https://github.com/open-telemetry/opentelemetry-python/pull/3780))
- Bump mypy to 1.9.0
  ([#3795](https://github.com/open-telemetry/opentelemetry-python/pull/3795))
- Fix exponential histograms
  ([#3798](https://github.com/open-telemetry/opentelemetry-python/pull/3798))
- Fix otlp exporter to export log_record.observed_timestamp
  ([#3785](https://github.com/open-telemetry/opentelemetry-python/pull/3785))
- Add capture the fully qualified type name for raised exceptions in spans
  ([#3837](https://github.com/open-telemetry/opentelemetry-python/pull/3837))
- Prometheus exporter sort label keys to prevent duplicate metrics when user input changes order
  ([#3698](https://github.com/open-telemetry/opentelemetry-python/pull/3698))
- Update semantic conventions to version 1.25.0.
  Refactor semantic-convention structure:
  - `SpanAttributes`, `ResourceAttributes`, and `MetricInstruments` are deprecated.
  - Attribute and metric definitions are now grouped by the namespace.
  - Stable attributes and metrics are moved to `opentelemetry.semconv.attributes`
  and `opentelemetry.semconv.metrics` modules.
  - Stable and experimental attributes and metrics are defined under
  `opentelemetry.semconv._incubating` import path.
  ([#3586](https://github.com/open-telemetry/opentelemetry-python/pull/3586))
- Rename test objects to avoid pytest warnings
  ([#3823] (https://github.com/open-telemetry/opentelemetry-python/pull/3823))
- Add span flags to OTLP spans and links
  ([#3881](https://github.com/open-telemetry/opentelemetry-python/pull/3881))
- Record links with invalid SpanContext if either attributes or TraceState are not empty
  ([#3917](https://github.com/open-telemetry/opentelemetry-python/pull/3917/))
- Add OpenTelemetry trove classifiers to PyPI packages
  ([#3913] (https://github.com/open-telemetry/opentelemetry-python/pull/3913))
- Fix prometheus metric name and unit conversion
  ([#3924](https://github.com/open-telemetry/opentelemetry-python/pull/3924))
  - this is a breaking change to prometheus metric names so they comply with the
  [specification](https://github.com/open-telemetry/opentelemetry-specification/blob/v1.33.0/specification/compatibility/prometheus_and_openmetrics.md#otlp-metric-points-to-prometheus).
  - you can temporarily opt-out of the unit normalization by setting the environment variable
  `OTEL_PYTHON_EXPERIMENTAL_DISABLE_PROMETHEUS_UNIT_NORMALIZATION=true`
  - common unit abbreviations are converted to Prometheus conventions (`s` -> `seconds`),
  following the [collector's implementation](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/c0b51136575aa7ba89326d18edb4549e7e1bbdb9/pkg/translator/prometheus/normalize_name.go#L108)
  - repeated `_` are replaced with a single `_`
  - unit annotations (enclosed in curly braces like `{requests}`) are stripped away
  - units with slash are converted e.g. `m/s` -> `meters_per_second`.
  - The exporter's API is not changed
- Add parameters for Distros and configurators to configure autoinstrumentation in addition to existing environment variables.
  ([#3864](https://github.com/open-telemetry/opentelemetry-python/pull/3864))

## Version 1.24.0/0.45b0 (2024-03-28)

- Make create_gauge non-abstract method
  ([#3817](https://github.com/open-telemetry/opentelemetry-python/pull/3817))
- Make `tracer.start_as_current_span()` decorator work with async functions
  ([#3633](https://github.com/open-telemetry/opentelemetry-python/pull/3633))
- Fix python 3.12 deprecation warning
  ([#3751](https://github.com/open-telemetry/opentelemetry-python/pull/3751))
- bump mypy to 0.982
  ([#3776](https://github.com/open-telemetry/opentelemetry-python/pull/3776))
- Add support for OTEL_SDK_DISABLED environment variable
  ([#3648](https://github.com/open-telemetry/opentelemetry-python/pull/3648))
- Fix ValueError message for PeriodicExportingMetricsReader
  ([#3769](https://github.com/open-telemetry/opentelemetry-python/pull/3769))
- Use `BaseException` instead of `Exception` in `record_exception`
  ([#3354](https://github.com/open-telemetry/opentelemetry-python/pull/3354))
- Make span.record_exception more robust
  ([#3778](https://github.com/open-telemetry/opentelemetry-python/pull/3778))
- Fix license field in pyproject.toml files
  ([#3803](https://github.com/open-telemetry/opentelemetry-python/pull/3803))

## Version 1.23.0/0.44b0 (2024-02-23)

- Use Attribute rather than boundattribute in logrecord
  ([#3567](https://github.com/open-telemetry/opentelemetry-python/pull/3567))
- Fix flush error when no LoggerProvider configured for LoggingHandler
  ([#3608](https://github.com/open-telemetry/opentelemetry-python/pull/3608))
- Add `Span.add_link()` method to add link after span start
  ([#3618](https://github.com/open-telemetry/opentelemetry-python/pull/3618))
- Fix `OTLPMetricExporter` ignores `preferred_aggregation` property
  ([#3603](https://github.com/open-telemetry/opentelemetry-python/pull/3603))
- Logs: set `observed_timestamp` field
  ([#3565](https://github.com/open-telemetry/opentelemetry-python/pull/3565))
- Add missing Resource SchemaURL in OTLP exporters
  ([#3652](https://github.com/open-telemetry/opentelemetry-python/pull/3652))
- Fix loglevel warning text
  ([#3566](https://github.com/open-telemetry/opentelemetry-python/pull/3566))
- Prometheus Exporter string representation for target_info labels
  ([#3659](https://github.com/open-telemetry/opentelemetry-python/pull/3659))
- Logs: ObservedTimestamp field is missing in console exporter output
  ([#3564](https://github.com/open-telemetry/opentelemetry-python/pull/3564))
- Fix explicit bucket histogram aggregation
  ([#3429](https://github.com/open-telemetry/opentelemetry-python/pull/3429))
- Add `code.lineno`, `code.function` and `code.filepath` to all logs
  ([#3675](https://github.com/open-telemetry/opentelemetry-python/pull/3675))
- Add Synchronous Gauge instrument
  ([#3462](https://github.com/open-telemetry/opentelemetry-python/pull/3462))
- Drop support for 3.7
  ([#3668](https://github.com/open-telemetry/opentelemetry-python/pull/3668))
- Include key in attribute sequence warning
  ([#3639](https://github.com/open-telemetry/opentelemetry-python/pull/3639))
- Upgrade markupsafe, Flask and related dependencies to dev and test
  environments ([#3609](https://github.com/open-telemetry/opentelemetry-python/pull/3609))
- Handle HTTP 2XX responses as successful in OTLP exporters
  ([#3623](https://github.com/open-telemetry/opentelemetry-python/pull/3623))
- Improve Resource Detector timeout messaging
  ([#3645](https://github.com/open-telemetry/opentelemetry-python/pull/3645))
- Add Proxy classes for logging
  ([#3575](https://github.com/open-telemetry/opentelemetry-python/pull/3575))
- Remove dependency on 'backoff' library
  ([#3679](https://github.com/open-telemetry/opentelemetry-python/pull/3679))

## Version 1.22.0/0.43b0 (2023-12-15)

- Prometheus exporter sanitize info metric
  ([#3572](https://github.com/open-telemetry/opentelemetry-python/pull/3572))
- Remove Jaeger exporters
  ([#3554](https://github.com/open-telemetry/opentelemetry-python/pull/3554))
- Log stacktrace on `UNKNOWN` status OTLP export error
  ([#3536](https://github.com/open-telemetry/opentelemetry-python/pull/3536))
- Fix OTLPExporterMixin shutdown timeout period
  ([#3524](https://github.com/open-telemetry/opentelemetry-python/pull/3524))
- Handle `taskName` `logrecord` attribute
  ([#3557](https://github.com/open-telemetry/opentelemetry-python/pull/3557))

## Version 1.21.0/0.42b0 (2023-11-01)

- Fix `SumAggregation`
￼  ([#3390](https://github.com/open-telemetry/opentelemetry-python/pull/3390))
- Fix handling of empty metric collection cycles
  ([#3335](https://github.com/open-telemetry/opentelemetry-python/pull/3335))
- Fix error when no LoggerProvider configured for LoggingHandler
  ([#3423](https://github.com/open-telemetry/opentelemetry-python/pull/3423))
- Make `opentelemetry_metrics_exporter` entrypoint support pull exporters
  ([#3428](https://github.com/open-telemetry/opentelemetry-python/pull/3428))
- Allow instrument names to have '/' and up to 255 characters
  ([#3442](https://github.com/open-telemetry/opentelemetry-python/pull/3442))
- Do not load Resource on sdk import
  ([#3447](https://github.com/open-telemetry/opentelemetry-python/pull/3447))
- Update semantic conventions to version 1.21.0
  ([#3251](https://github.com/open-telemetry/opentelemetry-python/pull/3251))
- Add missing schema_url in global api for logging and metrics
  ([#3251](https://github.com/open-telemetry/opentelemetry-python/pull/3251))
- Prometheus exporter support for auto instrumentation
  ([#3413](https://github.com/open-telemetry/opentelemetry-python/pull/3413))
- Implement Process Resource detector
  ([#3472](https://github.com/open-telemetry/opentelemetry-python/pull/3472))


## Version 1.20.0/0.41b0 (2023-09-04)

- Modify Prometheus exporter to translate non-monotonic Sums into Gauges
  ([#3306](https://github.com/open-telemetry/opentelemetry-python/pull/3306))

## Version 1.19.0/0.40b0 (2023-07-13)

- Drop `setuptools` runtime requirement.
  ([#3372](https://github.com/open-telemetry/opentelemetry-python/pull/3372))
- Update the body type in the log
  ([$3343](https://github.com/open-telemetry/opentelemetry-python/pull/3343))
- Add max_scale option to Exponential Bucket Histogram Aggregation
  ([#3323](https://github.com/open-telemetry/opentelemetry-python/pull/3323))
- Use BoundedAttributes instead of raw dict to extract attributes from LogRecord
  ([#3310](https://github.com/open-telemetry/opentelemetry-python/pull/3310))
- Support dropped_attributes_count in LogRecord and exporters
  ([#3351](https://github.com/open-telemetry/opentelemetry-python/pull/3351))
- Add unit to view instrument selection criteria
  ([#3341](https://github.com/open-telemetry/opentelemetry-python/pull/3341))
- Upgrade opentelemetry-proto to 0.20 and regen
  [#3355](https://github.com/open-telemetry/opentelemetry-python/pull/3355))
- Include endpoint in Grpc transient error warning
  [#3362](https://github.com/open-telemetry/opentelemetry-python/pull/3362))
- Fixed bug where logging export is tracked as trace
  [#3375](https://github.com/open-telemetry/opentelemetry-python/pull/3375))
- Default LogRecord observed_timestamp to current timestamp
  [#3377](https://github.com/open-telemetry/opentelemetry-python/pull/3377))


## Version 1.18.0/0.39b0 (2023-05-19)

- Select histogram aggregation with an environment variable
  ([#3265](https://github.com/open-telemetry/opentelemetry-python/pull/3265))
- Move Protobuf encoding to its own package
  ([#3169](https://github.com/open-telemetry/opentelemetry-python/pull/3169))
- Add experimental feature to detect resource detectors in auto instrumentation
  ([#3181](https://github.com/open-telemetry/opentelemetry-python/pull/3181))
- Fix exporting of ExponentialBucketHistogramAggregation from opentelemetry.sdk.metrics.view
  ([#3240](https://github.com/open-telemetry/opentelemetry-python/pull/3240))
- Fix headers types mismatch for OTLP Exporters
  ([#3226](https://github.com/open-telemetry/opentelemetry-python/pull/3226))
- Fix suppress instrumentation for log batch processor
  ([#3223](https://github.com/open-telemetry/opentelemetry-python/pull/3223))
- Add speced out environment variables and arguments for BatchLogRecordProcessor
  ([#3237](https://github.com/open-telemetry/opentelemetry-python/pull/3237))
- Add benchmark tests for metrics
  ([#3267](https://github.com/open-telemetry/opentelemetry-python/pull/3267))


## Version 1.17.0/0.38b0 (2023-03-22)

- Implement LowMemory temporality
  ([#3223](https://github.com/open-telemetry/opentelemetry-python/pull/3223))
- PeriodicExportingMetricReader will continue if collection times out
  ([#3100](https://github.com/open-telemetry/opentelemetry-python/pull/3100))
- Fix formatting of ConsoleMetricExporter.
  ([#3197](https://github.com/open-telemetry/opentelemetry-python/pull/3197))
- Fix use of built-in samplers in SDK configuration
  ([#3176](https://github.com/open-telemetry/opentelemetry-python/pull/3176))
- Implement shutdown procedure forOTLP grpc exporters
  ([#3138](https://github.com/open-telemetry/opentelemetry-python/pull/3138))
- Add exponential histogram
  ([#2964](https://github.com/open-telemetry/opentelemetry-python/pull/2964))
- Add OpenCensus trace bridge/shim
  ([#3210](https://github.com/open-telemetry/opentelemetry-python/pull/3210))

## Version 1.16.0/0.37b0 (2023-02-17)

- Change ``__all__`` to be statically defined.
  ([#3143](https://github.com/open-telemetry/opentelemetry-python/pull/3143))
- Remove the ability to set a global metric prefix for Prometheus exporter
  ([#3137](https://github.com/open-telemetry/opentelemetry-python/pull/3137))
- Adds environment variables for log exporter
  ([#3037](https://github.com/open-telemetry/opentelemetry-python/pull/3037))
- Add attribute name to type warning message.
  ([3124](https://github.com/open-telemetry/opentelemetry-python/pull/3124))
- Add db metric name to semantic conventions
  ([#3115](https://github.com/open-telemetry/opentelemetry-python/pull/3115))
- Fix User-Agent header value for OTLP exporters to conform to RFC7231 & RFC7230
  ([#3128](https://github.com/open-telemetry/opentelemetry-python/pull/3128))
- Fix validation of baggage values
  ([#3058](https://github.com/open-telemetry/opentelemetry-python/pull/3058))
- Fix capitalization of baggage keys
  ([#3151](https://github.com/open-telemetry/opentelemetry-python/pull/3151))
- Bump min required api version for OTLP exporters
  ([#3156](https://github.com/open-telemetry/opentelemetry-python/pull/3156))
- deprecate jaeger exporters
  ([#3158](https://github.com/open-telemetry/opentelemetry-python/pull/3158))
- Create a single resource instance
  ([#3118](https://github.com/open-telemetry/opentelemetry-python/pull/3118))

## Version 1.15.0/0.36b0 (2022-12-09)

- PeriodicExportingMetricsReader with +Inf interval
  to support explicit metric collection
  ([#3059](https://github.com/open-telemetry/opentelemetry-python/pull/3059))
- Regenerate opentelemetry-proto to be compatible with protobuf 3 and 4
  ([#3070](https://github.com/open-telemetry/opentelemetry-python/pull/3070))
- Rename parse_headers to parse_env_headers and improve error message
  ([#2376](https://github.com/open-telemetry/opentelemetry-python/pull/2376))
- Add url decode values from OTEL_RESOURCE_ATTRIBUTES
  ([#3046](https://github.com/open-telemetry/opentelemetry-python/pull/3046))
- Fixed circular dependency issue with custom samplers
  ([#3026](https://github.com/open-telemetry/opentelemetry-python/pull/3026))
- Add missing entry points for OTLP/HTTP exporter
  ([#3027](https://github.com/open-telemetry/opentelemetry-python/pull/3027))
- Update logging to include logging api as per specification
  ([#3038](https://github.com/open-telemetry/opentelemetry-python/pull/3038))
- Fix: Avoid generator in metrics _ViewInstrumentMatch.collect()
  ([#3035](https://github.com/open-telemetry/opentelemetry-python/pull/3035)
- [exporter-otlp-proto-grpc] add user agent string
  ([#3009](https://github.com/open-telemetry/opentelemetry-python/pull/3009))

## Version 1.14.0/0.35b0 (2022-11-04)

- Add logarithm and exponent mappings
  ([#2960](https://github.com/open-telemetry/opentelemetry-python/pull/2960))
- Add and use missing metrics environment variables
  ([#2968](https://github.com/open-telemetry/opentelemetry-python/pull/2968))
- Enabled custom samplers via entry points
  ([#2972](https://github.com/open-telemetry/opentelemetry-python/pull/2972))
- Update log symbol names
  ([#2943](https://github.com/open-telemetry/opentelemetry-python/pull/2943))
- Update explicit histogram bucket boundaries
  ([#2947](https://github.com/open-telemetry/opentelemetry-python/pull/2947))
- `exporter-otlp-proto-http`: add user agent string
  ([#2959](https://github.com/open-telemetry/opentelemetry-python/pull/2959))
- Add http-metric instrument names to semantic conventions
  ([#2976](https://github.com/open-telemetry/opentelemetry-python/pull/2976))
- [exporter/opentelemetry-exporter-otlp-proto-http] Add OTLPMetricExporter
  ([#2891](https://github.com/open-telemetry/opentelemetry-python/pull/2891))
- Add support for py3.11
  ([#2997](https://github.com/open-telemetry/opentelemetry-python/pull/2997))
- Fix a bug with exporter retries for with newer versions of the backoff library
  ([#2980](https://github.com/open-telemetry/opentelemetry-python/pull/2980))

## Version 1.13.0/0.34b0 (2022-09-26)

- Add a configurable max_export_batch_size to the gRPC metrics exporter
  ([#2809](https://github.com/open-telemetry/opentelemetry-python/pull/2809))
- Remove support for 3.6
  ([#2763](https://github.com/open-telemetry/opentelemetry-python/pull/2763))
- Update PeriodicExportingMetricReader to never call export() concurrently
  ([#2873](https://github.com/open-telemetry/opentelemetry-python/pull/2873))
- Add param for `indent` size to `LogRecord.to_json()`
  ([#2870](https://github.com/open-telemetry/opentelemetry-python/pull/2870))
- Fix: Remove `LogEmitter.flush()` to align with OTel Log spec
  ([#2863](https://github.com/open-telemetry/opentelemetry-python/pull/2863))
- Bump minimum required API/SDK version for exporters that support metrics
  ([#2918](https://github.com/open-telemetry/opentelemetry-python/pull/2918))
- Fix metric reader examples + added `preferred_temporality` and `preferred_aggregation`
  for `ConsoleMetricExporter`
  ([#2911](https://github.com/open-telemetry/opentelemetry-python/pull/2911))
- Add support for setting OTLP export protocol with env vars, as defined in the
  [specifications](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/protocol/exporter.md#specify-protocol)
  ([#2893](https://github.com/open-telemetry/opentelemetry-python/pull/2893))
- Add force_flush to span exporters
  ([#2919](https://github.com/open-telemetry/opentelemetry-python/pull/2919))

## Version 1.12.0/0.33b0 (2022-08-08)

- Add `force_flush` method to metrics exporter
  ([#2852](https://github.com/open-telemetry/opentelemetry-python/pull/2852))
- Change tracing to use `Resource.to_json()`
  ([#2784](https://github.com/open-telemetry/opentelemetry-python/pull/2784))
- Fix get_log_emitter instrumenting_module_version args typo
  ([#2830](https://github.com/open-telemetry/opentelemetry-python/pull/2830))
- Fix OTLP gRPC exporter warning message
  ([#2781](https://github.com/open-telemetry/opentelemetry-python/pull/2781))
- Fix tracing decorator with late configuration
  ([#2754](https://github.com/open-telemetry/opentelemetry-python/pull/2754))
- Fix --insecure of CLI argument
  ([#2696](https://github.com/open-telemetry/opentelemetry-python/pull/2696))
- Add temporality and aggregation configuration for metrics exporters,
  use `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` only for OTLP metrics exporter
  ([#2843](https://github.com/open-telemetry/opentelemetry-python/pull/2843))
- Instrument instances are always created through a Meter
  ([#2844](https://github.com/open-telemetry/opentelemetry-python/pull/2844))

## Version 1.12.0rc2/0.32b0 (2022-07-04)

- Fix instrument name and unit regexes
  ([#2796](https://github.com/open-telemetry/opentelemetry-python/pull/2796))
- Add optional sessions parameter to all Exporters leveraging requests.Session
  ([#2783](https://github.com/open-telemetry/opentelemetry-python/pull/2783)
- Add min/max fields to Histogram
  ([#2759](https://github.com/open-telemetry/opentelemetry-python/pull/2759))
- `opentelemetry-exporter-otlp-proto-http` Add support for OTLP/HTTP log exporter
  ([#2462](https://github.com/open-telemetry/opentelemetry-python/pull/2462))
- Fix yield of `None`-valued points
  ([#2745](https://github.com/open-telemetry/opentelemetry-python/pull/2745))
- Add missing `to_json` methods
  ([#2722](https://github.com/open-telemetry/opentelemetry-python/pull/2722)
- Fix type hints for textmap `Getter` and `Setter`
  ([#2657](https://github.com/open-telemetry/opentelemetry-python/pull/2657))
- Fix LogEmitterProvider.force_flush hanging randomly
  ([#2714](https://github.com/open-telemetry/opentelemetry-python/pull/2714))
- narrow protobuf dependencies to exclude protobuf >= 4
  ([#2720](https://github.com/open-telemetry/opentelemetry-python/pull/2720))
- Specify worker thread names
  ([#2724](https://github.com/open-telemetry/opentelemetry-python/pull/2724))
- Loosen dependency on `backoff` for newer Python versions
  ([#2726](https://github.com/open-telemetry/opentelemetry-python/pull/2726))
- fix: frozenset object has no attribute items
  ([#2727](https://github.com/open-telemetry/opentelemetry-python/pull/2727))
- fix: create suppress HTTP instrumentation key in opentelemetry context
  ([#2729](https://github.com/open-telemetry/opentelemetry-python/pull/2729))
- Support logs SDK auto instrumentation enable/disable with env
  ([#2728](https://github.com/open-telemetry/opentelemetry-python/pull/2728))
- fix: update entry point object references for metrics
  ([#2731](https://github.com/open-telemetry/opentelemetry-python/pull/2731))
- Allow set_status to accept the StatusCode and optional description
  ([#2735](https://github.com/open-telemetry/opentelemetry-python/pull/2735))
- Configure auto instrumentation to support metrics
  ([#2705](https://github.com/open-telemetry/opentelemetry-python/pull/2705))
- Add entrypoint for metrics exporter
  ([#2748](https://github.com/open-telemetry/opentelemetry-python/pull/2748))
- Fix Jaeger propagator usage with NonRecordingSpan
  ([#2762](https://github.com/open-telemetry/opentelemetry-python/pull/2762))
- Add `opentelemetry.propagate` module and `opentelemetry.propagators` package
  to the API reference documentation
  ([#2785](https://github.com/open-telemetry/opentelemetry-python/pull/2785))

## Version 1.12.0rc1/0.31b0 (2022-05-17)

- Fix LoggingHandler to handle LogRecord with exc_info=False
  ([#2690](https://github.com/open-telemetry/opentelemetry-python/pull/2690))
- Make metrics components public
  ([#2684](https://github.com/open-telemetry/opentelemetry-python/pull/2684))
- Update to semantic conventions v1.11.0
  ([#2669](https://github.com/open-telemetry/opentelemetry-python/pull/2669))
- Update opentelemetry-proto to v0.17.0
  ([#2668](https://github.com/open-telemetry/opentelemetry-python/pull/2668))
- Add CallbackOptions to observable instrument callback params
  ([#2664](https://github.com/open-telemetry/opentelemetry-python/pull/2664))
- Add timeouts to metric SDK
  ([#2653](https://github.com/open-telemetry/opentelemetry-python/pull/2653))
- Add variadic arguments to metric exporter/reader interfaces
  ([#2654](https://github.com/open-telemetry/opentelemetry-python/pull/2654))
- Added a `opentelemetry.sdk.resources.ProcessResourceDetector` that adds the
  'process.runtime.{name,version,description}' resource attributes when used
  with the `opentelemetry.sdk.resources.get_aggregated_resources` API
  ([#2660](https://github.com/open-telemetry/opentelemetry-python/pull/2660))
- Move Metrics API behind internal package
  ([#2651](https://github.com/open-telemetry/opentelemetry-python/pull/2651))

## Version 1.11.1/0.30b1 (2022-04-21)

- Add parameter to MetricReader constructor to select aggregation per instrument kind
  ([#2638](https://github.com/open-telemetry/opentelemetry-python/pull/2638))
- Add parameter to MetricReader constructor to select temporality per instrument kind
  ([#2637](https://github.com/open-telemetry/opentelemetry-python/pull/2637))
- Fix unhandled callback exceptions on async instruments
  ([#2614](https://github.com/open-telemetry/opentelemetry-python/pull/2614))
- Rename `DefaultCounter`, `DefaultHistogram`, `DefaultObservableCounter`,
  `DefaultObservableGauge`, `DefaultObservableUpDownCounter`, `DefaultUpDownCounter`
  instruments to `NoOpCounter`, `NoOpHistogram`, `NoOpObservableCounter`,
  `NoOpObservableGauge`, `NoOpObservableUpDownCounter`, `NoOpUpDownCounter`
  ([#2616](https://github.com/open-telemetry/opentelemetry-python/pull/2616))
- Deprecate InstrumentationLibraryInfo and Add InstrumentationScope
  ([#2583](https://github.com/open-telemetry/opentelemetry-python/pull/2583))

## Version 1.11.0/0.30b0 (2022-04-18)

- Rename API Measurement for async instruments to Observation
  ([#2617](https://github.com/open-telemetry/opentelemetry-python/pull/2617))
- Add support for zero or more callbacks
  ([#2602](https://github.com/open-telemetry/opentelemetry-python/pull/2602))
- Fix parsing of trace flags when extracting traceparent
  ([#2577](https://github.com/open-telemetry/opentelemetry-python/pull/2577))
- Add default aggregation
  ([#2543](https://github.com/open-telemetry/opentelemetry-python/pull/2543))
- Fix incorrect installation of some exporter “convenience” packages into
  “site-packages/src”
  ([#2525](https://github.com/open-telemetry/opentelemetry-python/pull/2525))
- Capture exception information as part of log attributes
  ([#2531](https://github.com/open-telemetry/opentelemetry-python/pull/2531))
- Change OTLPHandler to LoggingHandler
  ([#2528](https://github.com/open-telemetry/opentelemetry-python/pull/2528))
- Fix delta histogram sum not being reset on collection
  ([#2533](https://github.com/open-telemetry/opentelemetry-python/pull/2533))
- Add InMemoryMetricReader to metrics SDK
  ([#2540](https://github.com/open-telemetry/opentelemetry-python/pull/2540))
- Drop the usage of name field from log model in OTLP
  ([#2565](https://github.com/open-telemetry/opentelemetry-python/pull/2565))
- Update opentelemetry-proto to v0.15.0
  ([#2566](https://github.com/open-telemetry/opentelemetry-python/pull/2566))
- Remove `enable_default_view` option from sdk MeterProvider
  ([#2547](https://github.com/open-telemetry/opentelemetry-python/pull/2547))
- Update otlp-proto-grpc and otlp-proto-http exporters to have more lax requirements for `backoff` lib
  ([#2575](https://github.com/open-telemetry/opentelemetry-python/pull/2575))
- Add min/max to histogram point
  ([#2581](https://github.com/open-telemetry/opentelemetry-python/pull/2581))
- Update opentelemetry-proto to v0.16.0
  ([#2619](https://github.com/open-telemetry/opentelemetry-python/pull/2619))

## Version 1.10.0/0.29b0 (2022-03-10)

- Docs rework: [non-API docs are
  moving](https://github.com/open-telemetry/opentelemetry-python/issues/2172) to
  [opentelemetry.io](https://opentelemetry.io). For details, including a list of
  pages that have moved, see
  [#2453](https://github.com/open-telemetry/opentelemetry-python/pull/2453), and
  [#2498](https://github.com/open-telemetry/opentelemetry-python/pull/2498).
- `opentelemetry-exporter-otlp-proto-grpc` update SDK dependency to ~1.9.
  ([#2442](https://github.com/open-telemetry/opentelemetry-python/pull/2442))
- bugfix(auto-instrumentation): attach OTLPHandler to root logger
  ([#2450](https://github.com/open-telemetry/opentelemetry-python/pull/2450))
- Bump semantic conventions from 1.6.1 to 1.8.0
  ([#2461](https://github.com/open-telemetry/opentelemetry-python/pull/2461))
- fix exception handling in get_aggregated_resources
  ([#2464](https://github.com/open-telemetry/opentelemetry-python/pull/2464))
- Fix `OTEL_EXPORTER_OTLP_ENDPOINT` usage in OTLP HTTP trace exporter
  ([#2493](https://github.com/open-telemetry/opentelemetry-python/pull/2493))
- [exporter/opentelemetry-exporter-prometheus] restore package using the new metrics API
  ([#2321](https://github.com/open-telemetry/opentelemetry-python/pull/2321))

## Version 1.9.1/0.28b1 (2022-01-29)

- Update opentelemetry-proto to v0.12.0. Note that this update removes deprecated status codes.
  ([#2415](https://github.com/open-telemetry/opentelemetry-python/pull/2415))

## Version 1.9.0/0.28b0 (2022-01-26)

- Fix SpanLimits global span limit defaulting when set to 0
  ([#2398](https://github.com/open-telemetry/opentelemetry-python/pull/2398))
- Add Python version support policy
  ([#2397](https://github.com/open-telemetry/opentelemetry-python/pull/2397))
- Decode URL-encoded headers in environment variables
  ([#2312](https://github.com/open-telemetry/opentelemetry-python/pull/2312))
- [exporter/opentelemetry-exporter-otlp-proto-grpc] Add OTLPMetricExporter
  ([#2323](https://github.com/open-telemetry/opentelemetry-python/pull/2323))
- Complete metric exporter format and update OTLP exporter
  ([#2364](https://github.com/open-telemetry/opentelemetry-python/pull/2364))
- [api] Add `NoOpTracer` and `NoOpTracerProvider`. Marking `_DefaultTracer` and `_DefaultTracerProvider` as deprecated.
  ([#2363](https://github.com/open-telemetry/opentelemetry-python/pull/2363))
- [exporter/opentelemetry-exporter-otlp-proto-grpc] Add Sum to OTLPMetricExporter
  ([#2370](https://github.com/open-telemetry/opentelemetry-python/pull/2370))
- [api] Rename `_DefaultMeter` and `_DefaultMeterProvider` to `NoOpMeter` and `NoOpMeterProvider`.
  ([#2383](https://github.com/open-telemetry/opentelemetry-python/pull/2383))
- [exporter/opentelemetry-exporter-otlp-proto-grpc] Add Gauge to OTLPMetricExporter
  ([#2408](https://github.com/open-telemetry/opentelemetry-python/pull/2408))
- [logs] prevent None from causing problems
  ([#2410](https://github.com/open-telemetry/opentelemetry-python/pull/2410))

## Version 1.8.0/0.27b0 (2021-12-17)

- Adds Aggregation and instruments as part of Metrics SDK
  ([#2234](https://github.com/open-telemetry/opentelemetry-python/pull/2234))
- Update visibility of OTEL_METRICS_EXPORTER environment variable
  ([#2303](https://github.com/open-telemetry/opentelemetry-python/pull/2303))
- Adding entrypoints for log emitter provider and console, otlp log exporters
  ([#2253](https://github.com/open-telemetry/opentelemetry-python/pull/2253))
- Rename ConsoleExporter to ConsoleLogExporter
  ([#2307](https://github.com/open-telemetry/opentelemetry-python/pull/2307))
- Adding OTEL_LOGS_EXPORTER environment variable
  ([#2320](https://github.com/open-telemetry/opentelemetry-python/pull/2320))
- Add `setuptools` to `install_requires`
  ([#2334](https://github.com/open-telemetry/opentelemetry-python/pull/2334))
- Add otlp entrypoint for log exporter
  ([#2322](https://github.com/open-telemetry/opentelemetry-python/pull/2322))
- Support insecure configuration for OTLP gRPC exporter
  ([#2350](https://github.com/open-telemetry/opentelemetry-python/pull/2350))

## Version 1.7.1/0.26b1 (2021-11-11)

- Add support for Python 3.10
  ([#2207](https://github.com/open-telemetry/opentelemetry-python/pull/2207))
- remove `X-B3-ParentSpanId` for B3 propagator as per OpenTelemetry specification
  ([#2237](https://github.com/open-telemetry/opentelemetry-python/pull/2237))
- Populate `auto.version` in Resource if using auto-instrumentation
  ([#2243](https://github.com/open-telemetry/opentelemetry-python/pull/2243))
- Return proxy instruments from ProxyMeter
  ([#2169](https://github.com/open-telemetry/opentelemetry-python/pull/2169))
- Make Measurement a concrete class
  ([#2153](https://github.com/open-telemetry/opentelemetry-python/pull/2153))
- Add metrics API
  ([#1887](https://github.com/open-telemetry/opentelemetry-python/pull/1887))
- Make batch processor fork aware and reinit when needed
  ([#2242](https://github.com/open-telemetry/opentelemetry-python/pull/2242))
- `opentelemetry-sdk` Sanitize env var resource attribute pairs
  ([#2256](https://github.com/open-telemetry/opentelemetry-python/pull/2256))
- `opentelemetry-test` start releasing to pypi.org
  ([#2269](https://github.com/open-telemetry/opentelemetry-python/pull/2269))

## Version 1.6.2/0.25b2 (2021-10-19)

- Fix parental trace relationship for opentracing `follows_from` reference
  ([#2180](https://github.com/open-telemetry/opentelemetry-python/pull/2180))

## Version 1.6.1/0.25b1 (2021-10-18)

- Fix ReadableSpan property types attempting to create a mapping from a list
  ([#2215](https://github.com/open-telemetry/opentelemetry-python/pull/2215))
- Upgrade GRPC/protobuf related dependency and regenerate otlp protobufs
  ([#2201](https://github.com/open-telemetry/opentelemetry-python/pull/2201))
- Propagation: only warn about oversized baggage headers when headers exist
  ([#2212](https://github.com/open-telemetry/opentelemetry-python/pull/2212))

## Version 1.6.0/0.25b0 (2021-10-13)

- Fix race in `set_tracer_provider()`
  ([#2182](https://github.com/open-telemetry/opentelemetry-python/pull/2182))
- Automatically load OTEL environment variables as options for `opentelemetry-instrument`
  ([#1969](https://github.com/open-telemetry/opentelemetry-python/pull/1969))
- `opentelemetry-semantic-conventions` Update to semantic conventions v1.6.1
  ([#2077](https://github.com/open-telemetry/opentelemetry-python/pull/2077))
- Do not count invalid attributes for dropped
  ([#2096](https://github.com/open-telemetry/opentelemetry-python/pull/2096))
- Fix propagation bug caused by counting skipped entries
  ([#2071](https://github.com/open-telemetry/opentelemetry-python/pull/2071))
- Add entry point for exporters with default protocol
  ([#2093](https://github.com/open-telemetry/opentelemetry-python/pull/2093))
- Renamed entrypoints `otlp_proto_http_span`, `otlp_proto_grpc_span`, `console_span` to remove
  redundant `_span` suffix.
  ([#2093](https://github.com/open-telemetry/opentelemetry-python/pull/2093))
- Do not skip sequence attribute on decode error
  ([#2097](https://github.com/open-telemetry/opentelemetry-python/pull/2097))
- `opentelemetry-test`: Add `HttpTestBase` to allow tests with actual TCP sockets
  ([#2101](https://github.com/open-telemetry/opentelemetry-python/pull/2101))
- Fix incorrect headers parsing via environment variables
  ([#2103](https://github.com/open-telemetry/opentelemetry-python/pull/2103))
- Add support for OTEL_ATTRIBUTE_COUNT_LIMIT
  ([#2139](https://github.com/open-telemetry/opentelemetry-python/pull/2139))
- Attribute limits no longer apply to Resource attributes
  ([#2138](https://github.com/open-telemetry/opentelemetry-python/pull/2138))
- `opentelemetry-exporter-otlp`: Add `opentelemetry-otlp-proto-http` as dependency
  ([#2147](https://github.com/open-telemetry/opentelemetry-python/pull/2147))
- Fix validity calculation for trace and span IDs
  ([#2145](https://github.com/open-telemetry/opentelemetry-python/pull/2145))
- Add `schema_url` to `TracerProvider.get_tracer`
  ([#2154](https://github.com/open-telemetry/opentelemetry-python/pull/2154))
- Make baggage implementation w3c spec complaint
  ([#2167](https://github.com/open-telemetry/opentelemetry-python/pull/2167))
- Add name to `BatchSpanProcessor` worker thread
  ([#2186](https://github.com/open-telemetry/opentelemetry-python/pull/2186))

## Version 1.5.0/0.24b0 (2021-08-26)

- Add pre and post instrumentation entry points
  ([#1983](https://github.com/open-telemetry/opentelemetry-python/pull/1983))
- Fix documentation on well known exporters and variable OTEL_TRACES_EXPORTER which were misnamed
  ([#2023](https://github.com/open-telemetry/opentelemetry-python/pull/2023))
- `opentelemetry-sdk` `get_aggregated_resource()` returns default resource and service name
  whenever called
  ([#2013](https://github.com/open-telemetry/opentelemetry-python/pull/2013))
- `opentelemetry-distro` & `opentelemetry-sdk` Moved Auto Instrumentation Configurator code to SDK
  to let distros use its default implementation
  ([#1937](https://github.com/open-telemetry/opentelemetry-python/pull/1937))
- Add Trace ID validation to
  meet [TraceID spec](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/overview.md#spancontext) ([#1992](https://github.com/open-telemetry/opentelemetry-python/pull/1992))
- Fixed Python 3.10 incompatibility in `opentelemetry-opentracing-shim` tests
  ([#2018](https://github.com/open-telemetry/opentelemetry-python/pull/2018))
- `opentelemetry-sdk` added support for `OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT`
  ([#2044](https://github.com/open-telemetry/opentelemetry-python/pull/2044))
- `opentelemetry-sdk` Fixed bugs (#2041, #2042 & #2045) in Span Limits
  ([#2044](https://github.com/open-telemetry/opentelemetry-python/pull/2044))
- `opentelemetry-sdk` Add support for `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` env var
  ([#2056](https://github.com/open-telemetry/opentelemetry-python/pull/2056))
- `opentelemetry-sdk` Treat limit even vars set to empty values as unset/unlimited.
  ([#2054](https://github.com/open-telemetry/opentelemetry-python/pull/2054))
- `opentelemetry-api` Attribute keys must be non-empty strings.
  ([#2057](https://github.com/open-telemetry/opentelemetry-python/pull/2057))

## Version 0.23.1 (2021-07-26)

### Changed

- Fix opentelemetry-bootstrap dependency script.
  ([#1987](https://github.com/open-telemetry/opentelemetry-python/pull/1987))

## Version 1.4.0/0.23b0 (2021-07-21)

### Added

- Moved `opentelemetry-instrumentation` to core repository.
  ([#1959](https://github.com/open-telemetry/opentelemetry-python/pull/1959))
- Add support for OTLP Exporter Protobuf over HTTP
  ([#1868](https://github.com/open-telemetry/opentelemetry-python/pull/1868))
- Dropped attributes/events/links count available exposed on ReadableSpans.
  ([#1893](https://github.com/open-telemetry/opentelemetry-python/pull/1893))
- Added dropped count to otlp, jaeger and zipkin exporters.
  ([#1893](https://github.com/open-telemetry/opentelemetry-python/pull/1893))

### Added

- Give OTLPHandler the ability to process attributes
  ([#1952](https://github.com/open-telemetry/opentelemetry-python/pull/1952))
- Add global LogEmitterProvider and convenience function get_log_emitter
  ([#1901](https://github.com/open-telemetry/opentelemetry-python/pull/1901))
- Add OTLPHandler for standard library logging module
  ([#1903](https://github.com/open-telemetry/opentelemetry-python/pull/1903))

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
- `opentelemetry-semantic-conventions` Generate semconv constants update for OTel Spec 1.5.0
  ([#1946](https://github.com/open-telemetry/opentelemetry-python/pull/1946))

### Fixed

- Updated `opentelementry-opentracing-shim` `ScopeShim` to report exceptions in
  opentelemetry specification format, rather than opentracing spec format.
  ([#1878](https://github.com/open-telemetry/opentelemetry-python/pull/1878))

## Version 1.3.0/0.22b0 (2021-06-01)

### Added

- Allow span limits to be set programmatically via TracerProvider.
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

## Version 1.2.0/0.21b0 (2021-05-11)

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

## Version 1.1.0 (2021-04-20)

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

## Version 1.0.0 (2021-03-26)

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

## Version 0.19b0 (2021-03-26)

### Changed

- remove `service_name` from constructor of jaeger and opencensus exporters and
  use of env variable `OTEL_PYTHON_SERVICE_NAME`
  ([#1669])(https://github.com/open-telemetry/opentelemetry-python/pull/1669)
- Rename `IdsGenerator` to `IdGenerator`
  ([#1651](https://github.com/open-telemetry/opentelemetry-python/pull/1651))

### Removed

- Removing support for Python 3.5
  ([#1706](https://github.com/open-telemetry/opentelemetry-python/pull/1706))

## Version 0.18b0 (2021-02-16)

### Added

- Add urllib to opentelemetry-bootstrap target list
  ([#1584](https://github.com/open-telemetry/opentelemetry-python/pull/1584))

## Version 1.0.0rc1 (2021-02-12)

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

## Version 0.17b0 (2021-01-20)

### Added

- Add support for OTLP v0.6.0
  ([#1472](https://github.com/open-telemetry/opentelemetry-python/pull/1472))
- Add protobuf via gRPC exporting support for Jaeger
  ([#1471](https://github.com/open-telemetry/opentelemetry-python/pull/1471))
- Add support for Python 3.9
  ([#1441](https://github.com/open-telemetry/opentelemetry-python/pull/1441))
- Added the ability to disable instrumenting libraries specified by OTEL_PYTHON_DISABLED_INSTRUMENTATIONS env variable,
  when using opentelemetry-instrument command.
  ([#1461](https://github.com/open-telemetry/opentelemetry-python/pull/1461))
- Add `fields` to propagators
  ([#1374](https://github.com/open-telemetry/opentelemetry-python/pull/1374))
- Add local/remote samplers to parent based sampler
  ([#1440](https://github.com/open-telemetry/opentelemetry-python/pull/1440))
- Add support for OTEL*SPAN*{ATTRIBUTE_COUNT_LIMIT,EVENT_COUNT_LIMIT,LINK_COUNT_LIMIT}
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
- `opentelemetry-exporter-jaeger`, `opentelemetry-exporter-zipkin` Update InstrumentationInfo tag keys for Jaeger and
  Zipkin exporters
  ([#1535](https://github.com/open-telemetry/opentelemetry-python/pull/1535))
- `opentelemetry-sdk` Remove rate property setter from TraceIdRatioBasedSampler
  ([#1536](https://github.com/open-telemetry/opentelemetry-python/pull/1536))
- Fix TraceState to adhere to specs
  ([#1502](https://github.com/open-telemetry/opentelemetry-python/pull/1502))
- Update Resource `merge` key conflict precedence
  ([#1544](https://github.com/open-telemetry/opentelemetry-python/pull/1544))

### Removed

- `opentelemetry-api` Remove ThreadLocalRuntimeContext since python3.4 is not supported.

## Version 0.16b1 (2020-11-26)

### Added

- Add meter reference to observers
  ([#1425](https://github.com/open-telemetry/opentelemetry-python/pull/1425))

## Version 0.16b0 (2020-11-25)

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

## Version 0.15b0 (2020-11-02)

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

## Version 0.14b0 (2020-10-13)

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
- Add support for `OTEL_BSP_MAX_QUEUE_SIZE`, `OTEL_BSP_SCHEDULE_DELAY_MILLIS`, `OTEL_BSP_MAX_EXPORT_BATCH_SIZE`
  and `OTEL_BSP_EXPORT_TIMEOUT_MILLIS` environment variables
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
- Parent is now always passed in via Context, instead of Span or SpanContext
  ([#1146](https://github.com/open-telemetry/opentelemetry-python/pull/1146))
- Update OpenTelemetry protos to v0.5.0
  ([#1143](https://github.com/open-telemetry/opentelemetry-python/pull/1143))
- Zipkin exporter now accepts a `max_tag_value_length` attribute to customize the
  maximum allowed size a tag value can have.
  ([#1151](https://github.com/open-telemetry/opentelemetry-python/pull/1151))
- Fixed OTLP events to Zipkin annotations translation.
  ([#1161](https://github.com/open-telemetry/opentelemetry-python/pull/1161))
- Fixed bootstrap command to correctly install opentelemetry-instrumentation-falcon instead of
  opentelemetry-instrumentation-flask.
  ([#1138](https://github.com/open-telemetry/opentelemetry-python/pull/1138))
- Update sampling result names
  ([#1128](https://github.com/open-telemetry/opentelemetry-python/pull/1128))
- Event attributes are now immutable
  ([#1195](https://github.com/open-telemetry/opentelemetry-python/pull/1195))
- Renaming metrics Batcher to Processor
  ([#1203](https://github.com/open-telemetry/opentelemetry-python/pull/1203))
- Protect access to Span implementation
  ([#1188](https://github.com/open-telemetry/opentelemetry-python/pull/1188))
- `start_as_current_span` and `use_span` can now optionally auto-record any exceptions raised inside the context
  manager.
  ([#1162](https://github.com/open-telemetry/opentelemetry-python/pull/1162))

## Version 0.13b0 (2020-09-17)

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

## Version 0.12b0 (2020-08-14)

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
- Add proper length zero padding to hex strings of traceId, spanId, parentId sent on the wire, for compatibility with
  jaeger-collector
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

## Version 0.11b0 (2020-07-28)

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

## Version 0.10b0 (2020-06-23)

### Changed

- Regenerate proto code and add pyi stubs
  ([#823](https://github.com/open-telemetry/opentelemetry-python/pull/823))
- Rename CounterAggregator -> SumAggregator
  ([#816](https://github.com/open-telemetry/opentelemetry-python/pull/816))

## Version 0.9b0 (2020-06-10)

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

## Version 0.8b0 (2020-05-27)

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
- Specify to_json indent from arguments
  ([#718](https://github.com/open-telemetry/opentelemetry-python/pull/718))
- Span.resource will now default to an empty resource
  ([#724](https://github.com/open-telemetry/opentelemetry-python/pull/724))
- bugfix: Fix error message
  ([#729](https://github.com/open-telemetry/opentelemetry-python/pull/729))
- deep copy empty attributes
  ([#714](https://github.com/open-telemetry/opentelemetry-python/pull/714))

## Version 0.7b1 (2020-05-12)

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

## Version 0.6b0 (2020-03-30)

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

## Version 0.5b0 (2020-03-16)

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

## Version 0.4a0 (2020-02-21)

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

## Version 0.3a0 (2019-12-11)

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

## Version 0.2a0 (2019-10-29)

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

## Version 0.1a0 (2019-09-30)

### Added

- Initial release api/sdk

- Use Attribute rather than boundattribute in logrecord
  ([#3567](https://github.com/open-telemetry/opentelemetry-python/pull/3567))
- Fix flush error when no LoggerProvider configured for LoggingHandler
  ([#3608](https://github.com/open-telemetry/opentelemetry-python/pull/3608))
- Fix `OTLPMetricExporter` ignores `preferred_aggregation` property
  ([#3603](https://github.com/open-telemetry/opentelemetry-python/pull/3603))
- Logs: set `observed_timestamp` field
  ([#3565](https://github.com/open-telemetry/opentelemetry-python/pull/3565))
- Add missing Resource SchemaURL in OTLP exporters
  ([#3652](https://github.com/open-telemetry/opentelemetry-python/pull/3652))
- Fix loglevel warning text
  ([#3566](https://github.com/open-telemetry/opentelemetry-python/pull/3566))
- Prometheus Exporter string representation for target_info labels
  ([#3659](https://github.com/open-telemetry/opentelemetry-python/pull/3659))
- Logs: ObservedTimestamp field is missing in console exporter output
  ([#3564](https://github.com/open-telemetry/opentelemetry-python/pull/3564))
- Fix explicit bucket histogram aggregation
  ([#3429](https://github.com/open-telemetry/opentelemetry-python/pull/3429))
- Add `code.lineno`, `code.function` and `code.filepath` to all logs
  ([#3645](https://github.com/open-telemetry/opentelemetry-python/pull/3645))
- Add Synchronous Gauge instrument
  ([#3462](https://github.com/open-telemetry/opentelemetry-python/pull/3462))
- Drop support for 3.7
  ([#3668](https://github.com/open-telemetry/opentelemetry-python/pull/3668))
- Include key in attribute sequence warning
  ([#3639](https://github.com/open-telemetry/opentelemetry-python/pull/3639))
- Upgrade markupsafe, Flask and related dependencies to dev and test
  environments ([#3609](https://github.com/open-telemetry/opentelemetry-python/pull/3609))
- Handle HTTP 2XX responses as successful in OTLP exporters
  ([#3623](https://github.com/open-telemetry/opentelemetry-python/pull/3623))
- Improve Resource Detector timeout messaging
  ([#3645](https://github.com/open-telemetry/opentelemetry-python/pull/3645))
- Add Proxy classes for logging
  ([#3575](https://github.com/open-telemetry/opentelemetry-python/pull/3575))
- Remove dependency on 'backoff' library
  ([#3679](https://github.com/open-telemetry/opentelemetry-python/pull/3679))


- Make create_gauge non-abstract method
  ([#3817](https://github.com/open-telemetry/opentelemetry-python/pull/3817))
- Make `tracer.start_as_current_span()` decorator work with async functions
  ([#3633](https://github.com/open-telemetry/opentelemetry-python/pull/3633))
- Fix python 3.12 deprecation warning
  ([#3751](https://github.com/open-telemetry/opentelemetry-python/pull/3751))
- bump mypy to 0.982
  ([#3776](https://github.com/open-telemetry/opentelemetry-python/pull/3776))
- Add support for OTEL_SDK_DISABLED environment variable
  ([#3648](https://github.com/open-telemetry/opentelemetry-python/pull/3648))
- Fix ValueError message for PeriodicExportingMetricsReader
  ([#3769](https://github.com/open-telemetry/opentelemetry-python/pull/3769))
- Use `BaseException` instead of `Exception` in `record_exception`
  ([#3354](https://github.com/open-telemetry/opentelemetry-python/pull/3354))
- Make span.record_exception more robust
  ([#3778](https://github.com/open-telemetry/opentelemetry-python/pull/3778))
- Fix license field in pyproject.toml files
  ([#3803](https://github.com/open-telemetry/opentelemetry-python/pull/3803))
