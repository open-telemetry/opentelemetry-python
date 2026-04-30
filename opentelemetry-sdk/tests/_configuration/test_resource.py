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

import os
import socket
import sys
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration._resource import create_resource
from opentelemetry.sdk._configuration.models import (
    AttributeNameValue,
    AttributeType,
    ExperimentalResourceDetection,
    ExperimentalResourceDetector,
    IncludeExclude,
)
from opentelemetry.sdk._configuration.models import Resource as ResourceConfig
from opentelemetry.sdk.resources import (
    CONTAINER_ID,
    HOST_ARCH,
    HOST_NAME,
    PROCESS_PID,
    PROCESS_RUNTIME_NAME,
    SERVICE_INSTANCE_ID,
    SERVICE_NAME,
    TELEMETRY_SDK_LANGUAGE,
    TELEMETRY_SDK_NAME,
    TELEMETRY_SDK_VERSION,
    Resource,
)


class TestCreateResourceDefaults(unittest.TestCase):
    def test_none_config_returns_sdk_defaults(self):
        resource = create_resource(None)
        self.assertIsInstance(resource, Resource)
        self.assertEqual(resource.attributes[TELEMETRY_SDK_LANGUAGE], "python")
        self.assertEqual(
            resource.attributes[TELEMETRY_SDK_NAME], "opentelemetry"
        )
        self.assertIn(TELEMETRY_SDK_VERSION, resource.attributes)
        self.assertEqual(resource.attributes[SERVICE_NAME], "unknown_service")

    def test_none_config_does_not_read_env_vars(self):
        with patch.dict(
            os.environ,
            {
                "OTEL_RESOURCE_ATTRIBUTES": "foo=bar",
                "OTEL_SERVICE_NAME": "my-service",
            },
        ):
            resource = create_resource(None)
        self.assertNotIn("foo", resource.attributes)
        self.assertEqual(resource.attributes[SERVICE_NAME], "unknown_service")

    def test_empty_resource_config(self):
        resource = create_resource(ResourceConfig())
        self.assertEqual(resource.attributes[TELEMETRY_SDK_LANGUAGE], "python")
        self.assertEqual(resource.attributes[SERVICE_NAME], "unknown_service")

    def test_service_name_default_added_when_missing(self):
        config = ResourceConfig(
            attributes=[AttributeNameValue(name="env", value="staging")]
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes[SERVICE_NAME], "unknown_service")

    def test_service_name_not_overridden_when_set(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(name="service.name", value="my-app")
            ]
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes[SERVICE_NAME], "my-app")

    def test_env_vars_not_read(self):
        """OTEL_RESOURCE_ATTRIBUTES must not affect declarative config resource."""
        with patch.dict(
            os.environ,
            {"OTEL_RESOURCE_ATTRIBUTES": "injected=true"},
        ):
            config = ResourceConfig(
                attributes=[AttributeNameValue(name="k", value="v")]
            )
            resource = create_resource(config)
        self.assertNotIn("injected", resource.attributes)

    def test_schema_url(self):
        config = ResourceConfig(
            schema_url="https://opentelemetry.io/schemas/1.24.0"
        )
        resource = create_resource(config)
        self.assertEqual(
            resource.schema_url, "https://opentelemetry.io/schemas/1.24.0"
        )

    def test_schema_url_none(self):
        resource = create_resource(ResourceConfig())
        self.assertEqual(resource.schema_url, "")


