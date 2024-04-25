import glob
import importlib
import inspect
import os
import shutil
import subprocess
import sys
import tempfile
import time
import typing
import venv
from pathlib import Path

from google.protobuf.json_format import MessageToDict
from oteltest import OtelTest, Telemetry
from oteltest.sink import GrpcSink, RequestHandler

from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)


def run(script_dir: str, wheel_file: str, venv_parent_dir: str):
    temp_dir = venv_parent_dir or tempfile.mkdtemp()
    print(f"- Using temp dir for venvs: {temp_dir}")

    sys.path.append(script_dir)

    for script in ls_scripts(script_dir):
        print(f"- Setting up environment for {script}")
        setup_script_environment(temp_dir, script_dir, script, wheel_file)


def ls_scripts(script_dir):
    original_dir = os.getcwd()
    os.chdir(script_dir)
    scripts = glob.glob("*.py")
    os.chdir(original_dir)
    return scripts


def setup_script_environment(venv_parent, script_dir, script, wheel_file):
    handler = AccumulatingHandler()
    sink = GrpcSink(handler)
    sink.start()

    module_name = script[:-3]
    oteltest_instance: OtelTest = load_test_class_for_script(module_name)()

    script_venv = Venv(str(Path(venv_parent) / module_name))
    script_venv.create()

    pip_path = script_venv.path_to_executable("pip")

    run_subprocess([pip_path, "install", (wheel_file or "oteltest")])

    for req in oteltest_instance.requirements():
        print(f"- Will install requirement: '{req}'")
        run_subprocess([pip_path, "install", req])

    stdout, stderr, returncode = run_python_script(
        script, script_dir, oteltest_instance, script_venv
    )
    print_subprocess_result(stdout, stderr, returncode)

    filename = get_next_json_file(script_dir, module_name)
    print(f"- Will save telemetry to {filename}")
    save_telemetry_json(script_dir, filename, handler.telemetry_to_json())

    oteltest_instance.on_stop(handler.telemetry, stdout, stderr, returncode)
    print(f"- PASSED: {script}")


def get_next_json_file(path_str: str, module_name: str):
    path = Path(path_str)
    max_index = -1
    for file in path.glob(f"{module_name}.*.json"):
        last_part = file.stem.split(".")[-1]
        if last_part.isdigit():
            index = int(last_part)
            if index > max_index:
                max_index = index
    return f"{module_name}.{max_index+1}.json"


def save_telemetry_json(script_dir: str, file_name: str, json_str: str):
    path = Path(script_dir) / file_name
    with open(str(path), "w", encoding="utf-8") as file:
        file.write(json_str)


def run_python_script(
    script, script_dir, oteltest_instance: OtelTest, v
) -> typing.Tuple[str, str, int]:
    print(f"- Running python script: {script}")
    python_script_cmd = [
        v.path_to_executable("python"),
        str(Path(script_dir) / script),
    ]

    wrapper_script = oteltest_instance.wrapper_command()
    if wrapper_script is not None:
        python_script_cmd.insert(0, v.path_to_executable(wrapper_script))

    # pylint: disable=R1732
    proc = subprocess.Popen(
        python_script_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=oteltest_instance.environment_variables(),
    )
    timeout = exec_onstart_callback(oteltest_instance, script)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return stdout, stderr, proc.returncode
    except subprocess.TimeoutExpired as ex:
        print(f"- Script {script} was force quit")
        return decode(ex.stdout), decode(ex.stderr), proc.returncode


def exec_onstart_callback(oteltest_instance, script):
    try:
        timeout = oteltest_instance.on_start()
    except Exception as ex:  # pylint: disable=W0718
        print(
            f"- Setting timeout to zero: on_start() threw an exception: {ex}"
        )
        timeout = 0
    if timeout is None:
        print(
            f"- Will wait indefinitely for {script} to finish: on_start() returned `None`"
        )
    else:
        print(
            f"- Will wait for up to {timeout} seconds for {script} to finish"
        )
    return timeout


def decode(b: bytes):
    return b.decode("utf-8") if b else None


def run_subprocess(args):
    print(f"- Subprocess: {args}")
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=True,
    )
    print_subprocess_result(result.stdout, result.stderr, result.returncode)


def print_subprocess_result(stdout: str, stderr: str, returncode: int):
    print(f"- Return Code: {returncode}")
    print("- Standard Output:")
    if stdout:
        print(stdout)
    print("- Standard Error:")
    if stderr:
        print(stderr)
    print("- End Subprocess -\n")


def load_test_class_for_script(module_name):
    module = importlib.import_module(module_name)
    for attr_name in dir(module):
        value = getattr(module, attr_name)
        if is_test_class(value):
            return value
    return None


def is_test_class(value):
    return (
        inspect.isclass(value)
        and issubclass(value, OtelTest)
        and value is not OtelTest
    )


class Venv:
    def __init__(self, venv_dir):
        self.venv_dir = venv_dir

    def create(self):
        venv.create(self.venv_dir, with_pip=True)

    def path_to_executable(self, executable_name: str):
        return f"{self.venv_dir}/bin/{executable_name}"

    def rm(self):
        shutil.rmtree(self.venv_dir)


class AccumulatingHandler(RequestHandler):
    def __init__(self):
        self.start_time = time.time_ns()
        self.telemetry = Telemetry()

    def handle_logs(
        self, request: ExportLogsServiceRequest, context
    ):  # noqa: ARG002
        self.telemetry.add_log(
            MessageToDict(request),
            get_context_headers(context),
            self.get_test_elapsed_ms(),
        )

    def handle_metrics(
        self, request: ExportMetricsServiceRequest, context
    ):  # noqa: ARG002
        self.telemetry.add_metric(
            MessageToDict(request),
            get_context_headers(context),
            self.get_test_elapsed_ms(),
        )

    def handle_trace(
        self, request: ExportTraceServiceRequest, context
    ):  # noqa: ARG002
        self.telemetry.add_trace(
            MessageToDict(request),
            get_context_headers(context),
            self.get_test_elapsed_ms(),
        )

    def get_test_elapsed_ms(self):
        return round((time.time_ns() - self.start_time) / 1e6)

    def telemetry_to_json(self):
        return self.telemetry.to_json()


def get_context_headers(context):
    return pbmetadata_to_dict(context.invocation_metadata())


def pbmetadata_to_dict(pbmetadata):
    out = {}
    for key, val in pbmetadata:
        out[key] = val
    return out
