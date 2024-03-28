# oteltest

[![PyPI - Version](https://img.shields.io/pypi/v/oteltest.svg)](https://pypi.org/project/oteltest)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/oteltest.svg)](https://pypi.org/project/oteltest)

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install oteltest
```

## Overview

The `oteltest` package contains utilities for testing OpenTelemetry Python.

### oteltest

`oteltest` is a CLI command which you can use to run black box tests against OpenTelemetry Python scripts.

#### Execution

You can run `oteltest` as a shell command and provide as an argument either a file:

```shell
oteltest my_script.py
```

or a directory:

```shell
oteltest my_script_dir
```

Given a directory, the `oteltest` command will attempt to run all `oteltest`-runnable scripts in `my_script_dir`,
non-recursively.

#### Operation

Running `oteltest` against `my_script.py` 1) starts a Python OTLP listener, 2) creates a new Python virtual
environment, 3) installs any `requirements()`, 4) starts a subprocess with any requested `wrapper_script()`
and `environment_variables()`, 5) waits for `my_script.py` to complete, 6) stops the OTLP listener, and finally 7) sends
the listener's telemetry received back to `my_script.py` in the form of a call to `validate(telemetry)`. It also writes
a `.json` file with that telemetry next to the script (with the same name but `.json` extension).

#### Scripts

For a Python script to be runnable by `oteltest`, it must both be executable and define an implementation of
`OtelTest`. The script below has an implementation called `MyTest`:

```python
import time
from opentelemetry import trace
from oteltest.common import OtelTest, Telemetry

SERVICE_NAME = "my-test"
NUM_ADDS = 12

if __name__ == "__main__":
    tracer = trace.get_tracer("my-tracer")
    for i in range(NUM_ADDS):
        with tracer.start_as_current_span("my-span"):
            print(f"{i + 1}/{NUM_ADDS}")
            time.sleep(0.5)


class MyTest(OtelTest):
    def requirements(self):
        return "opentelemetry-distro", "opentelemetry-exporter-otlp-proto-grpc"

    def wrapper_script(self):
        return "opentelemetry-instrument"

    def environment_variables(self):
        return {"OTEL_SERVICE_NAME": SERVICE_NAME}

    def validate(self, telemetry: Telemetry):
        assert telemetry.num_spans() == NUM_ADDS
```

#### Usage with OTel Examples

Runnable examples are a great way for new users to get up to speed, but it would be nice to give them an opportunity
to see the telemetry they just generated. Adding an `OtelTest` implementation (e.g. `MyTest` above) to existing
example scripts lets users run examples without having to set up Python environments with dependencies. It also lets
them potentially see the output of their instrumented script.

### otelsink

`otelsink` is a gRPC server that listens for OTel metrics, traces, and logs.

#### Operation

You can run it either from the command line by using the `otelsink` command (installed when you
`pip install oteltest`), or programatically.

Either way, `otelsink` runs a gRPC server listening on 0.0.0.0:4317.

#### Command Line

```
% otelsink
starting otelsink with print handler
```

#### Programmatic

```
from oteltest.sink import GrpcSink, PrintHandler

class MyHandler(RequestHandler):
    def handle_logs(self, request, context):
        print(f"received log request: {request}")

    def handle_metrics(self, request, context):
        print(f"received metrics request: {request}")

    def handle_trace(self, request, context):
        print(f"received trace request: {request}")


sink = GrpcSink(MyHandler())
sink.start()
sink.wait_for_termination()
```

## License

`oteltest` is distributed under the terms of the [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) license.
