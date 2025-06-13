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
from typing import Any, Optional, Union

from dataclasses_json import dataclass_json

from . import utils


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
    value : Any
        Value for the option.

    Examples
    --------
    >>> from nextpipe import AppOption
    >>> option = AppOption(name="threads", value=4)
    """

    name: str
    """Key for the option."""
    value: Any
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
    input : dict[str, Any], optional
        Input data for the app, by default None.
    options : Union[list[AppOption], dict[str, Any]], optional
        Options for running the app, by default empty. These can be provided as a list of
        `AppOption` instances, or, simply as a dictionary of key-value pairs.
    name : str, optional
        Name for the run, by default None.

    Examples
    --------
    >>> from nextpipe import AppRunConfig, AppOption
    >>> config = AppRunConfig(
    ...     input={"data": [1, 2, 3]},
    ...     options={"threads": 4},
    ...     name="my-run"
    ... )
    """

    input: dict[str, Any] = None
    """Input for the app."""
    options: Union[list[AppOption], dict[str, Any]] = field(default_factory=list)
    """Options for running the app."""
    name: Optional[str] = None
    """Name for the run."""

    def get_options(self) -> dict[str, Any]:
        """
        Get options as a dictionary.

        This method converts the `options` attribute to a dictionary if it is provided
        as a list of `AppOption` instances.

        Returns
        -------
        dict[str, Any]
            Dictionary of options.
        """
        options = self.options
        if isinstance(self.options, list):
            options = {option.name: option.value for option in self.options}
        options = utils.convert_to_string_values(options)
        return options
