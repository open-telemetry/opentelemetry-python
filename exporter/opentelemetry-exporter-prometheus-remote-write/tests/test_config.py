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

import os
import unittest

import yaml

from opentelemetry.exporter.prometheus_remote_write import (
    Config,
    parse_config,
)


class TestConfig(unittest.TestCase):
    # Series of test cases to ensure config validation works as intended
    def test_valid_standard_config(self):
        try:
            Config(endpoint="/prom/test_endpoint")
        except ValueError:
            self.fail("valid config failed config.validate()")

    def test_valid_basic_auth_config(self):
        try:
            Config(
                endpoint="/prom/test_endpoint",
                basic_auth={
                    "username": "test_username",
                    "password": "test_password",
                },
            )
        except ValueError:
            self.fail("valid config failed config.validate()")

    def test_valid_bearer_token_config(self):
        try:
            Config(
                endpoint="/prom/test_endpoint",
                bearer_token="test_bearer_token",
            )
        except ValueError:
            self.fail("valid config failed config.validate()")

    def test_invalid_no_endpoint_config(self):
        with self.assertRaises(ValueError):
            Config()

    def test_invalid_no_username_config(self):
        with self.assertRaises(ValueError):
            Config(
                endpoint="/prom/test_endpoint",
                basic_auth={"password": "test_password"},
            )

    def test_invalid_no_password_config(self):
        with self.assertRaises(ValueError):
            Config(
                endpoint="/prom/test_endpoint",
                basic_auth={"username": "test_username"},
            )

    def test_invalid_conflicting_passwords_config(self):
        with self.assertRaises(ValueError):
            Config(
                endpoint="/prom/test_endpoint",
                basic_auth={
                    "username": "test_username",
                    "password": "test_password",
                    "password_file": "test_file",
                },
            )

    def test_invalid_conflicting_bearer_tokens_config(self):
        with self.assertRaises(ValueError):
            Config(
                endpoint="/prom/test_endpoint",
                bearer_token="test_bearer_token",
                bearer_token_file="test_file",
            )

    def test_invalid_conflicting_auth_config(self):
        with self.assertRaises(ValueError):
            Config(
                endpoint="/prom/test_endpoint",
                basic_auth={
                    "username": "test_username",
                    "password": "test_password",
                },
                bearer_token="test_bearer_token",
            )

    # Verifies that valid yaml file is parsed correctly
    def test_valid_yaml_file(self):
        yml_dict = [{"endpoint": ["/prom/test_endpoint"]}]
        filepath = "./test.yml"
        with open(filepath, "w") as file:
            yaml.dump(yml_dict, file)
        config = parse_config(filepath)
        os.remove(filepath)
        self.assertEqual(config.endpoint, "/prom/test_endpoint")

    # Ensures invalid filepath raises error when parsing
    def test_invalid_yaml_filepath(self):
        filepath = "/incorrect_filepath.yml"
        with self.assertRaises(FileNotFoundError):
            parse_config(filepath)

    # Ensures incorrect file type raises error when parsing
    def test_incorrect_file_type(self):
        filepath = "/tmp/test.txt"
        with open(filepath, 'w'):
            pass
        with self.assertRaises(ValueError):
            parse_config(filepath)
        os.remove(filepath)
