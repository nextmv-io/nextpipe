import os
import sys
import unittest

import nextmv

from nextpipe import AppRunConfig, decorators
from nextpipe.flow import Runner

# Add the parent directory to the sys.path to allow imports from the main package. This
# is meant to help VS Code testing features.
sys.path.append(os.path.dirname(sys.path[0]))


class _FakeNode:
    """Minimal stand-in for a FlowNode, providing what run arg preparation needs."""

    def __init__(self, id: str = "solve_0"):
        self.id = id
        self.cancel = False


def _prepare(inputs: list[object], app_step: decorators.App) -> tuple[dict, str]:
    """Prepare the run kwargs and instance ID for the given inputs and app step."""

    run_kwargs, _, _, instance_id = Runner._Runner__prepare_app_run_args(_FakeNode(), inputs, app_step)
    return run_kwargs, instance_id


class TestPrepareAppRunArgs(unittest.TestCase):
    def test_no_run_configuration(self):
        app_step = decorators.App(app_id="echo")
        run_kwargs, _ = _prepare([{"data": [1, 2, 3]}], app_step)
        self.assertNotIn("configuration", run_kwargs)

    def test_decorator_run_configuration(self):
        app_step = decorators.App(
            app_id="echo",
            run_configuration=nextmv.RunConfiguration(execution_class="4c8gb12h"),
        )
        run_kwargs, _ = _prepare([{"data": [1, 2, 3]}], app_step)
        self.assertEqual(run_kwargs["configuration"].execution_class, "4c8gb12h")

    def test_app_run_config_run_configuration(self):
        app_step = decorators.App(app_id="echo")
        app_run_config = AppRunConfig(
            input={"data": [1, 2, 3]},
            run_configuration=nextmv.RunConfiguration(execution_class="8c16gb12h"),
        )
        run_kwargs, _ = _prepare([app_run_config], app_step)
        self.assertEqual(run_kwargs["configuration"].execution_class, "8c16gb12h")

    def test_app_run_config_run_configuration_replaces_decorator(self):
        """The run configuration of an AppRunConfig replaces the decorator one as a whole."""

        app_step = decorators.App(
            app_id="echo",
            run_configuration=nextmv.RunConfiguration(
                execution_class="4c8gb12h",
                secrets_collection_id="some-secrets",
            ),
        )
        app_run_config = AppRunConfig(
            input={"data": [1, 2, 3]},
            run_configuration=nextmv.RunConfiguration(execution_class="8c16gb12h"),
        )
        run_kwargs, _ = _prepare([app_run_config], app_step)
        self.assertEqual(run_kwargs["configuration"].execution_class, "8c16gb12h")
        self.assertIsNone(run_kwargs["configuration"].secrets_collection_id)

    def test_app_run_config_without_run_configuration_keeps_decorator(self):
        app_step = decorators.App(
            app_id="echo",
            run_configuration=nextmv.RunConfiguration(execution_class="4c8gb12h"),
        )
        app_run_config = AppRunConfig(input={"data": [1, 2, 3]})
        run_kwargs, _ = _prepare([app_run_config], app_step)
        self.assertEqual(run_kwargs["configuration"].execution_class, "4c8gb12h")

    def test_no_instance_id(self):
        app_step = decorators.App(app_id="echo")
        _, instance_id = _prepare([{"data": [1, 2, 3]}], app_step)
        self.assertEqual(instance_id, "")

    def test_decorator_instance_id(self):
        app_step = decorators.App(app_id="echo", instance_id="decorator-instance")
        _, instance_id = _prepare([{"data": [1, 2, 3]}], app_step)
        self.assertEqual(instance_id, "decorator-instance")

    def test_app_run_config_instance_id_replaces_decorator(self):
        app_step = decorators.App(app_id="echo", instance_id="decorator-instance")
        app_run_config = AppRunConfig(input={"data": [1, 2, 3]}, instance_id="per-run-instance")
        _, instance_id = _prepare([app_run_config], app_step)
        self.assertEqual(instance_id, "per-run-instance")

    def test_app_run_config_without_instance_id_keeps_decorator(self):
        app_step = decorators.App(app_id="echo", instance_id="decorator-instance")
        app_run_config = AppRunConfig(input={"data": [1, 2, 3]})
        _, instance_id = _prepare([app_run_config], app_step)
        self.assertEqual(instance_id, "decorator-instance")


if __name__ == "__main__":
    unittest.main()
