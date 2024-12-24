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
from unittest.mock import Mock, patch

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs._internal import (
    NoOpLogger,
    SynchronousMultiLogRecordProcessor,
)
from opentelemetry.sdk.environment_variables import OTEL_SDK_DISABLED
from opentelemetry.sdk.resources import Resource


class TestLoggerProvider(unittest.TestCase):
    def test_resource(self):
        """
        `LoggerProvider` provides a way to allow a `Resource` to be specified.
        """

        logger_provider_0 = LoggerProvider()
        logger_provider_1 = LoggerProvider()

        self.assertEqual(
            logger_provider_0.resource,
            logger_provider_1.resource,
        )
        self.assertIsInstance(logger_provider_0.resource, Resource)
        self.assertIsInstance(logger_provider_1.resource, Resource)

        resource = Resource({"key": "value"})
        self.assertIs(LoggerProvider(resource=resource).resource, resource)

    def test_get_logger(self):
        """
        `LoggerProvider.get_logger` arguments are used to create an
        `InstrumentationScope` object on the created `Logger`.
        """

        logger = LoggerProvider().get_logger(
            "name",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value"},
        )

        self.assertEqual(logger._instrumentation_scope.name, "name")
        self.assertEqual(logger._instrumentation_scope.version, "version")
        self.assertEqual(
            logger._instrumentation_scope.schema_url, "schema_url"
        )
        self.assertEqual(
            logger._instrumentation_scope.attributes, {"key": "value"}
        )

    @patch.dict("os.environ", {OTEL_SDK_DISABLED: "true"})
    def test_get_logger_with_sdk_disabled(self):
        logger = LoggerProvider().get_logger(Mock())

        self.assertIsInstance(logger, NoOpLogger)

    @patch.object(Resource, "create")
    def test_logger_provider_init(self, resource_patch):
        logger_provider = LoggerProvider()
        resource_patch.assert_called_once()
        self.assertIsNotNone(logger_provider._resource)
        self.assertTrue(
            isinstance(
                logger_provider._multi_log_record_processor,
                SynchronousMultiLogRecordProcessor,
            )
        )
        self.assertIsNotNone(logger_provider._at_exit_handler)
