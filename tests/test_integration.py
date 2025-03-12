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

            # Create app for testing
            app = cloud.Application.new(CLIENT, APP_ID, APP_ID)
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
            result = app.new_run_with_result(input={"random": r})
            self.assertTrue(hasattr(result, "error_log") and result.error_log is None)
            self.assertEqual(result.output["echo"]["enhanced"], True)
            self.assertEqual(result.output["echo"]["prepared"], True)
            self.assertEqual(result.output["echo"]["random"], r)
        finally:
            # Make sure to delete the app
            if app:
                app.delete()


class TestExample(unittest.TestCase):
    def test_locals(self):
        # Create key file
        path = os.path.join(os.path.dirname(__file__), "pipelines")
        _create_key_file(path)

        # Define golden file tests
        config = goldie.ConfigDirectoryTest(
            # We want to test all JSON files in the data directory.
            explicit_files=[
                goldie.TestDefinition(
                    input_file=os.path.join(path, "chain.json"),
                    extra_args=[("pipeline", os.path.join(path, "chain.py"))],
                )
            ],
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
        goldie.directory.run_unittest(self, config)


if __name__ == "__main__":
    unittest.main()
