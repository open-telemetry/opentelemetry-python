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

# pylint: disable=import-error,unspecified-encoding

import argparse

import requests
from ruamel.yaml import YAML

API_URL = "https://api.github.com/repos/open-telemetry/opentelemetry-python-contrib/commits/"
WORKFLOW_FILE = ".github/workflows/test.yml"


def get_sha(branch):
    url = API_URL + branch
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["sha"]


def update_sha(sha):
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(WORKFLOW_FILE, "r") as file:
        workflow = yaml.load(file)
    workflow["env"]["CONTRIB_REPO_SHA"] = sha
    with open(WORKFLOW_FILE, "w") as file:
        yaml.dump(workflow, file)


def main():
    args = parse_args()
    sha = get_sha(args.branch)
    update_sha(sha)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Updates the SHA in the workflow file"
    )
    parser.add_argument("-b", "--branch", help="branch to use")
    return parser.parse_args()


if __name__ == "__main__":
    main()
