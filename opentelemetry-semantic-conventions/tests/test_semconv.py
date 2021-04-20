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
# type: ignore

from unittest import TestCase

from pkg_resources import DistributionNotFound, require


class TestSemanticConventions(TestCase):
    def test_semantic_conventions(self):

        try:
            require(["opentelemetry-semantic-conventions"])
        except DistributionNotFound:
            self.fail("opentelemetry-semantic-conventions not installed")
