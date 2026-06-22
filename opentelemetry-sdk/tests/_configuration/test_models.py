# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest


class TestModelsImport(unittest.TestCase):
    def test_models_import(self):  # pylint: disable=no-self-use
        """Verify generated models import successfully across all Python versions"""
        from opentelemetry.sdk._configuration import (  # pylint: disable=import-outside-toplevel,unused-import
            models,  # noqa: F401  # type: ignore
        )
