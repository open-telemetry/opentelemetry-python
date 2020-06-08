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
    from opentelemetry import trace
    from opentelemetry.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())

    Jinja2Instrumentor().instrument()

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("mytemplate.html")

API
---
"""
# pylint: disable=no-value-for-parameter

import logging

import jinja2
from wrapt import ObjectProxy
from wrapt import wrap_function_wrapper as _wrap

from opentelemetry.ext.jinja2.version import __version__
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.trace import SpanKind, get_tracer
from opentelemetry.trace.status import Status, StatusCanonicalCode

logger = logging.getLogger(__name__)

ATTRIBUTE_JINJA2_TEMPLATE_NAME = "jinja2.template_name"
ATTRIBUTE_JINJA2_TEMPLATE_PATH = "jinja2.template_path"
DEFAULT_TEMPLATE_NAME = "<memory>"


def _with_tracer_wrapper(func):
    """Helper for providing tracer for wrapper functions.
    """

    def _with_tracer(tracer):
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, wrapped, instance, args, kwargs)

        return wrapper

    return _with_tracer


@_with_tracer_wrapper
def _wrap_render(tracer, wrapped, instance, args, kwargs):
    """Wrap `Template.render()` or `Template.generate()`
    """
    template_name = instance.name or DEFAULT_TEMPLATE_NAME
    attributes = {ATTRIBUTE_JINJA2_TEMPLATE_NAME: template_name}
    with tracer.start_as_current_span(
        "jinja2.render", kind=SpanKind.INTERNAL, attributes=attributes
    ):
        return wrapped(*args, **kwargs)


@_with_tracer_wrapper
def _wrap_compile(tracer, wrapped, _, args, kwargs):
    template_name = (
        args[1] if len(args) > 1 else kwargs.get("name", DEFAULT_TEMPLATE_NAME)
    )
    attributes = {ATTRIBUTE_JINJA2_TEMPLATE_NAME: template_name}
    with tracer.start_as_current_span(
        "jinja2.compile", kind=SpanKind.INTERNAL, attributes=attributes
    ):
        return wrapped(*args, **kwargs)


@_with_tracer_wrapper
def _wrap_load_template(tracer, wrapped, _, args, kwargs):
    template_name = kwargs.get("name", args[0])
    attributes = {ATTRIBUTE_JINJA2_TEMPLATE_NAME: template_name}
    with tracer.start_as_current_span(
        "jinja2.load", kind=SpanKind.INTERNAL, attributes=attributes
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


class Jinja2Instrumentor(BaseInstrumentor):
    """An instrumentor for jinja2

    See `BaseInstrumentor`
    """

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, __version__, tracer_provider)

        _wrap(jinja2, "environment.Template.render", _wrap_render(tracer))
        _wrap(jinja2, "environment.Template.generate", _wrap_render(tracer))
        _wrap(jinja2, "environment.Environment.compile", _wrap_compile(tracer))
        _wrap(
            jinja2,
            "environment.Environment._load_template",
            _wrap_load_template(tracer),
        )

    def _uninstrument(self, **kwargs):
        unwrap(jinja2.Template, "render")
        unwrap(jinja2.Template, "generate")
        unwrap(jinja2.Environment, "compile")
        unwrap(jinja2.Environment, "_load_template")
