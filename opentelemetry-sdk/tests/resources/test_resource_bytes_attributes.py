# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""`bytes` is a valid attribute value type, so a Resource carrying one must
stay hashable and serialisable.

Every OTLP encoder groups telemetry by using the Resource as a dict key, so a
Resource that cannot be hashed takes the whole export path down with it.
"""

import json
import unittest

from opentelemetry.sdk.resources import Resource

_BYTES_RESOURCE = {"service.name": "svc", "build.id": b"\x01\x02\x03"}


class TestResourceWithBytesAttribute(unittest.TestCase):
    def setUp(self):
        self.resource = Resource.create(_BYTES_RESOURCE)

    def test_resource_is_hashable(self):
        hash(self.resource)

    def test_resource_usable_as_dict_key(self):
        """OTLP encoders group telemetry by Resource identity."""
        self.assertEqual({self.resource: "value"}[self.resource], "value")

    def test_resource_to_json_is_valid_json(self):
        payload = json.loads(self.resource.to_json())
        self.assertEqual(payload["attributes"]["build.id"], "010203")

    def test_equal_resources_hash_equally(self):
        self.assertEqual(hash(self.resource), hash(Resource.create(dict(_BYTES_RESOURCE))))

    def test_differing_bytes_hash_differently(self):
        other = Resource.create({"service.name": "svc", "build.id": b"\xff"})
        self.assertNotEqual(hash(self.resource), hash(other))

    def test_bytes_and_equivalent_string_are_distinct(self):
        """The hash fallback must not make b"\\x01\\x02\\x03" collide with "010203"."""
        as_text = Resource.create({"service.name": "svc", "build.id": "010203"})
        self.assertNotEqual(self.resource, as_text)
