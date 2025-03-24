from dataclasses import dataclass, field

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class AppPollingOptions:
    """Options for polling the platform for the status of an app."""

    timeout: float = 1800
    """
    Timeout in seconds for polling the platform.
    This is used for example when waiting for results of an app run.
    """
    max_backoff: float = 30
    """
    Maximum backoff time in seconds.
    """


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
    app_polling: AppPollingOptions = field(default_factory=AppPollingOptions)
    """
    Options for polling the platform for the status of an app.
    """
