import typing
from collections.abc import Callable
from enum import Enum
from functools import wraps

from nextmv import cloud

from . import utils


class InputType(Enum):
    JSON = 1
    FILES = 2


class StepType(Enum):
    DEFAULT = 1
    APP = 2


class Step:
    def __init__(self, function: callable):
        self.function = function
        self.type = StepType.DEFAULT
        self.run_ids = []
        self._inputs = {}
        self._output = None

    def __repr__(self):
        b = f"Step({self.function.__name__}"
        if hasattr(self, "needs"):
            b += f", {self.needs}"
        if hasattr(self, "repeat"):
            b += f", {self.repeat}"
        if hasattr(self, "app"):
            b += f", {self.app}"
        return b + ")"

    def get_id(self):
        return self.function.__name__

    def is_needs(self):
        return hasattr(self, "needs")

    def skip(self):
        return hasattr(self, "optional") and not self.optional.condition(self)

    def is_repeat(self):
        return hasattr(self, "repeat")

    def get_repetitions(self):
        return self.repeat.repetitions if self.is_repeat() else 1

    def is_app(self):
        return self.type == StepType.APP

    def get_app_id(self):
        return self.app.app_id if self.is_app() else None

    def set_run_ids(self, run_ids: list[str]):
        self.run_ids = run_ids

    def get_run_ids(self):
        return self.run_ids

    def is_foreach(self):
        return hasattr(self, "foreach")

    def is_join(self):
        return hasattr(self, "join")


def step(function):
    """
    Decorator to mark a function as a step in the pipeline. This is the most
    basic decorator. This decorator doesn’t require any parameters or the use
    of parentheses.

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
    def __init__(self, predecessors: list[Callable]):
        self.predecessors = predecessors

    def __repr__(self):
        return f"StepNeeds({','.join([p.step.get_id() for p in self.predecessors])})"


def needs(predecessors: list[Callable]):
    """
    Decorator to mark the predecessors of a step. This is used to
    determine the order in which the steps are executed. The predecessors
    are the steps that need to be executed before this actual step can be
    run.

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
    def __init__(self, condition: callable):
        self.condition = condition

    def __repr__(self):
        return f"StepOnlyIf({self.condition})"


def optional(condition: Callable[[Step], bool]):
    """
    Decorator to mark a step as optional. This is used to determine
    whether the step should be executed or not. The condition is a
    callable that takes the step as an argument and returns a boolean
    indicating whether the step should be executed or not.
    The condition is evaluated at runtime, so it can depend on the
    runtime state of the pipeline.

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
    def __init__(self, repetitions: int):
        self.repetitions = repetitions

    def __repr__(self):
        return f"StepRepeat({self.repetitions})"


def repeat(repetitions: int):
    """
    Decorator to make a step be repeated a number of times. The number of
    repetitions determines how many times the step will be run.

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
    def __init__(self):
        pass

    def __repr__(self):
        return "StepForeach()"


def foreach(f: Callable = None):
    """
    Decorator to perform a "fanout", which means creating multiple parallel
    steps out of a single step. The function that is decorated should return a
    list of some sort. Each element of the list is consumed as an input by the
    successor step. When using this decorator, use parentheses without any
    parameters.

    Parameters
    ----------
    None. Use this decorator with no parameters.

    Example
    -------
    In this example the step `step2` is executed for each element in the list
    returned by `step1`. The input to `step2` is the element of the list.

    ```
    from nextpipe import FlowSpec, foreach, log, needs, step


    class Flow(FlowSpec):
        @foreach()
        @step
        def step1() -> list[dict[str, any]]:
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
    def __init__(self):
        pass

    def __repr__(self):
        return "StepJoin()"


def join(f: Callable = None):
    """
    Decorator to perform a "join", which means collecting the results of
    multiple parallel predecessor steps into a single step. The outputs of the
    predecessor steps should be received as a list. The order of the elements
    in the list is the same as the order of the predecessor steps. Unpack the
    list to obtain the results and perform processing on them as needed. When
    using this decorator, use parentheses without any parameters.

    Parameters
    ----------
    None. Use this decorator with no parameters.

    Example
    -------
    In this example the step `step3` is executed after `step1` and `step2`.
    The input to `step3` is a list containing the outputs of `step1` and
    `step2`.

    ```
    from nextpipe import FlowSpec, join, log, needs, step


    class Flow(FlowSpec):
        @step
        def step1() -> dict[str, any]:
            return {"input": 1}

        @step
        def step2() -> dict[str, any]:
            return {"input": 2}

        @join()
        @needs(predecessors=[step1, step2])
        @step
        def step3(data: list[dict[str, any]]) -> None:
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
"""Default polling options to use when polling for a run result."""


class App:
    def __init__(
        self,
        app_id: str,
        instance_id: str = "devint",
        input_type: InputType = InputType.JSON,
        parameters: dict[str, any] = None,
        full_result: bool = False,
        polling_options: typing.Optional[cloud.PollingOptions] = _DEFAULT_POLLING_OPTIONS,
    ):
        self.app_id = app_id
        self.instance_id = instance_id
        self.parameters = parameters if parameters else {}
        self.input_type = input_type
        self.full_result = full_result
        self.polling_options = polling_options

    def __repr__(self):
        return f"StepRun({self.app_id}, {self.instance_id}, {self.parameters}, {self.input_type}, {self.full_result})"


def app(
    app_id: str,
    instance_id: str = "devint",
    parameters: dict[str, any] = None,
    input_type: InputType = InputType.JSON,
    full_result: bool = False,
    polling_options: typing.Optional[cloud.PollingOptions] = _DEFAULT_POLLING_OPTIONS,
):
    """
    Decorator to mark a step as a Nextmv Application (external application)
    step. If this decorator is used, an external application will be run, using
    the specified parameters. You need to have a valid Nextmv account and
    Application before you can use this decorator. Make sure the
    `NEXTMV_API_KEY` environment variable is set as well.

    Parameters
    ----------
    app_id : str
        The ID of the application to run.
    instance_id : str
       The ID of the instance to run. Default is "devint".
    parameters : dict[str, any]
        The parameters to pass to the application. This is a dictionary of
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
        def pre_process(input: dict[str, any]) -> dict[str, any]:
            log("You can pre-process your data here.")
            return input

        @app(app_id="echo")
        @needs(predecessors=[pre_process])
        @step
        def solve():
            pass

        @needs(predecessors=[solve])
        @step
        def post_process(result: dict[str, any]) -> dict[str, any]:
            log("You can post-process your data here.")
            return result


    data = {"foo": "bar"}
    flow = Flow("DecisionFlow", data)
    flow.run()
    log(flow.get_result(flow.post_process))
    ```
    """

    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            utils.log_internal(f"Running {app_id} version {instance_id}")
            return function(*args, **kwargs)

        # We need to make sure that all values of the parameters are converted to strings,
        # as no other types are allowed in the JSON.
        converted_parameters = utils.convert_to_string_values(parameters if parameters else {})

        wrapper.step.app = App(
            app_id=app_id,
            instance_id=instance_id,
            parameters=converted_parameters,
            input_type=input_type,
            full_result=full_result,
            polling_options=polling_options,
        )
        wrapper.step.type = StepType.APP

        return wrapper

    return decorator
