"""
Schema definitions for Nextpipe.

This module contains schema definitions used for pipeline configurations.

Classes
-------
AppOption
    Option for running an app.
AppRunConfig
    Configuration for running an app.
"""

from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class AppOption:
    """
    Option for running an app.

    You can import the `AppOption` class directly from `nextpipe`:

    ```python
    from nextpipe import AppOption
    ```

    This class represents a key-value pair for specifying options when running an app
    in a pipeline.

    Parameters
    ----------
    name : str
        Key for the option.
    value : any
        Value for the option.

    Examples
    --------
    >>> from nextpipe import AppOption
    >>> option = AppOption(name="threads", value=4)
    """

    name: str
    """Key for the option."""
    value: any
    """Value for the option."""


@dataclass_json
@dataclass
class AppRunConfig:
    """
    Configuration for running an app.

    You can import the `AppRunConfig` class directly from `nextpipe`:

    ```python
    from nextpipe import AppRunConfig
    ```

    This class represents a configuration object used when running an app
    in a pipeline, containing input data, options, and an optional name.

    Parameters
    ----------
    input : dict[str, any], optional
        Input data for the app, by default None.
    options : list[AppOption], optional
        Options for running the app, by default an empty list.
    name : str, optional
        Name for the run, by default None.

    Examples
    --------
    >>> from nextpipe import AppRunConfig, AppOption
    >>> config = AppRunConfig(
    ...     input={"data": [1, 2, 3]},
    ...     options=[AppOption(name="threads", value=4)],
    ...     name="my-run"
    ... )
    """

    input: dict[str, any] = None
    """Input for the app."""
    options: list[AppOption] = field(default_factory=list)
    """Options for running the app."""
    name: Optional[str] = None
    """Name for the run."""
