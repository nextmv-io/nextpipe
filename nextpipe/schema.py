from dataclasses import dataclass, field

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class AppOption:
    """Option for running an app."""

    name: str
    """Key for the option."""
    value: any
    """Value for the option."""


@dataclass_json
@dataclass
class AppRunConfig:
    """Configuration for running an app."""

    input: dict[str, any] = None
    """Input for the app."""
    options: list[AppOption] = field(default_factory=list)
    """Options for running the app."""
