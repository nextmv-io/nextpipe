"""
Decorators for defining pipeline steps and workflows.

This module provides decorators and helper classes for defining pipeline steps
and their relationships in a workflow. These decorators are used to annotate
functions that represent steps in a pipeline, and to define the order in which
they are executed.

Classes
-------
InputType
    Enumeration of input types for application steps.
StepType
    Enumeration of step types.
Step
    Represents a step in a pipeline.
Needs
    Represents dependencies between steps.
Optional
    Represents an optional step condition.
Repeat
    Represents a repeating step.
Foreach
    Represents a step that fans out its output.
Join
    Represents a step that joins multiple inputs.
App
    Represents an external application step.

Functions
---------
step
    Decorator to mark a function as a step in the pipeline.
needs
    Decorator to mark the predecessors of a step.
optional
    Decorator to mark a step as optional.
repeat
    Decorator to make a step be repeated a number of times.
foreach
    Decorator to perform a "fanout" operation.
join
    Decorator to perform a "join" operation.
app
    Decorator to mark a step as a Nextmv Application.
"""

import typing
from collections.abc import Callable
from enum import Enum
from functools import wraps

from nextmv import cloud
from nextmv.deprecated import deprecated

from . import utils


class InputType(Enum):
    """
    Enumeration of input types for application steps.

    This enum defines the possible input types when using the `app` decorator.

    Attributes
    ----------
    JSON : int
        Indicates that the input to the application is in JSON format.
    FILES : int
        Indicates that the input to the application consists of files.
    """

    JSON = 1
    """Input is in JSON format."""
    FILES = 2
    """Input consists of files."""


class StepType(Enum):
    """
    Enumeration of step types.

    This enum defines the possible types of steps in a pipeline.

    Attributes
    ----------
    DEFAULT : int
        Indicates that the step is a regular Python function.
    APP : int
        Indicates that the step runs a Nextmv Application.
    """

    DEFAULT = 1
    """Default step type, indicating a regular Python function."""
    APP = 2
    """Step type for running a Nextmv Application."""


class Step:
    """
    Represents a step in a pipeline.

    A step is a function that has been decorated with the `@step` decorator.
    It can have additional properties set by other decorators like `@needs`,
    `@optional`, `@repeat`, `@foreach`, `@join`, or `@app`.

    Attributes
    ----------
    function : callable
        The function that has been decorated as a step.
    type : StepType
        The type of step (DEFAULT or APP).
    run_ids : list[str]
        The IDs of the runs associated with this step.
    _inputs : dict
        The inputs to the step.
    _output : Any
        The output of the step.
    """

    def __init__(self, function: callable):
        """
        Initialize a Step object.

        Parameters
        ----------
        function : callable
            The function that has been decorated as a step.
        """

        self.function = function
        self.type = StepType.DEFAULT
        self.run_ids = []
        self._inputs = {}
        self._output = None

    def __repr__(self):
        """
        Return a string representation of the step.

        Returns
        -------
        str
            A string representation of the step.
        """

        b = f"Step({self.function.__name__}"
        if hasattr(self, "needs"):
            b += f", {self.needs}"
        if hasattr(self, "repeat"):
            b += f", {self.repeat}"
        if hasattr(self, "app"):
            b += f", {self.app}"
        return b + ")"

    def get_id(self):
        """
        Get the ID of the step.

        Returns
        -------
        str
            The name of the function that has been decorated as a step.
        """

        return self.function.__name__

    def is_needs(self):
        """
        Check if the step has predecessors.

        Returns
        -------
        bool
            True if the step has predecessors, False otherwise.
        """

        return hasattr(self, "needs")

    def skip(self):
        """
        Check if the step should be skipped.

        Returns
        -------
        bool
            True if the step should be skipped, False otherwise.
        """

        return hasattr(self, "optional") and not self.optional.condition(self)

    def is_repeat(self):
        """
        Check if the step should be repeated.

        Returns
        -------
        bool
            True if the step should be repeated, False otherwise.
        """

        return hasattr(self, "repeat")

    def get_repetitions(self):
        """
        Get the number of times the step should be repeated.

        Returns
        -------
        int
            The number of times the step should be repeated, or 1 if the
            step should not be repeated.
        """

        return self.repeat.repetitions if self.is_repeat() else 1

    def is_app(self):
        """
        Check if the step is a Nextmv Application step.

        Returns
        -------
        bool
            True if the step is a Nextmv Application step, False otherwise.
        """

        return self.type == StepType.APP

    def get_app_id(self):
        """
        Get the ID of the Nextmv Application.

        Returns
        -------
        str or None
            The ID of the Nextmv Application, or None if the step is not a
            Nextmv Application step.
        """

        return self.app.app_id if self.is_app() else None

    def set_run_ids(self, run_ids: list[str]):
        """
        Set the run IDs for this step.

        Parameters
        ----------
        run_ids : list[str]
            The run IDs to set.
        """

        self.run_ids = run_ids

    def get_run_ids(self):
        """
        Get the run IDs for this step.

        Returns
        -------
        list[str]
            The run IDs for this step.
        """

        return self.run_ids

    def is_foreach(self):
        """
        Check if the step is a foreach step.

        Returns
        -------
        bool
            True if the step is a foreach step, False otherwise.
        """

        return hasattr(self, "foreach")

    def is_join(self):
        """
        Check if the step is a join step.

        Returns
        -------
        bool
            True if the step is a join step, False otherwise.
        """

        return hasattr(self, "join")


