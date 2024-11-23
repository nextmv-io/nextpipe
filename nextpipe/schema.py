import base64
import dataclasses
from typing import List

import dataclasses_json


@dataclasses_json.dataclass_json
@dataclasses.dataclass
class NodeUpdateDTO:
    node_id: str
    """The ID of the node to update."""
    state: str
    """The state of the node."""
    run_ids: List[str] = dataclasses.field(default_factory=list)
    """The ID of the associated run (if any)."""


@dataclasses_json.dataclass_json
@dataclasses.dataclass
class NodeDTO:
    id: str
    """The ID of the node."""
    app_id: str
    """The ID of the app this step represents (if any)."""
    step_name: str
    """The name of the step (func)."""
    docs: str
    """The doc string of the step."""
    successors: List[str]
    """The IDs of the nodes that depend on this node."""


@dataclasses_json.dataclass_json
@dataclasses.dataclass
class DAGDTO:
    nodes: List[NodeDTO]
    """The nodes in the DAG."""


def serialize_dag(dag: DAGDTO) -> str:
    """Serialize the DAG for transmission."""
    j_str = dag.to_json(separators=(",", ":"))
    return base64.b64encode(j_str.encode()).decode()


def serialize_node_update(node_update: NodeUpdateDTO) -> str:
    """Serialize the node update for transmission."""
    j_str = node_update.to_json(separators=(",", ":"))
    return base64.b64encode(j_str.encode()).decode()
