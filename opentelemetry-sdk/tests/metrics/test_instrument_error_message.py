import unittest

from opentelemetry.sdk.metrics._internal.instrument import _Synchronous
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

class TestInstrumentErrorMessage(unittest.TestCase):
    def test_invalid_name_error_message(self):
        scope = InstrumentationScope("test")
        with self.assertRaises(Exception) as cm:
            _Synchronous("1invalid", scope, object())
        msg = str(cm.exception)
        self.assertIn("start with a letter", msg)
        self.assertIn("255", msg)

    def test_invalid_unit_error_message(self):
        scope = InstrumentationScope("test")
        # name valid, unit invalid (non-ASCII)
        with self.assertRaises(Exception) as cm:
            _Synchronous("validname", scope, object(), unit="Ñ")
        msg = str(cm.exception)
        self.assertIn("maximum length 63", msg)
        self.assertIn("ASCII", msg)


if __name__ == "__main__":
    unittest.main()
