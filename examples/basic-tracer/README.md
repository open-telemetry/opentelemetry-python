# Overview

This example shows how to use OpenTelemetry to instrument a Python application - e.g. a batch job.
It supports exporting spans either to the console or to [Jaeger](https://www.jaegertracing.io).

## Installation

```sh
$ pip install opentelemetry-api opentelemetry-sdk
```

Setup [Jaeger Tracing](https://www.jaegertracing.io/docs/latest/getting-started/#all-in-one)

## Run the Application

### Console

* Run the sample

```bash
$ # from this director
$ python tracer.py
```

The output will be displayed at the console

```bash
AsyncRuntimeContext({'current_span': Span(name="baz", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x5611c1407e06e4d7, trace_state={}))})
Span(name="baz", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x5611c1407e06e4d7, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="bar", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1b9db0e0cc1a3f60, trace_state={})), start_time=2019-11-07T21:26:45.934412Z, end_time=2019-11-07T21:26:45.934567Z)
Span(name="bar", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1b9db0e0cc1a3f60, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="foo", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1d5d87441ec2f410, trace_state={})), start_time=2019-11-07T21:26:45.934396Z, end_time=2019-11-07T21:26:45.934576Z)
Span(name="foo", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1d5d87441ec2f410, trace_state={}), kind=SpanKind.INTERNAL, parent=None, start_time=2019-11-07T21:26:45.934369Z, end_time=2019-11-07T21:26:45.934580Z)
```



### Jaeger

 - Run the sample

   ```sh
   $ pip install opentelemetry-ext-jaeger
   $ # from this directory
   $ EXPORTER=jaeger python tracer.py
   ```

#### Jaeger UI

Open the Jaeger UI in your browser [http://localhost:16686](http://localhost:16686)

<p align="center"><img src="images/jaeger-ui.png?raw=true"/></p>

Select `basic-service` under *Service Name* and click on *Find Traces*.

Click on the trace to view its details.

<p align="center"><img src="./images/jaeger-ui-detail.png?raw=true"/></p>
## Useful links
- For more information on OpenTelemetry, visit: <https://opentelemetry.io/>
- For more information on tracing in Python, visit: <https://github.com/open-telemetry/opentelemetry-python>

## LICENSE

Apache License 2.0
