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

import flask
from flask import request

from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor

application = flask.Flask(__name__)

FlaskInstrumentor().instrument_app(application)

tracer = trace.get_tracer(__name__)


def fib_slow(n):
    if n <= 1:
        return n
    return fib_slow(n - 1) + fib_fast(n - 2)


def fib_fast(n):
    nth_fib = [0] * (n + 2)
    nth_fib[1] = 1
    for i in range(2, n + 1):
        nth_fib[i] = nth_fib[i - 1] + nth_fib[i - 2]
    return nth_fib[n]


@application.route("/fibonacci")
def fibonacci():
    n = int(request.args.get("n", 1))
    with tracer.start_as_current_span("root"):
        with tracer.start_as_current_span("fib_slow") as slow_span:
            ans = fib_slow(n)
            slow_span.set_attribute("n", n)
            slow_span.set_attribute("nth_fibonacci", ans)
        with tracer.start_as_current_span("fib_fast") as fast_span:
            ans = fib_fast(n)
            fast_span.set_attribute("n", n)
            fast_span.set_attribute("nth_fibonacci", ans)

    return f"F({n}) is: ({ans})"


if __name__ == "__main__":
    application.run()
