# OpenTelemetry Rationale

When creating a library, often times designs and decisions are made that get lost over time. This
document tries to collect information on design decisions to answer common questions that may come
up when you explore the SDK.

## Versioning and Releasing

The OTP Applications and OpenTelemetry Spec itself use semver v2.

## Goals

### API Stability

Once the API for a given signal (spans, logs, metrics, baggage) has been officially released, that API module will function with any SDK that has the same major version, and equal or greater minor or patch version.

For example, libraries that are instrumented with `opentelemetry-api 1.0.1` will function with SDK library `opentelemetry-sdk 1.11.33` or `opentelemetry-sdk 1.3.4`.

### SDK Stability:

Public portions of the SDK (constructors, configuration, end-user interfaces) must remain backwards compatible.
Internal interfaces are allowed to break.

## OTP Applications

### Experimental API (`opentelemetry-api-experimental`)

The experimental package is where any API that is not stable when 1.0 is
released must live. At this time (prior to 1.0) that means Metrics and Logging.

This package will always be 0.x because it is never stable and modules will be
removed when they are moved to the stable API package.

### API (`opentelemetry-api`)

The API package is the stable API package that we must provide semver defined
backwards compatibility once a major (1.0) release is made. When an API becomes
stable its modules are moved from `opentelemetry-api-experimental` to
`opentelemetry-api` and a new minor release of both is published.

At the time of 1.0 the following APIs will live in the `opentelemetry-api`
package:

* Tracing
* Baggage
* Context

### Experimental SDK (`opentelemetry-sdk-experimental`)

The experimental SDK contains the implementations for the APIs in the
experimental API of the same version.

This Application is versioned in lockstep with the experimental API and will
never go above 0.x.

### SDK (`opentelemetry-sdk`)

Functionality is implemented in this Application and the API is dynamically
configured to use a particular SDK -- at this time there is only one SDK
implementation, the default implementation.

A goal is that the latest SDK can always be used with any version of the API, so
that a user can always pull the latest implementation into their final Release
to run with any API that was used in instrumented Applications within the
Release.

## Releases

### Experimental API

As noted in the previous section `opentelemetry-api-experimental` is versioned
separately from the rest and will always remain 0.x.

### API

Additions to the API are released with minor version bumps.

### Experimental SDK

As noted in the previous section `opentelemetry-sdk-experimental` is versioned
separately from the rest, but in lockstep with `opentelemetry-api-experimental`,
and will always remain 0.x.

### SDK

Additions to the SDK are released with minor version bumps.

## Removal

A major version bump is required to remove a signal or module.

## Examples

Purely for illustration purposes, not intended to represent actual releases:

- v1.0.0 release:
   - `opentelemetry-api` 1.0.0
     - Contains APIs for tracing, baggage, propagators
   - `opentelemetry-api-experimental` 0.2.0
   - `opentelemetry-sdk` 1.0.0
   - `opentelemetry-sdk-experimental` 0.2.0
- v1.5.0 release (with metrics)
   - `opentelemetry-api` 1.5.0
     - Contains APIs for tracing, baggage, propagators, metrics
   - `opentelemetry-api-experimental` 0.3.0
   - `opentelemetry-sdk` 1.5.0
   - `opentelemetry-sdk-experimental` 0.3.0
- v1.10.0 release (with logging)
   - `opentelemetry-api` 1.10.0
     - Contains APIs for tracing, baggage, propagators, metrics, logging
   - `opentelemetry-sdk` 1.10.0
