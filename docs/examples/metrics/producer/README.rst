# MetricProducer Examples

This directory contains examples of how to implement and use the `MetricProducer` interface to bridge third-party metric sources with OpenTelemetry.

## What is MetricProducer?

`MetricProducer` is an interface defined in the OpenTelemetry specification that allows you to plug third-party metric sources into an OpenTelemetry `MetricReader`. This is particularly useful for:

- Bridging existing monitoring systems to OpenTelemetry
- Integrating with systems like Prometheus, StatsD, or custom monitoring solutions
- Collecting pre-processed metrics from external sources

## Key Concepts

- **MetricProducer**: Interface that defines how to produce metrics from third-party sources
- **MetricReader**: Collects metrics from both the OpenTelemetry SDK and registered MetricProducers
- **Pre-processed data**: Unlike OpenTelemetry instruments that collect raw measurements, MetricProducers work with already aggregated metrics

## Examples

### basic_example.py

A comprehensive example showing:
- How to implement `MetricProducer` for different systems (Prometheus simulation, custom system)
- How to convert third-party metric formats to OpenTelemetry `MetricsData`
- How to register producers with a `MetricReader`
- How both SDK metrics and producer metrics are combined

## Running the Examples

```bash
# From the repo root
cd docs/examples/metrics/producer
python basic_example.py
```

## Implementation Pattern

When implementing a `MetricProducer`:

1. **Inherit from MetricProducer**: Create a class that extends the abstract base class
2. **Implement produce()**: This method should fetch and convert metrics to OpenTelemetry format
3. **Handle errors gracefully**: Your producer should not crash the entire collection process
4. **Respect timeout**: The `produce()` method receives a timeout parameter
5. **Return MetricsData**: Convert your metrics to the standard OpenTelemetry format

```python
from opentelemetry.sdk.metrics.export import MetricProducer, MetricsData

class MyMetricProducer(MetricProducer):
    def produce(self, timeout_millis: float = 10_000) -> MetricsData:
        # Fetch metrics from your source
        raw_metrics = self.fetch_from_source()
        
        # Convert to OpenTelemetry format
        otel_metrics = self.convert_to_otel_format(raw_metrics)
        
        # Return as MetricsData
        return MetricsData(resource_metrics=otel_metrics)
```

## Best Practices

1. **Resource Identification**: Use appropriate resource attributes to identify the source system
2. **Instrumentation Scope**: Create meaningful instrumentation scopes for your producers
3. **Metric Naming**: Use clear, descriptive metric names, optionally with prefixes
4. **Error Handling**: Handle network errors, parsing errors, and timeouts gracefully
5. **Performance**: Consider caching and efficient data fetching to avoid impacting collection performance
6. **Thread Safety**: Ensure your producer is thread-safe as it may be called concurrently

## Integration with MetricReader

```python
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

# Create your producers
producer1 = MyCustomProducer()
producer2 = PrometheusProducer()

# Create a reader with producers
reader = PeriodicExportingMetricReader(
    exporter=ConsoleMetricExporter(),
    metric_producers=[producer1, producer2]
)

# The reader will automatically collect from both SDK and producers
```

## Relationship to OpenTelemetry Instruments

MetricProducer is different from OpenTelemetry instruments:

- **Instruments** (Counter, Histogram, etc.): Collect raw measurements and aggregate them in the SDK
- **MetricProducer**: Provides already-aggregated metrics from external sources

Use MetricProducer when you have an existing system that already aggregates metrics and you want to bridge that data into OpenTelemetry.

## Further Reading

- [OpenTelemetry Metrics Specification](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#metricproducer)
- [OpenTelemetry Python SDK Documentation](https://opentelemetry-python.readthedocs.io/)