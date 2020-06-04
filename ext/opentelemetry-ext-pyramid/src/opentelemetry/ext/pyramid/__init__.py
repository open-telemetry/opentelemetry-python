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
Pyramid instrumentation supporting `pyramid`_, it can be enabled by
using ``PyramidInstrumentor``.

.. _pyramid: https://docs.pylonsproject.org/projects/pyramid/en/latest/

Usage
-----
    There are two methods to instrument Pyramid:

Method 1 (Instrument all Configurators):
----------------------------------------
.. code:: python

    from pyramid.config import Configurator
    from opentelemetry.ext.pyramid import PyramidInstrumentor

    PyramidInstrumentor.instrument()

    config = Configurator()

    # use your config as normal
    config.add_route('index', '/')

Method 2 (Instrument one Configurator):
---------------------------------------
.. code:: python

    from pyramid.config import Configurator
    from opentelemetry.ext.pyramid import PyramidInstrumentor

    config = Configurator()
    PyramidInstrumentor().instrument_config(config)

    # use your config as normal
    config.add_route('index', '/')

Using ``pyramid.tweens`` settings:
----------------------------------
    If you use Method 2 and then set tweens for your application with the ``pyramid.tweens`` setting,
    you need to add ``opentelemetry.ext.pyramid.trace_tween_factory`` explicity to the list,
    *as well as* instrumenting the config with `PyramidInstrumentor().instrument_config(config)`.

    For example:
.. code:: python
    settings = {
        'pyramid.tweens', 'opentelemetry.ext.pyramid.trace_tween_factory\\nyour_tween_no_1\\nyour_tween_no_2',
    }
    config = Configurator(settings=settings)
    PyramidInstrumentor.instrument_config(config)

    # use your config as normal.
    config.add_route('index', '/')
---
"""

import typing

from pyramid.config import Configurator
from pyramid.path import caller_package
from pyramid.settings import aslist
from wrapt import ObjectProxy
from wrapt import wrap_function_wrapper as _wrap

from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.ext.pyramid.callbacks import (
    SETTING_TRACE_ENABLED,
    TWEEN_NAME,
    trace_tween_factory,
)
from opentelemetry.ext.pyramid.version import __version__
from opentelemetry.trace import TracerProvider, get_tracer


def traced_init(wrapped, instance, args, kwargs):
    settings = kwargs.get("settings", {})
    tweens = aslist(settings.get("pyramid.tweens", []))

    if tweens and TWEEN_NAME not in settings:
        # pyramid.tweens.EXCVIEW is the name of built-in exception view provided by
        # pyramid.  We need our tween to be before it, otherwise unhandled
        # exceptions will be caught before they reach our tween.
        tweens = [TWEEN_NAME] + tweens

        settings["pyramid.tweens"] = "\n".join(tweens)

    kwargs["settings"] = settings

    # `caller_package` works by walking a fixed amount of frames up the stack
    # to find the calling package. So if we let the original `__init__`
    # function call it, our wrapper will mess things up.
    if not kwargs.get("package", None):
        # Get the package for the third frame up from this one.
        # Default is `level=2` which will give us the package from `wrapt`
        # instead of the desired package (the caller)
        kwargs["package"] = caller_package(level=3)

    wrapped(*args, **kwargs)
    instance.include("opentelemetry.ext.pyramid.callbacks")


def unwrap(obj, attr: str):
    """Given a function that was wrapped by wrapt.wrap_function_wrapper, unwrap it
    Args:
        obj: Object that holds a reference to the wrapped function
        attr (str): Name of the wrapped function
    """
    func = getattr(obj, attr, None)
    if func and isinstance(func, ObjectProxy) and hasattr(func, "__wrapped__"):
        setattr(obj, attr, func.__wrapped__)


class PyramidInstrumentor(BaseInstrumentor):
    def _instrument(self, **kwargs):
        """Integrate with Pyramid Python library.
        https://docs.pylonsproject.org/projects/pyramid/en/latest/
        """
        _wrap("pyramid.config", "Configurator.__init__", traced_init)

    def _uninstrument(self, **kwargs):
        """"Disable Pyramid instrumentation"""
        unwrap(Configurator, "__init__")

    # pylint:disable=no-self-use
    def instrument_config(self, config):
        """Enable instrumentation in a Pyramid configurator.

        Args:
            config: The Configurator to instrument.

        Returns:
            An instrumented Configurator.
        """
        config.include("opentelemetry.ext.pyramid.callbacks")

    def uninstrument_config(self, config):
        config.add_settings({SETTING_TRACE_ENABLED: False})
