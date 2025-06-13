import unittest

from nextpipe import AppRunConfig


class TestAppRunConfig(unittest.TestCase):
    def test_options(self):
        config = AppRunConfig(input={"data": [1, 2, 3]}, options={"threads": 4, "verbose": True}, name="test-run")
        options = config.get_options()
        self.assertEqual(options["threads"], "4")
        self.assertTrue(options["verbose"], "True")
