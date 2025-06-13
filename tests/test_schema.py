import unittest

from nextpipe import AppOption, AppRunConfig


class TestAppRunConfig(unittest.TestCase):
    def test_options_dict(self):
        config = AppRunConfig(input={"data": [1, 2, 3]}, options={"threads": 4, "verbose": True}, name="test-run")
        options = config.get_options()
        self.assertEqual(options["threads"], "4")
        self.assertEqual(options["verbose"], "True")

    def test_options_obj(self):
        config = AppRunConfig(
            input={"data": [1, 2, 3]},
            options=[AppOption(name="threads", value=4), AppOption(name="verbose", value=True)],
            name="test-run",
        )
        options = config.get_options()
        self.assertEqual(options["threads"], "4")
        self.assertTrue(options["verbose"], "True")
