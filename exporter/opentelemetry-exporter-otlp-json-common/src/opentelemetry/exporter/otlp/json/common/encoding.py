import enum


class IdEncoding(enum.Enum):
    """
    Encoding for OpenTelemetry IDs.
    JSON Protobuf uses base64 encoding for IDs.
    JSON file uses hex encoding for IDs.
    """

    BASE64 = "base64"
    HEX = "hex"