def step(function):
    """
    Decorator to mark a function as a step in the pipeline.

    You can import the `step` decorator directly from `nextpipe`:

    ```python
    from nextpipe import step
    ```

    This is the most basic decorator. This decorator doesn't require any
    parameters or the use of parentheses.

    Example
    -------
    A simple example shows that a step is executed.
    ```
    from nextpipe import FlowSpec, log, step


    class Flow(FlowSpec):
        @step
        def my_step() -> None:
            log("Some code is executed here")


    flow = Flow("DecisionFlow", None)
    flow.run()
    ```
    """

    @wraps(function)
    def wrapper(*args, **kwargs):
        utils.log_internal(f"Entering {function.__name__}")
        ret_val = function(*args, **kwargs)
        utils.log_internal(f"Finished {function.__name__}")
        return ret_val

    wrapper.step = Step(function)
    wrapper.is_step = True
    return wrapper


class Needs:
    """
    Represents dependencies between steps.

    This class is used by the `needs` decorator to specify which steps
    must be executed before a specific step.

    Attributes
    ----------
    predecessors : list[Callable]
        The steps that must be executed before the decorated step.
    """

    def __init__(self, predecessors: list[Callable]):
        """
        Initialize a Needs object.

        Parameters
        ----------
        predecessors : list[Callable]
            The steps that must be executed before the decorated step.
        """

        self.predecessors = predecessors

    def __repr__(self):
        """
        Return a string representation of the needs.

        Returns
        -------
        str
            A string representation of the needs.
        """

        return f"StepNeeds({','.join([p.step.get_id() for p in self.predecessors])})"


def needs(predecessors: list[Callable]):
    """
    Decorator to mark the predecessors of a step.

    You can import the `needs` decorator directly from `nextpipe`:

    ```python
    from nextpipe import needs
    ```

    This is used to determine the order in which the steps are executed. The
    predecessors are the steps that need to be executed before this actual step
    can be run.

    Parameters
    ----------
    predecessors : list[Callable]
        The list of predecessors

    Example
    -------
    In this example steps `step1` and `step2` are executed before `step3`.

    ```
    from nextpipe import FlowSpec, log, needs, step


    class Flow(FlowSpec):
        @step
        def step1() -> None:
            log("Execute step 1")

        @step
        def step2() -> None:
            log("Execute step 2")

        @needs(predecessors=[step1, step2])
        @step
        def step3() -> None:
            log("Execute step 3 after steps 1 and 2")


    flow = Flow("DecisionFlow", None)
    flow.run()
    ```
    """

    def decorator(function):
        function.step.needs = Needs(predecessors)
        return function

    return decorator


