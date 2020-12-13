import logging

from grpc import ChannelCredentials, ssl_channel_credentials

from opentelemetry.configuration import Configuration

logger = logging.getLogger(__name__)

DEFAULT_INSECURE = False


def _get_insecure(param):
    if param is not None:
        return param
    insecure_env = Configuration().get("EXPORTER_JAEGER_INSECURE", None)
    if insecure_env is not None:
        return insecure_env.lower() == "true"
    return DEFAULT_INSECURE


def _load_credential_from_file(path) -> ChannelCredentials:
    try:
        with open(path, "rb") as f:
            credential = f.read()
            return ssl_channel_credentials(credential)
    except FileNotFoundError:
        logger.exception("Failed to read credential file")
        return None


def _get_credentials(param):
    if param is not None:
        return param
    creds_env = Configuration().get("EXPORTER_JAEGER_CERTIFICATE", None)
    if creds_env:
        return _load_credential_from_file(creds_env)
    return ssl_channel_credentials()
