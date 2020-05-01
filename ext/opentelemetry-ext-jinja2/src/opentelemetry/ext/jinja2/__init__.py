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

The OpenTelemetry ``jinja2`` integration traces templates loading, compilation and rendering.

.. code-block:: python

Instrumentation example::

    from opentelemetry.ext.jinja2 import Jinja2Instrumentor
    Jinja2Instrumentor().instrument()  # This needs to be executed before importing jinja2
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader("templates")
    )
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

DEFAULT_TEMPLATE_NAME = "<memory>"


def _wrap_render(wrapped, instance, args, kwargs):
    """Wrap `Template.render()` or `Template.generate()`
    """
    template_name = instance.name or DEFAULT_TEMPLATE_NAME
    tracer = trace.get_tracer(__name__, __version__)
    with tracer.start_as_current_span(
        "jinja2.render", kind=trace.SpanKind.INTERNAL
    ) as span:
        try:
            return wrapped(*args, **kwargs)
        finally:
            span.set_attribute("component", "template")
            span.set_attribute("jinja2.template_name", template_name)


def _wrap_compile(wrapped, _, args, kwargs):
    if len(args) > 1:
        template_name = args[1]
    else:
        template_name = kwargs.get("name", DEFAULT_TEMPLATE_NAME)

    tracer = trace.get_tracer(__name__, __version__)
    with tracer.start_as_current_span(
        "jinja2.compile", kind=trace.SpanKind.INTERNAL
    ) as span:
        try:
            return wrapped(*args, **kwargs)
        finally:
            span.set_attribute("component", "template")
            span.set_attribute("jinja2.template_name", template_name)


def _wrap_load_template(wrapped, _, args, kwargs):
    template_name = kwargs.get("name", args[0])
    tracer = trace.get_tracer(__name__, __version__)
    with tracer.start_as_current_span(
        "jinja2.load", kind=trace.SpanKind.INTERNAL
    ) as span:
        template = None
        try:
            template = wrapped(*args, **kwargs)
            return template
        finally:
            span.set_attribute("component", "template")
            span.set_attribute("jinja2.template_name", template_name)
            if template:
                span.set_attribute("jinja2.template_path", template.filename)


def _unwrap(obj, attr):
    func = getattr(obj, attr, None)
    if func and isinstance(func, ObjectProxy) and hasattr(func, "__wrapped__"):
        setattr(obj, attr, func.__wrapped__)


class Jinja2Instrumentor(BaseInstrumentor):
    """A instrumentor for jinja2

    See `BaseInstrumentor`
    """

    def __init__(self):
        super().__init__()
        self._original_jinja2_tempalte_render = None

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
