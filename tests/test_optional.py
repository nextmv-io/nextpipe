import os
import sys
import unittest

from nextmv.deprecated import NextmvDeprecationWarning

from nextpipe import FlowSpec, decorators, foreach, join, needs, optional, step
from nextpipe.flow import STATUS_SKIPPED, STATUS_SUCCEEDED

# Add the parent directory to the sys.path to allow imports from the main package. This
# is meant to help VS Code testing features.
sys.path.append(os.path.dirname(sys.path[0]))


class IfElseFlow(FlowSpec):
    @step
    def prepare(data: dict) -> dict:
        return data

    @optional(condition=lambda step, data: data["mode"] == "a", skip_downstream=True)
    @needs(predecessors=[prepare])
    @step
    def branch_a(data: dict) -> str:
        return "a"

    @optional(condition=lambda step, data: data["mode"] == "b", skip_downstream=True)
    @needs(predecessors=[prepare])
    @step
    def branch_b(data: dict) -> str:
        return "b"

    @needs(predecessors=[branch_b])
    @step
    def after_b(result: str) -> str:
        return result + "+"

    @needs(predecessors=[branch_a, after_b])
    @step
    def merge(a: str | None, b: str | None) -> str:
        return a or b


class LocalSkipFlow(FlowSpec):
    @optional(condition=lambda step: step.get_id() == "nope")
    @step
    def first() -> str:
        return "first"

    @needs(predecessors=[first])
    @step
    def second(result: str | None) -> str:
        return f"second after {result}"


class ForeachFlow(FlowSpec):
    @optional(condition=lambda step, data: data["fan_out"], skip_downstream=True)
    @foreach()
    @step
    def fan_out(data: dict) -> list[int]:
        return [1, 2, 3]

    @needs(predecessors=[fan_out])
    @step
    def work(item: int) -> int:
        return item * 2

    @join()
    @needs(predecessors=[work])
    @step
    def collect(results: list[list[int]]) -> list[int]:
        return [r[0] for r in results]


class SkipThenCollectFlow(FlowSpec):
    @foreach()
    @step
    def split(data: dict) -> list[int]:
        return [1, 2]

    @optional(condition=lambda step: False)
    @needs(predecessors=[split])
    @step
    def refine(item: int) -> int:
        return item

    @join()
    @needs(predecessors=[refine])
    @step
    def merge(results: list[list[int | None]]) -> str:
        return "merged"

    @needs(predecessors=[merge])
    @step
    def finish(result: str) -> str:
        return result + "+"


def _statuses(flow: FlowSpec) -> dict[str, list[str]]:
    return {s.definition.get_id(): [n.status for n in s.nodes] for s in flow.graph.steps}


class TestOptional(unittest.TestCase):
    def test_branch_a(self):
        flow = IfElseFlow("IfElse", {"mode": "a"})
        flow.run()
        self.assertEqual(flow.get_result(flow.merge), "a")
        statuses = _statuses(flow)
        self.assertEqual(statuses["branch_a"], [STATUS_SUCCEEDED])
        self.assertEqual(statuses["branch_b"], [STATUS_SKIPPED])
        self.assertEqual(statuses["after_b"], [STATUS_SKIPPED])  # Skip propagates
        self.assertEqual(statuses["merge"], [STATUS_SUCCEEDED])  # One branch was taken
        self.assertIsNone(flow.get_result(flow.after_b))

    def test_branch_b(self):
        flow = IfElseFlow("IfElse", {"mode": "b"})
        flow.run()
        self.assertEqual(flow.get_result(flow.merge), "b+")
        statuses = _statuses(flow)
        self.assertEqual(statuses["branch_a"], [STATUS_SKIPPED])
        self.assertEqual(statuses["after_b"], [STATUS_SUCCEEDED])

    def test_no_branch_skips_merge(self):
        flow = IfElseFlow("IfElse", {"mode": "c"})
        flow.run()
        self.assertEqual(_statuses(flow)["merge"], [STATUS_SKIPPED])
        self.assertIsNone(flow.get_result(flow.merge))

    def test_local_skip_by_default(self):
        flow = LocalSkipFlow("LocalSkip", None)
        flow.run()
        self.assertEqual(_statuses(flow), {"first": [STATUS_SKIPPED], "second": [STATUS_SUCCEEDED]})
        self.assertEqual(flow.get_result(flow.second), "second after None")

    def test_skipped_foreach(self):
        flow = ForeachFlow("Foreach", {"fan_out": True})
        flow.run()
        self.assertEqual(flow.get_result(flow.collect), [2, 4, 6])

        flow = ForeachFlow("Foreach", {"fan_out": False})
        flow.run()
        self.assertEqual(
            _statuses(flow),
            {"fan_out": [STATUS_SKIPPED], "work": [STATUS_SKIPPED], "collect": [STATUS_SKIPPED]},
        )

    def test_skip_then_collect(self):
        flow = SkipThenCollectFlow("SkipThenCollect", {})
        flow.run()
        self.assertEqual(
            _statuses(flow),
            {
                "split": [STATUS_SUCCEEDED],
                "refine": [STATUS_SKIPPED],
                "merge": [STATUS_SUCCEEDED],
                "finish": [STATUS_SUCCEEDED],
            },
        )
        self.assertEqual(flow.get_result(flow.finish), "merged+")


class _Conditions:
    def only_step(self, step):
        return step == "s"

    def with_input(self, step, data):
        return data == "d"


class TestConditionArguments(unittest.TestCase):
    def _evaluate(self, condition) -> bool:
        return decorators.Optional(condition).evaluate("s", ["d"])

    def test_step_only(self):
        self.assertTrue(self._evaluate(lambda step: step == "s"))

    def test_with_inputs(self):
        self.assertTrue(self._evaluate(lambda step, data: data == "d"))
        self.assertTrue(self._evaluate(lambda step, *inputs: inputs == ("d",)))

    def test_defaults_are_not_inputs(self):
        self.assertTrue(self._evaluate(lambda step, verbose=False: step == "s" and verbose is False))

    def test_bound_methods(self):
        conditions = _Conditions()
        self.assertTrue(self._evaluate(conditions.only_step))
        self.assertTrue(self._evaluate(conditions.with_input))

    def test_deprecated_skip(self):
        @optional(condition=lambda step: False)
        @step
        def skipped():
            pass

        with self.assertWarns(NextmvDeprecationWarning):
            self.assertTrue(skipped.step.skip())


if __name__ == "__main__":
    unittest.main()
