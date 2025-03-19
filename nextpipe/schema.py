from dataclasses import dataclass

import nextmv
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class AppRunConfig:
    """Configuration for running an app."""

    options: nextmv.Options = nextmv.Options()
    """Options for running the app."""
    input: dict[str, any] = None
    """Input for the app."""
