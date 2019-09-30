# OpenTelemetry Python
[![Gitter chat][gitter-image]][gitter-url]

[gitter-image]: https://badges.gitter.im/open-telemetry/opentelemetry-python.svg
[gitter-url]: https://gitter.im/open-telemetry/opentelemetry-python?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

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

```python
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()
tracer.add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
with tracer.start_span('foo'):
    with tracer.start_span('bar'):
        with tracer.start_span('baz'):
            print(Context)
```

See the [API
documentation](https://open-telemetry.github.io/opentelemetry-python/) for more
detail, and the
[opentelemetry-example-app](./examples/opentelemetry-example-app/README.rst)
for a complete example.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Release Schedule

OpenTelemetry Python is under active development.

The library is not yet _generally available_, and releases aren't guaranteed to
conform to a specific version of the specification.  Future releases will not
attempt to maintain backwards compatibility with current releases.

The _alpha_ release includes:

- Tracing API
- Tracing SDK
- Metrics API
- Metrics SDK
- W3C Context Propagation
- B3 Context Propagation

Future release targets include:

| Component                   | Version | Target Date     |
| --------------------------- | ------- | --------------- |
| Zipkin Trace Exporter       | Beta    | October 14 2019 |
| Jaeger Trace Exporter       | Beta    | October 14 2019 |
| Prometheus Metrics Exporter | Beta    | October 14 2019 |
| OpenTracing Bridge          | Beta    | October 14 2019 |
| OpenCensus Bridge           | Beta    | October 14 2019 |
