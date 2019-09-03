# OpenTelemetry Python
[![Gitter chat][gitter-image]][gitter-url]

[gitter-image]: https://badges.gitter.im/open-telemetry/opentelemetry-python.svg
[gitter-url]: https://gitter.im/open-telemetry/opentelemetry-python?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

The Python [OpenTelemetry](https://opentelemetry.io/) client.

## Installation

## Usage
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