class Optional:
    """
    Represents an optional step condition.

    This class is used by the `optional` decorator to specify a condition
    under which a step should be executed.

    Attributes
    ----------
    condition : callable
        A function that takes a step and returns a boolean indicating
        whether the step should be executed or not.
    """

    def __init__(self, condition: callable):
        """
        Initialize an Optional object.

        Parameters
        ----------
        condition : callable
            A function that takes a step and returns a boolean indicating
            whether the step should be executed or not.
        """

        self.condition = condition

    def __repr__(self):
        """
        Return a string representation of the optional condition.

        Returns
        -------
        str
            A string representation of the optional condition.
        """

        return f"StepOnlyIf({self.condition})"


def optional(condition: Callable[[Step], bool]):
    """
    Decorator to mark a step as optional.

    You can import the `optional` decorator directly from `nextpipe`:

    ```python
    from nextpipe import optional
    ```

    This is used to determine whether the step should be executed or not. The
    condition is a callable that takes the step as an argument and returns a
    boolean indicating whether the step should be executed or not. The
    condition is evaluated at runtime, so it can depend on the runtime state of
    the pipeline.

    Parameters
    ----------
    condition : Callable[[Step], bool]
        The condition to evaluate. This is a callable that takes the step
        as an argument and returns a boolean indicating whether the step
        should be executed or not.

    Example
    -------
    In this example the step `step1` is executed given that the condition is
    true.

    ```
    from nextpipe import FlowSpec, log, optional, step


    class Flow(FlowSpec):
        @optional(condition=lambda step: step.get_id() == "step1")
        @step
        def step1() -> None:
            log("Execute optional step 1")


    flow = Flow("DecisionFlow", None)
    flow.run()
    ```
    """

    def decorator(function):
        function.step.optional = Optional(condition)
        return function

    return decorator


class Repeat:
    """
    Represents a repeating step.

    This class is used by the `repeat` decorator to specify how many times
    a step should be repeated.

    Attributes
    ----------
    repetitions : int
        The number of times to repeat the step.
    """

    def __init__(self, repetitions: int):
        """
        Initialize a Repeat object.

        Parameters
        ----------
        repetitions : int
            The number of times to repeat the step.
        """

        self.repetitions = repetitions

    def __repr__(self):
        """
        Return a string representation of the repeat.

        Returns
        -------
        str
            A string representation of the repeat.
        """

        return f"StepRepeat({self.repetitions})"


def repeat(repetitions: int):
    """
    Decorator to make a step be repeated a number of times. The number of
    repetitions determines how many times the step will be run.

    You can import the `repeat` decorator directly from `nextpipe`:

    ```python
    from nextpipe import repeat
    ```

    Parameters
    ----------
    repetitions : int
        The number of times to repeat the step.

    Example
    -------
    In this example the step `step1` is repeated 3 times.

    ```
    from nextpipe import FlowSpec, log, repeat, step


    class Flow(FlowSpec):
        @repeat(repetitions=3)
        @step
        def step1() -> None:
            log("Hello, world.")


    flow = Flow("DecisionFlow", None)
    flow.run()
    ```
    """

    def decorator(function):
        function.step.repeat = Repeat(repetitions)
        return function

    return decorator


class Foreach:
    """
    Represents a step that fans out its output.

    This class is used by the `foreach` decorator to indicate that a step's
    output should be spread across multiple instances of the successor step.
    """

    def __init__(self):
        """Initialize a Foreach object."""
        pass

    def __repr__(self):
        """
        Return a string representation of the foreach operation.

        Returns
        -------
        str
            A string representation of the foreach operation.
        """

        return "StepForeach()"


