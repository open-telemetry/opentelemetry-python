# OpenTelemetry Python
[![Gitter chat](https://img.shields.io/gitter/room/opentelemetry/opentelemetry-python)](https://gitter.im/open-telemetry/opentelemetry-python)
[![Build status](https://travis-ci.org/open-telemetry/opentelemetry-python.svg?branch=master)](https://travis-ci.org/open-telemetry/opentelemetry-python)

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

**Please note** that this library is currently in _alpha_, and shouldn't be
used in production environments.

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

## Quick Start

### Tracing

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerSource
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
trace.tracer_source().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span('foo'):
    with tracer.start_as_current_span('bar'):
        with tracer.start_as_current_span('baz'):
            print("Hello world from OpenTelemetry Python!")
```

### Metrics

```python
from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, Meter
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter

metrics.set_preferred_meter_implementation(lambda T: Meter())
meter = metrics.meter()
exporter = ConsoleMetricsExporter()

counter = meter.create_metric(
    "available memory",
    "available memory",
    "bytes",
    int,
    Counter,
    ("environment",),
)

label_values = ("staging",)
counter_handle = counter.get_handle(label_values)
counter_handle.add(100)

exporter.export([(counter, label_values)])
exporter.shutdown()
```

See the [API documentation](https://open-telemetry.github.io/opentelemetry-python/) for more detail, and the [examples folder](./examples) for a more sample code.

## Extensions

### Third-party exporters

OpenTelemetry supports integration with the following third-party exporters.

-  [Azure Monitor](https://github.com/microsoft/opentelemetry-exporters-python/tree/master/azure_monitor)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

We meet weekly on Thursday at 8AM PT. The meeting is subject to change depending on contributors' availability. Check the [OpenTelemetry community calendar](https://calendar.google.com/calendar/embed?src=google.com_b79e3e90j7bbsa2n2p5an5lf60%40group.calendar.google.com) for specific dates.

Meetings take place via [Zoom video conference](https://zoom.us/j/6729396170).

Meeting notes are available as a public [Google doc](https://docs.google.com/document/d/1CIMGoIOZ-c3-igzbd6_Pnxx1SjAkjwqoYSUWxPY8XIs/edit). For edit access, get in touch on [Gitter](https://gitter.im/open-telemetry/opentelemetry-python).

Approvers ([@open-telemetry/python-approvers](https://github.com/orgs/open-telemetry/teams/python-approvers)):

- [Alex Boten](https://github.com/codeboten), LightStep
- [Carlos Alberto Cortez](https://github.com/carlosalberto), LightStep
- [Christian Neumüller](https://github.com/Oberon00), Dynatrace
- [Hector Hernandez](https://github.com/hectorhdzg), Microsoft
- [Leighton Chen](https://github.com/lzchen), Microsoft
- [Mauricio Vásquez](https://github.com/mauriciovasquezbernal), Kinvolk
- [Reiley Yang](https://github.com/reyang), Microsoft

*Find more about the approver role in [community repository](https://github.com/open-telemetry/community/blob/master/community-membership.md#approver).*

Maintainers ([@open-telemetry/python-maintainers](https://github.com/orgs/open-telemetry/teams/python-maintainers)):

- [Chris Kleinknecht](https://github.com/c24t), Google
- [Yusuke Tsutsumi](https://github.com/toumorokoshi), Zillow Group

*Find more about the maintainer role in [community repository](https://github.com/open-telemetry/community/blob/master/community-membership.md#maintainer).*

## Release Schedule

OpenTelemetry Python is under active development.

The library is not yet _generally available_, and releases aren't guaranteed to
conform to a specific version of the specification. Future releases will not
attempt to maintain backwards compatibility with previous releases. Each alpha
release includes significant changes to the API and SDK packages, making them
incompatible with each other.

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

The v0.4 alpha release includes:

- Metrics MinMaxSumCount Aggregator
- Context API 
- Full Metrics SDK Pipeline 
- Metrics STDOUT Exporter
- Dbapi2 Integration
- MySQL Integration
- Psycopg2 Integration
- Zipkin Exporter
- Added Examples
- Additional and Improved Examples

Thank you to the following individuals for contributing to this release:

* Alex Boten
* Chris Kleinknecht
* Christian Neumüller
* Daniel González
* Diego Hurtado
* Golovin Pavel
* Hector Hernandez
* Jake Malachowski
* Joshua H Lang
* Leighton Chen
* Mauricio Vásquez
* Yusuke Tsutsumi

See the [project
milestones](https://github.com/open-telemetry/opentelemetry-python/milestones)
for details on upcoming releases. The dates and features described here are
estimates, and subject to change.

Future releases targets include:

| Component                           | Version    | Target Date  |
| ----------------------------------- | ---------- | ----         |
| W3C Correlation Context Propagation | Alpha v0.5 | TBD          |
| Support for Tags/Baggage            | Alpha v0.5 | TBD          |
| gRPC Integrations                   | Alpha v0.5 | TBD          |
| Prometheus Metrics Exporter         | Alpha v0.5 | TBD          |
| OpenCensus Bridge                   | Alpha v0.5 | TBD          |
| Metrics SDK (Complete)              | Alpha v0.5 | TBD          |