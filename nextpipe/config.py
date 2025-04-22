from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Configuration:
    """Configuration for the pipeline."""

    thread_count: int = 0
    """
    Number of threads to use for parallel processing.
    If 0, the number of threads is set to the number of available CPUs.
    """
    max_step_inputs: int = 50
    """
    Maximum number of inputs to a step.
    This is used to avoid accidental combinatorial explosions due to the Cartesian product
    of inputs used when a step has multiple predecessors which are themselves repeated or
    foreach steps.
    """
