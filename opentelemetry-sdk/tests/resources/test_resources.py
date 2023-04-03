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
import uuid
from logging import ERROR
from os import environ
from unittest.mock import Mock, patch
from urllib import parse

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPERIMENTAL_RESOURCE_DETECTORS,
)
from opentelemetry.sdk.resources import (
    _DEFAULT_RESOURCE,
    _EMPTY_RESOURCE,
    _OPENTELEMETRY_SDK_VERSION,
    OTEL_RESOURCE_ATTRIBUTES,
    OTEL_SERVICE_NAME,
    PROCESS_EXECUTABLE_NAME,
    PROCESS_RUNTIME_DESCRIPTION,
    PROCESS_RUNTIME_NAME,
    PROCESS_RUNTIME_VERSION,
    SERVICE_NAME,
    TELEMETRY_SDK_LANGUAGE,
    TELEMETRY_SDK_NAME,
    TELEMETRY_SDK_VERSION,
    OTELResourceDetector,
    ProcessResourceDetector,
    Resource,
    ResourceDetector,
    get_aggregated_resources,
)


class TestResources(unittest.TestCase):
    def setUp(self) -> None:
        environ[OTEL_RESOURCE_ATTRIBUTES] = ""

    def tearDown(self) -> None:
        environ.pop(OTEL_RESOURCE_ATTRIBUTES)

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
            TELEMETRY_SDK_NAME: "opentelemetry",
            TELEMETRY_SDK_LANGUAGE: "python",
            TELEMETRY_SDK_VERSION: _OPENTELEMETRY_SDK_VERSION,
            SERVICE_NAME: "unknown_service",
        }

        resource = Resource.create(attributes)
        self.assertIsInstance(resource, Resource)
        self.assertEqual(resource.attributes, expected_attributes)
        self.assertEqual(resource.schema_url, "")

        schema_url = "https://opentelemetry.io/schemas/1.3.0"

        resource = Resource.create(attributes, schema_url)
        self.assertIsInstance(resource, Resource)
        self.assertEqual(resource.attributes, expected_attributes)
        self.assertEqual(resource.schema_url, schema_url)

        environ[OTEL_RESOURCE_ATTRIBUTES] = "key=value"
        resource = Resource.create(attributes)
        self.assertIsInstance(resource, Resource)
        expected_with_envar = expected_attributes.copy()
        expected_with_envar["key"] = "value"
        self.assertEqual(resource.attributes, expected_with_envar)
        environ[OTEL_RESOURCE_ATTRIBUTES] = ""

        resource = Resource.get_empty()
        self.assertEqual(resource, _EMPTY_RESOURCE)

        resource = Resource.create(None)
        self.assertEqual(
            resource,
            _DEFAULT_RESOURCE.merge(
                Resource({SERVICE_NAME: "unknown_service"}, "")
            ),
        )
        self.assertEqual(resource.schema_url, "")

        resource = Resource.create(None, None)
        self.assertEqual(
            resource,
            _DEFAULT_RESOURCE.merge(
                Resource({SERVICE_NAME: "unknown_service"}, "")
            ),
        )
        self.assertEqual(resource.schema_url, "")

        resource = Resource.create({})
        self.assertEqual(
            resource,
            _DEFAULT_RESOURCE.merge(
                Resource({SERVICE_NAME: "unknown_service"}, "")
            ),
        )
        self.assertEqual(resource.schema_url, "")

        resource = Resource.create({}, None)
        self.assertEqual(
            resource,
            _DEFAULT_RESOURCE.merge(
                Resource({SERVICE_NAME: "unknown_service"}, "")
            ),
        )
        self.assertEqual(resource.schema_url, "")

    def test_resource_merge(self):
        left = Resource({"service": "ui"})
        right = Resource({"host": "service-host"})
        self.assertEqual(
            left.merge(right),
            Resource({"service": "ui", "host": "service-host"}),
        )
        schema_urls = (
            "https://opentelemetry.io/schemas/1.2.0",
            "https://opentelemetry.io/schemas/1.3.0",
        )

        left = Resource.create({}, None)
        right = Resource.create({}, None)
        self.assertEqual(left.merge(right).schema_url, "")

        left = Resource.create({}, None)
        right = Resource.create({}, schema_urls[0])
        self.assertEqual(left.merge(right).schema_url, schema_urls[0])

        left = Resource.create({}, schema_urls[0])
        right = Resource.create({}, None)
        self.assertEqual(left.merge(right).schema_url, schema_urls[0])

        left = Resource.create({}, schema_urls[0])
        right = Resource.create({}, schema_urls[0])
        self.assertEqual(left.merge(right).schema_url, schema_urls[0])

        left = Resource.create({}, schema_urls[0])
        right = Resource.create({}, schema_urls[1])
        with self.assertLogs(level=ERROR) as log_entry:
            self.assertEqual(left.merge(right), left)
            self.assertIn(schema_urls[0], log_entry.output[0])
            self.assertIn(schema_urls[1], log_entry.output[0])

    def test_resource_merge_empty_string(self):
        """Verify Resource.merge behavior with the empty string.

        Attributes from the source Resource take precedence, with
        the exception of the empty string.

        """
        left = Resource({"service": "ui", "host": ""})
        right = Resource({"host": "service-host", "service": "not-ui"})
        self.assertEqual(
            left.merge(right),
            Resource({"service": "not-ui", "host": "service-host"}),
        )

    def test_immutability(self):
        attributes = {
            "service": "ui",
            "version": 1,
            "has_bugs": True,
            "cost": 112.12,
        }

        default_attributes = {
            TELEMETRY_SDK_NAME: "opentelemetry",
            TELEMETRY_SDK_LANGUAGE: "python",
            TELEMETRY_SDK_VERSION: _OPENTELEMETRY_SDK_VERSION,
            SERVICE_NAME: "unknown_service",
        }

        attributes_copy = attributes.copy()
        attributes_copy.update(default_attributes)

        resource = Resource.create(attributes)
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
        resource = Resource.create({PROCESS_EXECUTABLE_NAME: "test"})
        self.assertEqual(
            resource.attributes.get(SERVICE_NAME),
            "unknown_service:test",
        )

    def test_invalid_resource_attribute_values(self):
        resource = Resource(
            {
                SERVICE_NAME: "test",
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
                SERVICE_NAME: "test",
            },
        )
        self.assertEqual(len(resource.attributes), 1)

    def test_aggregated_resources_no_detectors(self):
        aggregated_resources = get_aggregated_resources([])
        self.assertEqual(
            aggregated_resources,
            _DEFAULT_RESOURCE.merge(
                Resource({SERVICE_NAME: "unknown_service"}, "")
            ),
        )

    def test_aggregated_resources_with_default_destroying_static_resource(
        self,
    ):
        static_resource = Resource({"static_key": "static_value"})

        self.assertEqual(
            get_aggregated_resources([], initial_resource=static_resource),
            static_resource,
        )

        resource_detector = Mock(spec=ResourceDetector)
        resource_detector.detect.return_value = Resource(
            {"static_key": "try_to_overwrite_existing_value", "key": "value"}
        )
        self.assertEqual(
            get_aggregated_resources(
                [resource_detector], initial_resource=static_resource
            ),
            Resource(
                {
                    "static_key": "try_to_overwrite_existing_value",
                    "key": "value",
                }
            ),
        )

    def test_aggregated_resources_multiple_detectors(self):
        resource_detector1 = Mock(spec=ResourceDetector)
        resource_detector1.detect.return_value = Resource({"key1": "value1"})
        resource_detector2 = Mock(spec=ResourceDetector)
        resource_detector2.detect.return_value = Resource(
            {"key2": "value2", "key3": "value3"}
        )
        resource_detector3 = Mock(spec=ResourceDetector)
        resource_detector3.detect.return_value = Resource(
            {
                "key2": "try_to_overwrite_existing_value",
                "key3": "try_to_overwrite_existing_value",
                "key4": "value4",
            }
        )

        self.assertEqual(
            get_aggregated_resources(
                [resource_detector1, resource_detector2, resource_detector3]
            ),
            _DEFAULT_RESOURCE.merge(
                Resource({SERVICE_NAME: "unknown_service"}, "")
            ).merge(
                Resource(
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
        resource_detector1 = Mock(spec=ResourceDetector)
        resource_detector1.detect.return_value = Resource(
            {"key1": "value1"}, ""
        )
        resource_detector2 = Mock(spec=ResourceDetector)
        resource_detector2.detect.return_value = Resource(
            {"key2": "value2", "key3": "value3"}, "url1"
        )
        resource_detector3 = Mock(spec=ResourceDetector)
        resource_detector3.detect.return_value = Resource(
            {
                "key2": "try_to_overwrite_existing_value",
                "key3": "try_to_overwrite_existing_value",
                "key4": "value4",
            },
            "url2",
        )
        resource_detector4 = Mock(spec=ResourceDetector)
        resource_detector4.detect.return_value = Resource(
            {
                "key2": "try_to_overwrite_existing_value",
                "key3": "try_to_overwrite_existing_value",
                "key4": "value4",
            },
            "url1",
        )
        self.assertEqual(
            get_aggregated_resources([resource_detector1, resource_detector2]),
            _DEFAULT_RESOURCE.merge(
                Resource({SERVICE_NAME: "unknown_service"}, "")
            ).merge(
                Resource(
                    {"key1": "value1", "key2": "value2", "key3": "value3"},
                    "url1",
                )
            ),
        )
        with self.assertLogs(level=ERROR) as log_entry:
            self.assertEqual(
                get_aggregated_resources(
                    [resource_detector2, resource_detector3]
                ),
                _DEFAULT_RESOURCE.merge(
                    Resource({SERVICE_NAME: "unknown_service"}, "")
                ).merge(
                    Resource({"key2": "value2", "key3": "value3"}, "url1")
                ),
            )
            self.assertIn("url1", log_entry.output[0])
            self.assertIn("url2", log_entry.output[0])
        with self.assertLogs(level=ERROR):
            self.assertEqual(
                get_aggregated_resources(
                    [
                        resource_detector2,
                        resource_detector3,
                        resource_detector4,
                        resource_detector1,
                    ]
                ),
                _DEFAULT_RESOURCE.merge(
                    Resource({SERVICE_NAME: "unknown_service"}, "")
                ).merge(
                    Resource(
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
        resource_detector = Mock(spec=ResourceDetector)
        resource_detector.detect.side_effect = Exception()
        resource_detector.raise_on_error = False
        self.assertEqual(
            get_aggregated_resources([resource_detector]),
            _DEFAULT_RESOURCE.merge(
                Resource({SERVICE_NAME: "unknown_service"}, "")
            ),
        )

    def test_resource_detector_raise_error(self):
        resource_detector = Mock(spec=ResourceDetector)
        resource_detector.detect.side_effect = Exception()
        resource_detector.raise_on_error = True
        self.assertRaises(
            Exception, get_aggregated_resources, [resource_detector]
        )

    @patch.dict(
        environ,
        {"OTEL_RESOURCE_ATTRIBUTES": "key1=env_value1,key2=env_value2"},
    )
    def test_env_priority(self):
        resource_env = Resource.create()
        self.assertEqual(resource_env.attributes["key1"], "env_value1")
        self.assertEqual(resource_env.attributes["key2"], "env_value2")

        resource_env_override = Resource.create(
            {"key1": "value1", "key2": "value2"}
        )
        self.assertEqual(resource_env_override.attributes["key1"], "value1")
        self.assertEqual(resource_env_override.attributes["key2"], "value2")

    @patch.dict(
        environ,
        {
            OTEL_SERVICE_NAME: "test-srv-name",
            OTEL_RESOURCE_ATTRIBUTES: "service.name=svc-name-from-resource",
        },
    )
    def test_service_name_env(self):
        resource = Resource.create()
        self.assertEqual(resource.attributes["service.name"], "test-srv-name")

        resource = Resource.create({"service.name": "from-code"})
        self.assertEqual(resource.attributes["service.name"], "from-code")


class TestOTELResourceDetector(unittest.TestCase):
    def setUp(self) -> None:
        environ[OTEL_RESOURCE_ATTRIBUTES] = ""

    def tearDown(self) -> None:
        environ.pop(OTEL_RESOURCE_ATTRIBUTES)

    def test_empty(self):
        detector = OTELResourceDetector()
        environ[OTEL_RESOURCE_ATTRIBUTES] = ""
        self.assertEqual(detector.detect(), Resource.get_empty())

    def test_one(self):
        detector = OTELResourceDetector()
        environ[OTEL_RESOURCE_ATTRIBUTES] = "k=v"
        self.assertEqual(detector.detect(), Resource({"k": "v"}))

    def test_one_with_whitespace(self):
        detector = OTELResourceDetector()
        environ[OTEL_RESOURCE_ATTRIBUTES] = "    k  = v   "
        self.assertEqual(detector.detect(), Resource({"k": "v"}))

    def test_multiple(self):
        detector = OTELResourceDetector()
        environ[OTEL_RESOURCE_ATTRIBUTES] = "k=v,k2=v2"
        self.assertEqual(detector.detect(), Resource({"k": "v", "k2": "v2"}))

    def test_multiple_with_whitespace(self):
        detector = OTELResourceDetector()
        environ[OTEL_RESOURCE_ATTRIBUTES] = "    k  = v  , k2   = v2 "
        self.assertEqual(detector.detect(), Resource({"k": "v", "k2": "v2"}))

    def test_invalid_key_value_pairs(self):
        detector = OTELResourceDetector()
        environ[OTEL_RESOURCE_ATTRIBUTES] = "k=v,k2=v2,invalid,,foo=bar=baz,"
        self.assertEqual(
            detector.detect(),
            Resource({"k": "v", "k2": "v2", "foo": "bar=baz"}),
        )

    def test_multiple_with_url_decode(self):
        detector = OTELResourceDetector()
        environ[
            OTEL_RESOURCE_ATTRIBUTES
        ] = "key=value%20test%0A, key2=value+%202"
        self.assertEqual(
            detector.detect(),
            Resource({"key": "value test\n", "key2": "value+ 2"}),
        )
        self.assertEqual(
            detector.detect(),
            Resource(
                {
                    "key": parse.unquote("value%20test%0A"),
                    "key2": parse.unquote("value+%202"),
                }
            ),
        )

    @patch.dict(
        environ,
        {OTEL_SERVICE_NAME: "test-srv-name"},
    )
    def test_service_name_env(self):
        detector = OTELResourceDetector()
        self.assertEqual(
            detector.detect(),
            Resource({"service.name": "test-srv-name"}),
        )

    @patch.dict(
        environ,
        {
            OTEL_SERVICE_NAME: "from-service-name",
            OTEL_RESOURCE_ATTRIBUTES: "service.name=from-resource-attrs",
        },
    )
    def test_service_name_env_precedence(self):
        detector = OTELResourceDetector()
        self.assertEqual(
            detector.detect(),
            Resource({"service.name": "from-service-name"}),
        )

    def test_process_detector(self):
        initial_resource = Resource({"foo": "bar"})
        aggregated_resource = get_aggregated_resources(
            [ProcessResourceDetector()], initial_resource
        )

        self.assertIn(
            PROCESS_RUNTIME_NAME,
            aggregated_resource.attributes.keys(),
        )
        self.assertIn(
            PROCESS_RUNTIME_DESCRIPTION,
            aggregated_resource.attributes.keys(),
        )
        self.assertIn(
            PROCESS_RUNTIME_VERSION,
            aggregated_resource.attributes.keys(),
        )

    def test_resource_detector_entry_points_default(self):

        resource = Resource({}).create()

        self.assertEqual(
            resource.attributes["telemetry.sdk.language"], "python"
        )
        self.assertEqual(
            resource.attributes["telemetry.sdk.name"], "opentelemetry"
        )
        self.assertEqual(
            resource.attributes["service.name"], "unknown_service"
        )
        self.assertEqual(resource.schema_url, "")

        resource = Resource({}).create({"a": "b", "c": "d"})

        self.assertEqual(
            resource.attributes["telemetry.sdk.language"], "python"
        )
        self.assertEqual(
            resource.attributes["telemetry.sdk.name"], "opentelemetry"
        )
        self.assertEqual(
            resource.attributes["service.name"], "unknown_service"
        )
        self.assertEqual(resource.attributes["a"], "b")
        self.assertEqual(resource.attributes["c"], "d")
        self.assertEqual(resource.schema_url, "")

    @patch.dict(
        environ, {OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: "mock"}, clear=True
    )
    @patch(
        "opentelemetry.sdk.resources.entry_points",
        Mock(
            return_value=[
                Mock(
                    **{
                        "load.return_value": Mock(
                            return_value=Mock(
                                **{"detect.return_value": Resource({"a": "b"})}
                            )
                        )
                    }
                )
            ]
        ),
    )
    def test_resource_detector_entry_points_non_default(self):
        resource = Resource({}).create()
        self.assertEqual(
            resource.attributes["telemetry.sdk.language"], "python"
        )
        self.assertEqual(
            resource.attributes["telemetry.sdk.name"], "opentelemetry"
        )
        self.assertEqual(
            resource.attributes["service.name"], "unknown_service"
        )
        self.assertEqual(resource.attributes["a"], "b")
        self.assertEqual(resource.schema_url, "")

    def test_resource_detector_entry_points_otel(self):
        """
        Test that OTELResourceDetector-resource-generated attributes are
        always being added.
        """
        with patch.dict(
            environ, {OTEL_RESOURCE_ATTRIBUTES: "a=b,c=d"}, clear=True
        ):
            resource = Resource({}).create()
            self.assertEqual(
                resource.attributes["telemetry.sdk.language"], "python"
            )
            self.assertEqual(
                resource.attributes["telemetry.sdk.name"], "opentelemetry"
            )
            self.assertEqual(
                resource.attributes["service.name"], "unknown_service"
            )
            self.assertEqual(resource.attributes["a"], "b")
            self.assertEqual(resource.attributes["c"], "d")
            self.assertEqual(resource.schema_url, "")

        with patch.dict(
            environ,
            {
                OTEL_RESOURCE_ATTRIBUTES: "a=b,c=d",
                OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: "process",
            },
            clear=True,
        ):
            resource = Resource({}).create()
            self.assertEqual(
                resource.attributes["telemetry.sdk.language"], "python"
            )
            self.assertEqual(
                resource.attributes["telemetry.sdk.name"], "opentelemetry"
            )
            self.assertEqual(
                resource.attributes["service.name"], "unknown_service"
            )
            self.assertEqual(resource.attributes["a"], "b")
            self.assertEqual(resource.attributes["c"], "d")
            self.assertIn(PROCESS_RUNTIME_NAME, resource.attributes.keys())
            self.assertIn(
                PROCESS_RUNTIME_DESCRIPTION, resource.attributes.keys()
            )
            self.assertIn(PROCESS_RUNTIME_VERSION, resource.attributes.keys())
            self.assertEqual(resource.schema_url, "")
