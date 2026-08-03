# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""grpc-python-compatible surface backed by the pure-Python _pygrpc transport.

The OTLP gRPC exporter and the generated service stubs are written against a
small slice of the ``grpc`` module: ``Compression``, ``StatusCode``,
``RpcError``, ``ChannelCredentials``, ``ssl_channel_credentials``, and the
``insecure_channel`` / ``secure_channel`` factories whose channels expose
``unary_unary``. This module provides exactly that surface over ``_pygrpc`` so
the exporter runs without the ``grpcio`` C extension. Only unary calls are
supported (all OTLP export RPCs are unary).
"""

import os
import ssl
import tempfile

from .client import Channel as _PyGrpcChannel
from .client import Compression, RpcError, StatusCode

__all__ = [
    "ChannelCredentials",
    "Compression",
    "RpcError",
    "StatusCode",
    "insecure_channel",
    "secure_channel",
    "ssl_channel_credentials",
]


class ChannelCredentials:
    """TLS credentials for a secure channel, wrapping a configured SSLContext."""

    def __init__(self, ssl_context):
        self.ssl_context = ssl_context


def _write_temp(data):
    if isinstance(data, str):
        data = data.encode()
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    return path


def ssl_channel_credentials(
    root_certificates=None, private_key=None, certificate_chain=None
):
    """Build TLS credentials. ``root_certificates``, ``private_key``, and
    ``certificate_chain`` are PEM bytes (as the exporter reads them from the
    OTEL_EXPORTER_OTLP_* certificate files). ALPN ``h2`` is applied by the
    transport when it wraps the socket, so it is not set here."""
    context = ssl.create_default_context()
    if root_certificates:
        cadata = (
            root_certificates.decode("ascii")
            if isinstance(root_certificates, (bytes, bytearray))
            else root_certificates
        )
        context.load_verify_locations(cadata=cadata)
    if certificate_chain or private_key:
        # ssl.load_cert_chain reads files only; stage the in-memory PEM in
        # short-lived temp files, removed as soon as it is loaded.
        cert_file = key_file = None
        try:
            if certificate_chain:
                cert_file = _write_temp(certificate_chain)
            if private_key:
                key_file = _write_temp(private_key)
            context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        finally:
            for path in (cert_file, key_file):
                if path:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
    return ChannelCredentials(context)


def _strip_scheme(target):
    for scheme in ("https://", "http://"):
        if target.startswith(scheme):
            return target[len(scheme) :]
    return target


class _UnaryUnaryMultiCallable:
    """The callable a service stub binds to one method."""

    def __init__(self, channel, method, request_serializer, response_deserializer):
        self._channel = channel
        self._method = method
        self._serialize = request_serializer
        self._deserialize = response_deserializer

    def __call__(self, request, metadata=(), timeout=None):
        response_bytes = self._channel._call(
            self._method, self._serialize(request), metadata, timeout
        )
        return self._deserialize(response_bytes)


class _Channel:
    """A grpc-style channel over one _pygrpc connection."""

    def __init__(
        self, target, use_tls, ssl_context=None, compression=Compression.NoCompression
    ):
        self._pygrpc = _PyGrpcChannel(
            _strip_scheme(target), use_tls=use_tls, ssl_context=ssl_context
        )
        self._compression = compression or Compression.NoCompression

    def _call(self, method, request_bytes, metadata, timeout):
        return self._pygrpc.unary_call(
            method,
            request_bytes,
            metadata=tuple(metadata or ()),
            timeout=timeout,
            compression=self._compression,
        )

    def unary_unary(self, method, request_serializer, response_deserializer):
        return _UnaryUnaryMultiCallable(
            self, method, request_serializer, response_deserializer
        )

    def close(self):
        self._pygrpc.close()


# grpc-python signature parity: (target, options=None, compression=None) and
# (target, credentials, options=None, compression=None). ``options`` are
# grpcio channel tuning hints with no _pygrpc equivalent and are ignored.
def insecure_channel(target, options=None, compression=None):
    return _Channel(target, use_tls=False, compression=compression)


def secure_channel(target, credentials, options=None, compression=None):
    return _Channel(
        target,
        use_tls=True,
        ssl_context=credentials.ssl_context,
        compression=compression,
    )
