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

"""

Usage
-----

The OpenTelemetry ``jinja2`` integration traces templates loading, compilation
and rendering.

Usage
-----

.. code-block:: python

    from jinja2 import Environment, FileSystemLoader
    from opentelemetry.ext.jinja2 import Jinja2Instrumentor

    trace.set_tracer_provider(TracerProvider())

    Jinja2Instrumentor().instrument()

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template('mytemplate.html')

API
---
"""

import logging

import jinja2
from wrapt import ObjectProxy
from wrapt import wrap_function_wrapper as _wrap

from opentelemetry import trace
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.ext.jinja2.version import __version__
from opentelemetry.trace.status import Status, StatusCanonicalCode

logger = logging.getLogger(__name__)

ATTRIBUTE_JINJA2_TEMPLATE_NAME = "jinja2.template_name"
ATTRIBUTE_JINJA2_TEMPLATE_PATH = "jinja2.template_path"
DEFAULT_TEMPLATE_NAME = "<memory>"


def _wrap_render(wrapped, instance, args, kwargs):
    """Wrap `Template.render()` or `Template.generate()`
    """
    tracer = trace.get_tracer(__name__, __version__)
    template_name = instance.name or DEFAULT_TEMPLATE_NAME
    attributes = {ATTRIBUTE_JINJA2_TEMPLATE_NAME: template_name}
    with tracer.start_as_current_span(
        "jinja2.render", kind=trace.SpanKind.INTERNAL, attributes=attributes
    ):
        return wrapped(*args, **kwargs)


def _wrap_compile(wrapped, _, args, kwargs):
    tracer = trace.get_tracer(__name__, __version__)
    template_name = (
        args[1] if len(args) > 1 else kwargs.get("name", DEFAULT_TEMPLATE_NAME)
    )
    attributes = {ATTRIBUTE_JINJA2_TEMPLATE_NAME: template_name}
    with tracer.start_as_current_span(
        "jinja2.compile", kind=trace.SpanKind.INTERNAL, attributes=attributes
    ):
        return wrapped(*args, **kwargs)


def _wrap_load_template(wrapped, _, args, kwargs):
    tracer = trace.get_tracer(__name__, __version__)
    template_name = kwargs.get("name", args[0])
    attributes = {ATTRIBUTE_JINJA2_TEMPLATE_NAME: template_name}
    with tracer.start_as_current_span(
        "jinja2.load", kind=trace.SpanKind.INTERNAL, attributes=attributes
    ) as span:
        template = None
        try:
            template = wrapped(*args, **kwargs)
            return template
        finally:
            if template:
                span.set_attribute(
                    ATTRIBUTE_JINJA2_TEMPLATE_PATH, template.filename
                )


def _unwrap(obj, attr):
    func = getattr(obj, attr, None)
    if func and isinstance(func, ObjectProxy) and hasattr(func, "__wrapped__"):
        setattr(obj, attr, func.__wrapped__)


class Jinja2Instrumentor(BaseInstrumentor):
    """An instrumentor for jinja2

    See `BaseInstrumentor`
    """

    def _instrument(self, **kwargs):
        _wrap(jinja2, "environment.Template.render", _wrap_render)
        _wrap(jinja2, "environment.Template.generate", _wrap_render)
        _wrap(jinja2, "environment.Environment.compile", _wrap_compile)
        _wrap(
            jinja2,
            "environment.Environment._load_template",
            _wrap_load_template,
        )

    def _uninstrument(self, **kwargs):
        _unwrap(jinja2.Template, "render")
        _unwrap(jinja2.Template, "generate")
        _unwrap(jinja2.Environment, "compile")
        _unwrap(jinja2.Environment, "_load_template")
