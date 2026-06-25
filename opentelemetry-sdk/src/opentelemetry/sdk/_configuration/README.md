# SDK File Configuration

This package implements [OpenTelemetry file-based configuration](https://opentelemetry.io/docs/specs/otel/configuration).

## Files

- `schema.json` — vendored copy of the [OpenTelemetry configuration JSON schema](https://github.com/open-telemetry/opentelemetry-configuration)
- `models.py` — Python dataclasses generated from `schema.json` by [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator), using a custom template from `opentelemetry-sdk/codegen/` (see that directory's README for details)

## Spec conformance

Which fields of the configuration schema the Python SDK actually applies at runtime is tracked in the shared [language support status matrix](https://github.com/open-telemetry/opentelemetry-configuration/blob/main/language-support-status.md#python) in the `opentelemetry-configuration` repository. The Python column is the source of truth; update [`schema/meta_schema_language_python.yaml`](https://github.com/open-telemetry/opentelemetry-configuration/blob/main/schema/meta_schema_language_python.yaml) there when wiring lands or changes, and the matrix regenerates.

## Updating the schema

1. Download the new schema from the [opentelemetry-configuration releases](https://github.com/open-telemetry/opentelemetry-configuration/releases):

   ```sh
   curl -o opentelemetry-sdk/src/opentelemetry/sdk/_configuration/schema.json \
     https://raw.githubusercontent.com/open-telemetry/opentelemetry-configuration/refs/tags/vX.Y.Z/opentelemetry_configuration.json
   ```

2. Regenerate `models.py`:

   ```sh
   tox -e generate-config-from-jsonschema
   ```

3. Update any version string references in tests and source:

   ```sh
   grep -r "OLD_VERSION" opentelemetry-sdk/
   ```
