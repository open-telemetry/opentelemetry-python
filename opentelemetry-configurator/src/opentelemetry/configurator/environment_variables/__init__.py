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

OTEL_PYTHON_CONFIGURATORS = "OTEL_PYTHON_CONFIGURATORS"
"""
.. envvar:: OTEL_PYTHON_CONFIGURATORS

Space-separated string of `opentelemetry-configurator` entry point names.

Example: ``firstconfigurator secondconfigurator``

This environment variable needs to be set only if there is more than one
installed configurator. The configurators will be executed in the order defined
in this environment variable.
"""
