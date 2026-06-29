import unittest

from connectors import sqlws


class SqlwsTimeoutTests(unittest.TestCase):
    def test_normalize_timeout_secs_handles_common_inputs(self):
        self.assertEqual(sqlws._normalize_timeout_secs(None), 0)
        self.assertEqual(sqlws._normalize_timeout_secs(0), 0)
        self.assertEqual(sqlws._normalize_timeout_secs("30"), 30)
        self.assertEqual(sqlws._normalize_timeout_secs(-5), 0)
        self.assertEqual(sqlws._normalize_timeout_secs("abc"), 0)
        self.assertEqual(sqlws._normalize_timeout_secs(sqlws.MAX_TIMEOUT_SECS + 10), sqlws.MAX_TIMEOUT_SECS)


if __name__ == "__main__":
    unittest.main()
