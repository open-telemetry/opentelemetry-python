# Overview

This example shows how to use [OpenTelemetryMiddleware](https://github.com/open-telemetry/opentelemetry-python/tree/master/ext/opentelemetry-ext-wsgi) and [requests](https://github.com/open-telemetry/opentelemetry-python/tree/master/ext/opentelemetry-ext-http-requests) integrations to instrument a client and a server in Python.
It supports exporting spans either to the console or to [Jaeger](https://www.jaegertracing.io).

## Installation

```sh
$ pip install opentelemetry-api opentelemetry-sdk opentelemetry-ext-wsgi opentelemetry-ext-http-requests
```

Setup [Jaeger Tracing](https://www.jaegertracing.io/docs/latest/getting-started/#all-in-one)

## Run the Application

### Console

* Run the server

```bash
$ # from this directory
$ python server.py
```

* Run the client from a different terminal

```bash
$ # from this directory
$ python client.py
```

The output will be displayed at the console on the client side

```bash
Span(name="/", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x3703fd889dcdeb2b, trace_state={}), kind=SpanKind.CLIENT, parent=None, start_time=2019-11-07T21:52:59.591634Z, end_time=2019-11-07T21:53:00.386014Z)
```

And on the server

```bash
127.0.0.1 - - [07/Nov/2019 13:53:00] "GET / HTTP/1.1" 200 -
Span(name="/wiki/Rabbit", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x4bf0be462b91d6ef, trace_state={}), kind=SpanKind.CLIENT, parent=Span(name="parent", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x68338643ccb2d53b, trace_state={})), start_time=2019-11-07T21:52:59.601597Z, end_time=2019-11-07T21:53:00.380491Z)
Span(name="parent", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x68338643ccb2d53b, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="/", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x36050ac596949bc1, trace_state={})), start_time=2019-11-07T21:52:59.601233Z, end_time=2019-11-07T21:53:00.384485Z)
Span(name="/", context=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x36050ac596949bc1, trace_state={}), kind=SpanKind.SERVER, parent=SpanContext(trace_id=0x7c5c0d62031570f00fd106d968139300, span_id=0x3703fd889dcdeb2b, trace_state={}), start_time=2019-11-07T21:52:59.600816Z, end_time=2019-11-07T21:53:00.385322Z)
```

### Jaeger

* Run the server

```sh
$ pip install opentelemetry-ext-jaeger
$ # from this directory
$ EXPORTER=jaeger python server.py
```

* Run the client from a different terminal

```bash
$ EXPORTER=jaeger python client.py
```

#### Jaeger UI

Open the Jaeger UI in your browser [http://localhost:16686](http://localhost:16686)

<p align="center"><img src="images/jaeger-ui.png?raw=true"/></p>
Select `http-server` under *Service Name* and click on *Find Traces*.

Click on the trace to view its details.

<p align="center"><img src="./images/jaeger-ui-detail.png?raw=true"/></p>
## Useful links
- For more information on OpenTelemetry, visit: <https://opentelemetry.io/>
- For more information on tracing in Python, visit: <https://github.com/open-telemetry/opentelemetry-python>

## LICENSE

Apache License 2.0