class TestCreateResourceAttributes(unittest.TestCase):
    def test_attributes_plain(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(name="service.name", value="my-service"),
                AttributeNameValue(name="env", value="production"),
            ]
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes["service.name"], "my-service")
        self.assertEqual(resource.attributes["env"], "production")
        # SDK defaults still present
        self.assertEqual(resource.attributes[TELEMETRY_SDK_LANGUAGE], "python")

    def test_attribute_type_string(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="k", value=42, type=AttributeType.string
                )
            ]
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes["k"], "42")
        self.assertIsInstance(resource.attributes["k"], str)

    def test_attribute_type_int(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(name="k", value=3.0, type=AttributeType.int)
            ]
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes["k"], 3)
        self.assertIsInstance(resource.attributes["k"], int)

    def test_attribute_type_double(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="k", value="1.5", type=AttributeType.double
                )
            ]
        )
        resource = create_resource(config)
        self.assertAlmostEqual(resource.attributes["k"], 1.5)  # type: ignore[arg-type]
        self.assertIsInstance(resource.attributes["k"], float)

    def test_attribute_type_bool(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="k", value="true", type=AttributeType.bool
                )
            ]
        )
        resource = create_resource(config)
        self.assertTrue(resource.attributes["k"])

    def test_attribute_type_bool_false_string(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="k", value="false", type=AttributeType.bool
                )
            ]
        )
        resource = create_resource(config)
        self.assertFalse(resource.attributes["k"])

    def test_attribute_type_string_array(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="k",
                    value=["a", "b"],
                    type=AttributeType.string_array,
                )
            ]
        )
        resource = create_resource(config)
        self.assertEqual(list(resource.attributes["k"]), ["a", "b"])  # type: ignore[arg-type]

    def test_attribute_type_int_array(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="k",
                    value=[1.0, 2.0],
                    type=AttributeType.int_array,
                )
            ]
        )
        resource = create_resource(config)
        self.assertEqual(list(resource.attributes["k"]), [1, 2])  # type: ignore[arg-type]

    def test_attribute_type_double_array(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="k",
                    value=[1, 2],
                    type=AttributeType.double_array,
                )
            ]
        )
        resource = create_resource(config)
        self.assertEqual(list(resource.attributes["k"]), [1.0, 2.0])  # type: ignore[arg-type]

    def test_attribute_type_bool_array(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="k",
                    value=[True, False],
                    type=AttributeType.bool_array,
                )
            ]
        )
        resource = create_resource(config)
        self.assertEqual(list(resource.attributes["k"]), [True, False])  # type: ignore[arg-type]

    def test_attribute_type_bool_array_string_values(self):
        """bool_array must use _coerce_bool, not plain bool() — 'false' must be False."""
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="k",
                    value=["true", "false"],
                    type=AttributeType.bool_array,
                )
            ]
        )
        resource = create_resource(config)
        self.assertEqual(list(resource.attributes["k"]), [True, False])  # type: ignore[arg-type]


class TestCreateResourceAttributesList(unittest.TestCase):
    def test_attributes_list_parsed(self):
        config = ResourceConfig(
            attributes_list="service.name=my-svc,region=us-east-1"
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes["service.name"], "my-svc")
        self.assertEqual(resource.attributes["region"], "us-east-1")

    def test_attributes_list_does_not_override_attributes(self):
        """Explicit attributes take precedence over attributes_list."""
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(name="service.name", value="explicit")
            ],
            attributes_list="service.name=from-list,extra=val",
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes["service.name"], "explicit")
        self.assertEqual(resource.attributes["extra"], "val")

    def test_attributes_list_only_includes_sdk_defaults(self):
        """attributes_list alone should still include telemetry.sdk.* defaults."""
        config = ResourceConfig(attributes_list="env=prod")
        resource = create_resource(config)
        self.assertEqual(resource.attributes["env"], "prod")
        self.assertEqual(resource.attributes[TELEMETRY_SDK_LANGUAGE], "python")

    def test_attributes_list_value_containing_equals(self):
        """Values containing '=' should be preserved intact."""
        config = ResourceConfig(attributes_list="token=abc=def=ghi")
        resource = create_resource(config)
        self.assertEqual(resource.attributes["token"], "abc=def=ghi")

    def test_attributes_list_empty_pairs_skipped(self):
        config = ResourceConfig(attributes_list=",foo=bar,,")
        resource = create_resource(config)
        self.assertEqual(resource.attributes["foo"], "bar")

    def test_attributes_list_url_decoded(self):
        config = ResourceConfig(
            attributes_list="service.namespace=my%20namespace,region=us-east-1"
        )
        resource = create_resource(config)
        self.assertEqual(
            resource.attributes["service.namespace"], "my namespace"
        )

    def test_attributes_list_invalid_pair_skipped(self):
        with self.assertLogs(
            "opentelemetry.sdk._configuration._resource", level="WARNING"
        ) as cm:
            config = ResourceConfig(attributes_list="no-equals,foo=bar")
            resource = create_resource(config)
        self.assertEqual(resource.attributes["foo"], "bar")
        self.assertNotIn("no-equals", resource.attributes)
        self.assertTrue(any("no-equals" in msg for msg in cm.output))


