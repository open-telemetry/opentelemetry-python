# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Proxy resolution from the environment, mirroring the behavior of ``requests``."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import unquote, urlparse
from urllib.request import getproxies, proxy_bypass


def _get_no_proxy() -> str | None:
    return os.environ.get("no_proxy") or os.environ.get("NO_PROXY")


def _is_ipv4_address(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        return False
    return True


def _address_in_network(address: str, network: str) -> bool:
    if "/" not in network:
        return False
    try:
        return ipaddress.IPv4Address(address) in ipaddress.IPv4Network(network, strict=False)
    except ValueError:
        return False


def _should_bypass_proxies(url: str) -> bool:
    """Return ``True`` if requests to *url* should not go through a proxy.

    Matches ``requests.utils.should_bypass_proxies``: entries in ``NO_PROXY``
    are compared against the host (IPv4 hosts by exact address or CIDR, other
    hosts by suffix, with or without port), then the platform's bypass rules
    are consulted via :func:`urllib.request.proxy_bypass`.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if hostname is None:
        return True

    no_proxy = _get_no_proxy()
    if no_proxy:
        entries = [entry for entry in no_proxy.replace(" ", "").split(",") if entry]
        if _is_ipv4_address(hostname):
            for entry in entries:
                if hostname == entry or _address_in_network(hostname, entry):
                    return True
        else:
            host_with_port = hostname
            if parsed.port:
                host_with_port += f":{parsed.port}"
            for entry in entries:
                if hostname.endswith(entry) or host_with_port.endswith(entry):
                    return True

    try:
        return bool(proxy_bypass(hostname))
    except (TypeError, socket.gaierror):
        return False


def _get_environ_proxy(url: str) -> str | None:
    """Return the proxy URL to use for *url*, or ``None`` for a direct connection.

    Proxies are read with :func:`urllib.request.getproxies`, which honors the
    ``<scheme>_proxy`` and ``all_proxy`` environment variables (lowercase taking
    precedence over uppercase) and falls back to the system proxy configuration
    on macOS and Windows. The scheme specific proxy is preferred over
    ``all_proxy``. Proxy URLs without a scheme are treated as ``http://``.
    """
    if _should_bypass_proxies(url):
        return None
    proxies = getproxies()
    scheme = urlparse(url).scheme.lower()
    proxy = proxies.get(scheme) or proxies.get("all")
    if not proxy:
        return None
    if "://" not in proxy:
        proxy = f"http://{proxy}"
    return proxy


def _get_proxy_auth(proxy_url: str) -> tuple[str, str] | tuple[None, None]:
    """Return the percent-decoded ``(username, password)`` from *proxy_url*."""
    parsed = urlparse(proxy_url)
    if parsed.username is None:
        return None, None
    return unquote(parsed.username), unquote(parsed.password or "")
