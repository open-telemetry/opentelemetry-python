# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=too-many-lines

import os
import subprocess
import sys
import unittest
import uuid
from concurrent.futures import TimeoutError
from logging import ERROR, WARNING
from os import environ
from unittest.mock import Mock, patch
from urllib import parse

import opentelemetry.sdk.resources as _resources_module
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPERIMENTAL_RESOURCE_DETECTORS,
)
from opentelemetry.sdk.resources import (
    _DEFAULT_RESOURCE,
    _EMPTY_RESOURCE,
    _OPENTELEMETRY_SDK_VERSION,
    HOST_ARCH,
    HOST_NAME,
    OS_TYPE,
    OS_VERSION,
    OTEL_RESOURCE_ATTRIBUTES,
    OTEL_SERVICE_NAME,
    PROCESS_COMMAND,
    PROCESS_COMMAND_ARGS,
    PROCESS_COMMAND_LINE,
    PROCESS_EXECUTABLE_NAME,
    PROCESS_EXECUTABLE_PATH,
    PROCESS_OWNER,
    PROCESS_PARENT_PID,
    PROCESS_PID,
    PROCESS_RUNTIME_DESCRIPTION,
    PROCESS_RUNTIME_NAME,
    PROCESS_RUNTIME_VERSION,
    SERVICE_INSTANCE_ID,
    SERVICE_NAME,
    TELEMETRY_SDK_LANGUAGE,
    TELEMETRY_SDK_NAME,
    TELEMETRY_SDK_VERSION,
    OsResourceDetector,
    OTELResourceDetector,
    ProcessResourceDetector,
    Resource,
    ResourceDetector,
    ServiceInstanceIdResourceDetector,
    _get_process_dependent_resource,
    _HostResourceDetector,
    get_aggregated_resources,
)
from opentelemetry.util._importlib_metadata import (
    entry_points as real_entry_points,
)

try:
    import psutil
except ImportError:
    psutil = None


class DefaultResourceDetector(ResourceDetector):
    def detect(self) -> Resource:
        return Resource.get_empty()


class ProcessDependentResourceDetector(ResourceDetector):
    def __init__(
        self, resource: Resource, process_dependent: bool = False
    ) -> None:
        super().__init__()
        self.resource = resource
        self.process_dependent = process_dependent

    def detect(self) -> Resource:
        return self.resource

    def is_process_dependent(self) -> bool:
        return self.process_dependent


