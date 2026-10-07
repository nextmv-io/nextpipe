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
from typing import Any

import nextmv
from dataclasses_json import config, dataclass_json

from . import utils


def _encode_run_configuration(
    run_configuration: nextmv.RunConfiguration | None,
) -> dict[str, Any] | None:
    """Encode a run configuration for JSON serialization."""

    return run_configuration.to_dict() if run_configuration is not None else None


def _decode_run_configuration(
    run_configuration: dict[str, Any] | nextmv.RunConfiguration | None,
) -> nextmv.RunConfiguration | None:
    """Decode a run configuration from its JSON representation."""

    if run_configuration is None or isinstance(run_configuration, nextmv.RunConfiguration):
        return run_configuration

    return nextmv.RunConfiguration.from_dict(run_configuration)


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
    input : Union[dict[str, Any], str, Any]
        Input data for the app. A JSON app can take a dictionary, multi-file apps can take
        a directory path as a string. Other types will be passed to the underlying Python
        SDK as-is (e.g., nextmv.Input).
    options : Union[list[AppOption], dict[str, Any]], optional
        Options for running the app, by default empty. These can be provided as a list of
        `AppOption` instances, or, simply as a dictionary of key-value pairs.
    name : str, optional
        Name for the run, by default None.
    description : str, optional
        Description for the run, by default None.
    run_configuration : nextmv.RunConfiguration, optional
        The configuration to apply when running the app, by default None. If given, it
        replaces the `run_configuration` of the `app` decorator for this run. Note that
        it replaces it as a whole, i.e., no fields are inherited from the decorator's
        configuration.

    Examples
    --------
    >>> from nextpipe import AppRunConfig, AppOption
    >>> config = AppRunConfig(
    ...     input={"data": [1, 2, 3]},
    ...     options={"threads": 4},
    ...     name="my-run"
    ... )

    The run configuration can be chosen per run, e.g., to pick an execution class
    based on the size of the scenario at hand.

    >>> import nextmv
    >>> from nextpipe import AppRunConfig
    >>> config = AppRunConfig(
    ...     input={"data": [1, 2, 3]},
    ...     run_configuration=nextmv.RunConfiguration(execution_class="8c16gb12h"),
    ... )
    """

    input: dict[str, Any] | str | Any
    """Input for the app. A JSON app can take a dictionary, multi-file apps can take a
    directory path as a string. Other types will be passed to the underlying Python SDK
    as-is (e.g., nextmv.Input)."""
    options: list[AppOption] | dict[str, Any] = field(default_factory=list)
    """Options for running the app."""
    name: str | None = None
    """Name for the run."""
    description: str | None = None
    """Description for the run."""
    run_configuration: nextmv.RunConfiguration | None = field(
        default=None,
        metadata=config(
            encoder=_encode_run_configuration,
            decoder=_decode_run_configuration,
        ),
    )
    """The configuration to apply when running the app. Replaces the `run_configuration`
    of the `app` decorator as a whole, if given."""

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
