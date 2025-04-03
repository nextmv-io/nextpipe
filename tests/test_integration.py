import os
import os.path
import random
import unittest

import goldie
from nextmv import cloud

# Get token for communication with platform
API_KEY = os.getenv("NEXTMV_API_KEY_NEXTPIPE")
CLIENT = cloud.Client(api_key=API_KEY)


def _create_key_file(path: str):
    with open(os.path.join(path, "key.json"), "w") as f:
        f.write(f'{{"nextmv_api_key": "{API_KEY}"}}')


class TestPlatform(unittest.TestCase):
    def test_platform(self):
        try:
            # Generate a random APP_ID
            app = None
            APP_ID = "int-test-" + "".join(random.choices("0123456789", k=8))

            # Log test app id
            print(f"Test app id: {APP_ID}")

            # Create app for testing
            app = cloud.Application.new(CLIENT, APP_ID, APP_ID, is_workflow=True)
            self.assertEqual(app.id, APP_ID)

            # Check if app is created
            app = cloud.Application(CLIENT, APP_ID)
            self.assertIsNotNone(app)
            self.assertEqual(app.id, APP_ID)

            # Push the app to the platform
            path = os.path.join(os.path.dirname(__file__), "deploy")
            current_dir = os.getcwd()
            os.chdir(path)
            _create_key_file(path)
            app.push()  # Use verbose=True for step-by-step output.
            os.chdir(current_dir)

            # Run the app
            r = random.randint(0, 100)
            polling_opts = cloud.PollingOptions(max_tries=500, max_duration=240)
            result = app.new_run_with_result(input={"random": r}, polling_options=polling_opts)
            self.assertTrue(hasattr(result, "error_log") and result.error_log is None)
            self.assertEqual(result.output["echo"]["data"]["enhanced"], True)
            self.assertEqual(result.output["echo"]["data"]["prepared"], True)
            self.assertEqual(result.output["echo"]["data"]["random"], r)
        finally:
            # Make sure to delete the app
            if app:
                app.delete()


class TestExample(unittest.TestCase):
    def test_locals(self):
        # Create key file
        path = os.path.join(os.path.dirname(__file__), "pipelines")
        _create_key_file(path)

        # Create base configuration
        config = goldie.ConfigFileTest(
            run_configuration=goldie.ConfigRun(
                # We simply run the script in this directory.
                cmd="python",
                args=["{pipeline}"],
                cwd=path,
                # The script reads from stdin and writes to stdout.
                input_mode=goldie.InputMode.STDIN,
                output_mode=goldie.OutputMode.STDOUT,
            ),
            comparison_configuration=goldie.ConfigComparison(
                # We want to leverage the JSON structure instead of comparing raw strings.
                comparison_type=goldie.ComparisonType.JSON,
            ),
        )

        # CHAIN
        goldie.run_file_unittest(
            test=self,
            td=goldie.TestDefinition(
                input_file=os.path.join(path, "chain.json"),
                extra_args=[("pipeline", os.path.join(path, "chain.py"))],
            ),
            configuration=config,
        )

        # FOREACH
        config.comparison_configuration.json_processing_config = goldie.ConfigProcessJson(
            replacements=[
                goldie.JsonReplacement(path="$[0].statistics.run.duration", value=0.123),
                goldie.JsonReplacement(path="$[1].statistics.run.duration", value=0.123),
                goldie.JsonReplacement(path="$[2].statistics.run.duration", value=0.123),
            ],
        )
        goldie.run_file_unittest(
            test=self,
            td=goldie.TestDefinition(
                input_file=os.path.join(path, "foreach.json"),
                extra_args=[("pipeline", os.path.join(path, "foreach.py"))],
            ),
            configuration=config,
        )

        # FOREACH 2 PREDECESSORS
        config.comparison_configuration.json_processing_config = goldie.ConfigProcessJson(
            replacements=[
                goldie.JsonReplacement(path="$[0][0].statistics.run.duration", value=0.123),
                goldie.JsonReplacement(path="$[1][0].statistics.run.duration", value=0.123),
                goldie.JsonReplacement(path="$[2][0].statistics.run.duration", value=0.123),
            ],
        )
        goldie.run_file_unittest(
            test=self,
            td=goldie.TestDefinition(
                input_file=os.path.join(path, "foreach-2-pred.json"),
                extra_args=[("pipeline", os.path.join(path, "foreach-2-pred.py"))],
            ),
            configuration=config,
        )

        # COMPLEX
        config.comparison_configuration.json_processing_config = goldie.ConfigProcessJson(
            replacements=[
                goldie.JsonReplacement(path="$.statistics.result.duration", value="0.123"),
                goldie.JsonReplacement(path="$.statistics.run.duration", value="0.123"),
            ],
        )
        goldie.run_file_unittest(
            test=self,
            td=goldie.TestDefinition(
                input_file=os.path.join(path, "complex.json"),
                extra_args=[("pipeline", os.path.join(path, "complex.py"))],
            ),
            configuration=config,
        )


if __name__ == "__main__":
    unittest.main()
