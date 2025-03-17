from .flow import FlowGraph
from .uplink import UplinkClient, UplinkConfig
from .utils import log


class Runner:
    def __init__(self, graph: FlowGraph, uplink_config: UplinkConfig):
        self.graph = graph
        self.uplink = UplinkClient(uplink_config)

    def run(self):
        # Start communicating updates to the platform
        try:
            self.uplink.post_graph(self.graph)
            self.uplink.run_async()
        except Exception as e:
            self.uplink.terminate()
            log(f"Failed to update graph with platform: {e}")

        # TODO: Implement the logic to run the pipeline
