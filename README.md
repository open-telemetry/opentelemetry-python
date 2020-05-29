---
<p align="center">
  <strong>
    <a href="https://opentelemetry-python.readthedocs.io/en/stable/getting-started.html">Getting Started<a/>
    &nbsp;&nbsp;&bull;&nbsp;&nbsp;
    <a href="https://opentelemetry-python.readthedocs.io/">API Documentation<a/>
    &nbsp;&nbsp;&bull;&nbsp;&nbsp;
    <a href="https://gitter.im/open-telemetry/opentelemetry-python">Getting In Touch (Gitter)<a/>
  </strong>
</p>

<p align="center">
  <a href="https://github.com/open-telemetry/opentelemetry-python/releases">
    <img alt="GitHub release (latest by date including pre-releases)" src="https://img.shields.io/github/v/release/open-telemetry/opentelemetry-python?include_prereleases&style=for-the-badge">
  </a>
  <a href="https://codecov.io/gh/open-telemetry/opentelemetry-python/branch/master/">
    <img alt="Codecov Status" src="https://img.shields.io/codecov/c/github/open-telemetry/opentelemetry-python?style=for-the-badge">
  </a>
  <a href="https://github.com/open-telemetry/opentelemetry-python/blob/master/LICENSE">
    <img alt="license" src="https://img.shields.io/badge/license-Apache_2.0-green.svg?style=for-the-badge">
  </a>
  <br/>
  <a href="https://travis-ci.org/open-telemetry/opentelemetry-python">
    <img alt="Build Status" src="https://travis-ci.org/open-telemetry/opentelemetry-python.svg?branch=master">
  </a>
  <img alt="Beta" src="https://img.shields.io/badge/status-beta-informational?logo=data:image/png;base64,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">
</p>

<p align="center">
  <strong>
    <a href="CONTRIBUTING.md">Contributing<a/>
    &nbsp;&nbsp;&bull;&nbsp;&nbsp;
    <a href="https://opentelemetry-python.readthedocs.io/en/stable/#examples">Examples<a/>
  </strong>
</p>

---

## About this project

The Python [OpenTelemetry](https://opentelemetry.io/) client.

## Installation

This repository includes multiple installable packages. The `opentelemetry-api`
package includes abstract classes and no-op implementations that comprise the OpenTelemetry API following
[the
specification](https://github.com/open-telemetry/opentelemetry-specification).
The `opentelemetry-sdk` package is the reference implementation of the API.

Libraries that produce telemetry data should only depend on `opentelemetry-api`,
and defer the choice of the SDK to the application developer. Applications may
depend on `opentelemetry-sdk` or another package that implements the API.

**Please note** that this library is currently in _beta_, and shouldn't
generally be used in production environments.

The API and SDK packages are available on PyPI, and can installed via `pip`:

```sh
pip install opentelemetry-api
pip install opentelemetry-sdk
```

The
[`ext/`](https://github.com/open-telemetry/opentelemetry-python/tree/master/ext)
directory includes OpenTelemetry integration packages, which can be installed
separately as:

```sh
pip install opentelemetry-ext-{integration}
```

To install the development versions of these packages instead, clone or fork
this repo and do an [editable
install](https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs):

```sh
pip install -e ./opentelemetry-api
pip install -e ./opentelemetry-sdk
pip install -e ./ext/opentelemetry-ext-{integration}
```

## Documentation

The online documentation is available at https://opentelemetry-python.readthedocs.io/,
if you want to access the documentation for the latest version use
https://opentelemetry-python.readthedocs.io/en/latest/.

## Compatible Exporters

See the [OpenTelemetry registry](https://opentelemetry.io/registry/?s=python) for a list of exporters available.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

We meet weekly on Thursday, and the time of the meeting alternates between 9AM PT and 4PM PT. The meeting is subject to change depending on contributors' availability. Check the [OpenTelemetry community calendar](https://calendar.google.com/calendar/embed?src=google.com_b79e3e90j7bbsa2n2p5an5lf60%40group.calendar.google.com) for specific dates.

Meetings take place via [Zoom video conference](https://zoom.us/j/6729396170).

Meeting notes are available as a public [Google doc](https://docs.google.com/document/d/1CIMGoIOZ-c3-igzbd6_Pnxx1SjAkjwqoYSUWxPY8XIs/edit). For edit access, get in touch on [Gitter](https://gitter.im/open-telemetry/opentelemetry-python).

Approvers ([@open-telemetry/python-approvers](https://github.com/orgs/open-telemetry/teams/python-approvers)):

- [Carlos Alberto Cortez](https://github.com/carlosalberto), LightStep
- [Chris Kleinknecht](https://github.com/c24t), Google
- [Christian Neumüller](https://github.com/Oberon00), Dynatrace
- [Diego Hurtado](https://github.com/ocelotl)
- [Hector Hernandez](https://github.com/hectorhdzg), Microsoft
- [Leighton Chen](https://github.com/lzchen), Microsoft
- [Mauricio Vásquez](https://github.com/mauriciovasquezbernal), Kinvolk
- [Reiley Yang](https://github.com/reyang), Microsoft

*Find more about the approver role in [community repository](https://github.com/open-telemetry/community/blob/master/community-membership.md#approver).*

Maintainers ([@open-telemetry/python-maintainers](https://github.com/orgs/open-telemetry/teams/python-maintainers)):

- [Alex Boten](https://github.com/codeboten), LightStep
- [Yusuke Tsutsumi](https://github.com/toumorokoshi), Zillow Group

*Find more about the maintainer role in [community repository](https://github.com/open-telemetry/community/blob/master/community-membership.md#maintainer).*

## Release Schedule

OpenTelemetry Python is under active development.

The library is not yet _generally available_, and releases aren't guaranteed to
conform to a specific version of the specification. Future releases will not
attempt to maintain backwards compatibility with previous releases. Each alpha
and beta release includes significant changes to the API and SDK packages,
making them incompatible with each other.

The [v0.1 alpha
release](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.1.0)
includes:

- Tracing API
- Tracing SDK
- Metrics API
- Metrics SDK (Partial)
- W3C Trace Context Propagation
- B3 Context Propagation
- HTTP Integrations

The [v0.2 alpha
release](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.2.0)
includes:

- OpenTracing Bridge
- Jaeger Trace Exporter
- Trace Sampling

The [v0.3 alpha
release](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.3.0)
includes:

- Metrics Instruments and Labels
- Flask Integration
- PyMongo Integration

The [v0.4 alpha
release](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.4.0)
includes:

- Metrics MinMaxSumCount Aggregator
- Context API
- Full Metrics SDK Pipeline
- Metrics STDOUT Exporter
- Dbapi2 Integration
- MySQL Integration
- Psycopg2 Integration
- Zipkin Exporter
- Prometheus Metrics Exporter
- New Examples and Improvements to Existing Examples

The [v0.5 beta
release](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.5.0)
includes:

- W3C Correlation Context Propagation
- OpenTelemetry Collector Exporter Integration for both metrics and traces
- Metrics SDK
- Global configuration module
- Documentation improvements

The [v0.6 beta
release](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v0.6.0)
includes:

- API changes and bugfixes
- An autoinstrumentation package and updated Flask instrumentation
- gRPC integration

See the [project
milestones](https://github.com/open-telemetry/opentelemetry-python/milestones)
for details on upcoming releases. The dates and features described in issues
and milestones are estimates, and subject to change.
