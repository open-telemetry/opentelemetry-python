# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Parsing of HTTP headers supplied through environment variables.

Several ``OTEL_*`` environment variables carry a list of HTTP headers in one
string, for example ``OTEL_EXPORTER_OTLP_HEADERS``. :func:`parse_env_headers`
turns such a string into a mapping, following the header format of the
OpenTelemetry protocol exporter specification.
"""

from collections.abc import Mapping
from logging import getLogger
from re import compile
from urllib.parse import unquote

from typing_extensions import deprecated

_logger = getLogger(__name__)

# The following regexes reference this spec: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/protocol/exporter.md#specifying-headers-via-environment-variables

# Optional whitespace
_OWS = r"[ \t]*"
# A key contains printable US-ASCII characters except: SP and "(),/:;<=>?@[\]{}
_KEY_FORMAT = r"[\x21\x23-\x27\x2a\x2b\x2d\x2e\x30-\x39\x41-\x5a\x5e-\x7a\x7c\x7e]+"
# A value contains a URL-encoded UTF-8 string. The encoded form can contain any
# printable US-ASCII characters (0x20-0x7f) other than SP, DEL, and ",;/
_VALUE_FORMAT = r"[\x21\x23-\x2b\x2d-\x3a\x3c-\x5b\x5d-\x7e]*"
# Like above with SP included
_LIBERAL_VALUE_FORMAT = r"[\x20\x21\x23-\x2b\x2d-\x3a\x3c-\x5b\x5d-\x7e]*"
# A key-value is key=value, with optional whitespace surrounding key and value
_KEY_VALUE_FORMAT = rf"{_OWS}{_KEY_FORMAT}{_OWS}={_OWS}{_VALUE_FORMAT}{_OWS}"

_HEADER_PATTERN = compile(_KEY_VALUE_FORMAT)
_LIBERAL_HEADER_PATTERN = compile(rf"{_OWS}{_KEY_FORMAT}{_OWS}={_OWS}{_LIBERAL_VALUE_FORMAT}{_OWS}")

_INVALID_HEADER_ERROR_MESSAGE_STRICT_TEMPLATE = (
    "Header format invalid! Header values in environment variables must be "
    "URL encoded per the OpenTelemetry Protocol Exporter specification: %s"
)

_INVALID_HEADER_ERROR_MESSAGE_LIBERAL_TEMPLATE = (
    "Header format invalid! Header values in environment variables must be "
    "URL encoded per the OpenTelemetry Protocol Exporter specification or "
    "a comma separated list of name=value occurrences: %s"
)

# pylint: disable=invalid-name


@deprecated("You should use parse_env_headers. Deprecated since version 1.15.0.")
def parse_headers(s: str) -> Mapping[str, str]:
    """Parse HTTP headers taken from an environment variable.

    Args:
        s: The raw environment variable value holding the headers.

    Returns:
        A mapping from lowercased header name to header value.

    .. deprecated:: 1.15.0
        Use :func:`parse_env_headers` instead.
    """
    return parse_env_headers(s)


def parse_env_headers(s: str, liberal: bool = False) -> Mapping[str, str]:
    """Parse HTTP headers encoded for use in an environment variable.

    ``s`` holds comma separated ``name=value`` pairs in the W3C Baggage HTTP
    header format at https://www.w3.org/TR/baggage/#baggage-http-header-format,
    except that the additional semi-colon delimited metadata is not supported.
    Names are lowercased. Both halves are URL-decoded only for a pair that
    matches the strict pattern above; a pair accepted only because ``liberal``
    is set is taken verbatim, so a percent escape in it survives into the
    result.

    A pair that does not match the expected format is skipped and a warning is
    logged, so a single malformed entry does not discard the rest.

    Args:
        s: The raw environment variable value holding the headers.
        liberal: When ``True``, also accept values that are not URL-encoded,
            which matches the behaviour of the SDKs of several other languages.
            A space is permitted inside a value in this mode. Defaults to
            ``False``, which accepts only the spec-conformant encoding.

    Returns:
        A mapping from lowercased header name to header value, holding one
        entry per pair that parsed successfully.
    """
    headers: dict[str, str] = {}
    headers_list: list[str] = [header.strip(" \t") for header in s.split(",")]
    for header in headers_list:
        if not header:  # empty string
            continue
        header_match = _HEADER_PATTERN.fullmatch(header.strip())
        if not header_match and not liberal:
            _logger.warning(_INVALID_HEADER_ERROR_MESSAGE_STRICT_TEMPLATE, header)
            continue

        if header_match:
            match_string: str = header_match.string
            # value may contain any number of `=`
            name, value = match_string.split("=", 1)
            name = unquote(name).strip().lower()
            value = unquote(value).strip()
            headers[name] = value
        else:
            # this is not url-encoded and does not match the spec but we decided to be
            # liberal in what we accept to match other languages SDKs behaviour
            liberal_header_match = _LIBERAL_HEADER_PATTERN.fullmatch(header.strip())
            if not liberal_header_match:
                _logger.warning(_INVALID_HEADER_ERROR_MESSAGE_LIBERAL_TEMPLATE, header)
                continue

            liberal_match_string: str = liberal_header_match.string
            # value may contain any number of `=`
            name, value = liberal_match_string.split("=", 1)
            name = name.strip().lower()
            value = value.strip()
            headers[name] = value

    return headers
