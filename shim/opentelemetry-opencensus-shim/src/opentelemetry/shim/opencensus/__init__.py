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
The OpenTelemetry OpenCensus shim is a library which allows an easy migration from OpenCensus
to OpenTelemetry. Additional details can be found `in the specification
<https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/compatibility/opencensus.md>`_.

The shim consists of a set of classes which implement the OpenCensus Python API while using
OpenTelemetry constructs behind the scenes. Its purpose is to allow applications which are
already instrumented using OpenCensus to start using OpenTelemetry with minimal effort, without
having to rewrite large portions of the codebase.
"""
