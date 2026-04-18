import unittest

from flet_pos.app import FletMarketApp


class AppVersioningTests(unittest.TestCase):
    def test_version_tuple_parses_v_prefix(self):
        self.assertEqual(FletMarketApp._version_tuple("V 1.0.2"), (1, 0, 2))

    def test_version_tuple_handles_short_values(self):
        self.assertEqual(FletMarketApp._version_tuple("V 2"), (2, 0, 0))
        self.assertEqual(FletMarketApp._version_tuple(""), (0, 0, 0))

    def test_is_newer_version(self):
        self.assertTrue(FletMarketApp._is_newer_version("V 1.0.3", "V 1.0.2"))
        self.assertFalse(FletMarketApp._is_newer_version("V 1.0.2", "V 1.0.2"))
        self.assertFalse(FletMarketApp._is_newer_version("V 0.9.9", "V 1.0.2"))


if __name__ == "__main__":
    unittest.main()
