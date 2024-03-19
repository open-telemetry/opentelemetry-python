import time
from typing import Mapping, Optional, Sequence

from flask import Flask, jsonify
from oteltest import OtelTest, Telemetry

PORT = 8909
HOST = "127.0.0.1"


app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"library": "flask"})


if __name__ == "__main__":
    app.run(port=PORT, host=HOST)


class FlaskTest(OtelTest):
    def environment_variables(self) -> Mapping[str, str]:
        return {}

    def requirements(self) -> Sequence[str]:
        return (
            "opentelemetry-distro",
            "opentelemetry-exporter-otlp-proto-grpc",
            "opentelemetry-instrumentation-flask",
            "flask==2.3.3",
            "jsonify",
        )

    def wrapper_command(self) -> str:
        return "opentelemetry-instrument"

    def on_start(self) -> Optional[float]:
        import http.client

        # Todo: replace this sleep with a liveness check!
        time.sleep(10)

        conn = http.client.HTTPConnection(HOST, PORT)
        conn.request("GET", "/")
        print("response:", conn.getresponse().read().decode())
        conn.close()

        # The return value of on_script_start() tells oteltest the number of seconds to wait for the script to
        # finish. In this case, we indicate 30 (seconds), which, once elapsed, will cause the script to be terminated,
        # if it's still running. If we return `None` then the script will run indefinitely.
        return 30

    def on_stop(
        self, telemetry: Telemetry, stdout: str, stderr: str, returncode: int
    ) -> None:
        print(f"on_stop: telemetry: {telemetry}")
