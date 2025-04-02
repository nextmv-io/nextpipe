import random
import time
import unittest

import nextmv.cloud

from nextpipe import FlowSpec, app, needs, step
from nextpipe.uplink import FlowDTO, FlowUpdateDTO, NodeDTO, StepDTO, UplinkClient


class Flow(FlowSpec):
    @step
    def prepare(input: dict):
        """Prepares the data."""
        return input

    @app(app_id="echo")
    @needs(predecessors=[prepare])
    @step
    def solve():
        """Runs the model."""
        pass

    @needs(predecessors=[solve])
    @step
    def enhance(result: dict):
        """Enhances the result."""
        return result


def _create_example_flow() -> FlowUpdateDTO:
    steps = [
        StepDTO(
            id="prepare",
            app_id=None,
            docs="Prepares the data.",
            predecessors=[],
        ),
        StepDTO(
            id="solve",
            app_id="echo",
            docs="Runs the model.",
            predecessors=["prepare"],
        ),
        StepDTO(
            id="enhance",
            app_id=None,
            predecessors=["solve"],
        ),
    ]
    nodes = [
        NodeDTO(
            id="prepare_0",
            parent_id="prepare",
            predecessor_ids=[],
            status="succeeded",
            run_id=None,
        ),
        NodeDTO(
            id="solve_0",
            parent_id="solve",
            predecessor_ids=["prepare_0"],
            status="succeeded",
            run_id="run-123",
        ),
        NodeDTO(
            id="solve_1",
            parent_id="solve",
            predecessor_ids=["prepare_0"],
            status="succeeded",
            run_id="run-124",
        ),
        NodeDTO(
            id="enhance_0",
            parent_id="enhance",
            predecessor_ids=["solve_0", "solve_1"],
            status="succeeded",
            run_id=None,
        ),
    ]
    flow = FlowUpdateDTO(
        pipeline_graph=FlowDTO(steps=steps, nodes=nodes),
        updated_at="2023-10-01T12:00:00Z",
    )

    return flow


class TestLogger(unittest.TestCase):
    def test_no_uplink(self):
        flow = _create_example_flow()
        client = nextmv.cloud.Client(
            api_key="unavailable",
            max_retries=0,
            url=f"https://unavailable.url/{random.randint(0, 1000)}",
        )
        # Make sure that unavailable uplink connection does not break a run.
        uplink = UplinkClient(client=client, config=None)
        uplink.run_async()
        uplink.submit_update(flow)
        time.sleep(0.5)
        uplink.terminate()
        time.sleep(0.5)
