"""
Module for communicating with the Nextmv platform.

This module provides functionality to communicate pipeline execution status with the
Nextmv platform. It includes data classes for modeling the pipeline graph state and
a client for updating this state in the platform.

Classes
-------
UplinkConfig
    Configuration for the uplink client.
StepDTO
    Data Transfer Object representing a pipeline step.
NodeDTO
    Data Transfer Object representing a node in the pipeline graph.
FlowDTO
    Data Transfer Object representing a flow graph.
FlowUpdateDTO
    Data Transfer Object for updating a flow in the platform.
UplinkClient
    Client for posting graph and node updates to the platform.

Functions
---------
ExcludeIfNone
    Helper function for dataclasses_json to exclude None fields.
"""

import datetime
import os
import threading
import time
from dataclasses import dataclass, field

from dataclasses_json import config, dataclass_json
from nextmv.cloud import Client

from nextpipe.utils import log_internal

FAILED_UPDATES_THRESHOLD = 10
"""Maximum number of consecutive failed updates before termination."""

UPDATE_INTERVAL = 5
"""Interval in seconds between update attempts."""

MAX_DOCS_LENGTH = 1000
"""Maximum length for documentation strings sent to the platform."""

ENV_APP_ID = "NEXTMV_APP_ID"
"""Environment variable name for the application ID."""

ENV_RUN_ID = "NEXTMV_RUN_ID"
"""Environment variable name for the run ID."""


def ExcludeIfNone(value):
    """
    Determine if a value should be excluded from serialization.

    This function is used as a helper for dataclasses_json to exclude None values
    during serialization.

    Parameters
    ----------
    value : Any
        The value to check.

    Returns
    -------
    bool
        True if the value is None and should be excluded, False otherwise.

    Examples
    --------
    >>> ExcludeIfNone(None)
    True
    >>> ExcludeIfNone("something")
    False
    """

    return value is None


@dataclass
class UplinkConfig:
    """
    Configuration for the uplink client.

    Parameters
    ----------
    application_id : str
        The ID of the application.
    run_id : str
        The ID of the run.
    """

    application_id: str
    """The ID of the application."""
    run_id: str
    """The ID of the run."""


@dataclass_json
@dataclass
class StepDTO:
    """
    Data Transfer Object representing a pipeline step.

    A StepDTO represents a step in a pipeline, with its unique identifier,
    dependencies, documentation, and optional associated application.

    Parameters
    ----------
    id : str
        The ID of the step.
    predecessors : list[str]
        The IDs of the nodes that depend on this node.
    docs : str, optional
        The documentation string of the step.
    app_id : str, optional
        The ID of the app this step represents (if any).
    """

    id: str
    """The ID of the step."""
    predecessors: list[str]
    """The IDs of the nodes that depend on this node."""
    docs: str = field(default=None, metadata=config(exclude=ExcludeIfNone))
    """The doc string of the step."""
    app_id: str = field(default=None, metadata=config(exclude=ExcludeIfNone))
    """The ID of the app this step represents (if any)."""


@dataclass_json
@dataclass
class NodeDTO:
    """
    Data Transfer Object representing a node in the pipeline graph.

    A NodeDTO represents a node in the pipeline execution graph, tracking its
    status, dependencies, and relationships.

    Parameters
    ----------
    id : str
        The ID of the node.
    parent_id : str
        Parent step ID.
    predecessor_ids : list[str]
        Predecessor nodes via their IDs.
    status : str
        Status of the node.
    run_id : str, optional
        ID of the associated run, if any.
    """

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
    Data Transfer Object representing a flow graph.

    A FlowDTO represents a flow and more importantly its graph and state,
    including steps and nodes.

    Parameters
    ----------
    steps : list[StepDTO]
        Steps in the flow.
    nodes : list[NodeDTO]
        Nodes and their current state.
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
    Data Transfer Object for updating a flow in the platform.

    A FlowUpdateDTO represents a flow in the platform, containing the pipeline graph
    and the timestamp of the update.

    Parameters
    ----------
    pipeline_graph : FlowDTO
        The graph of the pipeline.
    updated_at : str, optional
        Time of the update as an RFC3339 string. Will be set automatically.
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
    Client for posting graph and node updates to the platform.

    This class provides an interface to communicate with the Nextmv platform,
    posting updates about the pipeline execution status and graph structure.

    Parameters
    ----------
    client : nextmv.cloud.Client
        The Nextmv Cloud client.
    config : UplinkConfig
        The configuration for the uplink client.

    Attributes
    ----------
    config : UplinkConfig
        The configuration for the uplink client.
    inactive : bool
        Whether the client is inactive.
    client : nextmv.cloud.Client
        The Nextmv Cloud client.
    flow : dict or FlowUpdateDTO
        The current flow.
    changed : bool
        Whether the flow has changed and needs to be updated.
    """

    def __init__(self, client: Client, config: UplinkConfig):
        """
        Initialize the UplinkClient.

        Parameters
        ----------
        client : nextmv.cloud.Client
            The Nextmv Cloud client.
        config : UplinkConfig, optional
            The configuration for the uplink client. If None, configuration is
            loaded from environment variables.

        Notes
        -----
        If no application ID or run ID is provided, the client will be marked as
        inactive and will not send any updates to the platform.
        """

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
        Post node updates to the platform.

        This internal method sends the current flow state to the Nextmv platform
        with the current timestamp.

        Raises
        ------
        Exception
            If the request to post the flow update fails.
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
        Post the full flow and its state to the platform.

        This method submits the flow state to be updated in the Nextmv platform.
        It truncates documentation strings if they exceed the maximum length.

        Parameters
        ----------
        flow : FlowUpdateDTO
            The flow to update.

        Raises
        ------
        ValueError
            If the flow is not a FlowUpdateDTO instance.
        """

        if self.inactive or self._terminate:
            return
        if not isinstance(flow, FlowUpdateDTO):
            raise ValueError(f"Expected FlowDTO, got {type(flow)}")
        # Truncate docs to a maximum length
        for step in flow.pipeline_graph.steps:
            if step.docs and len(step.docs) > MAX_DOCS_LENGTH:
                step.docs = step.docs[:MAX_DOCS_LENGTH] + "..."
        # Inform the client about the new flow
        with self._lock:
            self.flow = flow
            self.changed = True

    def run_async(self):
        """
        Start the uplink client in a separate thread.

        This method starts the uplink client in a separate thread, which will
        post node updates to the platform until terminated. Updates are sent
        at regular intervals defined by UPDATE_INTERVAL.

        If the client is inactive or already terminated, this method returns
        without starting a new thread.
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
        Terminate the uplink client gracefully.

        This method stops the uplink client's update thread and sends a final
        update to the platform if there are pending changes. It waits for the
        thread to terminate before returning.

        If the client is inactive, this method returns without taking any action.
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
