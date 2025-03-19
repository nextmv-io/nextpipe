import os
import threading
import time
from dataclasses import dataclass

from dataclasses_json import dataclass_json
from nextmv.cloud import Client

from nextpipe.utils import log

FAILED_UPDATES_THRESHOLD = 10
NODE_UPDATE_BATCH_SIZE = 20

ENV_APPLICATION_ID = "NEXTMV_APPLICATION_ID"
ENV_RUN_ID = "NEXTMV_RUN_ID"


@dataclass
class UplinkConfig:
    application_id: str
    run_id: str


@dataclass_json
@dataclass
class StepDTO:
    id: str
    """The ID of the step."""
    app_id: str
    """The ID of the app this step represents (if any)."""
    docs: str
    """The doc string of the step."""
    predecessors: list[str]
    """The IDs of the nodes that depend on this node."""


@dataclass_json
@dataclass
class FlowDTO:
    """
    Represents a flow in the platform.
    """

    steps: list[StepDTO]
    """
    Steps in the flow.
    """


@dataclass_json
@dataclass
class NodeDTO:
    id: str
    """
    Node ID based on the step ID and a number.
    """
    parent_id: str
    """
    Parent step.
    """
    predecessor_ids: list[str]
    """
    Predecessor nodes via their IDs.
    """
    status: str
    """
    Status of the node.
    """
    run_id: str = None
    """
    ID of the associated run, if any.
    """


@dataclass
class GraphDTO:
    steps: list[StepDTO]


class UplinkClient:
    """
    A client that posts graph and node updates to the platform.
    """

    def __init__(self, client: Client, config: UplinkConfig):
        if config is None:
            # Load config from environment
            config = UplinkConfig(
                application_id=os.environ.get(ENV_APPLICATION_ID),
                run_id=os.environ.get(ENV_RUN_ID),
            )
        self.config = config
        self.inactive = False
        if not self.config.application_id or not self.config.run_id:
            self.inactive = True
            self.terminated = True
            log("No application ID or run ID found, uplink is inactive.")
        self.client = client
        self._lock = threading.Lock()
        self._terminate = False
        self._terminated = False
        self._pending_node_updates = []
        self._updates_failed = 0

    def post_graph(self, graph: FlowDTO):
        """
        Posts the initial graph to the server.
        """
        if self.inactive:
            return
        resp = self.client.request(
            "POST",
            f"/v1/applications/{self.config.application_id}/runs/{self.config.run_id}/graph",
            payload=graph.to_dict(),
        )
        if not resp.ok:
            raise Exception(f"Failed to post graph: {resp.text}")

    def _post_node_update(self, nodes: list[NodeDTO]):
        """
        Posts node updates to the server.
        """
        node_list = [node.to_dict() for node in nodes]
        resp = self.client.request(
            "PATCH",
            f"/v1/applications/{self.config.application_id}/runs/{self.config.run_id}/graph",
            payload=node_list,
        )
        if not resp.ok:
            raise Exception(f"Failed to post node update: {resp.text}")

    def _clear_duplicated_updates(self):
        """
        Clears duplicated updates from the pending queue.
        """
        with self._lock:
            seen = set()
            for i in range(len(self._pending_node_updates) - 1, -1, -1):
                if self._pending_node_updates[i].name in seen:
                    del self._pending_node_updates[i]
                else:
                    seen.add(self._pending_node_updates[i].name)

    def _reenqueue_failed_updates(self, nodes: list[NodeDTO]):
        """
        Re-enqueues failed updates to the pending queue.
        """
        with self._lock:
            self._pending_node_updates = nodes + self._pending_node_updates
            self._clear_duplicated_updates()

    def _pop_node_updates(self, count: int) -> list[NodeDTO]:
        """
        Pops the first `count` node updates from the pending queue.
        """
        with self._lock:
            nodes = self._pending_node_updates[:count]
            self._pending_node_updates = self._pending_node_updates[count:]
        return nodes

    def enqueue_node_update(self, node: NodeDTO):
        """
        Enqueues a node update to be posted to the uplink server.
        """
        if self.inactive:
            return
        if not isinstance(node, NodeDTO):
            raise ValueError(f"Expected NodeDTO, got {type(node)}")
        with self._lock:
            self._pending_node_updates.append(node)
            self._clear_duplicated_updates()

    def run_async(self):
        """
        Starts the uplink client in a separate thread.
        The client will post node updates to until terminated.
        """
        if self.inactive:
            return

        def run():
            while not self._terminate:
                # Sleep
                time.sleep(1)
                # Get pending node updates
                node_updates = None
                with self._lock:
                    node_updates = self._pop_node_updates(NODE_UPDATE_BATCH_SIZE)
                # Post update, if any
                if node_updates:
                    try:
                        self._post_node_update(node_updates)
                    except Exception:
                        with self._lock:
                            # Update failed, keep in pending
                            self._updates_failed += len(node_updates)
                            self._pending_node_updates = node_updates + self._pending_node_updates
                            if self._updates_failed > FAILED_UPDATES_THRESHOLD:
                                # Too many failed updates, terminate
                                self._terminate = True
                else:
                    self._updates_failed = 0

            # Signal termination
            self._terminated = True

        threading.Thread(target=run).start()

    def terminate(self):
        """
        Terminates the uplink client gracefully.
        """
        if self.inactive:
            return

        self._terminate = True
        while not self._terminated:
            time.sleep(0.1)
