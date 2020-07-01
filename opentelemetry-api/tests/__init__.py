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
import pkg_resources

# naming the tests module as a namespace package ensures that
# relative imports will resolve properly for other test packages,
# as it enables searching for a composite of multiple test modules.
#
# only the opentelemetry-api directory needs this code, as it is
# the first tests module found by pylint during eachdist.py lint
pkg_resources.declare_namespace(__name__)
