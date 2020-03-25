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
        "publish_request",
        parent=propagators.extract(get_as_list, request.headers)[
            "current-span"
        ],
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
$ pip install opentelemetry-api
$ pip install opentelemetry-sdk
$ pip install opentelemetry-auto-instrumentation
$ pip install ext/opentelemetry-ext-flask
$ pip install flask
$ pip install requests
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
$ python3 opentelemetry-python/opentelemetry-auto-instrumentation/example/publisher_instrumented.py
```

```sh
$ source auto_instrumentation/bin/activate
$ python3 opentelemetry-python/opentelemetry-auto-instrumentation/example/hello.py testing
```

The execution of `publisher_instrumented.py` should return an output similar to:

```sh
Hello, testing!
Span(name="publish_request", context=SpanContext(trace_id=0x9c0e0ce8f7b7dbb51d1d6e744a4dad49, span_id=0xd1ba3ec4c76a0d7f, trace_state={}), kind=SpanKind.INTERNAL, parent=None, start_time=2020-03-19T00:06:31.275719Z, end_time=2020-03-19T00:06:31.275920Z)
127.0.0.1 - - [18/Mar/2020 18:06:31] "GET /publish_request?helloStr=Hello%2C+testing%21 HTTP/1.1" 200 -
```

## Execution of an automatically instrumented publisher

Now, kill the execution of `publisher_instrumented.py` with `ctrl + c` and run this instead:

```sh
$ opentelemetry-auto-instrumentation opentelemetry-python/opentelemetry-auto-instrumentation/example/publisher_uninstrumented.py
```

In the console where you previously executed `hello.py`, run again this again:

```sh
$ python3 opentelemetry-python/opentelemetry-auto-instrumentation/example/hello.py testing
```

The execution of `publisher_uninstrumented.py` should return an output similar to:

```sh
Hello, testing!
Span(name="publish_request", context=SpanContext(trace_id=0xf26b28b5243e48f5f96bfc753f95f3f0, span_id=0xbeb179a095d087ed, trace_state={}), kind=SpanKind.SERVER, parent=<opentelemetry.trace.DefaultSpan object at 0x7f1a20a54908>, start_time=2020-03-19T00:24:18.828561Z, end_time=2020-03-19T00:24:18.845127Z)
127.0.0.1 - - [18/Mar/2020 18:24:18] "GET /publish_request?helloStr=Hello%2C+testing%21 HTTP/1.1" 200 -
```

As you can see, both outputs are equal since the automatic instrumentation does what the manual instrumentation does too.