def foreach(f: Callable = None):
    """
    Decorator to perform a "fanout", which means creating multiple parallel
    steps out of a single step.

    You can import the `foreach` decorator directly from `nextpipe`:

    ```python
    from nextpipe import foreach
    ```

    The function that is decorated should return a list of some sort. Each
    element of the list is consumed as an input by the successor step. When
    using this decorator, use parentheses without any parameters.

    Example
    -------
    In this example the step `step2` is executed for each element in the list
    returned by `step1`. The input to `step2` is the element of the list.

    ```
    from nextpipe import FlowSpec, foreach, log, needs, step


    class Flow(FlowSpec):
        @foreach()
        @step
        def step1() -> list[dict[str, Any]]:
            return [{"input": 1}, {"input": 2}, {"input": 3}]

        @needs(predecessors=[step1])
        @step
        def step2(data: dict) -> None:
            log(data)


    flow = Flow("DecisionFlow", None)
    flow.run()
    ```
    """

    def decorator(function):
        function.step.foreach = Foreach()
        return function

    return decorator


class Join:
    """
    Represents a step that joins multiple inputs.

    This class is used by the `join` decorator to indicate that a step
    should receive the outputs of multiple predecessor steps as a list.
    """

    def __init__(self):
        """Initialize a Join object."""
        pass

    def __repr__(self):
        """
        Return a string representation of the join operation.

        Returns
        -------
        str
            A string representation of the join operation.
        """

        return "StepJoin()"


def join(f: Callable = None):
    """
    Decorator to perform a "join", which means collecting the results of
    multiple parallel predecessor steps into a single step.

    You can import the `join` decorator directly from `nextpipe`:

    ```python
    from nextpipe import join
    ```

    The outputs of the predecessor steps should be received as a list. The
    order of the elements in the list is the same as the order of the
    predecessor steps. Unpack the list to obtain the results and perform
    processing on them as needed. When using this decorator, use parentheses
    without any parameters.

    Example
    -------
    In this example the step `step3` is executed after `step1` and `step2`.
    The input to `step3` is a list containing the outputs of `step1` and
    `step2`.

    ```
    from nextpipe import FlowSpec, join, log, needs, step


    class Flow(FlowSpec):
        @step
        def step1() -> dict[str, Any]:
            return {"input": 1}

        @step
        def step2() -> dict[str, Any]:
            return {"input": 2}

        @join()
        @needs(predecessors=[step1, step2])
        @step
        def step3(data: list[dict[str, Any]]) -> None:
            log(data)


    flow = Flow("DecisionFlow", None)
    flow.run()
    ```
    """

    def decorator(function):
        function.step.join = Join()
        return function

    return decorator


_DEFAULT_POLLING_OPTIONS: cloud.PollingOptions = cloud.PollingOptions()
"""Default polling options to use when polling for a run result.

This variable defines the default polling options used by the `app` decorator
when waiting for the results of a Nextmv Application run. It configures behavior
such as the timeout and backoff strategy.
"""


class App:
    """
    Represents an external application step.

    This class is used by the `app` decorator to specify an external
    Nextmv Application to run as part of the pipeline.

    Attributes
    ----------
    app_id : str
        The ID of the Nextmv Application to run.
    instance_id : str
        The ID of the instance to run.
    options : dict[str, Any]
        The options to pass to the application.
    input_type : InputType
        The type of input to pass to the application (JSON or FILES).
    full_result : bool
        Whether to return the full result including metadata.
    polling_options : Optional[cloud.PollingOptions]
        Options for polling for the results of the app run.
    """

    def __init__(
        self,
        app_id: str,
        instance_id: str = "devint",
        input_type: InputType = InputType.JSON,
        parameters: dict[str, typing.Any] = None,
        options: dict[str, typing.Any] = None,
        full_result: bool = False,
        polling_options: typing.Optional[cloud.PollingOptions] = _DEFAULT_POLLING_OPTIONS,
    ):
        """
        Initialize an App object.

        Parameters
        ----------
        app_id : str
            The ID of the Nextmv Application to run.
        instance_id : str, optional
            The ID of the instance to run, by default "devint".
        input_type : InputType, optional
            The type of input to pass to the application, by default InputType.JSON.
        options : dict[str, Any], optional
            The options to pass to the application, by default None.
        full_result : bool, optional
            Whether to return the full result including metadata, by default False.
        polling_options : Optional[cloud.PollingOptions], optional
            Options for polling for the results of the app run, by default _DEFAULT_POLLING_OPTIONS.
        """

        # Make sure only one of options or parameters is used.
        if parameters and options:
            raise ValueError("You can only use either 'parameters' or 'options', not both.")
        if parameters:
            deprecated(
                "parameters",
                "Use 'options' instead. The 'parameters' argument will be removed in a future release.",
            )
            options = parameters

        self.app_id = app_id
        self.instance_id = instance_id
        self.options = options if options else {}
        self.input_type = input_type
        self.full_result = full_result
        self.polling_options = polling_options

    def __repr__(self):
        """Return a string representation of the app.

        Returns
        -------
        str
            A string representation of the app.
        """

        return f"StepRun({self.app_id}, {self.instance_id}, {self.options}, {self.input_type}, {self.full_result})"


