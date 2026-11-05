import io
import os
import sys
import threading
import unittest
from contextlib import redirect_stderr
from unittest import mock

import nextmv

from nextpipe import AppRunError, FlowSpec, app, foreach, join, needs, on_failure, step
from nextpipe.flow import STATUS_FAILED, STATUS_SUCCEEDED

# Add the parent directory to the sys.path to allow imports from the main package. This
# is meant to help VS Code testing features.
sys.path.append(os.path.dirname(sys.path[0]))


class _FakeApplication:
    """Stand-in for a nextmv Application whose runs end with a given status."""

    status = nextmv.StatusV2.failed
    error = "solver crashed"

    def __init__(self, client=None, id=None, **kwargs):
        self.id = id
        self.default_instance_id = None

    def new_run(self, **kwargs) -> str:
        return f"run-{self.id}"

    def run_information(self, run_id):
        status = _FakeApplication.status
        metadata = mock.Mock(status_v2=status, error=_FakeApplication.error, run_is_finalized=lambda: True)
        return mock.Mock(metadata=metadata)

    def run_result(self, run_id, output_dir_path):
        return mock.Mock(output={"solution": "ok"}, metadata=mock.Mock(error=""))


class FallbackFlow(FlowSpec):
    @step
    def prepare(data: dict) -> dict:
        return data

    @on_failure(fallback=lambda error: {"error": str(error)})
    @needs(predecessors=[prepare])
    @step
    def broken(data: dict) -> dict:
        raise ValueError("boom")

    @needs(predecessors=[broken])
    @step
    def report(result: dict) -> dict:
        return {"report": result}


class DefaultFallbackFlow(FlowSpec):
    @on_failure()
    @step
    def broken(data: dict) -> dict:
        raise ValueError("boom")

    @needs(predecessors=[broken])
    @step
    def report(result: dict | None) -> str:
        return "no result" if result is None else "result"


class FailingFallbackFlow(FlowSpec):
    @on_failure(fallback=lambda error: 1 / 0)
    @step
    def broken(data: dict) -> dict:
        raise ValueError("boom")


class ForeachFallbackFlow(FlowSpec):
    @foreach()
    @step
    def split(data: dict) -> list[int]:
        return [1, 2, 3]

    @on_failure(fallback=-1)
    @needs(predecessors=[split])
    @step
    def work(item: int) -> int:
        if item == 2:
            raise ValueError("boom")
        return item * 10

    @join()
    @needs(predecessors=[work])
    @step
    def collect(results: list[list[int]]) -> list[int]:
        return [r[0] for r in results]


class AppFlow(FlowSpec):
    @step
    def prepare(data: dict) -> dict:
        return data

    @app(app_id="solver")
    @needs(predecessors=[prepare])
    @step
    def solve() -> None:
        pass

    @needs(predecessors=[solve])
    @step
    def report(result: dict) -> dict:
        return result


class AppFallbackFlow(FlowSpec):
    @step
    def prepare(data: dict) -> dict:
        return data

    @on_failure(fallback=lambda error: error)
    @app(app_id="solver")
    @needs(predecessors=[prepare])
    @step
    def solve() -> None:
        pass

    @needs(predecessors=[solve])
    @step
    def report(result) -> object:
        return result


class TestOnFailure(unittest.TestCase):
    def test_fallback_is_passed_to_successors(self):
        flow = FallbackFlow("Fallback", {})
        flow.run()
        self.assertEqual(flow.get_result(flow.report), {"report": {"error": "boom"}})
        node = flow.graph.get_step(FallbackFlow.broken.step).nodes[0]
        self.assertEqual(node.status, STATUS_FAILED)
        self.assertEqual(node.error, "boom")

    def test_handled_failure_does_not_print_traceback(self):
        unhandled = []
        previous_hook = threading.excepthook
        threading.excepthook = lambda args: unhandled.append(args.exc_value)
        try:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                FallbackFlow("Fallback", {}).run()
        finally:
            threading.excepthook = previous_hook
        self.assertEqual(unhandled, [])
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertIn("Node broken_0 failed, continuing with fallback: boom", stderr.getvalue())

    def test_failure_keeps_cause(self):
        flow = FailingFallbackFlow("FailingFallback", {})
        with self.assertRaises(RuntimeError) as ctx:
            flow.run()
        self.assertIsInstance(ctx.exception.__cause__, ZeroDivisionError)

    def test_default_fallback_is_none(self):
        flow = DefaultFallbackFlow("DefaultFallback", {})
        flow.run()
        self.assertEqual(flow.get_result(flow.report), "no result")

    def test_failing_fallback_fails_flow(self):
        flow = FailingFallbackFlow("FailingFallback", {})
        with self.assertRaises(RuntimeError) as ctx:
            flow.run()
        self.assertIn("division by zero", str(ctx.exception))

    def test_fallback_per_node(self):
        flow = ForeachFallbackFlow("ForeachFallback", {})
        flow.run()
        self.assertEqual(flow.get_result(flow.collect), [10, -1, 30])
        statuses = [n.status for n in flow.graph.get_step(ForeachFallbackFlow.work.step).nodes]
        self.assertEqual(statuses, [STATUS_SUCCEEDED, STATUS_FAILED, STATUS_SUCCEEDED])


@mock.patch("nextpipe.flow.Application", _FakeApplication)
@mock.patch("nextpipe.flow.random.uniform", lambda a, b: 0)
class TestAppRunFailure(unittest.TestCase):
    def setUp(self):
        _FakeApplication.status = nextmv.StatusV2.failed
        _FakeApplication.error = "solver crashed"

    def test_failed_run_fails_flow(self):
        flow = AppFlow("App", {}, client=mock.Mock(console_url="https://console"))
        with self.assertRaises(RuntimeError) as ctx:
            flow.run()
        message = str(ctx.exception)
        self.assertIn("Step solve failed", message)
        self.assertIn("run run-solver of app solver failed: solver crashed", message)
        self.assertIn("https://console/app/solver/run/run-solver", message)
        self.assertIsNone(flow.get_result(flow.report))
        # The error message describes the failed run, no traceback of nextpipe internals
        self.assertIsNone(ctx.exception.__cause__)

    def test_failed_run_with_fallback(self):
        flow = AppFallbackFlow("AppFallback", {}, client=mock.Mock(console_url="https://console"))
        flow.run()
        error = flow.get_result(flow.report)
        self.assertIsInstance(error, AppRunError)
        self.assertEqual(error.run_id, "run-solver")
        self.assertEqual(error.status, "failed")
        self.assertEqual(error.error, "solver crashed")

    def test_succeeded_run(self):
        _FakeApplication.status = nextmv.StatusV2.succeeded
        flow = AppFlow("App", {}, client=mock.Mock(console_url="https://console"))
        flow.run()
        self.assertEqual(flow.get_result(flow.report), {"solution": "ok"})


if __name__ == "__main__":
    unittest.main()
