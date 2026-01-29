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

from opentelemetry.exporter.otlp.json.http import Compression

_DEFAULT_ENDPOINT = "http://localhost:4318"
_DEFAULT_TRACES_EXPORT_PATH = "/v1/traces"
_DEFAULT_TIMEOUT = 10  # in seconds
_DEFAULT_COMPRESSION = Compression.NoCompression
