import unittest

from app import core


class TestImport(unittest.TestCase):
    def test_import_core(self):
        self.assertIsNotNone(core)


if __name__ == "__main__":
    unittest.main()
