# OpenTelemetry Python
[![Gitter chat][gitter-image]][gitter-url]

[gitter-image]: https://badges.gitter.im/open-telemetry/opentelemetry-python.svg
[gitter-url]: https://gitter.im/open-telemetry/opentelemetry-python?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

The Python [OpenTelemetry](https://opentelemetry.io/) client.

## Installation

This repo include multiple installable packages. The `opentelemetry-api`
package includes abstract classes that comprise the OpenTelemetry API following
[the
specification](https://github.com/open-telemetry/opentelemetry-specification).
The `opentelemetry-sdk` package is the reference implementation of the API.

To install the API and SDK packages, fork or clone this repo and do an
[editable
install](https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs)
via `pip`:

```sh
pip install -e ./opentelemetry-api
pip install -e ./opentelemetry-sdk
```

The
[`ext/`](https://github.com/open-telemetry/opentelemetry-python/tree/master/ext)
directory includes OpenTelemetry integration packages, which can be installed
separately as:

```sh
pip install -e ./ext/opentelemetry-ext-{integration}
```

## Development

This project uses [`tox`](https://tox.readthedocs.io) to automate some aspects
of development, including testing against multiple Python versions.

You can run:

- `tox` to run all existing tox commands, including unit tests for all packages
  under multiple Python versions
- `tox -e docs` to regenerate the API docs
- `tox -e test-api` and `tox -e test-sdk` to run the API and SDK unit tests
- `tox -e py37-test-api` to e.g. run the the API unit tests under a specific
  Python version
- `tox -e lint` to run lint checks on all code

See
[`tox.ini`](https://github.com/open-telemetry/opentelemetry-python/blob/master/tox.ini)
for more detail on available tox commands.

## Quick Start

```python
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.trace import Tracer

trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()
with tracer.start_span('foo'):
    print(Context)
    with tracer.start_span('bar'):
        print(Context)
        with tracer.start_span('baz'):
            print(Context)
        print(Context)
    print(Context)
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Release Schedule

OpenTelemetry Python is under active development. Our goal is to release an
_alpha_ version of the library at the end of September 2019. This release isn't
guaranteed to conform to a specific version of the specification, and is likely
to include backwards-incompatible changes in later releases.

| Component                   | Version | Target Date       |
| --------------------------- | ------- | ----------------- |
| Tracing API                 | Alpha   | September 30 2019 |
| Tracing SDK                 | Alpha   | September 30 2019 |
| Metrics API                 | Alpha   | September 30 2019 |
| Metrics SDK                 | Alpha   | September 30 2019 |
| Jaeger Trace Exporter       | Alpha   | Unknown           |
| Prometheus Metrics Exporter | Alpha   | Unknown           |
| Context Propagation         | Alpha   | September 30 2019 |
| OpenTracing Bridge          | Alpha   | Unknown           |
| OpenCensus Bridge           | Alpha   | Unknown           |
