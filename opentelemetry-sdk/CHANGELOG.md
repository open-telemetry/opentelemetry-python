# Changelog

## Unreleased

## Version 0.15b0

Released 2020-11-02

- Make `SpanProcessor.on_start` accept parent Context
  ([#1251](https://github.com/open-telemetry/opentelemetry-python/pull/1251))
- Fix b3 propagator entrypoint
  ([#1265](https://github.com/open-telemetry/opentelemetry-python/pull/1265))
- Allow None in sequence attributes values
  ([#998](https://github.com/open-telemetry/opentelemetry-python/pull/998))
- Samplers to accept parent Context
  ([#1267](https://github.com/open-telemetry/opentelemetry-python/pull/1267))
- Updating status codes to adhere to spec
  ([#1282](https://github.com/open-telemetry/opentelemetry-python/pull/1282))
- Span.is_recording() returns false after span has ended
  ([#1289](https://github.com/open-telemetry/opentelemetry-python/pull/1289))
- Set initial checkpoint timestamp in aggregators
  ([#1237](https://github.com/open-telemetry/opentelemetry-python/pull/1237))
- Remove TracerProvider coupling from Tracer init
  ([#1295](https://github.com/open-telemetry/opentelemetry-python/pull/1295))

## Version 0.14b0

Released 2020-10-13

- Add timestamps to aggregators
  ([#1199](https://github.com/open-telemetry/opentelemetry-python/pull/1199))
- Add Global Error Handler
  ([#1080](https://github.com/open-telemetry/opentelemetry-python/pull/1080))
- Update sampling result names
  ([#1128](https://github.com/open-telemetry/opentelemetry-python/pull/1128))
- Add support for `OTEL_BSP_MAX_QUEUE_SIZE`, `OTEL_BSP_SCHEDULE_DELAY_MILLIS`, `OTEL_BSP_MAX_EXPORT_BATCH_SIZE` and `OTEL_BSP_EXPORT_TIMEOUT_MILLIS` environment variables
  ([#1105](https://github.com/open-telemetry/opentelemetry-python/pull/1120))
- Allow for Custom Trace and Span IDs Generation - `IdsGenerator` for TracerProvider
  ([#1153](https://github.com/open-telemetry/opentelemetry-python/pull/1153))
- Event attributes are now immutable
  ([#1195](https://github.com/open-telemetry/opentelemetry-python/pull/1195))
- Renaming metrics Batcher to Processor
  ([#1203](https://github.com/open-telemetry/opentelemetry-python/pull/1203))
- Protect access to Span implementation
  ([#1188](https://github.com/open-telemetry/opentelemetry-python/pull/1188))
- `start_as_current_span` and `use_span` can now optionally auto-record any exceptions raised inside the context manager.
  ([#1162](https://github.com/open-telemetry/opentelemetry-python/pull/1162))
- Adding Resource to MeterRecord
  ([#1209](https://github.com/open-telemetry/opentelemetry-python/pull/1209))
- Parent is now always passed in via Context, intead of Span or SpanContext
  ([#1146](https://github.com/open-telemetry/opentelemetry-python/pull/1146))
- Add keys method to TextMap propagator Getter
  ([#1196](https://github.com/open-telemetry/opentelemetry-python/issues/1196))

## Version 0.13b0

Released 2020-09-17

- Moved samplers from API to SDK
  ([#1023](https://github.com/open-telemetry/opentelemetry-python/pull/1023))
- Sampling spec changes
  ([#1034](https://github.com/open-telemetry/opentelemetry-python/pull/1034))
- Remove lazy Event and Link API from Span interface
  ([#1045](https://github.com/open-telemetry/opentelemetry-python/pull/1045))
- Improve BatchExportSpanProcessor
  ([#1062](https://github.com/open-telemetry/opentelemetry-python/pull/1062))
- Populate resource attributes as per semantic conventions
  ([#1053](https://github.com/open-telemetry/opentelemetry-python/pull/1053))
- Rename Resource labels to attributes
  ([#1082](https://github.com/open-telemetry/opentelemetry-python/pull/1082))
- Fix api/sdk setup.cfg to include missing python files
  ([#1091](https://github.com/open-telemetry/opentelemetry-python/pull/1091))
- Drop support for Python 3.4
  ([#1099](https://github.com/open-telemetry/opentelemetry-python/pull/1099))
- Rename members of `trace.sampling.Decision` enum
  ([#1115](https://github.com/open-telemetry/opentelemetry-python/pull/1115))
- Merge `OTELResourceDetector` result when creating resources
  ([#1096](https://github.com/open-telemetry/opentelemetry-python/pull/1096))

## Version 0.12b0

Released 2020-08-14

- Changed default Sampler to `ParentOrElse(AlwaysOn)`
  ([#960](https://github.com/open-telemetry/opentelemetry-python/pull/960))
- Update environment variable names, prefix changed from `OPENTELEMETRY` to `OTEL`
  ([#904](https://github.com/open-telemetry/opentelemetry-python/pull/904))
- Implement Views in metrics SDK
  ([#596](https://github.com/open-telemetry/opentelemetry-python/pull/596))
- Update environment variable OTEL_RESOURCE to OTEL_RESOURCE_ATTRIBUTES as per
  the specification

## Version 0.11b0

- Add support for resources and resource detector
  ([#853](https://github.com/open-telemetry/opentelemetry-python/pull/853))
- Rename record_error to record_exception
  ([#927](https://github.com/open-telemetry/opentelemetry-python/pull/927))

## Version 0.10b0

Released 2020-06-23

- Rename CounterAggregator -> SumAggregator
  ([#816](https://github.com/open-telemetry/opentelemetry-python/pull/816))

## 0.9b0

Released 2020-06-10

- Move stateful & resource from Meter to MeterProvider
  ([#751](https://github.com/open-telemetry/opentelemetry-python/pull/751))
- Rename Measure to ValueRecorder in metrics
  ([#761](https://github.com/open-telemetry/opentelemetry-python/pull/761))
- Adding trace.get_current_span, Removing Tracer.get_current_span
  ([#552](https://github.com/open-telemetry/opentelemetry-python/pull/552))
- bugfix: byte type attributes are decoded before adding to attributes dict
  ([#775](https://github.com/open-telemetry/opentelemetry-python/pull/775))
- Rename Observer to ValueObserver
  ([#764](https://github.com/open-telemetry/opentelemetry-python/pull/764))
- Add SumObserver, UpDownSumObserver and LastValueAggregator in metrics
  ([#789](https://github.com/open-telemetry/opentelemetry-python/pull/789))
- Add start_pipeline to MeterProvider
  ([#791](https://github.com/open-telemetry/opentelemetry-python/pull/791))

## 0.8b0

Released 2020-05-27

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

## 0.7b1

Released 2020-05-12

- Exporter API: span parents are now always spancontext
  ([#548](https://github.com/open-telemetry/opentelemetry-python/pull/548))
- tracer.get_tracer now optionally accepts a TracerProvider
  ([#602](https://github.com/open-telemetry/opentelemetry-python/pull/602))
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

## 0.6b0

Released 2020-03-30

- Add support for lazy events and links
  ([#474](https://github.com/open-telemetry/opentelemetry-python/pull/474))
- Metrics API no longer uses LabelSet
  ([#527](https://github.com/open-telemetry/opentelemetry-python/pull/527))
- Adding is_remote flag to SpanContext, indicating when a span is remote
  ([#516](https://github.com/open-telemetry/opentelemetry-python/pull/516))
- Adding a solution to release metric handles and observers
  ([#435](https://github.com/open-telemetry/opentelemetry-python/pull/435))

## 0.5b0

Released 2020-03-16

- Adding Correlation Context SDK and propagator
  ([#471](https://github.com/open-telemetry/opentelemetry-python/pull/471))
- Adding OT Collector metrics exporter
  ([#454](https://github.com/open-telemetry/opentelemetry-python/pull/454))
- Improve validation of attributes
  ([#460](https://github.com/open-telemetry/opentelemetry-python/pull/460))
- Moving resources to sdk
  ([#464](https://github.com/open-telemetry/opentelemetry-python/pull/464))
- Re-raise errors caught in opentelemetry.sdk.trace.Tracer.use_span()
  ([#469](https://github.com/open-telemetry/opentelemetry-python/pull/469))
- Implement observer instrument
  ([#425](https://github.com/open-telemetry/opentelemetry-python/pull/425))

## 0.4a0

Released 2020-02-21

- Added named Tracers
  ([#301](https://github.com/open-telemetry/opentelemetry-python/pull/301))
- Set status for ended spans
  ([#297](https://github.com/open-telemetry/opentelemetry-python/pull/297) and
  [#358](https://github.com/open-telemetry/opentelemetry-python/pull/358))
- Use module loggers
  ([#351](https://github.com/open-telemetry/opentelemetry-python/pull/351))
- Protect start_time and end_time from being set manually by the user
  ([#363](https://github.com/open-telemetry/opentelemetry-python/pull/363))
- Add runtime validation for set_attribute
  ([#348](https://github.com/open-telemetry/opentelemetry-python/pull/348))
- Add support for B3 ParentSpanID
  ([#286](https://github.com/open-telemetry/opentelemetry-python/pull/286))
- Set status in start_as_current_span
  ([#377](https://github.com/open-telemetry/opentelemetry-python/pull/377))
- Implement force_flush for span processors
  ([#389](https://github.com/open-telemetry/opentelemetry-python/pull/389))
- Metrics export pipeline, and stdout exporter
  ([#341](https://github.com/open-telemetry/opentelemetry-python/pull/389))
- Set sampled flag on sampling trace
  ([#407](https://github.com/open-telemetry/opentelemetry-python/pull/407))
- Add io and formatter options to console exporter
  ([#412](https://github.com/open-telemetry/opentelemetry-python/pull/412))
- Clean up ProbabilitySample for 64 bit trace IDs
  ([#238](https://github.com/open-telemetry/opentelemetry-python/pull/238))
- Adding Context API Implementation
  ([#395](https://github.com/open-telemetry/opentelemetry-python/pull/395))
- Remove monotonic and absolute metric instruments
  ([#410](https://github.com/open-telemetry/opentelemetry-python/pull/410))
- Implement MinMaxSumCount aggregator
  ([#422](https://github.com/open-telemetry/opentelemetry-python/pull/422))

## 0.3a0

Released 2019-12-11

- Multiple tracing SDK changes
- Multiple metrics SDK changes
- Add metrics exporters
  ([#192](https://github.com/open-telemetry/opentelemetry-python/pull/192))
- Multiple bugfixes and improvements

## 0.2a0

Released 2019-10-29

- W3C TraceContext fixes and compliance tests
  ([#228](https://github.com/open-telemetry/opentelemetry-python/pull/228))
- Multiple metrics SDK changes
- Multiple tracing SDK changes
- Sampler SDK
  ([#225](https://github.com/open-telemetry/opentelemetry-python/pull/225))
- Multiple bugfixes and improvements

## 0.1a0

Released 2019-09-30

- Initial release
