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

## Quick Start

### Tracing

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

See the [API
documentation](https://open-telemetry.github.io/opentelemetry-python/) for more
detail, and the
[opentelemetry-example-app](./examples/opentelemetry-example-app/README.rst)
for a complete example.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Release Schedule

OpenTelemetry Python is under active development. Our goal is to release an
_alpha_ version of the library at the end of September 2019. This release isn't
guaranteed to conform to a specific version of the specification, and future
releases will not attempt to maintain backwards compatibility with the alpha
release.

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
