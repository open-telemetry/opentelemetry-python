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


from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.sdk.metrics.export import ConsoleExporter, Record

records = """{
    "instrument": "a",
    "labels": "b",
    "aggregator": "c",
    "resource": "d"
}
{
    "instrument": "e",
    "labels": "f",
    "aggregator": "g",
    "resource": "h"
}
"""


class TestExport(TestCase):
    def test_console_exporter(self):

        with patch("sys.stdout", new=StringIO()) as stdout:
            ConsoleExporter().export(
                [
                    Record("a", "b", "c", "d"),
                    Record("e", "f", "g", "h"),
                ]
            )
            self.assertEqual(stdout.getvalue(), records)