# pylint: disable-next=too-many-public-methods
class TestResources(unittest.TestCase):
    def setUp(self) -> None:
        environ[OTEL_RESOURCE_ATTRIBUTES] = ""
        self._service_instance_id = (
            ServiceInstanceIdResourceDetector()
            .detect()
            .attributes[SERVICE_INSTANCE_ID]
        )

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
            SERVICE_INSTANCE_ID: self._service_instance_id,
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

        expected_default = _DEFAULT_RESOURCE.merge(
            Resource(
                {
                    SERVICE_INSTANCE_ID: self._service_instance_id,
                    SERVICE_NAME: "unknown_service",
                },
                "",
            )
        )

        resource = Resource.create(None)
        self.assertEqual(resource, expected_default)
        self.assertEqual(resource.schema_url, "")

        resource = Resource.create(None, None)
        self.assertEqual(resource, expected_default)
        self.assertEqual(resource.schema_url, "")

        resource = Resource.create({})
        self.assertEqual(resource, expected_default)
        self.assertEqual(resource.schema_url, "")

        resource = Resource.create({}, None)
        self.assertEqual(resource, expected_default)
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
            SERVICE_INSTANCE_ID: self._service_instance_id,
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
        # This class has no __str__ or __repr__ method, so BoundedAttributes does
        # not attempt to convert it to a string and defaults to returning None.
        class NoStrNoRepr:
            def __init__(self):
                pass

        with self.assertLogs(level=WARNING):
            resource = Resource(
                {
                    SERVICE_NAME: "test",
                    "bad-type": NoStrNoRepr(),
                    "": "empty-key-value",
                }
            )
        self.assertEqual(
            resource.attributes,
            {
                SERVICE_NAME: "test",
                "bad-type": None,
            },
        )
        self.assertEqual(len(resource.attributes), 2)

    def test_aggregated_resources_no_detectors(self):
        aggregated_resources = get_aggregated_resources([])
        self.assertEqual(
            aggregated_resources,
            _DEFAULT_RESOURCE.merge(
                Resource(
                    {
                        SERVICE_INSTANCE_ID: self._service_instance_id,
                        SERVICE_NAME: "unknown_service",
                    },
                    "",
                )
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
                Resource(
                    {
                        SERVICE_INSTANCE_ID: self._service_instance_id,
                        SERVICE_NAME: "unknown_service",
                    },
                    "",
                )
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
                Resource(
                    {
                        SERVICE_INSTANCE_ID: self._service_instance_id,
                        SERVICE_NAME: "unknown_service",
                    },
                    "",
                )
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
                    Resource(
                        {
                            SERVICE_INSTANCE_ID: self._service_instance_id,
                            SERVICE_NAME: "unknown_service",
                        },
                        "",
                    )
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
                    Resource(
                        {
                            SERVICE_INSTANCE_ID: self._service_instance_id,
                            SERVICE_NAME: "unknown_service",
                        },
                        "",
                    )
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
        with self.assertLogs(level=WARNING):
            self.assertEqual(
                get_aggregated_resources([resource_detector]),
                _DEFAULT_RESOURCE.merge(
                    Resource(
                        {
                            SERVICE_INSTANCE_ID: self._service_instance_id,
                            SERVICE_NAME: "unknown_service",
                        },
                        "",
                    )
                ),
            )

    def test_resource_detector_raise_error(self):
        resource_detector = Mock(spec=ResourceDetector)
        resource_detector.detect.side_effect = Exception()
        resource_detector.raise_on_error = True
        self.assertRaises(
            Exception, get_aggregated_resources, [resource_detector]
        )

    def test_resource_detector_is_not_process_dependent_by_default(self):
        self.assertFalse(DefaultResourceDetector().is_process_dependent())

    def test_process_resource_detector_is_process_dependent(self):
        self.assertTrue(ProcessResourceDetector().is_process_dependent())

    @patch("opentelemetry.sdk.resources._build_resource_detectors")
    def test_get_process_dependent_resource(
        self, build_resource_detectors_mock
    ):
        build_resource_detectors_mock.return_value = [
            ProcessDependentResourceDetector(Resource({"ignored": "ignored"})),
            ProcessDependentResourceDetector(
                Resource({"one": "one", "two": "old"}), process_dependent=True
            ),
            ProcessDependentResourceDetector(
                Resource({"two": "new", "three": "three"}),
                process_dependent=True,
            ),
        ]

        self.assertEqual(
            _get_process_dependent_resource(),
            Resource({"one": "one", "two": "new", "three": "three"}),
        )

    @patch("opentelemetry.sdk.resources._build_resource_detectors")
    def test_get_process_dependent_resource_empty(
        self, build_resource_detectors_mock
    ):
        build_resource_detectors_mock.return_value = [
            ProcessDependentResourceDetector(Resource({"ignored": "ignored"})),
        ]

        self.assertEqual(
            _get_process_dependent_resource(), Resource.get_empty()
        )

    @patch("opentelemetry.sdk.resources.logger")
    def test_resource_detector_timeout(self, mock_logger):
        resource_detector = Mock(spec=ResourceDetector)
        resource_detector.detect.side_effect = TimeoutError()
        resource_detector.raise_on_error = False
        self.assertEqual(
            get_aggregated_resources([resource_detector]),
            _DEFAULT_RESOURCE.merge(
                Resource(
                    {
                        SERVICE_INSTANCE_ID: self._service_instance_id,
                        SERVICE_NAME: "unknown_service",
                    },
                    "",
                )
            ),
        )
        mock_logger.warning.assert_called_with(
            "Detector %s took longer than %s seconds, skipping",
            resource_detector,
            5,
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


# pylint: disable=too-many-public-methods
def _make_detector_ep(resource):
    return Mock(
        **{
            "load.return_value": Mock(
                return_value=Mock(**{"detect.return_value": resource})
            )
        }
    )


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
        with self.assertLogs(level=WARNING):
            self.assertEqual(
                detector.detect(),
                Resource({"k": "v", "k2": "v2", "foo": "bar=baz"}),
            )

    def test_multiple_with_url_decode(self):
        detector = OTELResourceDetector()
        environ[OTEL_RESOURCE_ATTRIBUTES] = (
            "key=value%20test%0A, key2=value+%202"
        )
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

    @patch(
        "sys.orig_argv",
        ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
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

        self.assertEqual(
            aggregated_resource.attributes[PROCESS_PID], os.getpid()
        )
        if hasattr(os, "getppid"):
            self.assertEqual(
                aggregated_resource.attributes[PROCESS_PARENT_PID],
                os.getppid(),
            )

        if psutil is not None:
            self.assertEqual(
                aggregated_resource.attributes[PROCESS_OWNER],
                psutil.Process().username(),
            )

        self.assertEqual(
            aggregated_resource.attributes[PROCESS_EXECUTABLE_NAME],
            sys.executable,
        )
        self.assertEqual(
            aggregated_resource.attributes[PROCESS_EXECUTABLE_PATH],
            os.path.dirname(sys.executable),
        )
        self.assertEqual(
            aggregated_resource.attributes[PROCESS_COMMAND], sys.orig_argv[0]
        )
        self.assertNotIn(
            PROCESS_COMMAND_LINE,
            aggregated_resource.attributes,
        )
        self.assertNotIn(
            PROCESS_COMMAND_ARGS,
            aggregated_resource.attributes,
        )

    @patch(
        "sys.orig_argv",
        ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
    )
    def test_process_detector_includes_command_args_on_opt_in(self):
        initial_resource = Resource({"foo": "bar"})
        aggregated_resource = get_aggregated_resources(
            [ProcessResourceDetector(include_command_args=True)],
            initial_resource,
        )

        self.assertEqual(
            aggregated_resource.attributes[PROCESS_COMMAND_LINE],
            " ".join(sys.orig_argv),
        )
        self.assertEqual(
            aggregated_resource.attributes[PROCESS_COMMAND_ARGS],
            tuple(sys.orig_argv),
        )

    def test_process_detector_does_not_iterate_orig_argv_by_default(self):
        class SensitiveOrigArgv:
            def __getitem__(self, index):
                if index == 0:
                    return "uvicorn"
                raise AssertionError("unexpected argv access")

            def __iter__(self):
                raise AssertionError("unexpected argv iteration")

        with patch("sys.orig_argv", SensitiveOrigArgv()):
            aggregated_resource = get_aggregated_resources(
                [ProcessResourceDetector()],
                Resource({"foo": "bar"}),
            )

        self.assertEqual(
            aggregated_resource.attributes[PROCESS_COMMAND],
            "uvicorn",
        )
        self.assertNotIn(
            PROCESS_COMMAND_LINE,
            aggregated_resource.attributes,
        )
        self.assertNotIn(
            PROCESS_COMMAND_ARGS,
            aggregated_resource.attributes,
        )

    @patch("sys.orig_argv", ["/usr/bin/python", "-m", "myapp"])
    def test_process_detector_uses_orig_argv_for_python_m(self):
        """For ``python -m <module>`` invocations sys.argv[0] is rewritten to
        the resolved module path, losing the ``-m <module>`` information.
        sys.orig_argv preserves the original invocation and must be preferred.
        See https://github.com/open-telemetry/opentelemetry-python/issues/4518.
        """
        aggregated_resource = get_aggregated_resources(
            [ProcessResourceDetector()], Resource({"foo": "bar"})
        )

        self.assertEqual(
            aggregated_resource.attributes[PROCESS_COMMAND],
            "/usr/bin/python",
        )
        self.assertNotIn(
            PROCESS_COMMAND_LINE,
            aggregated_resource.attributes,
        )
        self.assertNotIn(
            PROCESS_COMMAND_ARGS,
            aggregated_resource.attributes,
        )

    @patch("sys.orig_argv", ["/usr/bin/python", "-m", "myapp"])
    def test_process_detector_uses_orig_argv_for_python_m_on_opt_in(self):
        aggregated_resource = get_aggregated_resources(
            [ProcessResourceDetector(include_command_args=True)],
            Resource({"foo": "bar"}),
        )

        self.assertEqual(
            aggregated_resource.attributes[PROCESS_COMMAND],
            "/usr/bin/python",
        )
        self.assertEqual(
            aggregated_resource.attributes[PROCESS_COMMAND_LINE],
            "/usr/bin/python -m myapp",
        )
        self.assertEqual(
            aggregated_resource.attributes[PROCESS_COMMAND_ARGS],
            ("/usr/bin/python", "-m", "myapp"),
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
        "opentelemetry.util._importlib_metadata.entry_points",
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

    @patch.dict(
        environ, {OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: ""}, clear=True
    )
    def test_resource_detector_entry_points_empty(self):
        resource = Resource({}).create()
        self.assertEqual(
            resource.attributes["telemetry.sdk.language"], "python"
        )

    @patch.dict(
        environ, {OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: "os"}, clear=True
    )
    def test_resource_detector_entry_points_os(self):
        resource = Resource({}).create()

        self.assertIn(OS_TYPE, resource.attributes)
        self.assertIn(OS_VERSION, resource.attributes)

    @patch.dict(
        environ, {OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: "*"}, clear=True
    )
    def test_resource_detector_entry_points_all(self):
        resource = Resource({}).create()

        self.assertIn(
            TELEMETRY_SDK_NAME,
            resource.attributes,
            "'otel' resource detector not enabled",
        )
        self.assertIn(
            OS_TYPE, resource.attributes, "'os' resource detector not enabled"
        )
        self.assertIn(
            HOST_ARCH,
            resource.attributes,
            "'host' resource detector not enabled",
        )
        self.assertIn(
            PROCESS_RUNTIME_NAME,
            resource.attributes,
            "'process' resource detector not enabled",
        )

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
                resource.attributes["service.name"],
                "unknown_service:"
                + resource.attributes["process.executable.name"],
            )
            self.assertEqual(resource.attributes["a"], "b")
            self.assertEqual(resource.attributes["c"], "d")
            self.assertIn(PROCESS_RUNTIME_NAME, resource.attributes.keys())
            self.assertIn(
                PROCESS_RUNTIME_DESCRIPTION, resource.attributes.keys()
            )
            self.assertIn(PROCESS_RUNTIME_VERSION, resource.attributes.keys())
            self.assertEqual(resource.schema_url, "")

    @patch.dict(
        environ,
        {OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: "mock_a,mock_b"},
        clear=True,
    )
    def test_resource_detector_ordering_last_wins(self):
        """Last detector in OTEL_EXPERIMENTAL_RESOURCE_DETECTORS wins on conflict."""
        ep_a = _make_detector_ep(Resource({"conflict_key": "from_a"}))
        ep_b = _make_detector_ep(Resource({"conflict_key": "from_b"}))

        def side_effect(*args, **kwargs):
            return {"mock_a": [ep_a], "mock_b": [ep_b]}.get(
                kwargs.get("name", ""), []
            )

        with patch(
            "opentelemetry.util._importlib_metadata.entry_points",
            side_effect=side_effect,
        ):
            resource = Resource({}).create()

        self.assertEqual(resource.attributes["conflict_key"], "from_b")

    @patch.dict(
        environ,
        {
            OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: "mock",
            OTEL_RESOURCE_ATTRIBUTES: "conflict_key=otel_value",
        },
        clear=True,
    )
    def test_otel_detector_appended_last(self):
        """'otel' detector is always appended last, so its attributes win over earlier detectors."""
        ep_mock = _make_detector_ep(Resource({"conflict_key": "mock_value"}))

        def side_effect(*args, **kwargs):
            if kwargs.get("name") == "mock":
                return [ep_mock]
            return real_entry_points(*args, **kwargs)

        with patch(
            "opentelemetry.util._importlib_metadata.entry_points",
            side_effect=side_effect,
        ):
            resource = Resource({}).create()

        self.assertEqual(resource.attributes["conflict_key"], "otel_value")

    @patch("platform.system", lambda: "Linux")
    @patch("platform.release", lambda: "666.5.0-35-generic")
    def test_os_detector_linux(self):
        resource = get_aggregated_resources(
            [OsResourceDetector()],
            Resource({}),
        )

        self.assertEqual(resource.attributes[OS_TYPE], "linux")
        self.assertEqual(resource.attributes[OS_VERSION], "666.5.0-35-generic")

    @patch("platform.system", lambda: "Windows")
    @patch("platform.version", lambda: "10.0.666")
    def test_os_detector_windows(self):
        resource = get_aggregated_resources(
            [OsResourceDetector()],
            Resource({}),
        )

        self.assertEqual(resource.attributes[OS_TYPE], "windows")
        self.assertEqual(resource.attributes[OS_VERSION], "10.0.666")

    @patch("platform.system", lambda: "SunOS")
    @patch("platform.version", lambda: "666.4.0.15.0")
    def test_os_detector_solaris(self):
        resource = get_aggregated_resources(
            [OsResourceDetector()],
            Resource({}),
        )

        self.assertEqual(resource.attributes[OS_TYPE], "solaris")
        self.assertEqual(resource.attributes[OS_VERSION], "666.4.0.15.0")


class TestHostResourceDetector(unittest.TestCase):
    @patch("socket.gethostname", lambda: "foo")
    @patch("platform.machine", lambda: "AMD64")
    def test_host_resource_detector(self):
        resource = get_aggregated_resources(
            [_HostResourceDetector()],
            Resource({}),
        )
        self.assertEqual(resource.attributes[HOST_NAME], "foo")
        self.assertEqual(resource.attributes[HOST_ARCH], "AMD64")

    @patch.dict(
        environ, {OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: "host"}, clear=True
    )
    def test_resource_detector_entry_points_host(self):
        resource = Resource({}).create()
        self.assertIn(HOST_NAME, resource.attributes)
        self.assertIn(HOST_ARCH, resource.attributes)

    @patch.dict(
        environ,
        {OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: "doesnotexist,host"},
        clear=True,
    )
    def test_resource_detector_entry_points_tolerate_missing_detector(self):
        resource = Resource({}).create()
        self.assertEqual(
            resource.attributes["telemetry.sdk.language"], "python"
        )
        self.assertIn(HOST_NAME, resource.attributes)


# pylint: disable=protected-access
class TestServiceInstanceIdResourceDetector(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_instance_id = _resources_module._service_instance_id
        self._orig_instance_pid = _resources_module._service_instance_id_pid

    def tearDown(self) -> None:
        _resources_module._service_instance_id = self._orig_instance_id
        _resources_module._service_instance_id_pid = self._orig_instance_pid

    def test_is_process_dependent(self):
        self.assertTrue(
            ServiceInstanceIdResourceDetector().is_process_dependent()
        )

    def test_detect_value_is_valid_uuid4(self):
        _resources_module._service_instance_id = None
        _resources_module._service_instance_id_pid = None
        detector = ServiceInstanceIdResourceDetector()
        value = detector.detect().attributes[SERVICE_INSTANCE_ID]
        parsed = uuid.UUID(value)
        self.assertEqual(parsed.version, 4)

    def test_detect_stable_within_instance(self):
        _resources_module._service_instance_id = None
        _resources_module._service_instance_id_pid = None
        detector = ServiceInstanceIdResourceDetector()
        id1 = detector.detect().attributes[SERVICE_INSTANCE_ID]
        id2 = detector.detect().attributes[SERVICE_INSTANCE_ID]
        self.assertEqual(id1, id2)

    def test_detect_shared_across_instances(self):
        _resources_module._service_instance_id = None
        _resources_module._service_instance_id_pid = None
        id1 = (
            ServiceInstanceIdResourceDetector()
            .detect()
            .attributes[SERVICE_INSTANCE_ID]
        )
        id2 = (
            ServiceInstanceIdResourceDetector()
            .detect()
            .attributes[SERVICE_INSTANCE_ID]
        )
        self.assertEqual(id1, id2)

    def test_detect_pid_change_generates_new_id(self):
        _resources_module._service_instance_id = "old-id"
        _resources_module._service_instance_id_pid = os.getpid() - 1
        new_id = (
            ServiceInstanceIdResourceDetector()
            .detect()
            .attributes[SERVICE_INSTANCE_ID]
        )
        self.assertNotEqual(new_id, "old-id")
        self.assertEqual(
            _resources_module._service_instance_id_pid, os.getpid()
        )
        uuid.UUID(new_id)

    def test_detect_pid_unchanged_returns_same_id(self):
        known_id = "known-stable-id"
        _resources_module._service_instance_id = known_id
        _resources_module._service_instance_id_pid = os.getpid()
        result = (
            ServiceInstanceIdResourceDetector()
            .detect()
            .attributes[SERVICE_INSTANCE_ID]
        )
        self.assertEqual(result, known_id)

    @unittest.skipUnless(hasattr(os, "fork"), "requires os.fork")
    def test_detect_fork_generates_new_id(self):
        script = """\
import os
import sys

from opentelemetry.sdk.resources import ServiceInstanceIdResourceDetector, SERVICE_INSTANCE_ID

parent_id = ServiceInstanceIdResourceDetector().detect().attributes[SERVICE_INSTANCE_ID]

pid = os.fork()
if not pid:
    child_id = ServiceInstanceIdResourceDetector().detect().attributes[SERVICE_INSTANCE_ID]
    print(f"child:{child_id}", flush=True)
    os._exit(0)
else:
    os.waitpid(pid, 0)
    print(f"parent:{parent_id}", flush=True)
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
        )
        ids = dict(
            line.split(":", 1) for line in result.stdout.strip().splitlines()
        )
        parent_id, child_id = ids["parent"], ids["child"]
        self.assertNotEqual(parent_id, child_id)
        self.assertEqual(uuid.UUID(parent_id).version, 4)
        self.assertEqual(uuid.UUID(child_id).version, 4)

    @patch.dict(
        environ,
        {OTEL_EXPERIMENTAL_RESOURCE_DETECTORS: "service_instance"},
        clear=True,
    )
    def test_resource_detector_entry_points_service_instance(self):
        resource = Resource.create()
        self.assertIn(SERVICE_INSTANCE_ID, resource.attributes)
        uuid.UUID(resource.attributes[SERVICE_INSTANCE_ID])
