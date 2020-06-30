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

import json
import unittest
from unittest import mock

from opentelemetry.sdk.resources import Resource
from opentelemetry.tools.resource_detector import (
    _GCE_METADATA_URL,
    GoogleCloudResourceDetector,
    get_gce_resources,
)


class DummyRequest:
    def __init__(self, text):
        self.text = text

    def json(self):
        return json.loads(self.text)


# pylint: disable=unused-argument
def mock_return_resources(url, headers):
    return DummyRequest(
        json.dumps(
            {
                "instance": {
                    "id": "instance_id",
                    "zone": "projects/123/zones/zone",
                },
                "project": {"projectId": "project_id"},
            }
        )
    )


class TestGCEResourceFinder(unittest.TestCase):
    @mock.patch("opentelemetry.tools.resource_detector.requests.get")
    def test_not_on_gce(self, getter):
        getter.side_effect = Exception()
        self.assertEqual(get_gce_resources(), {})

    @mock.patch("opentelemetry.tools.resource_detector.requests.get")
    def test_finding_gce_resources(self, getter):
        getter.side_effect = mock_return_resources
        found_resources = get_gce_resources()
        self.assertEqual(getter.call_args_list[0][0][0], _GCE_METADATA_URL)
        self.assertEqual(
            found_resources,
            {
                "host.id": "instance_id",
                "cloud.provider": "gcp",
                "cloud.account.id": "project_id",
                "cloud.zone": "zone",
                "gcp.resource_type": "gce_instance",
            },
        )


class TestGoogleCloudResourceDetector(unittest.TestCase):
    @mock.patch("opentelemetry.tools.resource_detector.requests.get")
    def test_finding_resources(self, getter):
        resource_finder = GoogleCloudResourceDetector()
        getter.side_effect = mock_return_resources
        found_resources = resource_finder.detect()
        self.assertEqual(getter.call_args_list[0][0][0], _GCE_METADATA_URL)
        self.assertEqual(
            found_resources,
            Resource(
                labels={
                    "host.id": "instance_id",
                    "cloud.provider": "gcp",
                    "cloud.account.id": "project_id",
                    "cloud.zone": "zone",
                    "gcp.resource_type": "gce_instance",
                }
            ),
        )
        self.assertEqual(getter.call_count, 1)

        found_resources = resource_finder.detect()
        self.assertEqual(getter.call_count, 1)
        self.assertEqual(
            found_resources,
            Resource(
                labels={
                    "host.id": "instance_id",
                    "cloud.provider": "gcp",
                    "cloud.account.id": "project_id",
                    "cloud.zone": "zone",
                    "gcp.resource_type": "gce_instance",
                }
            ),
        )

    @mock.patch("opentelemetry.tools.resource_detector.requests.get")
    def test_not_on_gcp(self, getter):
        resource_finder = GoogleCloudResourceDetector()
        getter.side_effect = Exception()
        found_resources = resource_finder.detect()
        self.assertEqual(found_resources, Resource.create_empty())
