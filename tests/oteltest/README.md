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

The `oteltest` package contains utilities for testing OpenTelemetry Python scenarios.

### oteltest

The `oteltest` command runs black box tests against Python scripts that send telemetry.

#### Execution

With the virtual environment (into which you've installed `oteltest`) active, run `oteltest` as a shell command and
provide a directory as an argument:

```shell
oteltest my_script_dir
```

This will attempt to run all [oteltest-eligible](#script-eligibility) scripts in `my_script_dir`, non-recursively.

#### Operation

Running `oteltest` against a directory containing only `my_script.py`

1) Starts an OTLP listener ([otelsink](#otelsink))
2) Creates a new Python virtual environment with `requirements()`
3) In that environment, starts running `my_script.py` in a subprocess
4) Calls `OtelTest#on_start()`
5) Depending on the return value from `on_start()`, waits for `my_script.py` to complete
6) Stops otelsink
7) Calls `on_stop()` with otelsink's received telemetry and script output
8) Writes the telemetry to a `.json` file next to the script (script name but with ".{number}.json" instead of ".py")

#### Script Eligibility

For a Python script to be runnable by `oteltest`, it must both be executable and define an implementation of the
[OtelTest](src/oteltest/__init__.py) abstract base class. The script below has an implementation called `MyOtelTest`:

```python
import time

from opentelemetry import trace
from oteltest import OtelTest, Telemetry

SERVICE_NAME = "my-otel-test"
NUM_ADDS = 12

if __name__ == "__main__":
    tracer = trace.get_tracer("my-tracer")
    for i in range(NUM_ADDS):
        with tracer.start_as_current_span("my-span"):
            print(f"simple_loop.py: {i+1}/{NUM_ADDS}")
            time.sleep(0.5)


class MyOtelTest(OtelTest):
    def requirements(self):
        return "opentelemetry-distro", "opentelemetry-exporter-otlp-proto-grpc"

    def environment_variables(self):
        return {"OTEL_SERVICE_NAME": SERVICE_NAME}

    def wrapper_command(self):
        return "opentelemetry-instrument"

    def on_start(self):
        return None

    def on_stop(self, telemetry: Telemetry, stdout: str, stderr: str, returncode: int) -> None:
        assert telemetry.num_spans() == NUM_ADDS
```

Here's a client-server example:

```python
import time
from typing import Mapping, Optional, Sequence

from flask import Flask, jsonify

from oteltest import OtelTest, Telemetry

PORT = 8002
HOST = "127.0.0.1"


app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"library": "flask"})


if __name__ == "__main__":
    app.run(port=PORT, host=HOST)


class FlaskTest(OtelTest):
    def environment_variables(self) -> Mapping[str, str]:
        return {}

    def requirements(self) -> Sequence[str]:
        return (
            "opentelemetry-distro",
            "opentelemetry-exporter-otlp-proto-grpc",
            "opentelemetry-instrumentation-flask",
            "flask==2.3.3",
            "jsonify",
        )

    def wrapper_command(self) -> str:
        return "opentelemetry-instrument"

    def on_start(self) -> Optional[float]:
        import http.client

        # Todo: replace this sleep with a liveness check!
        time.sleep(10)

        conn = http.client.HTTPConnection(HOST, PORT)
        conn.request("GET", "/")
        print("response:", conn.getresponse().read().decode())
        conn.close()

        # The return value of on_script_start() tells oteltest the number of seconds to wait for the script to complete.
        # In this case, we indicate 30 (seconds), which, once elapsed, will cause the script to be terminated, if it's
        # still running. If we return `None` then the script will run indefinitely.
        return 30

    def on_stop(self, telemetry: Telemetry, stdout: str, stderr: str, returncode: int) -> None:
        print(f"on_stop: telemetry: {telemetry}")

```

### otelsink

`otelsink` is a gRPC server that listens for OTel metrics, traces, and logs.

#### Operation

You can run otelsink either from the command line by using the `otelsink` command (installed when you
`pip install oteltest`), or programmatically.

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
