# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# type: ignore

from traceback import format_tb
from unittest import TestCase


class _AssertNotRaisesMixin:
    class _AssertNotRaises:
        def __init__(self, test_case):
            self._test_case = test_case

        def __enter__(self):
            return self

        def __exit__(self, type_, value, tb):  # pylint: disable=invalid-name
            if value is not None and type_ in self._exception_types:
                self._test_case.fail(
                    "Unexpected exception was raised:\n{}".format(
                        "\n".join(format_tb(tb))
                    )
                )

            return True

        def __call__(self, exception, *exceptions):
            # pylint: disable=attribute-defined-outside-init
            self._exception_types = (exception, *exceptions)
            return self

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # pylint: disable=invalid-name
        self.assertNotRaises = self._AssertNotRaises(self)


class TestCase(_AssertNotRaisesMixin, TestCase):  # pylint: disable=function-redefined
    pass
