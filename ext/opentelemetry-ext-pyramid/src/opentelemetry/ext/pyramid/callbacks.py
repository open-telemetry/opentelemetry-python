from logging import getLogger

from pyramid.events import BeforeTraversal
from pyramid.httpexceptions import HTTPException
from pyramid.settings import asbool
from pyramid.tweens import EXCVIEW

import opentelemetry.ext.wsgi as otel_wsgi
from opentelemetry import configuration, context, propagators, trace
from opentelemetry.ext.pyramid.version import __version__
from opentelemetry.util import disable_trace, time_ns

TWEEN_NAME = "opentelemetry.ext.pyramid.trace_tween_factory"
SETTING_TRACE_ENABLED = "opentelemetry-pyramid.trace_enabled"

_ENVIRON_STARTTIME_KEY = "opentelemetry-pyramid.starttime_key"
_ENVIRON_SPAN_KEY = "opentelemetry-pyramid.span_key"
_ENVIRON_ACTIVATION_KEY = "opentelemetry-pyramid.activation_key"
_ENVIRON_ENABLED_KEY = "opentelemetry-pyramid.tracing_enabled_key"
_ENVIRON_TOKEN = "opentelemetry-pyramid.token"

_logger = getLogger(__name__)


def get_excluded_hosts():
    hosts = configuration.Configuration().PYRAMID_EXCLUDED_HOSTS or []
    if hosts:
        hosts = str.split(hosts, ",")
    return hosts


def get_excluded_paths():
    paths = configuration.Configuration().PYRAMID_EXCLUDED_PATHS or []
    if paths:
        paths = str.split(paths, ",")
    return paths


_excluded_hosts = get_excluded_hosts()
_excluded_paths = get_excluded_paths()


def includeme(config):
    config.add_settings({SETTING_TRACE_ENABLED: True})

    config.add_subscriber(_before_traversal, BeforeTraversal)
    _insert_tween(config)


def _insert_tween(config):
    settings = config.get_settings()
    tweens = settings.get("pyramid.tweens")
    # If the list is empty, pyramid does not consider the tweens have been
    # set explicitly. And if our tween is already there, nothing to do
    if not tweens or not tweens.strip():
        # Add our tween just before the default exception handler
        config.add_tween(TWEEN_NAME, over=EXCVIEW)


def _before_traversal(event):
    request = event.request
    environ = request.environ
    span_name = otel_wsgi.get_default_span_name(environ)

    enabled = environ.get(_ENVIRON_ENABLED_KEY)
    if enabled is None:
        _logger.warning(
            "Opentelemetry pyramid tween 'opentelemetry.ext.pyramid.trace_tween_factory'"
            "was not called. Make sure that the tween is included in 'pyramid.tweens' if"
            "the tween list was created manually"
        )
        return

    if not enabled:
        # Tracing not enabled, return
        return

    start_time = environ.get(_ENVIRON_STARTTIME_KEY)

    token = context.attach(
        propagators.extract(otel_wsgi.get_header_from_environ, environ)
    )
    tracer = trace.get_tracer(__name__, __version__)

    attributes = otel_wsgi.collect_request_attributes(environ)

    if request.matched_route:
        span_name = request.matched_route.pattern
        attributes["http.route"] = request.matched_route.pattern
    else:
        span_name = otel_wsgi.get_default_span_name(environ)

    span = tracer.start_span(
        span_name,
        kind=trace.SpanKind.SERVER,
        attributes=attributes,
        start_time=start_time,
    )

    activation = tracer.use_span(span, end_on_exit=True)
    activation.__enter__()
    environ[_ENVIRON_ACTIVATION_KEY] = activation
    environ[_ENVIRON_SPAN_KEY] = span
    environ[_ENVIRON_TOKEN] = token


def trace_tween_factory(handler, registry):
    settings = registry.settings
    enabled = asbool(settings.get(SETTING_TRACE_ENABLED, True))

    if enabled:
        # make a request tracing function
        def trace_tween(request):
            if disable_trace(request.url, _excluded_hosts, _excluded_paths):
                request.environ[_ENVIRON_ENABLED_KEY] = False
                # short-circuit when we don't want to trace anything
                return handler(request)

            request.environ[_ENVIRON_ENABLED_KEY] = True
            request.environ[_ENVIRON_STARTTIME_KEY] = time_ns()

            response = None
            try:
                response = handler(request)
            except HTTPException as exc:
                # If the exception is a pyramid HTTPException,
                # that's still valuable information that isn't necessarily
                # a 500. For instance, HTTPFound is a 302.
                # As described in docs, Pyramid exceptions are all valid
                # response types
                response = exc
                raise
            finally:
                span = request.environ.get(_ENVIRON_SPAN_KEY)
                enabled = request.environ.get(_ENVIRON_ENABLED_KEY)
                if not span and enabled:
                    _logger.warning(
                        "Pyramid environ's OpenTelemetry span missing."
                        "If the OpenTelemetry tween was added manually, make sure"
                        "PyramidInstrumentor().instrument_config(config) is called"
                    )
                elif enabled:
                    if response:
                        otel_wsgi.add_response_attributes(
                            span, response.status, response.headers
                        )

                    activation = request.environ.get(_ENVIRON_ACTIVATION_KEY)

                    if isinstance(response, HTTPException):
                        activation.__exit__(
                            type(response),
                            response,
                            getattr(response, "__traceback__", None),
                        )
                    else:
                        activation.__exit__(None, None, None)

                    context.detach(request.environ.get(_ENVIRON_TOKEN))
            return response

        return trace_tween

    # If not enabled, make a tween that signals to the
    # BeforeTraversal subscriber that tracing is disabled
    def disabled_tween(request):
        request.environ[_ENVIRON_ENABLED_KEY] = False
        return handler(request)

    return disabled_tween
