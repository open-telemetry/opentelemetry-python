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
import uuid
from logging import ERROR
from unittest import mock

from opentelemetry.sdk import resources


class TestResources(unittest.TestCase):
    def setUp(self) -> None:
        os.environ[resources.OTEL_RESOURCE_ATTRIBUTES] = ""

    def tearDown(self) -> None:
        os.environ.pop(resources.OTEL_RESOURCE_ATTRIBUTES)

    def test_create(self):
        attributes = {
            "service": "ui",
            "version": 1,
            "has_bugs": True,
            "cost": 112.12,
        }

        expected_attributes = {
            "service": "ui",
            "version": 1,
            "has_bugs": True,
            "cost": 112.12,
            resources.TELEMETRY_SDK_NAME: "opentelemetry",
            resources.TELEMETRY_SDK_LANGUAGE: "python",
            resources.TELEMETRY_SDK_VERSION: resources._OPENTELEMETRY_SDK_VERSION,
            resources.SERVICE_NAME: "unknown_service",
        }

        resource = resources.Resource.create(attributes)
        self.assertIsInstance(resource, resources.Resource)
        self.assertEqual(resource.attributes, expected_attributes)
        self.assertEqual(resource.schema_url, "")

        schema_url = "https://opentelemetry.io/schemas/1.3.0"

        resource = resources.Resource.create(attributes, schema_url)
        self.assertIsInstance(resource, resources.Resource)
        self.assertEqual(resource.attributes, expected_attributes)
        self.assertEqual(resource.schema_url, schema_url)

        os.environ[resources.OTEL_RESOURCE_ATTRIBUTES] = "key=value"
        resource = resources.Resource.create(attributes)
        self.assertIsInstance(resource, resources.Resource)
        expected_with_envar = expected_attributes.copy()
        expected_with_envar["key"] = "value"
        self.assertEqual(resource.attributes, expected_with_envar)
        os.environ[resources.OTEL_RESOURCE_ATTRIBUTES] = ""

        resource = resources.Resource.get_empty()
        self.assertEqual(resource, resources._EMPTY_RESOURCE)

        resource = resources.Resource.create(None)
        self.assertEqual(
            resource,
            resources._DEFAULT_RESOURCE.merge(
                resources.Resource(
                    {resources.SERVICE_NAME: "unknown_service"}, ""
                )
            ),
        )
        self.assertEqual(resource.schema_url, "")

        resource = resources.Resource.create(None, None)
        self.assertEqual(
            resource,
            resources._DEFAULT_RESOURCE.merge(
                resources.Resource(
                    {resources.SERVICE_NAME: "unknown_service"}, ""
                )
            ),
        )
        self.assertEqual(resource.schema_url, "")

        resource = resources.Resource.create({})
        self.assertEqual(
            resource,
            resources._DEFAULT_RESOURCE.merge(
                resources.Resource(
                    {resources.SERVICE_NAME: "unknown_service"}, ""
                )
            ),
        )
        self.assertEqual(resource.schema_url, "")

        resource = resources.Resource.create({}, None)
        self.assertEqual(
            resource,
            resources._DEFAULT_RESOURCE.merge(
                resources.Resource(
                    {resources.SERVICE_NAME: "unknown_service"}, ""
                )
            ),
        )
        self.assertEqual(resource.schema_url, "")

    def test_resource_merge(self):
        left = resources.Resource({"service": "ui"})
        right = resources.Resource({"host": "service-host"})
        self.assertEqual(
            left.merge(right),
            resources.Resource({"service": "ui", "host": "service-host"}),
        )
        schema_urls = (
            "https://opentelemetry.io/schemas/1.2.0",
            "https://opentelemetry.io/schemas/1.3.0",
        )

        left = resources.Resource.create({}, None)
        right = resources.Resource.create({}, None)
        self.assertEqual(left.merge(right).schema_url, "")

        left = resources.Resource.create({}, None)
        right = resources.Resource.create({}, schema_urls[0])
        self.assertEqual(left.merge(right).schema_url, schema_urls[0])

        left = resources.Resource.create({}, schema_urls[0])
        right = resources.Resource.create({}, None)
        self.assertEqual(left.merge(right).schema_url, schema_urls[0])

        left = resources.Resource.create({}, schema_urls[0])
        right = resources.Resource.create({}, schema_urls[0])
        self.assertEqual(left.merge(right).schema_url, schema_urls[0])

        left = resources.Resource.create({}, schema_urls[0])
        right = resources.Resource.create({}, schema_urls[1])
        with self.assertLogs(level=ERROR) as log_entry:
            self.assertEqual(left.merge(right), left)
            self.assertIn(schema_urls[0], log_entry.output[0])
            self.assertIn(schema_urls[1], log_entry.output[0])

    def test_resource_merge_empty_string(self):
        """Verify Resource.merge behavior with the empty string.

        Attributes from the source Resource take precedence, with
        the exception of the empty string.

        """
        left = resources.Resource({"service": "ui", "host": ""})
        right = resources.Resource(
            {"host": "service-host", "service": "not-ui"}
        )
        self.assertEqual(
            left.merge(right),
            resources.Resource({"service": "not-ui", "host": "service-host"}),
        )

    def test_immutability(self):
        attributes = {
            "service": "ui",
            "version": 1,
            "has_bugs": True,
            "cost": 112.12,
        }

        default_attributes = {
            resources.TELEMETRY_SDK_NAME: "opentelemetry",
            resources.TELEMETRY_SDK_LANGUAGE: "python",
            resources.TELEMETRY_SDK_VERSION: resources._OPENTELEMETRY_SDK_VERSION,
            resources.SERVICE_NAME: "unknown_service",
        }

        attributes_copy = attributes.copy()
        attributes_copy.update(default_attributes)

        resource = resources.Resource.create(attributes)
        self.assertEqual(resource.attributes, attributes_copy)

        with self.assertRaises(TypeError):
            resource.attributes["has_bugs"] = False
        self.assertEqual(resource.attributes, attributes_copy)

        attributes["cost"] = 999.91
        self.assertEqual(resource.attributes, attributes_copy)

        with self.assertRaises(AttributeError):
            resource.schema_url = "bug"

        self.assertEqual(resource.schema_url, "")

    def test_service_name_using_process_name(self):
        resource = resources.Resource.create(
            {resources.PROCESS_EXECUTABLE_NAME: "test"}
        )
        self.assertEqual(
            resource.attributes.get(resources.SERVICE_NAME),
            "unknown_service:test",
        )

    def test_invalid_resource_attribute_values(self):
        resource = resources.Resource(
            {
                resources.SERVICE_NAME: "test",
                "non-primitive-data-type": {},
                "invalid-byte-type-attribute": b"\xd8\xe1\xb7\xeb\xa8\xe5 \xd2\xb7\xe1",
                "": "empty-key-value",
                None: "null-key-value",
                "another-non-primitive": uuid.uuid4(),
            }
        )
        self.assertEqual(
            resource.attributes,
            {
                resources.SERVICE_NAME: "test",
            },
        )
        self.assertEqual(len(resource.attributes), 1)

    def test_aggregated_resources_no_detectors(self):
        aggregated_resources = resources.get_aggregated_resources([])
        self.assertEqual(
            aggregated_resources,
            resources._DEFAULT_RESOURCE.merge(
                resources.Resource(
                    {resources.SERVICE_NAME: "unknown_service"}, ""
                )
            ),
        )

    def test_aggregated_resources_with_default_destroying_static_resource(
        self,
    ):
        static_resource = resources.Resource({"static_key": "static_value"})

        self.assertEqual(
            resources.get_aggregated_resources(
                [], initial_resource=static_resource
            ),
            static_resource,
        )

        resource_detector = mock.Mock(spec=resources.ResourceDetector)
        resource_detector.detect.return_value = resources.Resource(
            {"static_key": "try_to_overwrite_existing_value", "key": "value"}
        )
        self.assertEqual(
            resources.get_aggregated_resources(
                [resource_detector], initial_resource=static_resource
            ),
            resources.Resource(
                {
                    "static_key": "try_to_overwrite_existing_value",
                    "key": "value",
                }
            ),
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

        self.assertEqual(
            resources.get_aggregated_resources(
                [resource_detector1, resource_detector2, resource_detector3]
            ),
            resources._DEFAULT_RESOURCE.merge(
                resources.Resource(
                    {resources.SERVICE_NAME: "unknown_service"}, ""
                )
            ).merge(
                resources.Resource(
                    {
                        "key1": "value1",
                        "key2": "try_to_overwrite_existing_value",
                        "key3": "try_to_overwrite_existing_value",
                        "key4": "value4",
                    }
                )
            ),
        )

    def test_aggregated_resources_different_schema_urls(self):
        resource_detector1 = mock.Mock(spec=resources.ResourceDetector)
        resource_detector1.detect.return_value = resources.Resource(
            {"key1": "value1"}, ""
        )
        resource_detector2 = mock.Mock(spec=resources.ResourceDetector)
        resource_detector2.detect.return_value = resources.Resource(
            {"key2": "value2", "key3": "value3"}, "url1"
        )
        resource_detector3 = mock.Mock(spec=resources.ResourceDetector)
        resource_detector3.detect.return_value = resources.Resource(
            {
                "key2": "try_to_overwrite_existing_value",
                "key3": "try_to_overwrite_existing_value",
                "key4": "value4",
            },
            "url2",
        )
        resource_detector4 = mock.Mock(spec=resources.ResourceDetector)
        resource_detector4.detect.return_value = resources.Resource(
            {
                "key2": "try_to_overwrite_existing_value",
                "key3": "try_to_overwrite_existing_value",
                "key4": "value4",
            },
            "url1",
        )
        self.assertEqual(
            resources.get_aggregated_resources(
                [resource_detector1, resource_detector2]
            ),
            resources._DEFAULT_RESOURCE.merge(
                resources.Resource(
                    {resources.SERVICE_NAME: "unknown_service"}, ""
                )
            ).merge(
                resources.Resource(
                    {"key1": "value1", "key2": "value2", "key3": "value3"},
                    "url1",
                )
            ),
        )
        with self.assertLogs(level=ERROR) as log_entry:
            self.assertEqual(
                resources.get_aggregated_resources(
                    [resource_detector2, resource_detector3]
                ),
                resources._DEFAULT_RESOURCE.merge(
                    resources.Resource(
                        {resources.SERVICE_NAME: "unknown_service"}, ""
                    )
                ).merge(
                    resources.Resource(
                        {"key2": "value2", "key3": "value3"}, "url1"
                    )
                ),
            )
            self.assertIn("url1", log_entry.output[0])
            self.assertIn("url2", log_entry.output[0])
        with self.assertLogs(level=ERROR):
            self.assertEqual(
                resources.get_aggregated_resources(
                    [
                        resource_detector2,
                        resource_detector3,
                        resource_detector4,
                        resource_detector1,
                    ]
                ),
                resources._DEFAULT_RESOURCE.merge(
                    resources.Resource(
                        {resources.SERVICE_NAME: "unknown_service"}, ""
                    )
                ).merge(
                    resources.Resource(
                        {
                            "key1": "value1",
                            "key2": "try_to_overwrite_existing_value",
                            "key3": "try_to_overwrite_existing_value",
                            "key4": "value4",
                        },
                        "url1",
                    )
                ),
            )
            self.assertIn("url1", log_entry.output[0])
            self.assertIn("url2", log_entry.output[0])

    def test_resource_detector_ignore_error(self):
        resource_detector = mock.Mock(spec=resources.ResourceDetector)
        resource_detector.detect.side_effect = Exception()
        resource_detector.raise_on_error = False
        self.assertEqual(
            resources.get_aggregated_resources([resource_detector]),
            resources._DEFAULT_RESOURCE.merge(
                resources.Resource(
                    {resources.SERVICE_NAME: "unknown_service"}, ""
                )
            ),
        )

    def test_resource_detector_raise_error(self):
        resource_detector = mock.Mock(spec=resources.ResourceDetector)
        resource_detector.detect.side_effect = Exception()
        resource_detector.raise_on_error = True
        self.assertRaises(
            Exception, resources.get_aggregated_resources, [resource_detector]
        )

    @mock.patch.dict(
        os.environ,
        {"OTEL_RESOURCE_ATTRIBUTES": "key1=env_value1,key2=env_value2"},
    )
    def test_env_priority(self):
        resource_env = resources.Resource.create()
        self.assertEqual(resource_env.attributes["key1"], "env_value1")
        self.assertEqual(resource_env.attributes["key2"], "env_value2")

        resource_env_override = resources.Resource.create(
            {"key1": "value1", "key2": "value2"}
        )
        self.assertEqual(resource_env_override.attributes["key1"], "value1")
        self.assertEqual(resource_env_override.attributes["key2"], "value2")

    @mock.patch.dict(
        os.environ,
        {
            resources.OTEL_SERVICE_NAME: "test-srv-name",
            resources.OTEL_RESOURCE_ATTRIBUTES: "service.name=svc-name-from-resource",
        },
    )
    def test_service_name_env(self):
        resource = resources.Resource.create()
        self.assertEqual(resource.attributes["service.name"], "test-srv-name")

        resource = resources.Resource.create({"service.name": "from-code"})
        self.assertEqual(resource.attributes["service.name"], "from-code")


class TestOTELResourceDetector(unittest.TestCase):
    def setUp(self) -> None:
        os.environ[resources.OTEL_RESOURCE_ATTRIBUTES] = ""

    def tearDown(self) -> None:
        os.environ.pop(resources.OTEL_RESOURCE_ATTRIBUTES)

    def test_empty(self):
        detector = resources.OTELResourceDetector()
        os.environ[resources.OTEL_RESOURCE_ATTRIBUTES] = ""
        self.assertEqual(detector.detect(), resources.Resource.get_empty())

    def test_one(self):
        detector = resources.OTELResourceDetector()
        os.environ[resources.OTEL_RESOURCE_ATTRIBUTES] = "k=v"
        self.assertEqual(detector.detect(), resources.Resource({"k": "v"}))

    def test_one_with_whitespace(self):
        detector = resources.OTELResourceDetector()
        os.environ[resources.OTEL_RESOURCE_ATTRIBUTES] = "    k  = v   "
        self.assertEqual(detector.detect(), resources.Resource({"k": "v"}))

    def test_multiple(self):
        detector = resources.OTELResourceDetector()
        os.environ[resources.OTEL_RESOURCE_ATTRIBUTES] = "k=v,k2=v2"
        self.assertEqual(
            detector.detect(), resources.Resource({"k": "v", "k2": "v2"})
        )

    def test_multiple_with_whitespace(self):
        detector = resources.OTELResourceDetector()
        os.environ[
            resources.OTEL_RESOURCE_ATTRIBUTES
        ] = "    k  = v  , k2   = v2 "
        self.assertEqual(
            detector.detect(), resources.Resource({"k": "v", "k2": "v2"})
        )

    def test_invalid_key_value_pairs(self):
        detector = resources.OTELResourceDetector()
        os.environ[
            resources.OTEL_RESOURCE_ATTRIBUTES
        ] = "k=v,k2=v2,invalid,,foo=bar=baz,"
        self.assertEqual(
            detector.detect(),
            resources.Resource({"k": "v", "k2": "v2", "foo": "bar=baz"}),
        )

    @mock.patch.dict(
        os.environ,
        {resources.OTEL_SERVICE_NAME: "test-srv-name"},
    )
    def test_service_name_env(self):
        detector = resources.OTELResourceDetector()
        self.assertEqual(
            detector.detect(),
            resources.Resource({"service.name": "test-srv-name"}),
        )

    @mock.patch.dict(
        os.environ,
        {
            resources.OTEL_SERVICE_NAME: "from-service-name",
            resources.OTEL_RESOURCE_ATTRIBUTES: "service.name=from-resource-attrs",
        },
    )
    def test_service_name_env_precedence(self):
        detector = resources.OTELResourceDetector()
        self.assertEqual(
            detector.detect(),
            resources.Resource({"service.name": "from-service-name"}),
        )
