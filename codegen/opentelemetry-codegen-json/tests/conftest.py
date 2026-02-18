import subprocess
import sys
from pathlib import Path

import pytest

PROTO_PATH = Path(__file__).parent / "proto"
GEN_PATH = Path(__file__).parent / "generated"


@pytest.fixture(scope="session", autouse=True)
def generate_code(tmp_path_factory: pytest.TempPathFactory) -> None:
    gen_path = tmp_path_factory.mktemp("generated")

    protos = list(PROTO_PATH.glob("**/*.proto"))
    proto_files = [str(p.relative_to(PROTO_PATH)) for p in protos]

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{PROTO_PATH}",
            f"--otlp_json_out={gen_path}",
            f"--python_out={gen_path}",
            *proto_files,
        ]
    )

    sys.path.insert(0, str(gen_path.absolute()))
