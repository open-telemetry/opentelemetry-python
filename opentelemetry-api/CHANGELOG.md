# Changelog

## Unreleased

## Version 0.15b0

Released 2020-11-02

- Updating status codes to adhere to specs ([#1282](https://github.com/open-telemetry/opentelemetry-python/pull/1282))

## Version 0.14b0

Released 2020-10-13

- Add support for `OTEL_PROPAGATORS`
  ([#1123](https://github.com/open-telemetry/opentelemetry-python/pull/1123))
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
- Add keys method to TextMap propagator Getter
  ([#1196](https://github.com/open-telemetry/opentelemetry-python/issues/1196))

## Version 0.13b0

Released 2020-09-17

- Refactor `SpanContext.is_valid` from a method to a data attribute
  ([#1005](https://github.com/open-telemetry/opentelemetry-python/pull/1005))
- Moved samplers from API to SDK
  ([#1023](https://github.com/open-telemetry/opentelemetry-python/pull/1023))
- Change return value type of `correlationcontext.get_correlations` to immutable `MappingProxyType`
  ([#1024](https://github.com/open-telemetry/opentelemetry-python/pull/1024))
- Change is_recording_events to is_recording
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
- Drop support for Python 3.4
  ([#1099](https://github.com/open-telemetry/opentelemetry-python/pull/1099))

## Version 0.12b0

Released 2020-08-14

- Update environment variable names, prefix changed from `OPENTELEMETRY` to `OTEL`
  ([#904](https://github.com/open-telemetry/opentelemetry-python/pull/904))
- Stop TracerProvider and MeterProvider from being overridden
  ([#959](https://github.com/open-telemetry/opentelemetry-python/pull/959))

## Version 0.11b0

- Return INVALID_SPAN if no TracerProvider set for get_current_span
  ([#751](https://github.com/open-telemetry/opentelemetry-python/pull/751))
- Rename record_error to record_exception
  ([#927](https://github.com/open-telemetry/opentelemetry-python/pull/927))

## 0.9b0

Released 2020-06-10

- Move stateful from Meter to MeterProvider
  ([#751](https://github.com/open-telemetry/opentelemetry-python/pull/751))
- Rename Measure to ValueRecorder in metrics
  ([#761](https://github.com/open-telemetry/opentelemetry-python/pull/761))
- Adding trace.get_current_span, Removing Tracer.get_current_span
  ([#552](https://github.com/open-telemetry/opentelemetry-python/pull/552))
- Rename Observer to ValueObserver
  ([#764](https://github.com/open-telemetry/opentelemetry-python/pull/764))
- Add SumObserver and UpDownSumObserver in metrics
  ([#789](https://github.com/open-telemetry/opentelemetry-python/pull/789))
- Log a warning when replacing the global Tracer/Meter provider
  ([#856](https://github.com/open-telemetry/opentelemetry-python/pull/856))

## 0.8b0

Released 2020-05-27

- Handle boolean, integer and float values in Configuration
  ([#662](https://github.com/open-telemetry/opentelemetry-python/pull/662))
- bugfix: ensure status is always string
  ([#640](https://github.com/open-telemetry/opentelemetry-python/pull/640))

## 0.7b1

Released 2020-05-12

- Add reset for the global configuration object, for testing purposes
  ([#636](https://github.com/open-telemetry/opentelemetry-python/pull/636))
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

## 0.6b0

Released 2020-03-30

- Add support for lazy events and links
  ([#474](https://github.com/open-telemetry/opentelemetry-python/pull/474))
- Metrics API no longer uses LabelSet
  ([#527](https://github.com/open-telemetry/opentelemetry-python/pull/527))
- Adding is_remote flag to SpanContext, indicating when a span is remote
  ([#516](https://github.com/open-telemetry/opentelemetry-python/pull/516))
- Allow digit as first char in vendor specific trace state key
  ([#511](https://github.com/open-telemetry/opentelemetry-python/pull/511))

## 0.5b0

Released 2020-03-16

- Adding Correlation Context API and propagator
  ([#471](https://github.com/open-telemetry/opentelemetry-python/pull/471))
- Adding a global configuration module to simplify setting and getting globals
  ([#466](https://github.com/open-telemetry/opentelemetry-python/pull/466))
- Rename metric handle to bound metric instrument
  ([#470](https://github.com/open-telemetry/opentelemetry-python/pull/470))
- Moving resources to sdk
  ([#464](https://github.com/open-telemetry/opentelemetry-python/pull/464))
- Implementing propagators to API to use context
  ([#446](https://github.com/open-telemetry/opentelemetry-python/pull/446))
- Adding named meters, removing batchers
  ([#431](https://github.com/open-telemetry/opentelemetry-python/pull/431))
- Renaming TraceOptions to TraceFlags
  ([#450](https://github.com/open-telemetry/opentelemetry-python/pull/450))
- Renaming TracerSource to TraceProvider
  ([#441](https://github.com/open-telemetry/opentelemetry-python/pull/441))
- Adding attach/detach methods as per spec
  ([#429](https://github.com/open-telemetry/opentelemetry-python/pull/450)

## 0.4a0

Released 2020-02-21

- Separate Default classes from interface descriptions
  ([#311](https://github.com/open-telemetry/opentelemetry-python/pull/311))
- Added named Tracers
  ([#301](https://github.com/open-telemetry/opentelemetry-python/pull/301))
- Add int and valid sequenced to AttributeValue type
  ([#368](https://github.com/open-telemetry/opentelemetry-python/pull/368))
- Add ABC for Metric
  ([#391](https://github.com/open-telemetry/opentelemetry-python/pull/391))
- Metric classes required for export pipeline
  ([#341](https://github.com/open-telemetry/opentelemetry-python/pull/341))
- Adding Context API Implementation
  ([#395](https://github.com/open-telemetry/opentelemetry-python/pull/395))
- Remove monotonic and absolute metric instruments
  ([#410](https://github.com/open-telemetry/opentelemetry-python/pull/410))
- Adding trace.get_tracer function
  ([#430](https://github.com/open-telemetry/opentelemetry-python/pull/430))

## 0.3a0

Released 2019-12-11

- Multiple tracing API changes
- Multiple metrics API changes
- Remove option to create unstarted spans from API
  ([#290](https://github.com/open-telemetry/opentelemetry-python/pull/290))

## 0.2a0

Released 2019-10-29

- W3C TraceContext fixes and compliance tests
  ([#228](https://github.com/open-telemetry/opentelemetry-python/pull/228))
- Multiple metrics API changes
- Multiple tracing API changes
- Multiple context API changes
- Sampler API
  ([#225](https://github.com/open-telemetry/opentelemetry-python/pull/225))
- Multiple bugfixes and improvements

## 0.1a0

Released 2019-09-30

- Initial release
