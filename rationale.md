# OpenTelemetry Rationale

When creating a library, often times designs and decisions are made that get lost over time. This document tries to collect information on design decisions to answer common questions that may come up when you explore the SDK.

## Versioning and Releasing

This document describes the versioning and stability policy of components shipped from this repository, as per the [OpenTelemetry versioning and stability
specification](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/versioning-and-stability.md).

The OpenTelemetry implementations, the OpenTelemetry Spec itself and this repo follows [SemVer V2](https://semver.org/spec/v2.0.0.html) guidelines.
This means that, for any stable packages released from this repo, all public APIs will remain [backward
compatible](https://www.python.org/dev/peps/pep-0387/),
unless a major version bump occurs. This applies to the API, SDK, as well as Exporters, Instrumentation etc. shipped from this repo.

For example, users can take a dependency on 1.0.0 version of any package, with the assurance that all future releases until 2.0.0 will be backward compatible.

## Goals

### API Stability

Once the API for a given signal (spans, logs, metrics, baggage) has been officially released, that API module will function with any SDK that has the same major version, and equal or greater minor or patch version.

For example, libraries that are instrumented with `opentelemetry-api 1.0.1` will function with SDK library `opentelemetry-sdk 1.11.33` or `opentelemetry-sdk 1.3.4`.

### SDK Stability:

Public portions of the SDK (constructors, configuration, end-user interfaces) must remain backwards compatible. Internal interfaces are allowed to break.

## Core components

Core components refer to the set of components which are required as per the spec. This includes API, SDK, propagators (B3 and Jaeger) and exporters which are required by the specification. These exporters are OTLP, Jaeger and Zipkin.

## Mature or stable Signals

Modules for mature (i.e. released) signals will be found in the latest versions of the corresponding packages of the core components. The version numbers of these will have no suffix appended, indicating they are stable. For example, the package `opentelemetry-api` v1.x.y will be considered stable.

## Pre-releases

Pre-release packages are denoted by appending identifiers such as -Alpha, -Beta, -RC etc. There are no API guarantees in pre-releases. Each release can contain breaking changes and functionality could be removed as well. In general, an RC pre-release is more stable than a Beta release, which is more stable than an Alpha release.

### Immature or experimental signals

Modules for experimental signals will be released in the same packages as the core components, but prefixed with `_` to indicate that they are unstable and subject to change. NO STABILITY GUARANTEES ARE MADE.

## Examples

Purely for illustration purposes, not intended to represent actual releases:

#### V1.0.0 Release (tracing, baggage, propagators, context)

- `opentelemetry-api` 1.0.0
  - Contains APIs for tracing, baggage, propagators, context
- `opentelemetry-sdk` 1.0.0
  - Contains SDK components for tracing, baggage, propagators, and context

#### V1.15.0 Release (with metrics)

- `opentelemetry-api` 1.15.0
  - Contains APIs for tracing, baggage, propagators, context, and metrics
- `opentelemetry-sdk` 1.15.0
  - Contains SDK components for tracing, baggage, propagators, context and metrics

##### Contains the following pre-release packages

- `opentelemetry-api` 1.x.yrc1
  - Contains the experimental public API for logging plus other unstable features. There are no stability guarantees.
- `opentelemetry-sdk` 1.x.yrc1
  - Contains the experimental public SDK for logging plus other unstable features. There are no stability guarantees.
