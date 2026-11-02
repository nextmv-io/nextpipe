import os
import signal
import sys
import threading
import time
import unittest
from unittest import mock

from nextpipe import FlowSpec, app, needs, step
from nextpipe.flow import STATUS_FAILED

# Add the parent directory to the sys.path to allow imports from the main package. This
# is meant to help VS Code testing features.
sys.path.append(os.path.dirname(sys.path[0]))


class _FakeApplication:
    """Stand-in for a nextmv Application whose runs only end when cancelled."""

    instances: list["_FakeApplication"] = []
    lock = threading.Lock()
    started = threading.Event()
    fail_cancel = False

    def __init__(self, client=None, id=None, **kwargs):
        self.id = id
        self.default_instance_id = None
        self.cancelled: list[str] = []
        with _FakeApplication.lock:
            _FakeApplication.instances.append(self)

    @classmethod
    def reset(cls):
        cls.instances = []
        cls.started = threading.Event()
        cls.fail_cancel = False

    @classmethod
    def cancelled_runs(cls) -> list[str]:
        with cls.lock:
            return sorted(r for a in cls.instances for r in a.cancelled)

    def new_run(self, **kwargs) -> str:
        _FakeApplication.started.set()
        return f"run-{self.id}"

    def run_result_with_polling(self, run_id, polling_options, output_dir_path):
        # Poll until the stop condition (i.e., the node cancel flag) is met.
        while not polling_options.stop():
            time.sleep(0.01)
        raise RuntimeError("polling stopped")

    def cancel_run(self, run_id: str) -> None:
        if _FakeApplication.fail_cancel:
            raise RuntimeError("cancel failed")
        with _FakeApplication.lock:
            self.cancelled.append(run_id)


class SubRunFlow(FlowSpec):
    @step
    def prepare(data: dict) -> dict:
        return data

    @app(app_id="solver-a")
    @needs(predecessors=[prepare])
    @step
    def solve_a() -> None:
        pass

    @app(app_id="solver-b")
    @needs(predecessors=[prepare])
    @step
    def solve_b() -> None:
        pass

    @needs(predecessors=[prepare])
    @step
    def broken(data: dict) -> None:
        if data.get("fail"):
            _FakeApplication.started.wait(5)
            time.sleep(0.2)  # Give both app steps the chance to start their runs
            raise ValueError("boom")
        _FakeApplication.started.wait(5)


def _interrupt_when_started(sig: int):
    """Send the given signal to this process once the sub-runs have been started."""

    def target():
        _FakeApplication.started.wait(5)
        time.sleep(0.2)
        os.kill(os.getpid(), sig)

    threading.Thread(target=target, daemon=True).start()


@mock.patch("nextpipe.flow.Application", _FakeApplication)
class TestCascadingCancel(unittest.TestCase):
    def setUp(self):
        _FakeApplication.reset()

    def test_failure_cancels_sub_runs(self):
        flow = SubRunFlow("SubRun", {"fail": True})
        with self.assertRaises(RuntimeError):
            flow.run()
        self.assertEqual(_FakeApplication.cancelled_runs(), ["run-solver-a", "run-solver-b"])

    def test_keyboard_interrupt_cancels_sub_runs(self):
        flow = SubRunFlow("SubRun", {})
        _interrupt_when_started(signal.SIGINT)
        with self.assertRaises(KeyboardInterrupt):
            flow.run()
        self.assertEqual(_FakeApplication.cancelled_runs(), ["run-solver-a", "run-solver-b"])
        for node in flow.graph.get_step(SubRunFlow.solve_a.step).nodes:
            self.assertTrue(node.cancel)
            self.assertEqual(node.status, STATUS_FAILED)

    def test_sigterm_cancels_sub_runs(self):
        previous = signal.getsignal(signal.SIGTERM)
        flow = SubRunFlow("SubRun", {})
        _interrupt_when_started(signal.SIGTERM)
        with self.assertRaises(SystemExit):
            flow.run()
        self.assertEqual(_FakeApplication.cancelled_runs(), ["run-solver-a", "run-solver-b"])
        # The previous SIGTERM handler is restored after the flow ran
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)

    def test_failing_cancel_request_does_not_mask_interrupt(self):
        _FakeApplication.fail_cancel = True
        flow = SubRunFlow("SubRun", {})
        _interrupt_when_started(signal.SIGINT)
        with self.assertRaises(KeyboardInterrupt):
            flow.run()
        self.assertEqual(_FakeApplication.cancelled_runs(), [])


if __name__ == "__main__":
    unittest.main()
