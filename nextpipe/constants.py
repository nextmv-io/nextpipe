"""
Constants for nextpipe.

This module provides constants used across the nextpipe package.

Functions
--------
_get_run_info
    Retrieves information about the run from environment variables.
"""

import os

ENV_APP_ID = "NEXTMV_APP_ID"
"""Environment variable name for the application ID."""

ENV_RUN_ID = "NEXTMV_RUN_ID"
"""Environment variable name for the run ID."""


def _get_run_info():
    """
    Retrieves information about the run from environment variables.
    If the environment variables are not set, it returns None for both values.
    """
    app_id = os.environ.get(ENV_APP_ID)
    run_id = os.environ.get(ENV_RUN_ID)
    return app_id, run_id
