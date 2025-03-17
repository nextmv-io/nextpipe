import time
import unittest

from nextpipe import FlowSpec, app, needs, step
from nextpipe.uplink import UplinkClient, UplinkConfig


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


class TestLogger(unittest.TestCase):
    def test_no_uplink(self):
        # Make sure that unavailable uplink connection does not break a run.
        flow = Flow("DecisionFlow", {})
        uplink = UplinkClient(UplinkConfig())
        uplink.run_async()
        uplink.post_graph(flow.graph)
        uplink.enqueue_node_update(flow.graph.nodes[0])
        time.sleep(1)
