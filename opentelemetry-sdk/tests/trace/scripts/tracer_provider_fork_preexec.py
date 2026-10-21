# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import signal
import subprocess
import sys

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider


def main() -> None:
    _provider = TracerProvider(resource=Resource({"service.name": "test"}))
    # pylint: disable=subprocess-popen-preexec-fn
    with subprocess.Popen(
        ["true"],
        preexec_fn=lambda: signal.signal(signal.SIGPIPE, signal.SIG_DFL),  # noqa: PLW1509
    ) as proc:
        proc.wait()
        sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
