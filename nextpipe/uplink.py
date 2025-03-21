import copy
import datetime
import os
import threading
import time
from dataclasses import dataclass

from dataclasses_json import dataclass_json
from nextmv.cloud import Client

from nextpipe.utils import log

FAILED_UPDATES_THRESHOLD = 10

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
class NodeStateDTO:
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
@dataclass_json
class NodeUpdateDTO:
    updated_at: str
    """
    Time of the update as an RFC3339 string.
    """
    nodes: dict[str, NodeStateDTO]
    """
    Nodes and their current state.
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
        self.node_state = {}
        self.changed = False
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

    def enqueue_node_update(self, node_id: str, node_state: NodeStateDTO):
        """
        Enqueues a node update to be posted to the uplink server.
        """
        if self.inactive:
            return
        if not isinstance(node_state, NodeStateDTO):
            raise ValueError(f"Expected NodeStateDTO, got {type(node_state)}")
        with self._lock:
            self.node_state[node_id] = node_state
            self.changed = True

    def _post_node_update(self):
        """
        Posts node updates to the server.
        """
        with self._lock:
            # Get RFC3339 timestamp in UTC
            timestamp = datetime.datetime.now(datetime.UTC).isoformat()
            # Create node update
            node_update = NodeUpdateDTO(
                updated_at=timestamp,
                nodes=copy.deepcopy(self.node_state),
            )
        # Post update
        resp = self.client.request(
            "PATCH",
            f"/v1/applications/{self.config.application_id}/runs/{self.config.run_id}/graph",
            payload=node_update.to_dict(),
        )
        if not resp.ok:
            raise Exception(f"Failed to post node update: {resp.text}")

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
                # Post update, if any
                if self.changed:
                    try:
                        self._post_node_update()
                        with self._lock:
                            self.changed = False
                    except Exception:
                        with self._lock:
                            # Update failed, keep in pending
                            self._updates_failed += 1
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
