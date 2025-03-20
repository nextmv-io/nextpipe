from enum import Enum
from functools import wraps
from typing import Callable

from pathos.multiprocessing import ProcessingPool as Pool

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
        self.state = "pending"
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

    def set_state(self, state: str):
        self.state = state

    def get_state(self):
        return self.state

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
    @wraps(function)
    def wrapper(*args, **kwargs):
        utils.log(f"Entering {function.__name__}")
        ret_val = function(*args, **kwargs)
        utils.log(f"Finished {function.__name__}")
        return ret_val

    wrapper.step = Step(function)
    wrapper.is_step = True
    return wrapper


class Needs:
    def __init__(self, predecessors: list[callable]):
        self.predecessors = predecessors

    def __repr__(self):
        return f"StepNeeds({','.join([p.step.get_id() for p in self.predecessors])})"


def needs(predecessors: list[callable]):
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
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            inputs = [(args, kwargs) for _ in range(repetitions)]
            outputs = []
            with Pool(repetitions) as pool:
                outputs = pool.map(utils.wrap_func(function), inputs)
            return outputs

        wrapper.step.repeat = Repeat(repetitions)

        return wrapper

    return decorator


class Foreach:
    def __init__(self):
        pass

    def __repr__(self):
        return "StepForeach()"


def foreach(f: Callable = None):
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
    def decorator(function):
        function.step.join = Join()
        return function

    return decorator


class App:
    def __init__(
        self,
        app_id: str,
        instance_id: str = "devint",
        input_type: InputType = InputType.JSON,
        parameters: dict[str, any] = None,
    ):
        self.app_id = app_id
        self.instance_id = instance_id
        self.parameters = parameters if parameters else {}
        self.input_type = input_type

    def __repr__(self):
        return f"StepRun({self.app_id}, {self.instance_id}, {self.parameters}, {self.input_type})"


def app(
    app_id: str,
    instance_id: str = "devint",
    parameters: dict[str, any] = None,
    input_type: InputType = InputType.JSON,
):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            utils.log(f"Running {app_id} version {instance_id}")
            return function(*args, **kwargs)

        # We need to make sure that all values of the parameters are converted to strings,
        # as no other types are allowed in the JSON.
        converted_parameters = utils.convert_to_string_values(parameters if parameters else {})

        wrapper.step.app = App(
            app_id=app_id,
            instance_id=instance_id,
            parameters=converted_parameters,
            input_type=input_type,
        )
        wrapper.step.type = StepType.APP

        return wrapper

    return decorator
