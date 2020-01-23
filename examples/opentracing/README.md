# Overview

This example shows how to use the [`opentelemetry-ext-opentracing-shim`
package](https://github.com/open-telemetry/opentelemetry-python/tree/master/ext/opentelemetry-ext-opentracing-shim)
to interact with libraries instrumented with
[`opentracing-python`](https://github.com/opentracing/opentracing-python).

The included `rediscache` library creates spans via the OpenTracing Redis
integration,
[`redis_opentracing`](https://github.com/opentracing-contrib/python-redis).
Spans are exported via the Jaeger exporter, which is attached to the
OpenTelemetry tracer.

## Installation

### Jaeger

Install and run
[Jaeger](https://www.jaegertracing.io/docs/latest/getting-started/#all-in-one).
See the [basic tracer
example](https://github.com/open-telemetry/opentelemetry-python/tree/master/examples/basic-tracer)
for more detail.

### Redis

Install Redis following the [instructions](https://redis.io/topics/quickstart).

Make sure that the Redis server is running by executing this:

```sh
$ redis-server
```

### Python Dependencies

Install the Python dependencies in [`requirements.txt`](requirements.txt):

```sh
$ pip install -r requirements.txt
```

Alternatively, you can install the Python dependencies separately:

```sh
$ pip install \
  opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-ext-jaeger \
  opentelemetry-opentracing-shim \
  redis \
  redis_opentracing
```

## Run the Application

The example script calculates a few Fibonacci numbers and stores the results in
Redis. The script, the `rediscache` library, and the OpenTracing Redis
integration all contribute spans to the trace.

To run the script:

```sh
$ python main.py
```

After running, you can view the generated trace in the Jaeger UI.

#### Jaeger UI

Open the Jaeger UI in your browser at
[http://localhost:16686](http://localhost:16686) and view traces for the
"OpenTracing Shim Example" service.

Each `main.py` run should generate a trace, and each trace should include
multiple spans that represent calls to Redis.

<p align="center"><img src="./images/jaeger-trace-full.png?raw=true"/></p>

Note that tags and logs (OpenTracing) and attributes and events (OpenTelemetry)
from both tracing systems appear in the exported trace.

<p align="center"><img src="./images/jaeger-span-expanded.png?raw=true"/></p>

## Useful links
- For more information on OpenTelemetry, visit: <https://opentelemetry.io/>
- For more information on tracing in Python, visit: <https://github.com/open-telemetry/opentelemetry-python>

## LICENSE

Apache License 2.0
