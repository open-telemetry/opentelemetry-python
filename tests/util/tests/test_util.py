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

from unittest import TestCase

from opentelemetry.test import AssertNotRaisesMixin


class TestAssertNotRaises(TestCase):
    class TestCaseAssertNotRaises(AssertNotRaisesMixin, TestCase):
        pass

    @classmethod
    def setUpClass(cls):
        cls.test_case = cls.TestCaseAssertNotRaises()

    def test_no_exception(self):

        try:

            with self.test_case.assertNotRaises(Exception):
                pass

        except Exception as error:  # pylint: disable=broad-except

            self._test_case.fail(  # pylint: disable=no-member
                "Unexpected exception {} was raised".format(error)
            )

    def test_no_specified_exception_single(self):

        try:

            with self.test_case.assertNotRaises(KeyError):
                1 / 0  # pylint: disable=pointless-statement

        except Exception as error:  # pylint: disable=broad-except

            self._test_case.fail(  # pylint: disable=no-member
                "Unexpected exception {} was raised".format(error)
            )

    def test_no_specified_exception_multiple(self):

        try:

            with self.test_case.assertNotRaises(KeyError, IndexError):
                1 / 0  # pylint: disable=pointless-statement

        except Exception as error:  # pylint: disable=broad-except

            self._test_case.fail(  # pylint: disable=no-member
                "Unexpected exception was raised:\n{}".format(error)
            )

    def test_exception(self):

        with self.assertRaises(AssertionError):

            with self.test_case.assertNotRaises(ZeroDivisionError):
                1 / 0  # pylint: disable=pointless-statement

    def test_missing_exception(self):

        with self.assertRaises(AssertionError) as error:

            with self.test_case.assertNotRaises(ZeroDivisionError):

                def raise_zero_division_error():
                    raise ZeroDivisionError()

                raise_zero_division_error()

        error_lines = error.exception.args[0].split("\n")

        self.assertEqual(
            error_lines[0].strip(), "Unexpected exception was raised:"
        )
        self.assertEqual(error_lines[2].strip(), "raise_zero_division_error()")
        self.assertEqual(error_lines[5].strip(), "raise ZeroDivisionError()")
