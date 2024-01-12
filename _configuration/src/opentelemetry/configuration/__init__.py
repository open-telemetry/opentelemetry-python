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

"""
The OpenTelemetry Configuration package is an implementation of the
OpenTelemetry Configuration Specification
"""


from opentelemetry.configuration._internal import (
    resolve_schema,
    validate_configuration,
    process_schema,
    render_schema,
    create_object,
    load_configuration,
    substitute_environment_variables,
)

__all__ = [
    "resolve_schema",
    "validate_configuration",
    "process_schema",
    "render_schema",
    "create_object",
    "load_configuration",
    "substitute_environment_variables",
]
