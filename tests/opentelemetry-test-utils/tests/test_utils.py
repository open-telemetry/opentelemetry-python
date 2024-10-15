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
