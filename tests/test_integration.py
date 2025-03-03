import os
import random
import unittest

from nextmv import cloud

# Get token for communication with platform
TOKEN = os.getenv("NEXTMV_TOKEN_NEXTPIPE")
CLIENT = cloud.Client(api_key=TOKEN)

# Generate a random APP_ID
APP_ID = "int-test-" + "".join(random.choices("0123456789", k=8))


def _create_app() -> cloud.Application:
    app = cloud.Application.new(CLIENT, APP_ID, APP_ID)
    # app.push()  # Use verbose=True for step-by-step output.
    return app


class TestLogger(unittest.TestCase):
    def test_apps(self):
        app = _create_app()
        self.assertEqual(app.id, APP_ID)
        app.delete()
