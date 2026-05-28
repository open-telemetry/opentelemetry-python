# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

FROM python:3.14-slim

WORKDIR /app

# Copy the project definition first so pip can install dependencies.
# Layering this before the source copy lets Docker cache the dependency
# layer when only application code changes.
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application source and configuration after dependencies are installed.
COPY otel-config.yaml .
COPY app/ app/
COPY library/ library/

EXPOSE 8080

# Key environment variables (override with -e / --env):
#   OTEL_EXPORTER_OTLP_ENDPOINT   — OTLP HTTP endpoint (default: http://localhost:4318)
#   OTEL_RESOURCE_ATTRIBUTES      — extra resource attributes, e.g. deployment.environment=prod
#   APPLICATION_PORT              — listening port (default: 8080)
CMD ["python", "-m", "app.main"]
