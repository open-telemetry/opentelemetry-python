# Changelog

## Unreleased

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
