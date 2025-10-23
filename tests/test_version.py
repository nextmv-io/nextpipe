import os
import sys
import unittest

import nextpipe

# Add the parent directory to the sys.path to allow imports from the main package. This
# is meant to help VS Code testing features.
sys.path.append(os.path.dirname(sys.path[0]))


class TestLogger(unittest.TestCase):
    def test_version(self):
        exported_version = nextpipe.VERSION
        expected_version = nextpipe.__about__.__version__
        self.assertEqual(exported_version, expected_version)
