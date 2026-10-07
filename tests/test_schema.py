import os
import sys
import unittest

import nextmv

from nextpipe import AppOption, AppRunConfig

# Add the parent directory to the sys.path to allow imports from the main package. This
# is meant to help VS Code testing features.
sys.path.append(os.path.dirname(sys.path[0]))


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

    def test_run_configuration_default(self):
        config = AppRunConfig(input={"data": [1, 2, 3]})
        self.assertIsNone(config.run_configuration)

    def test_run_configuration(self):
        config = AppRunConfig(
            input={"data": [1, 2, 3]},
            run_configuration=nextmv.RunConfiguration(execution_class="8c16gb12h"),
        )
        self.assertEqual(config.run_configuration.execution_class, "8c16gb12h")

    def test_run_configuration_json_round_trip(self):
        config = AppRunConfig(
            input={"data": [1, 2, 3]},
            options={"threads": 4},
            run_configuration=nextmv.RunConfiguration(
                execution_class="8c16gb12h",
                secrets_collection_id="some-secrets",
            ),
        )
        restored = AppRunConfig.from_json(config.to_json())
        self.assertIsInstance(restored.run_configuration, nextmv.RunConfiguration)
        self.assertEqual(restored.run_configuration.execution_class, "8c16gb12h")
        self.assertEqual(restored.run_configuration.secrets_collection_id, "some-secrets")

    def test_run_configuration_json_round_trip_none(self):
        config = AppRunConfig(input={"data": [1, 2, 3]})
        restored = AppRunConfig.from_json(config.to_json())
        self.assertIsNone(restored.run_configuration)