def app(
    app_id: str,
    instance_id: str = "devint",
    parameters: dict[str, typing.Any] = None,
    options: dict[str, typing.Any] = None,
    input_type: InputType = InputType.JSON,
    full_result: bool = False,
    polling_options: typing.Optional[cloud.PollingOptions] = _DEFAULT_POLLING_OPTIONS,
):
    """
    Decorator to mark a step as a Nextmv Application (external application)
    step.

    You can import the `app` decorator directly from `nextpipe`:

    ```python
    from nextpipe import app
    ```

    If this decorator is used, an external application will be run, using the
    specified options. You need to have a valid Nextmv account and
    Application before you can use this decorator. Make sure the
    `NEXTMV_API_KEY` environment variable is set as well.

    Parameters
    ----------
    app_id : str
        The ID of the application to run.
    instance_id : str
        The ID of the instance to run. Default is "devint".
    options : dict[str, Any]
        The options to pass to the application. This is a dictionary of
        parameter names and values. The values must be JSON serializable.
    input_type : InputType
        The type of input to pass to the application. This can be either
        JSON or FILES. Default is JSON.
    full_result : bool
        Whether to return the full result of the application run. If this is
        set to `True`, the full result (with metadata) will be returned. If
        this is set to `False`, only the output of the application will be
        returned.
    polling_options : Optional[cloud.PollingOptions]
        Options for polling for the results of the app run. This is used to
        configure the polling behavior, such as the timeout and backoff
        options. Default (or when undefined) is the predefined options in the
        class itself. Please note that the `.initial_delay` attribute will be
        overridden internally, as a strategy to stagger multiple parallel runs
        and avoid overloading the Platform.

    Example
    -------
    In this example the step `pre_process` is executed first. After
    pre-processing is completed, the result is passed to the `solve` step. This
    step runs a Nextmv Application with the ID `echo`. The result of the
    application run is passed to the final step `post_process`, which
    post-processes the result.
    ```
    from nextpipe import FlowSpec, app, log, needs, step


    class Flow(FlowSpec):
        @step
        def pre_process(input: dict[str, Any]) -> dict[str, Any]:
            log("You can pre-process your data here.")
            return input

        @app(app_id="echo")
        @needs(predecessors=[pre_process])
        @step
        def solve():
            pass

        @needs(predecessors=[solve])
        @step
        def post_process(result: dict[str, Any]) -> dict[str, Any]:
            log("You can post-process your data here.")
            return result


    data = {"foo": "bar"}
    flow = Flow("DecisionFlow", data)
    flow.run()
    log(flow.get_result(flow.post_process))
    ```
    """

    # Make sure only one of options or parameters is used.
    if parameters and options:
        raise ValueError("You can only use either 'parameters' or 'options', not both.")
    if parameters:
        deprecated(
            "parameters",
            "Use 'options' instead. The 'parameters' argument will be removed in a future release.",
        )
        options = parameters

    # We need to make sure that all values of the options are converted to strings, as no
    # other types are allowed in the JSON.
    converted_options = utils.convert_to_string_values(options if options else {})

    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            utils.log_internal(f"Running {app_id} version {instance_id}")
            return function(*args, **kwargs)

        wrapper.step.app = App(
            app_id=app_id,
            instance_id=instance_id,
            options=converted_options,
            input_type=input_type,
            full_result=full_result,
            polling_options=polling_options,
        )
        wrapper.step.type = StepType.APP

        return wrapper

    return decorator
