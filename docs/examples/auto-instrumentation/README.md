# Overview

This example shows how to use auto-instrumentation in OpenTelemetry. This example is also based on a previous example
for OpenTracing that can be found [here](https://github.com/yurishkuro/opentracing-tutorial/tree/master/python).

This example uses 2 scripts whose main difference is they being instrumented manually or not:

1. `server_instrumented.py` which has been instrumented manually
2. `server_uninstrumented.py` which has not been instrumented manually

The former will be run without the automatic instrumentation agent and the latter with the automatic instrumentation
agent. They should produce the same result, showing that the automatic instrumentation agent does the equivalent
of what manual instrumentation does.

In order to understand this better, here is the relevant part of both scripts:

## Manually instrumented server

`server_instrumented.py`

```python
@app.route("/server_request")
def server_request():
    with tracer.start_as_current_span(
        "server_request",
        parent=propagators.extract(
            lambda dict_, key: dict_.get(key, []), request.headers
        )["current-span"],
    ):
        print(request.args.get("param"))
        return "served"
```

## Publisher not instrumented manually

`server_uninstrumented.py`

```python
@app.route("/server_request")
def server_request():
    print(request.args.get("param"))
    return "served"
```

# Preparation

This example will be executed in a separate virtual environment:

```sh
$ mkdir auto_instrumentation
$ virtualenv auto_instrumentation
$ source auto_instrumentation/bin/activate
```

# Installation

```sh
$ pip install opentelemetry-sdk
$ pip install opentelemetry-auto-instrumentation
$ pip install opentelemetry-ext-flask
$ pip install requests
```

# Execution

## Execution of the manually instrumented server

This is done in 2 separate consoles, one to run each of the scripts that make up this example:

```sh
$ source auto_instrumentation/bin/activate
$ python opentelemetry-python/docs/examples/auto-instrumentation/server_instrumented.py
```

```sh
$ source auto_instrumentation/bin/activate
$ python opentelemetry-python/docs/examples/auto-instrumentation/client.py testing
```

The execution of `server_instrumented.py` should return an output similar to:

```sh
{
    "name": "server_request",
    "context": {
        "trace_id": "0xfa002aad260b5f7110db674a9ddfcd23",
        "span_id": "0x8b8bbaf3ca9c5131",
        "trace_state": "{}"
    },
    "kind": "SpanKind.SERVER",
    "parent_id": null,
    "start_time": "2020-04-30T17:28:57.886397Z",
    "end_time": "2020-04-30T17:28:57.886490Z",
    "status": {
        "canonical_code": "OK"
    },
    "attributes": {
        "component": "http",
        "http.method": "GET",
        "http.server_name": "127.0.0.1",
        "http.scheme": "http",
        "host.port": 8082,
        "http.host": "localhost:8082",
        "http.target": "/server_request?param=testing",
        "net.peer.ip": "127.0.0.1",
        "net.peer.port": 52872,
        "http.flavor": "1.1"
    },
    "events": [],
    "links": []
}
```

## Execution of an automatically instrumented server

Now, kill the execution of `server_instrumented.py` with `ctrl + c` and run this instead:

```sh
$ opentelemetry-auto-instrumentation python docs/examples/auto-instrumentation/server_uninstrumented.py
```

In the console where you previously executed `client.py`, run again this again:

```sh
$ python opentelemetry-python/docs/examples/auto-instrumentation/client.py testing
```

The execution of `server_uninstrumented.py` should return an output similar to:

```sh
{
    "name": "server_request",
    "context": {
        "trace_id": "0x9f528e0b76189f539d9c21b1a7a2fc24",
        "span_id": "0xd79760685cd4c269",
        "trace_state": "{}"
    },
    "kind": "SpanKind.SERVER",
    "parent_id": "0xb4fb7eee22ef78e4",
    "start_time": "2020-04-30T17:10:02.400604Z",
    "end_time": "2020-04-30T17:10:02.401858Z",
    "status": {
        "canonical_code": "OK"
    },
    "attributes": {
        "component": "http",
        "http.method": "GET",
        "http.server_name": "127.0.0.1",
        "http.scheme": "http",
        "host.port": 8082,
        "http.host": "localhost:8082",
        "http.target": "/server_request?param=testing",
        "net.peer.ip": "127.0.0.1",
        "net.peer.port": 48240,
        "http.flavor": "1.1",
        "http.route": "/server_request",
        "http.status_text": "OK",
        "http.status_code": 200
    },
    "events": [],
    "links": []
}
```

Both outputs are equivalent since the automatic instrumentation does what the manual instrumentation does too.
