# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
