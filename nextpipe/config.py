"""
Configuration module for the pipeline.

This module provides configuration classes for controlling pipeline behavior.

Classes
-------
Configuration
    Configuration parameters for pipeline execution.
"""

from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Configuration:
    """
    Configuration for the pipeline.

    This class encapsulates configuration parameters that control how the
    pipeline executes, including parallelization and input limitations.

    Parameters
    ----------
    thread_count : int, default=0
        Number of threads to use for parallel processing.
        If 0, the number of threads is set to the number of available CPUs.
    max_step_inputs : int, default=50
        Maximum number of inputs to a step.
        This is used to avoid accidental combinatorial explosions due to the Cartesian product
        of inputs used when a step has multiple predecessors which are themselves repeated or
        foreach steps.

    Examples
    --------
    >>> from nextpipe import Configuration
    >>> config = Configuration(thread_count=4, max_step_inputs=100)
    >>> config.thread_count
    4
    """

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
