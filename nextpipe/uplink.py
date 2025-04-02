import datetime
import os
import threading
import time
from dataclasses import dataclass, field

from dataclasses_json import config, dataclass_json
from nextmv.cloud import Client

from nextpipe.utils import log_internal

FAILED_UPDATES_THRESHOLD = 10
UPDATE_INTERVAL = 5
MAX_DOCS_LENGTH = 1000

ENV_APP_ID = "NEXTMV_APP_ID"
ENV_RUN_ID = "NEXTMV_RUN_ID"


# TODO REMOVE INTERNAL LOG STATEMENTS BEFORE MERGING!


def ExcludeIfNone(value):
    return value is None


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
class NodeDTO:
    id: str
    """
    The ID of the node.
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
    run_id: str = field(default=None, metadata=config(exclude=ExcludeIfNone))
    """
    ID of the associated run, if any.
    """


@dataclass_json
@dataclass
class FlowDTO:
    """
    Represents a flow and more importantly its graph and state.
    """

    steps: list[StepDTO]
    """
    Steps in the flow.
    """
    nodes: list[NodeDTO]
    """
    Nodes and their current state.
    """


@dataclass_json
@dataclass
class FlowUpdateDTO:
    """
    Represents a flow in the platform.
    """

    pipeline_graph: FlowDTO
    """
    The graph of the pipeline.
    """
    updated_at: str = None
    """
    Time of the update as an RFC3339 string. Will be set automatically.
    """


class UplinkClient:
    """
    A client that posts graph and node updates to the platform.
    """

    def __init__(self, client: Client, config: UplinkConfig):
        if config is None:
            # Load config from environment
            config = UplinkConfig(
                application_id=os.environ.get(ENV_APP_ID),
                run_id=os.environ.get(ENV_RUN_ID),
            )
        self.config = config
        self.inactive = False
        if not self.config.application_id or not self.config.run_id:
            self.inactive = True
            self.terminated = True
            log_internal("No application ID or run ID found, uplink is inactive.")
        self.client = client
        self._lock = threading.Lock()
        self.flow = {}
        self.changed = False
        self._terminate = False
        self._terminated = False
        self._updates_failed = 0

    def _post_node_update(self):
        """
        Posts node updates to the platform.
        """
        # Get RFC3339 timestamp in UTC
        timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        self.flow.updated_at = timestamp
        resp = self.client.request(
            "PUT",
            f"/v1/internal/applications/{self.config.application_id}/runs/{self.config.run_id}/flow",
            payload=self.flow.to_dict(),
        )
        if not resp.ok:
            raise Exception(f"Failed to post flow update: {resp.text}")

    def submit_update(self, flow: FlowUpdateDTO):
        """
        Posts the full flow and its state to the platform.
        """
        if self.inactive or self._terminate:
            return
        if not isinstance(flow, FlowUpdateDTO):
            raise ValueError(f"Expected FlowDTO, got {type(flow)}")
        # Truncate docs to a maximum length
        for step in flow.pipeline_graph.steps:
            if len(step.docs) > MAX_DOCS_LENGTH:
                step.docs = step.docs[:MAX_DOCS_LENGTH] + "..."
        # Inform the client about the new flow
        with self._lock:
            self.flow = flow
            self.changed = True

    def run_async(self):
        """
        Starts the uplink client in a separate thread.
        The client will post node updates to the platform until terminated.
        """
        if self.inactive or self._terminate:
            return

        def run():
            while not self._terminate:
                # Post update, if any
                if self.changed:
                    with self._lock:
                        try:
                            self._post_node_update()
                            self.changed = False
                        except Exception as e:
                            # Update failed, keep in pending
                            log_internal(f"Failed to post flow update (#{self._updates_failed}): {e}")
                            self._updates_failed += 1
                            if self._updates_failed > FAILED_UPDATES_THRESHOLD:
                                # Too many failed updates, terminate
                                self._terminate = True
                else:
                    self._updates_failed = 0
                # Sleep
                time.sleep(UPDATE_INTERVAL)

            # Signal termination
            self._terminated = True

        threading.Thread(target=run).start()

    def terminate(self):
        """
        Terminates the uplink client gracefully.
        """
        if self.inactive:
            return

        # Terminate the client
        self._terminate = True
        while not self._terminated:
            time.sleep(0.1)

        # Send final update
        if self._updates_failed > 0:
            log_internal(f"Uplink client is terminating (failed updates: {self._updates_failed})")
        if self.changed:
            try:
                self._post_node_update()
            except Exception:
                pass
