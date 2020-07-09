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

import os
import unittest
from unittest import mock

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

    def test_aggregated_resources_no_detectors(self):
        aggregated_resources = resources.get_aggregated_resources([])
        self.assertEqual(
            aggregated_resources, resources.Resource.create_empty()
        )

    def test_aggregated_resources_with_static_resource(self):
        static_resource = resources.Resource({"static_key": "static_value"})

        self.assertEqual(
            resources.get_aggregated_resources(
                [], initial_resource=static_resource
            ),
            static_resource,
        )

        # Static resource values should never be overwritten
        resource_detector = mock.Mock(spec=resources.ResourceDetector)
        resource_detector.detect.return_value = resources.Resource(
            {"static_key": "try_to_overwrite_existing_value", "key": "value"}
        )
        self.assertEqual(
            resources.get_aggregated_resources(
                [resource_detector], initial_resource=static_resource
            ),
            resources.Resource({"static_key": "static_value", "key": "value"}),
        )

    def test_aggregated_resources_multiple_detectors(self):
        resource_detector1 = mock.Mock(spec=resources.ResourceDetector)
        resource_detector1.detect.return_value = resources.Resource(
            {"key1": "value1"}
        )
        resource_detector2 = mock.Mock(spec=resources.ResourceDetector)
        resource_detector2.detect.return_value = resources.Resource(
            {"key2": "value2", "key3": "value3"}
        )
        resource_detector3 = mock.Mock(spec=resources.ResourceDetector)
        resource_detector3.detect.return_value = resources.Resource(
            {
                "key2": "try_to_overwrite_existing_value",
                "key3": "try_to_overwrite_existing_value",
                "key4": "value4",
            }
        )

        # New values should not overwrite existing values
        self.assertEqual(
            resources.get_aggregated_resources(
                [resource_detector1, resource_detector2, resource_detector3]
            ),
            resources.Resource(
                {
                    "key1": "value1",
                    "key2": "value2",
                    "key3": "value3",
                    "key4": "value4",
                }
            ),
        )

    def test_resource_detector_ignore_error(self):
        resource_detector = mock.Mock(spec=resources.ResourceDetector)
        resource_detector.detect.side_effect = Exception()
        resource_detector.raise_on_error = False
        self.assertEqual(
            resources.get_aggregated_resources([resource_detector]),
            resources.Resource.create_empty(),
        )

    def test_resource_detector_raise_error(self):
        resource_detector = mock.Mock(spec=resources.ResourceDetector)
        resource_detector.detect.side_effect = Exception()
        resource_detector.raise_on_error = True
        self.assertRaises(
            Exception, resources.get_aggregated_resources, [resource_detector],
        )


class TestOTELResourceDetector(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["OTEL_RESOURCE"] = ""

    def tearDown(self) -> None:
        os.environ.pop("OTEL_RESOURCE")

    def test_otel_resource_detector_empty(self):
        detector = resources.OTELResourceDetector()
        os.environ["OTEL_RESOURCE"] = ""
        self.assertEqual(detector.detect(), resources.Resource.create_empty())

    def test_otel_resource_detector_one(self):
        detector = resources.OTELResourceDetector()
        os.environ["OTEL_RESOURCE"] = "k=v"
        self.assertEqual(detector.detect(), resources.Resource({"k": "v"}))

    def test_otel_resource_detector_one_with_whitespace(self):
        detector = resources.OTELResourceDetector()
        os.environ["OTEL_RESOURCE"] = "    k  = v   "
        self.assertEqual(detector.detect(), resources.Resource({"k": "v"}))

    def test_otel_resource_detector_multiple(self):
        detector = resources.OTELResourceDetector()
        os.environ["OTEL_RESOURCE"] = "k=v,k2=v2"
        self.assertEqual(
            detector.detect(), resources.Resource({"k": "v", "k2": "v2"})
        )

    def test_otel_resource_detector_multiple_with_whitespace(self):
        detector = resources.OTELResourceDetector()
        os.environ["OTEL_RESOURCE"] = "    k  = v  , k2   = v2 "
        self.assertEqual(
            detector.detect(), resources.Resource({"k": "v", "k2": "v2"})
        )