class TestServiceResourceDetector(unittest.TestCase):
    @staticmethod
    def _config_with_service() -> ResourceConfig:
        return ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(service={})]
            )
        )

    def test_service_detector_adds_instance_id(self):
        resource = create_resource(self._config_with_service())
        self.assertIn(SERVICE_INSTANCE_ID, resource.attributes)

    def test_service_instance_id_is_unique_per_call(self):
        r1 = create_resource(self._config_with_service())
        r2 = create_resource(self._config_with_service())
        self.assertNotEqual(
            r1.attributes[SERVICE_INSTANCE_ID],
            r2.attributes[SERVICE_INSTANCE_ID],
        )

    def test_service_detector_reads_otel_service_name_env_var(self):
        with patch.dict(os.environ, {"OTEL_SERVICE_NAME": "my-service"}):
            resource = create_resource(self._config_with_service())
        self.assertEqual(resource.attributes[SERVICE_NAME], "my-service")

    def test_service_detector_no_env_var_leaves_default_service_name(self):
        with patch.dict(os.environ, {}, clear=True):
            resource = create_resource(self._config_with_service())
        self.assertEqual(resource.attributes[SERVICE_NAME], "unknown_service")

    def test_explicit_service_name_overrides_env_var(self):
        """Config attributes win over the service detector's env-var value."""
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(name="service.name", value="explicit-svc")
            ],
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(service={})]
            ),
        )
        with patch.dict(os.environ, {"OTEL_SERVICE_NAME": "env-svc"}):
            resource = create_resource(config)
        self.assertEqual(resource.attributes[SERVICE_NAME], "explicit-svc")

    def test_service_detector_not_run_when_absent(self):
        resource = create_resource(ResourceConfig())
        self.assertNotIn(SERVICE_INSTANCE_ID, resource.attributes)

    def test_service_detector_not_run_when_detection_development_is_none(self):
        resource = create_resource(ResourceConfig(detection_development=None))
        self.assertNotIn(SERVICE_INSTANCE_ID, resource.attributes)

    def test_service_detector_also_includes_sdk_defaults(self):
        resource = create_resource(self._config_with_service())
        self.assertEqual(resource.attributes[TELEMETRY_SDK_LANGUAGE], "python")
        self.assertIn(TELEMETRY_SDK_VERSION, resource.attributes)

    def test_included_filter_limits_service_attributes(self):
        config = ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(service={})],
                attributes=IncludeExclude(included=["service.instance.id"]),
            )
        )
        with patch.dict(os.environ, {"OTEL_SERVICE_NAME": "my-service"}):
            resource = create_resource(config)
        self.assertIn(SERVICE_INSTANCE_ID, resource.attributes)
        # service.name comes from the filter-excluded detector output, but the
        # default "unknown_service" is still added by create_resource directly
        self.assertEqual(resource.attributes[SERVICE_NAME], "unknown_service")


class TestHostResourceDetector(unittest.TestCase):
    @staticmethod
    def _config_with_host() -> ResourceConfig:
        return ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(host={})]
            )
        )

    def test_host_detector_adds_host_attributes(self):
        resource = create_resource(self._config_with_host())
        self.assertIn(HOST_NAME, resource.attributes)
        self.assertEqual(resource.attributes[HOST_NAME], socket.gethostname())
        self.assertIn(HOST_ARCH, resource.attributes)

    def test_host_detector_also_includes_sdk_defaults(self):
        resource = create_resource(self._config_with_host())
        self.assertEqual(resource.attributes[TELEMETRY_SDK_LANGUAGE], "python")
        self.assertIn(TELEMETRY_SDK_VERSION, resource.attributes)

    def test_host_detector_not_run_when_absent(self):
        resource = create_resource(ResourceConfig())
        self.assertNotIn(HOST_NAME, resource.attributes)
        self.assertNotIn(HOST_ARCH, resource.attributes)

    def test_host_detector_not_run_when_detection_development_is_none(self):
        resource = create_resource(ResourceConfig(detection_development=None))
        self.assertNotIn(HOST_NAME, resource.attributes)

    def test_host_detector_not_run_when_detectors_list_empty(self):
        config = ResourceConfig(
            detection_development=ExperimentalResourceDetection(detectors=[])
        )
        resource = create_resource(config)
        self.assertNotIn(HOST_NAME, resource.attributes)

    def test_explicit_attributes_override_host_detector(self):
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(name="host.name", value="custom-host")
            ],
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(host={})]
            ),
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes[HOST_NAME], "custom-host")

    def test_included_filter_limits_host_attributes(self):
        config = ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(host={})],
                attributes=IncludeExclude(included=["host.name"]),
            )
        )
        resource = create_resource(config)
        self.assertIn(HOST_NAME, resource.attributes)
        self.assertNotIn(HOST_ARCH, resource.attributes)

    def test_excluded_filter_removes_host_attributes(self):
        config = ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(host={})],
                attributes=IncludeExclude(excluded=["host.name"]),
            )
        )
        resource = create_resource(config)
        self.assertNotIn(HOST_NAME, resource.attributes)
        self.assertIn(HOST_ARCH, resource.attributes)


