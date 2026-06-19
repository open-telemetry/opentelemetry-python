# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry.process_context._rs import (
    publish_context,
    unpublish_context,
    update_context,
)
from opentelemetry.sdk.resources import Resource


class TestPublishContext(unittest.TestCase):
    def tearDown(self):
        try:
            unpublish_context()
        except RuntimeError:
            pass

    def test_publish_context_lifecycle(self):
        resource = Resource(
            {"service.name": "test", "version": 1, "pi": 3.14, "active": True}
        )
        self.assertIsNone(publish_context(resource))

        with self.assertRaises(RuntimeError):
            publish_context(resource)

        self.assertIsNone(update_context(resource))
        self.assertIsNone(update_context(resource))

        self.assertIsNone(unpublish_context())
        self.assertIsNone(publish_context(resource))

    def test_update_before_publish_raises(self):
        with self.assertRaises(RuntimeError):
            update_context(Resource({}))

    def test_unpublish_before_publish_raises(self):
        with self.assertRaises(RuntimeError):
            unpublish_context()
