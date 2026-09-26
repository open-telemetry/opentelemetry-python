# OpenTelemetry Semantic Conventions

The modules in this package are generated from the
[OpenTelemetry Semantic Conventions](https://github.com/open-telemetry/semantic-conventions)
registry using [weaver](https://github.com/open-telemetry/weaver). Do **NOT** modify the
generated files by hand.

## Updating to a new semantic conventions release

1. In `scripts/semconv/generate.sh`, set `SEMCONV_VERSION` to the new release
   (and bump `OTEL_WEAVER_IMG_VERSION` if needed).
2. Add the new schema URL to `Schemas` in
   `src/opentelemetry/semconv/schemas.py`. The script fails if it is missing.
3. Run `scripts/semconv/generate.sh` (requires Docker).
4. **Update the "Supported Semantic Conventions Version" section of
   [`README.rst`](README.rst) to the new `SEMCONV_VERSION`**, including the
   link to the upstream tag. The README must always state the semantic
   conventions version this package is generated from.
5. Review the diff against the compatibility rules below, then commit.

## Compatibility rules

This package is on the stable 1.x release line. The stable modules
(`opentelemetry.semconv.attributes`, `opentelemetry.semconv.metrics` and
`opentelemetry.semconv.schemas`) are public API and **MUST** stay backwards
compatible.
