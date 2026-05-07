# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from flask import Flask, request

app = Flask(__name__)


@app.route("/server_request")
def server_request():
    print(request.args.get("param"))
    return "served"


if __name__ == "__main__":
    app.run(port=8082)
