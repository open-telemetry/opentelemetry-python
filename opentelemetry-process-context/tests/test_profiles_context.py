# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry.process_context._rs import publish_context
from opentelemetry.sdk.resources import Resource


class TestPublishContext(unittest.TestCase):
    # pylint: disable-next=no-self-use
    def test_publish_context_does_not_raise(self):
        resource = Resource(
            {"service.name": "test", "version": 1, "pi": 3.14, "active": True}
        )
        publish_context(resource)
