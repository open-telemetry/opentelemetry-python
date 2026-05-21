# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.test import TestCase


class TestAssertNotRaises(TestCase):
    def test_no_exception(self):
        try:
            with self.assertNotRaises(Exception):
                pass

        except Exception as error:  # pylint: disable=broad-exception-caught
            self.fail(  # pylint: disable=no-member
                f"Unexpected exception {error} was raised"
            )

    def test_no_specified_exception_single(self):
        try:
            with self.assertNotRaises(KeyError):
                1 / 0  # pylint: disable=pointless-statement

        except Exception as error:  # pylint: disable=broad-exception-caught
            self.fail(  # pylint: disable=no-member
                f"Unexpected exception {error} was raised"
            )

    def test_no_specified_exception_multiple(self):
        try:
            with self.assertNotRaises(KeyError, IndexError):
                1 / 0  # pylint: disable=pointless-statement

        except Exception as error:  # pylint: disable=broad-exception-caught
            self.fail(  # pylint: disable=no-member
                f"Unexpected exception {error} was raised"
            )

    def test_exception(self):
        with self.assertRaises(AssertionError):
            with self.assertNotRaises(ZeroDivisionError):
                1 / 0  # pylint: disable=pointless-statement

    def test_missing_exception(self):
        with self.assertRaises(AssertionError) as error:
            with self.assertNotRaises(ZeroDivisionError):

                def raise_zero_division_error():
                    raise ZeroDivisionError()

                raise_zero_division_error()

        error_lines = error.exception.args[0].split("\n")
        stripped_error_lines = [line.strip() for line in error_lines]

        self.assertIn("Unexpected exception was raised:", stripped_error_lines)
        self.assertIn("raise_zero_division_error()", stripped_error_lines)
        self.assertIn("raise ZeroDivisionError()", stripped_error_lines)
