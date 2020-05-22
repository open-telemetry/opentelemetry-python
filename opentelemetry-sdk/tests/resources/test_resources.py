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

# pylint: disable=protected-access

import unittest

from opentelemetry.sdk import resources


class TestResources(unittest.TestCase):
    def test_create(self):
        labels = {
            "service": "ui",
            "version": 1,
            "has_bugs": True,
            "cost": 112.12,
        }

        resource = resources.Resource.create(labels)
        self.assertIsInstance(resource, resources.Resource)
        self.assertEqual(resource.labels, labels)

        resource = resources.Resource.create_empty()
        self.assertIs(resource, resources._EMPTY_RESOURCE)

        resource = resources.Resource.create(None)
        self.assertIs(resource, resources._EMPTY_RESOURCE)

        resource = resources.Resource.create({})
        self.assertIs(resource, resources._EMPTY_RESOURCE)

    def test_resource_merge(self):
        left = resources.Resource({"service": "ui"})
        right = resources.Resource({"host": "service-host"})
        self.assertEqual(
            left.merge(right),
            resources.Resource({"service": "ui", "host": "service-host"}),
        )

    def test_resource_merge_empty_string(self):
        """Verify Resource.merge behavior with the empty string.

        Labels from the source Resource take precedence, with
        the exception of the empty string.

        """
        left = resources.Resource({"service": "ui", "host": ""})
        right = resources.Resource(
            {"host": "service-host", "service": "not-ui"}
        )
        self.assertEqual(
            left.merge(right),
            resources.Resource({"service": "ui", "host": "service-host"}),
        )

    def test_immutability(self):
        labels = {
            "service": "ui",
            "version": 1,
            "has_bugs": True,
            "cost": 112.12,
        }

        labels_copy = labels.copy()

        resource = resources.Resource.create(labels)
        self.assertEqual(resource.labels, labels_copy)

        resource.labels["has_bugs"] = False
        self.assertEqual(resource.labels, labels_copy)

        labels["cost"] = 999.91
        self.assertEqual(resource.labels, labels_copy)
