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

from logging import getLogger
from os import environ

from django import VERSION
from django.conf import settings

from opentelemetry.configuration import Configuration

from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor

from opentelemetry.instrumentors.django.middleware import (
    OpenTelemetryMiddleware
)

_logger = getLogger(__name__)


class DjangoInstrumentor(BaseInstrumentor):
    """A instrumentor for flask.Django

    See `BaseInstrumentor`
    """

    def _instrument(self):
        # Django Middleware is code that is executed before and/or after a
        # request. Read about Django middleware here:
        # https://docs.djangoproject.com/en/3.0/topics/http/middleware/

        # This method must set this Django settings attribute:
        # MIDDLEWARE: for Django version > 1.0
        # MIDDLEWARE_CLASSES: for Django version <= 1.0

        # Django settings.MIDDLEWARE is a list of strings, each one a Python
        # path to a class or a function that acts as middleware.

        # FIXME this is probably a pattern that will show up in the rest of the
        # instrumentors. Find a better way of implementing this.
        if (
            hasattr(Configuration(), "django_instrument")
            and not Configuration().django_instrument
        ):
            return

        self._middleware_setting = (
            "MIDDLEWARE" if VERSION >= (1, 10, 0) else "MIDDLEWARE_CLASSES"
        )

        if "DJANGO_SETTINGS_MODULE" not in environ.keys():
            raise Exception(
                "Missing environment variable DJANGO_SETTINGS_MODULE"
            )

        settings_middleware = getattr(
            settings,
            self._middleware_setting,
            []
        )

        settings_middleware.append(
            ".".join(
                [
                    OpenTelemetryMiddleware.__module__,
                    OpenTelemetryMiddleware.__qualname__
                ]
            )
        )
        setattr(
            settings,
            self._middleware_setting,
            settings_middleware
        )

    def _uninstrument(self):
        settings_middleware = getattr(
            settings,
            self._middleware_setting,
            None
        )

        # FIXME This is starting to smell like trouble. We have 2 mechanisms
        # that may make this condition be True, one implemented in
        # BaseInstrumentor and another one implemented in _instrument. Both
        # stop _instrument from running and thus, settings_middleware not being
        # set.
        if settings_middleware is None:
            return

        settings_middleware.remove(
            ".".join(
                [
                    OpenTelemetryMiddleware.__module__,
                    OpenTelemetryMiddleware.__qualname__
                ]
            )
        )
        setattr(
            settings,
            self._middleware_setting,
            settings_middleware
        )
