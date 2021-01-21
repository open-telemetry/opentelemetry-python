# OpenTelemetry Rationale

When creating a library, often times designs and decisions are made that get lost over time. This
document tries to collect information on design decisions to answer common questions that may come
up when you explore the SDK.

## Versioning and Releasing

The OpenTelemetry Applications and OpenTelemetry Spec itself use semver v2.

## Goals

### API Stability

Once the API for a given signal (spans, logs, metrics, baggage) has been officially released, that API module will function with any SDK that has the same major version, and equal or greater minor or patch version.

For example, libraries that are instrumented with `opentelemetry-api 1.0.1` will function with SDK library `opentelemetry-sdk 1.11.33` or `opentelemetry-sdk 1.3.4`.

### SDK Stability:

Public portions of the SDK (constructors, configuration, end-user interfaces) must remain backwards compatible.
Internal interfaces are allowed to break.

## Methods

### Mature Signals
API modules for mature (i.e. released) signals will be included in the `opentelemetry-api` module.

### Immature or experimental signals
API modules for experimental signals will not be included in the `opentelemetry-api` module, and must be installed manually. API modules will remain at version v0.x.y to make it abundantly clear that depending on them is at your own risk. For example, the `opentelemetry-metrics-api` v0.x.y module will provide experimental access to the unfinished metrics API. NO STABILITY GUARANTEES ARE MADE.

## Examples

Purely for illustration purposes, not intended to represent actual releases:

#### V1.0.0 Release (tracing, baggage, propagators, context)

- `opentelemetry-api` 1.0.0
  - Contains APIs for tracing, baggage, propagators, context
- `opentelemetry-tracing` 1.0.0
  - Contains the tracing SDK
- `opentelemetry-sdk` 1.0.0
  - Contains SDK components for tracing, baggage, propagators, and context

##### Contains the following experimental packages

- `opentelemetry-api-metrics` 0.x.y
  - Contains the EXPERIMENTAL API for metrics. There are no stability guarantees.
- `opentelemetry-metrics` 0.x.y
  - Contains the EXPERIMENTAL SDK for metrics. There are no stability guarantees.

#### V1.15.0 Release (with metrics)

- `opentelemetry-api` 1.15.0
  - Contains APIs for tracing, baggage, propagators, context, and metrics
- `opentelemetry-tracing` 1.15.0
  - Contains tracing SDK
- `opentelemetry-metrics` 1.15.0
  - Contains metrics SDK
- `opentelemetry-sdk` 1.15.0
  - Contains SDK components for tracing, baggage, propagators, context and metrics
