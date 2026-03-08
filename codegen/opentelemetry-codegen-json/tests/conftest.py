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

# pylint: disable=redefined-outer-name

import importlib
import subprocess
import sys
from pathlib import Path

import pytest  # type: ignore
from _pytest.monkeypatch import MonkeyPatch  # type: ignore

PROTO_PATH = Path(__file__).parent / "proto"
GEN_PATH = Path(__file__).parent / "generated"


@pytest.fixture(scope="session")
def monkeysession():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope="session", autouse=True)
def generate_code(
    tmp_path_factory: pytest.TempPathFactory, monkeysession: MonkeyPatch
) -> None:
    gen_path = tmp_path_factory.mktemp("generated")

    protos = list(PROTO_PATH.glob("**/*.proto"))
    proto_files = [p.relative_to(PROTO_PATH).as_posix() for p in protos]

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{PROTO_PATH.as_posix()}",
            f"--otlp_json_out={gen_path.as_posix()}",
            f"--python_out={gen_path.as_posix()}",
            *proto_files,
        ]
    )

    monkeysession.syspath_prepend(str(gen_path.absolute()))
    importlib.invalidate_caches()
