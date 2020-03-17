# Overview

This example shows how to use auto-instrumentation in OpenTelemetry. This example is also based on a previous example
for OpenTracing that can be found [here](https://github.com/yurishkuro/opentracing-tutorial/tree/master/python).

This example uses 2 scripts whose main difference is they being instrumented manually or not:

1. `publisher_instrumented.py` which has been instrumented manually
2. `publisher_uninstrumented.py` which has not been instrumented manually

The former will be run without the automatic instrumentation agent and the latter with the automatic instrumentation
agent. They should produce an equal result, showing that the automatic instrumentation agent does the equivalent
of what manual instrumentation does.

In order to understand this better, here is the relevant part of both scripts:

## Publisher instrumented manually

`publisher_instrumented.py`

```python
@app.route("/publish_request")
def publish_request():

    with tracer.start_as_current_span(
        "publish_request", propagators.extract(get_as_list, request.headers)
    ):
        hello_str = request.args.get("helloStr")
        print(hello_str)
        return "published"
```

## Publisher not instrumented manually

`publisher_uninstrumented.py`

```python
@app.route("/publish_request")
def publish_request():
    hello_str = request.args.get("helloStr")
    print(hello_str)
    return "published"
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
$ git clone git@github.com:open-telemetry/opentelemetry-python.git
$ cd opentelemetry-python
$ pip3 install -e opentelemetry-api
$ pip3 install -e opentelemetry-sdk
$ pip3 install -e opentelemetry-auto-instrumentation
$ pip3 install -e ext/opentelemetry-ext-flask
$ pip3 install flask
$ pip3 install requests
```

# Execution

## Execution of the manually instrumented publisher

This is done in 3 separate consoles, one to run each of the scripts that make up this example:

```sh
$ source auto_instrumentation/bin/activate
$ python3 opentelemetry-python/opentelemetry-auto-instrumentation/example/formatter.py
```

```sh
$ source auto_instrumentation/bin/activate
$ python3 opentelemetry-python/examples/auto_instrumentation/publisher_instrumented.py
```

```sh
$ source auto_instrumentation/bin/activate
$ python3 opentelemetry-python/examples/auto_instrumentation/hello.py testing
```

The execution of `publisher_instrumented.py` should return an output similar to:

```sh
Hello, testing!
Span(name="publish", context=SpanContext(trace_id=0xd18be4c644d3be57a8623bbdbdbcef76, span_id=0x6162c475bab8d365, trace_state={}), kind=SpanKind.SERVER, parent=SpanContext(trace_id=0xd18be4c644d3be57a8623bbdbdbcef76, span_id=0xdafb264c5b1b6ed0, trace_state={}), start_time=2019-12-19T01:11:12.172866Z, end_time=2019-12-19T01:11:12.173383Z)
127.0.0.1 - - [18/Dec/2019 19:11:12] "GET /publish?helloStr=Hello%2C+testing%21 HTTP/1.1" 200 -
```

## Execution of an automatically instrumented publisher

Now, kill the execution of `publisher_instrumented.py` with `ctrl + c` and run this instead:

```sh
$ opentelemetry-auto-instrumentation opentelemetry-python/examples/auto_instrumentation/publisher_uninstrumented.py
```

In the console where you previously executed `hello.py`, run again this again:

```sh
$ python3 opentelemetry-python/examples/auto_instrumentation/hello.py testing
```

The execution of `publisher_uninstrumented.py` should return an output similar to:

```sh
Hello, testing!
Span(name="publish", context=SpanContext(trace_id=0xd18be4c644d3be57a8623bbdbdbcef76, span_id=0x6162c475bab8d365, trace_state={}), kind=SpanKind.SERVER, parent=SpanContext(trace_id=0xd18be4c644d3be57a8623bbdbdbcef76, span_id=0xdafb264c5b1b6ed0, trace_state={}), start_time=2019-12-19T01:11:12.172866Z, end_time=2019-12-19T01:11:12.173383Z)
127.0.0.1 - - [18/Dec/2019 19:11:12] "GET /publish?helloStr=Hello%2C+testing%21 HTTP/1.1" 200 -
```

As you can see, both outputs are equal since the automatic instrumentation does what the manual instrumentation does too.
