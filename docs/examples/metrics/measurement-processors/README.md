# OpenTelemetry Python - MeasurementProcessor Implementation

This implementation adds support for **MeasurementProcessor** to the OpenTelemetry Python SDK, following the [OpenTelemetry Specification PR #4318](https://github.com/open-telemetry/opentelemetry-specification/pull/4318).

## Overview

The MeasurementProcessor allows you to process measurements before they are aggregated and exported. This enables powerful use cases such as:

- **Dynamic injection of additional attributes** to measurements based on Context (e.g., from Baggage)
- **Dropping attributes** (e.g., removing sensitive information)
- **Dropping individual measurements** (e.g., filtering invalid values)
- **Modifying measurements** (e.g., unit conversion, value transformation)

## Key Features

### Chain-of-Responsibility Pattern

Unlike existing processors in OpenTelemetry (SpanProcessor, LogRecordProcessor), MeasurementProcessor uses a **chain-of-responsibility pattern** where each processor is responsible for calling the next processor in the chain. This gives processors fine-grained control over the processing flow.

### High Performance

The implementation is designed for high-performance scenarios:

- Minimal overhead when no processors are configured
- Efficient processor chaining using closures
- No unnecessary object creation in the hot path

## Architecture

```
Measurement → Processor 1 → Processor 2 → ... → Processor N → Aggregation
```

Each processor can:

1. **Pass through unchanged**: `next_processor(measurement)`
2. **Modify and pass**: `next_processor(modified_measurement)`
3. **Drop measurement**: Simply don't call `next_processor`
4. **Split into multiple**: Call `next_processor` multiple times

## Usage

### Basic Setup

```python
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.measurement_processor import (
    BaggageMeasurementProcessor,
    StaticAttributeMeasurementProcessor,
    ValueRangeMeasurementProcessor,
)

# Create measurement processors
processors = [
    BaggageMeasurementProcessor(),  # Add baggage as attributes
    StaticAttributeMeasurementProcessor({"env": "prod"}),  # Add static attributes
    ValueRangeMeasurementProcessor(min_value=0),  # Drop negative values
]

# Configure MeterProvider with processors
meter_provider = MeterProvider(
    measurement_processors=processors,
    # ... other configuration
)
```

### Built-in Processors

#### 1. BaggageMeasurementProcessor

Extracts values from OpenTelemetry Baggage and adds them as measurement attributes, enabling end-to-end telemetry correlation.

```python
# Add all baggage as attributes with "baggage." prefix
processor = BaggageMeasurementProcessor()

# Add only specific baggage keys
processor = BaggageMeasurementProcessor(baggage_keys=["user.id", "trace.id"])
```

#### 2. AttributeFilterMeasurementProcessor

Removes specific attributes from measurements (useful for removing sensitive data).

```python
processor = AttributeFilterMeasurementProcessor([
    "password", "secret", "auth_token"
])
```

#### 3. StaticAttributeMeasurementProcessor

Adds static attributes to all measurements.

```python
processor = StaticAttributeMeasurementProcessor({
    "environment": "production",
    "service": "api-server",
    "version": "1.0.0"
})
```

### Custom Processors

Create custom processors by implementing the `MeasurementProcessor` interface:

```python
from opentelemetry.sdk.metrics._internal.measurement_processor import MeasurementProcessor
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from dataclasses import replace
from typing import Callable

class CustomMeasurementProcessor(MeasurementProcessor):
    def process(
        self,
        measurement: Measurement,
        next_processor: Callable[[Measurement], None]
    ) -> None:
        # Example: Add timestamp attribute
        new_attributes = dict(measurement.attributes or {})
        new_attributes["processed_at"] = str(int(time.time()))

        modified_measurement = replace(measurement, attributes=new_attributes)
        next_processor(modified_measurement)

# Unit conversion processor
class MetersToFeetProcessor(MeasurementProcessor):
    def process(self, measurement: Measurement, next_processor: Callable[[Measurement], None]) -> None:
        if measurement.instrument.name.endswith("_meters"):
            # Convert meters to feet
            feet_value = measurement.value * 3.28084
            new_measurement = replace(measurement, value=feet_value)
            next_processor(new_measurement)
        else:
            next_processor(measurement)
```

## Integration with Existing Metrics SDK

The MeasurementProcessor integrates seamlessly with the existing metrics SDK:

1. **SdkConfiguration** - Extended to include `measurement_processor_chain`
2. **MeasurementConsumer** - Modified to process measurements through the processor chain
3. **MeterProvider** - Extended constructor to accept `measurement_processors` parameter

### Configuration Flow

```
MeterProvider(measurement_processors=[...])
    ↓
SdkConfiguration(measurement_processor_chain=...)
    ↓
SynchronousMeasurementConsumer(sdk_config)
    ↓
MeasurementProcessorChain.process(measurement, final_consumer)
```

## Advanced Examples

### Baggage-based Attribute Injection

```python
from opentelemetry import baggage
from opentelemetry.context import attach, detach

# Set baggage in context
ctx = baggage.set_baggage("user.id", "12345")
ctx = baggage.set_baggage("tenant.id", "acme-corp", context=ctx)
token = attach(ctx)

try:
    # This measurement will automatically get baggage.user.id and baggage.tenant.id attributes
    counter.add(1, {"operation": "login"})
finally:
    detach(token)
```

### Complex Processing Chain

```python
processors = [
    # 1. Add baggage for correlation
    BaggageMeasurementProcessor(baggage_keys=["user.id", "trace.id"]),

    # 2. Add environment info
    StaticAttributeMeasurementProcessor({
        "environment": "production",
        "datacenter": "us-west-2"
    }),

    # 3. Remove sensitive attributes
    AttributeFilterMeasurementProcessor(["password", "secret", "token"]),

    # 4. Custom processing
    CustomTimestampProcessor(),
]
```

### Error Handling

Processors should handle errors gracefully to avoid breaking the metrics pipeline:

```python
class SafeProcessor(MeasurementProcessor):
    def process(self, measurement: Measurement, next_processor: Callable[[Measurement], None]) -> None:
        try:
            # Custom processing logic
            processed_measurement = self.transform(measurement)
            next_processor(processed_measurement)
        except Exception as e:
            # Log error but don't break the pipeline
            logger.warning(f"Processor error: {e}")
            # Pass through original measurement
            next_processor(measurement)
```

---

**Note**: This implementation is experimental and the API may change based on community feedback and the final OpenTelemetry specification.
