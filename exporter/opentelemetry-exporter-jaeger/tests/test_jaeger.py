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

import unittest

# pylint:disable=no-name-in-module
# pylint:disable=import-error
from opentelemetry.exporter.jaeger import thrift
from opentelemetry.exporter.jaeger.proto import grpc


# pylint:disable=no-member
class TestJaegerExporter(unittest.TestCase):
    def test_constructors(self):
        """Test ensures both exporters can co-exist"""
        try:
            grpc.JaegerExporter()
            thrift.JaegerExporter()
        except Exception as exc:  # pylint: disable=broad-except
            self.assertIsNone(exc)
