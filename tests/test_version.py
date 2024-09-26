import unittest

import nextpipe


class TestLogger(unittest.TestCase):
    def test_version(self):
        exported_version = nextpipe.VERSION
        expected_version = nextpipe.__about__.__version__
        self.assertEqual(exported_version, expected_version)
