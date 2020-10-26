# Changelog

## Unreleased

## Version 0.14b0

Released 2020-10-13

- Fixed boostrap command to correctly install opentelemetry-instrumentation-falcon instead of opentelemetry-instrumentation-flask

## Version 0.13b0

Released 2020-09-17

- Drop support for Python 3.4
  ([#1099](https://github.com/open-telemetry/opentelemetry-python/pull/1099))
- Add support for http metrics
  ([#1116](https://github.com/open-telemetry/opentelemetry-python/pull/1116))

## 0.9b0

Released 2020-06-10

- Rename opentelemetry-auto-instrumentation to opentelemetry-instrumentation,
  and console script `opentelemetry-auto-instrumentation` to `opentelemetry-instrument`

## 0.8b0

Released 2020-05-27

- Add a new bootstrap command that enables automatic instrument installations.
  ([#650](https://github.com/open-telemetry/opentelemetry-python/pull/650))

## 0.7b1

Released 2020-05-12

- Add support for programmatic instrumentation
  ([#579](https://github.com/open-telemetry/opentelemetry-python/pull/569))
- bugfix: enable auto-instrumentation command to work for custom entry points
  (e.g. flask_run)
  ([#567](https://github.com/open-telemetry/opentelemetry-python/pull/567))


## 0.6b0

Released 2020-03-30

- Initial release.
