from unittest import TestCase
from unittest.mock import patch

from grpc import Compression

from opentelemetry.exporter.otlp.exporter import environ_to_compression


class TestOTLPExporterMixin(TestCase):
    def test_environ_to_compression(self):
        with patch.dict(
            "os.environ",
            {
                "test_gzip": "gzip",
                "test_deflate": "deflate",
                "test_invalid": "some invalid compression",
            },
        ):
            self.assertEqual(
                environ_to_compression("test_gzip"), Compression.Gzip
            )
            self.assertEqual(
                environ_to_compression("test_deflate"), Compression.Deflate
            )
            self.assertIsNone(environ_to_compression("missing_key"),)
            with self.assertRaises(Exception):
                environ_to_compression("test_invalid")
