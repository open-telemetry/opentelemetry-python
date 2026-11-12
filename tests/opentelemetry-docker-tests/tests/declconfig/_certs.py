# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Generation of the throwaway CA, server and client certificates used by the TLS scenarios."""

from __future__ import annotations

import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

# The name the server certificate is issued for. TLS scenarios dial it and
# resolve it to the collector themselves, see the README.
TLS_SERVER_NAME = "otel-collector.test"

# Readable by the collector container, which runs as a different user.
_FILE_MODE = 0o644
_VALIDITY = datetime.timedelta(days=1)


def _build_name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _write_pem(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(_FILE_MODE)


def _private_key_to_pem(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _issue_leaf_certificate(
    common_name: str,
    extended_key_usage: x509.ObjectIdentifier,
    ca_certificate: x509.Certificate,
    ca_key: ec.EllipticCurvePrivateKey,
    san: x509.SubjectAlternativeName | None = None,
) -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(_build_name(common_name))
        .issuer_name(ca_certificate.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(hours=1))
        .not_valid_after(now + _VALIDITY)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([extended_key_usage]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
    )
    if san is not None:
        builder = builder.add_extension(san, critical=False)
    return builder.sign(ca_key, hashes.SHA256()), key


def write_tls_certs(directory: Path) -> None:
    """Write ``ca.crt``, ``server.crt``/``server.key`` and ``client.crt``/``client.key`` to ``directory``."""
    ca_key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_certificate = (
        x509.CertificateBuilder()
        .subject_name(_build_name("declconfig-test-ca"))
        .issuer_name(_build_name("declconfig-test-ca"))
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(hours=1))
        .not_valid_after(now + _VALIDITY)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    server_certificate, server_key = _issue_leaf_certificate(
        TLS_SERVER_NAME,
        ExtendedKeyUsageOID.SERVER_AUTH,
        ca_certificate,
        ca_key,
        san=x509.SubjectAlternativeName([x509.DNSName(TLS_SERVER_NAME)]),
    )
    client_certificate, client_key = _issue_leaf_certificate(
        "declconfig-client",
        ExtendedKeyUsageOID.CLIENT_AUTH,
        ca_certificate,
        ca_key,
    )

    _write_pem(directory / "ca.crt", ca_certificate.public_bytes(serialization.Encoding.PEM))
    _write_pem(directory / "server.crt", server_certificate.public_bytes(serialization.Encoding.PEM))
    _write_pem(directory / "server.key", _private_key_to_pem(server_key))
    _write_pem(directory / "client.crt", client_certificate.public_bytes(serialization.Encoding.PEM))
    _write_pem(directory / "client.key", _private_key_to_pem(client_key))
