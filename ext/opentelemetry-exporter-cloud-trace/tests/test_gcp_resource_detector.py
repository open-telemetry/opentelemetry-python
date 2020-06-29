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

from mock import patch

from opentelemetry.sdk.resources import Resource
from opentelemetry.tools.resource_detector import (
    _GCP_METADATA_URL_HEADER,
    GCEResourceFinder,
    GoogleCloudResourceDetector,
    GoogleResourceFinder,
)


class DummyRequest:
    def __init__(self, text):
        self.text = text


class TestGoogleResourceFinder(unittest.TestCase):
    def setUp(self):
        self.base_url = "base_url/"
        self.attribute_url = "attribute_url"

    @patch("opentelemetry.tools.resource_detector.requests.get")
    def test_get_attribute(self, getter):
        resource_finder = GoogleResourceFinder(self.base_url)
        getter.return_value = DummyRequest("resource_info")
        found_resource = resource_finder.get_attribute(self.attribute_url)
        self.assertEqual(found_resource, "resource_info")
        self.assertEqual(
            getter.call_args.args[0], self.base_url + self.attribute_url
        )
        self.assertEqual(
            getter.call_args.kwargs["headers"], _GCP_METADATA_URL_HEADER
        )

        resource_finder = GoogleResourceFinder(
            self.base_url, {self.attribute_url: lambda x: x + "_suffix"}
        )
        getter.return_value = DummyRequest("resource_info")
        found_resource = resource_finder.get_attribute(self.attribute_url)
        self.assertEqual(found_resource, "resource_info_suffix")

        getter.return_value = DummyRequest("other_resource_info")
        found_resource = resource_finder.get_attribute("other_url")
        self.assertEqual(found_resource, "other_resource_info")


# pylint:disable=unused-argument
def mock_return_resources(url, headers):
    url_to_resources = {
        "http://metadata.google.internal/computeMetadata/v1/instance/id": "instance_id",
        "http://metadata.google.internal/computeMetadata/v1/project/project-id": "project_id",
        "http://metadata.google.internal/computeMetadata/v1/instance/zone": "zone",
    }
    return DummyRequest(url_to_resources[url])


class TestGCEResourceFinder(unittest.TestCase):
    @patch("opentelemetry.tools.resource_detector.requests.get")
    def test_not_on_gce(self, getter):
        resource_finder = GCEResourceFinder()
        getter.side_effect = Exception()
        self.assertEqual(resource_finder.get_resources(), {})

    @patch("opentelemetry.tools.resource_detector.requests.get")
    def test_finding_gce_resources(self, getter):
        resource_finder = GCEResourceFinder()
        getter.side_effect = mock_return_resources
        found_resources = resource_finder.get_resources()
        self.assertEqual(
            getter.call_args_list[0].args[0],
            "http://metadata.google.internal/computeMetadata/v1/instance/id",
        )
        self.assertEqual(
            getter.call_args_list[1].args[0],
            "http://metadata.google.internal/computeMetadata/v1/project/project-id",
        )
        self.assertEqual(
            getter.call_args_list[2].args[0],
            "http://metadata.google.internal/computeMetadata/v1/instance/zone",
        )
        self.assertEqual(
            found_resources,
            {
                "host.id": "instance_id",
                "cloud.provider": "gcp",
                "cloud.account.id": "project_id",
                "cloud.zone": "zone",
            },
        )


class TestGoogleCloudResourceDetector(unittest.TestCase):
    @patch("opentelemetry.tools.resource_detector.requests.get")
    def test_finding_resources(self, getter):
        resource_finder = GoogleCloudResourceDetector()
        getter.side_effect = mock_return_resources
        found_resources = resource_finder.detect()
        self.assertEqual(
            getter.call_args_list[0].args[0],
            "http://metadata.google.internal/computeMetadata/v1/instance/id",
        )
        self.assertEqual(
            getter.call_args_list[1].args[0],
            "http://metadata.google.internal/computeMetadata/v1/project/project-id",
        )
        self.assertEqual(
            getter.call_args_list[2].args[0],
            "http://metadata.google.internal/computeMetadata/v1/instance/zone",
        )
        self.assertEqual(
            found_resources,
            Resource(
                labels={
                    "gce_instance": {
                        "host.id": "instance_id",
                        "cloud.provider": "gcp",
                        "cloud.account.id": "project_id",
                        "cloud.zone": "zone",
                    }
                }
            ),
        )
        self.assertEqual(getter.call_count, 3)

        found_resources = resource_finder.detect()
        self.assertEqual(getter.call_count, 3)
        self.assertEqual(
            found_resources,
            Resource(
                labels={
                    "gce_instance": {
                        "host.id": "instance_id",
                        "cloud.provider": "gcp",
                        "cloud.account.id": "project_id",
                        "cloud.zone": "zone",
                    }
                }
            ),
        )

    @patch("opentelemetry.tools.resource_detector.requests.get")
    def test_not_on_gcp(self, getter):
        resource_finder = GoogleCloudResourceDetector()
        getter.side_effect = Exception()
        found_resources = resource_finder.detect()
        self.assertEqual(found_resources, Resource.create_empty())