class TestContainerResourceDetector(unittest.TestCase):
    @staticmethod
    def _config_with_container() -> ResourceConfig:
        return ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(container={})]
            )
        )

    def test_container_detector_not_run_when_absent(self):
        resource = create_resource(ResourceConfig())
        self.assertNotIn(CONTAINER_ID, resource.attributes)

    def test_container_detector_not_run_when_detection_development_is_none(
        self,
    ):
        resource = create_resource(ResourceConfig(detection_development=None))
        self.assertNotIn(CONTAINER_ID, resource.attributes)

    def test_container_detector_not_run_when_detectors_list_empty(self):
        config = ResourceConfig(
            detection_development=ExperimentalResourceDetection(detectors=[])
        )
        resource = create_resource(config)
        self.assertNotIn(CONTAINER_ID, resource.attributes)

    def test_container_detector_raises_when_package_missing(self):
        """ConfigurationError is raised when the contrib entry point is not found."""
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[],
        ):
            with self.assertRaises(ConfigurationError):
                create_resource(self._config_with_container())

    def test_container_detector_uses_contrib_when_available(self):
        """When the contrib entry point is registered, container.id is detected."""
        mock_resource = Resource({CONTAINER_ID: "abc123"})
        mock_detector = MagicMock()
        mock_detector.return_value.detect.return_value = mock_resource
        mock_ep = MagicMock()
        mock_ep.load.return_value = mock_detector

        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            resource = create_resource(self._config_with_container())

        self.assertEqual(resource.attributes[CONTAINER_ID], "abc123")

    def test_explicit_attributes_override_container_detector(self):
        """Config attributes win over detector-provided values."""
        mock_resource = Resource({CONTAINER_ID: "detected-id"})
        mock_detector = MagicMock()
        mock_detector.return_value.detect.return_value = mock_resource
        mock_ep = MagicMock()
        mock_ep.load.return_value = mock_detector

        config = ResourceConfig(
            attributes=[
                AttributeNameValue(name="container.id", value="explicit-id")
            ],
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(container={})]
            ),
        )
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            resource = create_resource(config)

        self.assertEqual(resource.attributes[CONTAINER_ID], "explicit-id")


class TestProcessResourceDetector(unittest.TestCase):
    @staticmethod
    def _config_with_process() -> ResourceConfig:
        return ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(process={})]
            )
        )

    def test_process_detector_adds_process_attributes(self):
        resource = create_resource(self._config_with_process())
        self.assertIn(PROCESS_PID, resource.attributes)
        self.assertEqual(resource.attributes[PROCESS_PID], os.getpid())
        self.assertEqual(
            resource.attributes[PROCESS_RUNTIME_NAME],
            sys.implementation.name,
        )

    def test_process_detector_also_includes_sdk_defaults(self):
        resource = create_resource(self._config_with_process())
        self.assertEqual(resource.attributes[TELEMETRY_SDK_LANGUAGE], "python")
        self.assertIn(TELEMETRY_SDK_VERSION, resource.attributes)

    def test_process_detector_not_run_when_absent(self):
        resource = create_resource(ResourceConfig())
        self.assertNotIn(PROCESS_PID, resource.attributes)

    def test_process_detector_not_run_when_detection_development_is_none(self):
        resource = create_resource(ResourceConfig(detection_development=None))
        self.assertNotIn(PROCESS_PID, resource.attributes)

    def test_process_detector_not_run_when_detectors_list_empty(self):
        config = ResourceConfig(
            detection_development=ExperimentalResourceDetection(detectors=[])
        )
        resource = create_resource(config)
        self.assertNotIn(PROCESS_PID, resource.attributes)

    def test_explicit_attributes_override_process_detector(self):
        """Config attributes win over detector-provided values."""
        config = ResourceConfig(
            attributes=[
                AttributeNameValue(
                    name="process.pid", value=99999, type=AttributeType.int
                )
            ],
            detection_development=ExperimentalResourceDetection(
                detectors=[ExperimentalResourceDetector(process={})]
            ),
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes[PROCESS_PID], 99999)

    def test_multiple_detector_entries_run_process_once(self):
        """Multiple detector list entries each with process={} should still work."""
        config = ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                detectors=[
                    ExperimentalResourceDetector(process={}),
                    ExperimentalResourceDetector(process={}),
                ]
            )
        )
        resource = create_resource(config)
        self.assertEqual(resource.attributes[PROCESS_PID], os.getpid())


class TestPluginResourceDetector(unittest.TestCase):
    def test_plugin_detector_loaded_via_entry_point(self):
        mock_resource = Resource({"custom.attr": "value"})
        mock_detector = MagicMock()
        mock_detector.return_value.detect.return_value = mock_resource
        mock_ep = MagicMock()
        mock_ep.load.return_value = mock_detector

        config = ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                # pylint: disable=unexpected-keyword-arg
                detectors=[ExperimentalResourceDetector(my_custom_detector={})]
            )
        )
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            resource = create_resource(config)

        self.assertEqual(resource.attributes["custom.attr"], "value")

    def test_unknown_detector_raises_configuration_error(self):
        config = ResourceConfig(
            detection_development=ExperimentalResourceDetection(
                # pylint: disable=unexpected-keyword-arg
                detectors=[ExperimentalResourceDetector(no_such_detector={})]
            )
        )
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[],
        ):
            with self.assertRaises(ConfigurationError):
                create_resource(config)
