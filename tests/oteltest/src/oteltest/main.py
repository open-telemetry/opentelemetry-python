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

import argparse

from oteltest.private import run


def main():
    parser = argparse.ArgumentParser(description="OpenTelemetry Python Tester")

    w_help = "Path to an optional wheel (.whl) file to `pip install` instead of `oteltest`"
    parser.add_argument(
        "-w", "--wheel-file", type=str, required=False, help=w_help
    )

    d_help = (
        "An optional override directory to hold per-script venv directories."
    )
    parser.add_argument(
        "-d", "--venv-parent-dir", type=str, required=False, help=d_help
    )

    parser.add_argument(
        "script_dir",
        type=str,
        help="The directory containing oteltest scripts at its top level",
    )

    args = parser.parse_args()
    run(args.script_dir, args.wheel_file, args.venv_parent_dir)


if __name__ == "__main__":
    main()
